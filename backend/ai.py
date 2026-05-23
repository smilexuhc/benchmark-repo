"""AI 能力：根据角色信息写提示词、根据提示词生成图片。

配置全部来自 backend/.env：
- 写提示词：OpenAI SDK -> ZenMux 的 OpenAI 兼容端点
- 生成图片：OpenAI SDK -> OpenRouter 代理，chat/completions + modalities 出图
未配置时抛出明确错误，不影响其余功能。
"""
import base64
import json
import os

import httpx

# 提示词生成的范例：让模型产出与现有资料库一致的 split-screen 设计稿提示词
PROMPT_SYSTEM = """你是角色设定提示词工程师。根据用户给出的角色信息，输出一段**英文**的 AI 绘图提示词。

要求：
- 固定为「分屏角色设计稿」结构：A split-screen character design sheet, solid white background. [Left 1/3]: extreme close-up ... [Right 2/3]: full-body turnaround (front, side, back) ...
- 结尾点明写实风格与画质，如 Photorealistic, 8k.
- 准确反映角色的时代、人种/类型、性别、年龄、人设造型、身材、特征。
- 只输出提示词本身，不要解释、不要引号、不要 markdown。"""

# 动物角色用：真实世界照片风格，非拟人
ANIMAL_PROMPT_SYSTEM = """你是动物形象设定提示词工程师。根据用户给出的动物信息，输出一段**英文** AI 绘图提示词。

要求：
- 「分屏动物设计稿」结构：A split-screen animal design sheet, solid white background. [Left 1/3]: extreme close-up of the animal's head ... [Right 2/3]: full-body turnaround (front, side, back) ...
- **真实世界照片写实风格**（photorealistic wildlife photography），绝不要插画、卡通、拟人化。
- 准确反映动物种类、外观特征、体型与典型姿态。
- 结尾点明 photorealistic wildlife photography, natural lighting, 8k, ultra-detailed.
- 只输出提示词本身，不要解释、不要引号、不要 markdown。"""

# 幻想生物（龙/凤凰/麒麟等纯异兽）用
CREATURE_PROMPT_SYSTEM = """你是幻想生物设定提示词工程师。根据用户给出的幻想生物信息，输出一段**英文** AI 绘图提示词。

要求：
- 「分屏幻想生物设计稿」结构：A split-screen creature design sheet, solid white background. [Left 1/3]: extreme close-up of the creature's head ... [Right 2/3]: full-body turnaround (front, side, back) ...
- 写实质感的幻想生物（photorealistic fantasy creature, highly detailed），既不是真人、也不是普通现实动物。
- 准确反映生物的种类、外观特征、体型与姿态。
- 结尾点明 photorealistic fantasy creature, cinematic lighting, 8k, ultra-detailed.
- 只输出提示词本身，不要解释、不要引号、不要 markdown。"""

# 拟人化动物（直立、穿衣的动物角色）用
ANTHRO_PROMPT_SYSTEM = """你是拟人化动物角色设定提示词工程师。根据用户给出的角色信息，输出一段**英文** AI 绘图提示词。

要求：
- 「分屏角色设计稿」结构：A split-screen character design sheet, solid white background. [Left 1/3]: extreme close-up of the character's head ... [Right 2/3]: full-body turnaround (front, side, back) ...
- 角色是**拟人化动物**（anthropomorphic animal character）：直立行走、穿着服饰、具人的体态与神情，但保留该动物的头部、毛皮/鳞羽等特征。
- 写实质感（photorealistic, highly detailed），不是卡通扁平。
- 准确反映动物种类、人设、服饰、体型与神态。
- 结尾点明 photorealistic anthropomorphic character, cinematic lighting, 8k, ultra-detailed.
- 只输出提示词本身，不要解释、不要引号、不要 markdown。"""

FIELD_LABELS = {
    "era": "时代",
    "type": "类型",
    "gender": "性别",
    "age": "年龄段",
    "persona": "人设/服装造型",
    "body": "身材",
    "features": "特征",
    "genre": "常见题材",
}


class AIConfigError(RuntimeError):
    """未配置 .env 时抛出。"""


def _translate_error(e: Exception) -> Exception:
    """把接口的常见报错转成中文友好提示。"""
    msg = str(e)
    low = msg.lower()
    if "quota" in low or "402" in msg or "insufficient" in low or "credit" in low:
        return RuntimeError("接口额度不足：请检查 OpenRouter 账户余额 / 额度")
    if "401" in msg or "unauthorized" in low or "api key" in low:
        return RuntimeError("接口鉴权失败：请检查 backend/.env 的 OPENROUTER_API_KEY")
    if "incomplete chunked read" in low or "peer closed" in low:
        return RuntimeError("接口连接中断：可能出图较慢被中途断开，请重试")
    return e


def _api_key() -> str:
    # 容错：去掉可能残留的引号与空白
    key = os.getenv("OPENROUTER_API_KEY", "").strip().strip('"').strip("'").strip()
    if not key:
        raise AIConfigError("尚未配置 OPENROUTER_API_KEY，请在 backend/.env 填写")
    return key


def generate_prompt(
    character: dict, description: str = "", force_system: str = ""
) -> str:
    """根据结构化字段或自由描述，生成英文绘图提示词。

    force_system 非空时强制用该 system（如幻想生物 CREATURE_PROMPT_SYSTEM）。
    """
    client, model = _text_client()

    if description.strip():
        user_msg = "角色自由描述：\n" + description.strip()
    else:
        lines = []
        for k, label in FIELD_LABELS.items():
            val = (character.get(k) or "").strip()
            if val:
                lines.append(f"{label}：{val}")
        if not lines:
            raise ValueError("角色信息为空，无法生成提示词")
        user_msg = "角色信息：\n" + "\n".join(lines)

    # 强制指定 > 按类型选风格 > 默认人物风格
    ctype = (character.get("type") or "").strip()
    if force_system:
        system = force_system
    elif ctype == "动物/宠物":
        system = ANIMAL_PROMPT_SYSTEM
    elif ctype == "动物拟人":
        system = ANTHRO_PROMPT_SYSTEM
    else:
        system = PROMPT_SYSTEM
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e
    return (resp.choices[0].message.content or "").strip()


def generate_image_bytes(
    prompt: str, ref_image_bytes: bytes | None = None, aspect_override: str = ""
) -> bytes:
    """根据提示词生成图片，返回 PNG/JPEG bytes。

    走 OpenRouter（OpenAI 兼容）的 chat/completions，请求带 modalities=["image","text"]，
    生成的图片在 choices[0].message.images[].image_url.url（base64 data URI）。
    传入 ref_image_bytes 时为图生图：把参考图一并作为输入。
    """
    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    key = _api_key()
    model = os.getenv("IMAGE_MODEL", "").strip()
    if not base_url or not model:
        raise AIConfigError(
            "尚未配置 OPENROUTER_BASE_URL / IMAGE_MODEL，请在 backend/.env 填写"
        )
    if not prompt.strip():
        raise ValueError("提示词为空，无法生成图片")

    aspect = aspect_override.strip() or os.getenv("IMAGE_ASPECT_RATIO", "").strip() or "3:2"
    size = os.getenv("IMAGE_SIZE", "").strip() or "2K"

    if ref_image_bytes:
        ref_b64 = base64.b64encode(ref_image_bytes).decode()
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + ref_b64}},
        ]
    else:
        content = prompt

    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=key, timeout=600.0)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            extra_body={
                "modalities": ["image", "text"],
                "image_config": {"aspect_ratio": aspect, "image_size": size},
            },
        )
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e

    data = resp.model_dump()
    try:
        images = data["choices"][0]["message"].get("images") or []
    except (KeyError, IndexError, TypeError):
        images = []
    if not images:
        raise RuntimeError("图片接口未返回图像数据")

    url = (images[0].get("image_url") or {}).get("url", "")
    if url.startswith("data:"):
        raw = base64.b64decode(url.split(",", 1)[1])
    elif url.startswith("http"):
        raw = httpx.get(url, timeout=120).content
    else:
        raise RuntimeError("图片接口返回的数据无法解析")
    return raw


def generate_image(
    prompt: str, ref_image_bytes: bytes | None = None, aspect_override: str = ""
) -> bytes:
    """Backward-compatible wrapper for callers that still use generate_image."""
    return generate_image_bytes(prompt, ref_image_bytes, aspect_override)


EXTRACT_SYSTEM = """你从用户的中文角色描述里提取结构化字段，只输出一个 JSON 对象，不要任何多余文字。
字段（值均用中文，描述未提及的填空字符串 ""）：
- era 时代、type 类型、gender 性别、age 年龄段、genre 常见题材：
  尽量从给定「候选值」中选最贴切的一个；候选里确实没有合适的再自拟简短词。
- persona 人设/服装造型、body 身材、features 特征：简短中文短语。"""

EXTRACT_KEYS = ["era", "type", "gender", "age", "genre", "persona", "body", "features"]


def _parse_json(text: str) -> dict:
    """从模型输出里抽出 JSON 对象，容忍 markdown 围栏。"""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
    s, e = t.find("{"), t.rfind("}")
    if s == -1 or e == -1:
        raise RuntimeError("模型未返回有效 JSON")
    return json.loads(t[s : e + 1])


def extract_fields(description: str, options: dict) -> dict:
    """根据自由描述，解析出结构化字段。options 为各维度的现有候选值。"""
    client, model = _text_client()
    if not description.strip():
        raise ValueError("自由描述为空")
    user_msg = (
        "候选值：\n"
        + json.dumps(options, ensure_ascii=False)
        + "\n\n角色描述：\n"
        + description.strip()
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e

    data = _parse_json(resp.choices[0].message.content or "")
    return {k: str(data.get(k, "") or "").strip() for k in EXTRACT_KEYS}


# ---------- 场景 ----------
SCENE_PROMPT_SYSTEM = """你是场景概念图提示词工程师。根据用户给出的场景信息，输出一段**英文** AI 绘图提示词。

要求：
- 描述一个环境/场景，画面中不出现任何人物（empty scene, no people, no characters）。
- 单张环境图，不要 split-screen、不要多视角。
- 准确反映时代、室内或室外、题材风格、氛围与时段、关键元素。
- 电影感构图，结尾点明 photorealistic, cinematic lighting, ultra-detailed, 8k。
- 只输出提示词本身，不要解释、不要引号、不要 markdown。"""

SCENE_FIELD_LABELS = {
    "name": "场景名称",
    "era": "时代",
    "scene_type": "场景类型",
    "genre": "题材风格",
    "mood": "氛围时段",
    "elements": "关键元素",
}

SCENE_EXTRACT_SYSTEM = """你从用户的中文场景描述里提取结构化字段，只输出一个 JSON 对象，不要任何多余文字。
字段（值均用中文，描述未提及的填空字符串 ""）：
- era 时代、scene_type 场景类型（室内/室外）、genre 题材风格、mood 氛围时段：
  尽量从给定「候选值」中选最贴切的一个；候选里确实没有合适的再自拟简短词。
- name 场景名称、elements 关键元素：简短中文短语。"""

SCENE_EXTRACT_KEYS = ["name", "era", "scene_type", "genre", "mood", "elements"]


def _text_client():
    """返回 (OpenAI client, model)，未配置则抛 AIConfigError。"""
    key = _api_key()
    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip()
    model = os.getenv("TEXT_MODEL", "").strip()
    if not base_url or not model:
        raise AIConfigError("尚未配置 OPENROUTER_BASE_URL / TEXT_MODEL，请在 backend/.env 填写")
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=key, timeout=600.0), model


def generate_scene_prompt(scene: dict, description: str = "") -> str:
    """根据结构化字段或自由描述，生成英文场景提示词。"""
    client, model = _text_client()
    if description.strip():
        user_msg = "场景自由描述：\n" + description.strip()
    else:
        lines = []
        for k, label in SCENE_FIELD_LABELS.items():
            val = (scene.get(k) or "").strip()
            if val:
                lines.append(f"{label}：{val}")
        if not lines:
            raise ValueError("场景信息为空，无法生成提示词")
        user_msg = "场景信息：\n" + "\n".join(lines)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SCENE_PROMPT_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e
    return (resp.choices[0].message.content or "").strip()


def extract_scene_fields(description: str, options: dict) -> dict:
    """根据自由描述，解析出场景结构化字段。"""
    client, model = _text_client()
    if not description.strip():
        raise ValueError("自由描述为空")
    user_msg = (
        "候选值：\n"
        + json.dumps(options, ensure_ascii=False)
        + "\n\n场景描述：\n"
        + description.strip()
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SCENE_EXTRACT_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
        )
    except Exception as e:  # noqa: BLE001
        raise _translate_error(e) from e
    data = _parse_json(resp.choices[0].message.content or "")
    return {k: str(data.get(k, "") or "").strip() for k in SCENE_EXTRACT_KEYS}
