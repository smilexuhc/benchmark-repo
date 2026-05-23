"""一次性脚本：把全部角色提示词结尾的风格片段统一改成真人摄影风格。

人类（亚洲人/欧洲人/非洲人/拉美人/混血）用真人措辞，
非人类（机器人/动物/神话生物）用通用写实措辞。
只替换末句风格片段，角色描述与 split-screen 结构不动。幂等：重复运行结果不变。

用法： python restyle_prompts.py
"""
from db import ASSET_CHARACTER, CHARACTER_FIELDS, all_assets, get_conn, init_db, update_data_fields

HUMAN_TYPES = {"亚洲人", "欧洲人", "非洲人", "拉美人", "混血"}

HUMAN_SUFFIX = (
    "Photorealistic photography of a real person, natural skin texture, "
    "professional studio lighting, 8k, highly detailed."
)
NONHUMAN_SUFFIX = (
    "Photorealistic, ultra-realistic, professional photography, 8k, highly detailed."
)


def restyle(prompt: str, is_human: bool) -> str:
    """砍掉提示词最后一句（风格片段），换上统一的真人摄影后缀。"""
    s = prompt.rstrip()
    if s.endswith("."):
        s = s[:-1].rstrip()
    idx = s.rfind(".")  # 末句风格片段的起点
    base = s[: idx + 1] if idx != -1 else s + "."
    suffix = HUMAN_SUFFIX if is_human else NONHUMAN_SUFFIX
    return base + " " + suffix


def main() -> None:
    init_db()
    conn = get_conn()
    rows = all_assets(conn, ASSET_CHARACTER, CHARACTER_FIELDS)
    changed = 0
    for row in rows:
        cid, ctype, prompt = row["id"], row["type"], row["prompt"]
        if not (prompt or "").strip():
            continue
        new = restyle(prompt, ctype in HUMAN_TYPES)
        if new != prompt:
            update_data_fields(conn, ASSET_CHARACTER, cid, {"prompt": new})
            changed += 1
    conn.commit()
    conn.close()
    print(f"已更新 {changed} / {len(rows)} 条提示词")


if __name__ == "__main__":
    main()
