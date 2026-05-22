"""角色资产库后端服务。

启动： python main.py     （或 uvicorn main:app --reload --port 8000）
前端使用同源 /api 与 /images 路径访问后端。
"""
import io
import os
import re
import zipfile
from typing import List, Optional
from urllib.parse import quote

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))  # 仅加载本项目的 .env

# 后端只访问 ZenMux（国内直连）与 localhost，清掉继承自 shell 的代理，
# 避免 httpx 因 SOCKS 代理报错。
for _p in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
           "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_p, None)

from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ai
from db import (
    CHARACTER_FIELDS, FILTER_FIELDS, SCENE_FIELDS, SCENE_FILTER_FIELDS,
    IMAGES_DIR, get_conn, init_db, now, genre_rank,
)

app = FastAPI(title="角色与场景资产库")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地工具，仅本机访问
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


# ---------- 数据模型 ----------
class CharacterIn(BaseModel):
    era: str = ""
    type: str = ""
    gender: str = ""
    age: str = ""
    persona: str = ""
    body: str = ""
    features: str = ""
    genre: str = ""
    prompt: str = ""
    description: str = ""


class PromptReq(CharacterIn):
    pass


class ImageGenReq(BaseModel):
    prompt: str
    set_cover: bool = False  # 生成后是否把新图设为封面


class ExtractReq(BaseModel):
    description: str = ""


# ---------- 工具函数 ----------
def character_to_dict(row, conn) -> dict:
    d = dict(row)
    imgs = conn.execute(
        "SELECT id, filename, source, created_at FROM images "
        "WHERE character_id = ? ORDER BY id",
        (d["id"],),
    ).fetchall()
    d["images"] = [dict(i) for i in imgs]
    cover = next((i for i in d["images"] if i["id"] == d["cover_image_id"]), None)
    if cover is None and d["images"]:
        cover = d["images"][0]
    d["cover_filename"] = cover["filename"] if cover else None
    return d


def fetch_character(conn, cid: int) -> dict:
    row = conn.execute("SELECT * FROM characters WHERE id = ?", (cid,)).fetchone()
    if row is None:
        raise HTTPException(404, "角色不存在")
    return character_to_dict(row, conn)


# ---------- 筛选选项 ----------
@app.get("/api/options")
def get_options():
    """返回各筛选维度在库中出现过的全部取值。"""
    conn = get_conn()
    out = {}
    for field in FILTER_FIELDS:
        rows = conn.execute(
            f"SELECT DISTINCT {field} AS v FROM characters "
            f"WHERE {field} != '' ORDER BY v"
        ).fetchall()
        out[field] = [r["v"] for r in rows]
    conn.close()
    return out


# ---------- 角色 CRUD ----------
@app.get("/api/characters")
def list_characters(
    era: Optional[str] = None,
    type: Optional[str] = None,
    gender: Optional[str] = None,
    age: Optional[str] = None,
    genre: Optional[str] = None,
    q: Optional[str] = None,
):
    """列表 + 多维筛选 + 关键词搜索。筛选值用英文逗号分隔，多选取并集。"""
    conn = get_conn()
    where, params = [], []
    for field, raw in [
        ("era", era), ("type", type), ("gender", gender),
        ("age", age), ("genre", genre),
    ]:
        if raw:
            vals = [v for v in raw.split(",") if v]
            if vals:
                where.append(f"{field} IN ({','.join('?' * len(vals))})")
                params.extend(vals)
    if q:
        where.append("(persona LIKE ? OR features LIKE ? OR prompt LIKE ?)")
        params.extend([f"%{q}%"] * 3)

    sql = "SELECT * FROM characters"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    result = [character_to_dict(r, conn) for r in rows]
    result.sort(key=lambda x: (genre_rank(x["genre"]), x["id"]))
    conn.close()
    return result


@app.get("/api/characters/{cid}")
def get_character(cid: int):
    conn = get_conn()
    data = fetch_character(conn, cid)
    conn.close()
    return data


@app.post("/api/characters")
def create_character(payload: CharacterIn):
    conn = get_conn()
    cols = CHARACTER_FIELDS + ["created_at", "updated_at"]
    vals = [getattr(payload, f) for f in CHARACTER_FIELDS] + [now(), now()]
    cur = conn.execute(
        f"INSERT INTO characters ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        vals,
    )
    conn.commit()
    data = fetch_character(conn, cur.lastrowid)
    conn.close()
    return data


@app.put("/api/characters/{cid}")
def update_character(cid: int, payload: CharacterIn):
    conn = get_conn()
    fetch_character(conn, cid)  # 404 校验
    sets = ", ".join(f"{f} = ?" for f in CHARACTER_FIELDS)
    vals = [getattr(payload, f) for f in CHARACTER_FIELDS] + [now(), cid]
    conn.execute(f"UPDATE characters SET {sets}, updated_at = ? WHERE id = ?", vals)
    conn.commit()
    data = fetch_character(conn, cid)
    conn.close()
    return data


@app.delete("/api/characters/{cid}")
def delete_character(cid: int):
    conn = get_conn()
    imgs = conn.execute(
        "SELECT filename FROM images WHERE character_id = ?", (cid,)
    ).fetchall()
    conn.execute("DELETE FROM characters WHERE id = ?", (cid,))
    conn.commit()
    conn.close()
    for i in imgs:  # 一并删除磁盘图片
        path = os.path.join(IMAGES_DIR, i["filename"])
        if os.path.exists(path):
            os.remove(path)
    return {"ok": True}


# ---------- 图片 ----------
@app.post("/api/characters/{cid}/images")
async def upload_image(cid: int, file: UploadFile = File(...)):
    """手动上传图片到角色图集。"""
    conn = get_conn()
    fetch_character(conn, cid)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    import uuid
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
        f.write(await file.read())
    img = _attach_image(conn, cid, filename, "uploaded")
    conn.close()
    return img


@app.delete("/api/images/{img_id}")
def delete_image(img_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM images WHERE id = ?", (img_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(404, "图片不存在")
    conn.execute("DELETE FROM images WHERE id = ?", (img_id,))
    conn.execute(
        "UPDATE characters SET cover_image_id = NULL WHERE cover_image_id = ?",
        (img_id,),
    )
    conn.commit()
    conn.close()
    path = os.path.join(IMAGES_DIR, row["filename"])
    if os.path.exists(path):
        os.remove(path)
    return {"ok": True}


@app.put("/api/characters/{cid}/cover/{img_id}")
def set_cover(cid: int, img_id: int):
    conn = get_conn()
    fetch_character(conn, cid)
    conn.execute(
        "UPDATE characters SET cover_image_id = ?, updated_at = ? WHERE id = ?",
        (img_id, now(), cid),
    )
    conn.commit()
    data = fetch_character(conn, cid)
    conn.close()
    return data


def _attach_image(conn, cid: int, filename: str, source: str) -> dict:
    cur = conn.execute(
        "INSERT INTO images (character_id, filename, source, created_at) "
        "VALUES (?, ?, ?, ?)",
        (cid, filename, source, now()),
    )
    # 首张图自动设为封面
    row = conn.execute("SELECT cover_image_id FROM characters WHERE id = ?", (cid,)).fetchone()
    if row and row["cover_image_id"] is None:
        conn.execute(
            "UPDATE characters SET cover_image_id = ? WHERE id = ?",
            (cur.lastrowid, cid),
        )
    conn.commit()
    img = conn.execute(
        "SELECT id, filename, source, created_at FROM images WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(img)


# ---------- AI ----------
@app.post("/api/extract-fields")
def api_extract_fields(payload: ExtractReq):
    """根据自由描述解析出结构化字段（无状态，不落库）。"""
    if not payload.description.strip():
        raise HTTPException(400, "自由描述为空")
    try:
        return ai.extract_fields(payload.description, get_options())
    except ai.AIConfigError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"字段解析失败：{e}")


@app.post("/api/generate-prompt")
def api_generate_prompt(payload: PromptReq):
    """根据结构化字段或自由描述生成英文提示词（无状态，不落库）。"""
    try:
        prompt = ai.generate_prompt(payload.model_dump(), payload.description)
    except ai.AIConfigError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"提示词生成失败：{e}")
    return {"prompt": prompt}


@app.post("/api/characters/{cid}/generate-image")
def api_generate_image(cid: int, payload: ImageGenReq):
    """根据提示词生成图片并加入该角色图集。"""
    conn = get_conn()
    fetch_character(conn, cid)
    try:
        filename = ai.generate_image(payload.prompt)
    except ai.AIConfigError as e:
        conn.close()
        raise HTTPException(400, str(e))
    except ValueError as e:
        conn.close()
        raise HTTPException(400, str(e))
    except Exception as e:
        conn.close()
        raise HTTPException(502, f"图片生成失败：{e}")
    img = _attach_image(conn, cid, filename, "generated")
    if payload.set_cover:
        conn.execute(
            "UPDATE characters SET cover_image_id = ?, updated_at = ? WHERE id = ?",
            (img["id"], now(), cid),
        )
        conn.commit()
    conn.close()
    return img


# ========== 场景资产库 ==========
class SceneIn(BaseModel):
    name: str = ""
    era: str = ""
    scene_type: str = ""
    genre: str = ""
    mood: str = ""
    elements: str = ""
    prompt: str = ""
    description: str = ""


class ScenePromptReq(SceneIn):
    pass


class SceneViewReq(BaseModel):
    view: str  # reverse | multiview


# 多视角图生图：source 标记 -> (英文指令, 宽高比)
VIEW_PROMPTS = {
    "reverse": (
        "The attached image is a reference of a scene environment. Create ONE "
        "wide image divided into 2 equal panels showing this EXACT SAME "
        "environment from two opposite camera directions (shot / reverse-shot): "
        "LEFT panel from one direction, RIGHT panel the reverse view with the "
        "camera turned 180 degrees. Keep architecture, layout, objects, "
        "materials, colors and lighting fully consistent with the reference. "
        "No people. Photorealistic, cinematic lighting, ultra-detailed.",
        "16:9",
    ),
    "multiview": (
        "The attached image is a reference of a scene environment. Create ONE "
        "image arranged as a 2x2 grid of 4 panels showing this EXACT SAME "
        "environment from 4 DISTINCTLY DIFFERENT camera angles, as if the camera "
        "rotates 90 degrees between each panel to face a different direction of "
        "the space: front, right side, the opposite (rear) direction, and left "
        "side. The four panels MUST be clearly different viewpoints, not minor "
        "variations of the same shot. Keep architecture, layout, objects, "
        "materials, colors and lighting consistent with the reference. No "
        "people. Photorealistic, cinematic lighting, ultra-detailed.",
        "1:1",
    ),
}
VIEW_SOURCES = set(VIEW_PROMPTS)


def scene_to_dict(row, conn) -> dict:
    d = dict(row)
    imgs = [
        dict(i)
        for i in conn.execute(
            "SELECT id, filename, source, created_at FROM scene_images "
            "WHERE scene_id = ? ORDER BY id",
            (d["id"],),
        ).fetchall()
    ]
    # 主图集只含普通图；多视角图（正反打/4视图）单独放 views
    d["images"] = [i for i in imgs if i["source"] not in VIEW_SOURCES]
    d["views"] = {}
    for v in VIEW_PROMPTS:
        same = [i for i in imgs if i["source"] == v]
        d["views"][v] = same[-1] if same else None
    cover = next((i for i in d["images"] if i["id"] == d["cover_image_id"]), None)
    if cover is None and d["images"]:
        cover = d["images"][0]
    d["cover_filename"] = cover["filename"] if cover else None
    return d


def fetch_scene(conn, sid: int) -> dict:
    row = conn.execute("SELECT * FROM scenes WHERE id = ?", (sid,)).fetchone()
    if row is None:
        raise HTTPException(404, "场景不存在")
    return scene_to_dict(row, conn)


def _attach_scene_image(conn, sid: int, filename: str, source: str) -> dict:
    cur = conn.execute(
        "INSERT INTO scene_images (scene_id, filename, source, created_at) "
        "VALUES (?, ?, ?, ?)",
        (sid, filename, source, now()),
    )
    row = conn.execute("SELECT cover_image_id FROM scenes WHERE id = ?", (sid,)).fetchone()
    if row and row["cover_image_id"] is None:
        conn.execute(
            "UPDATE scenes SET cover_image_id = ? WHERE id = ?",
            (cur.lastrowid, sid),
        )
    conn.commit()
    img = conn.execute(
        "SELECT id, filename, source, created_at FROM scene_images WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    return dict(img)


@app.get("/api/scenes/options")
def get_scene_options():
    conn = get_conn()
    out = {}
    for field in SCENE_FILTER_FIELDS:
        rows = conn.execute(
            f"SELECT DISTINCT {field} AS v FROM scenes "
            f"WHERE {field} != '' ORDER BY v"
        ).fetchall()
        out[field] = [r["v"] for r in rows]
    conn.close()
    return out


@app.get("/api/scenes")
def list_scenes(
    era: Optional[str] = None,
    scene_type: Optional[str] = None,
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    q: Optional[str] = None,
):
    conn = get_conn()
    where, params = [], []
    for field, raw in [
        ("era", era), ("scene_type", scene_type),
        ("genre", genre), ("mood", mood),
    ]:
        if raw:
            vals = [v for v in raw.split(",") if v]
            if vals:
                where.append(f"{field} IN ({','.join('?' * len(vals))})")
                params.extend(vals)
    if q:
        where.append("(name LIKE ? OR elements LIKE ? OR prompt LIKE ?)")
        params.extend([f"%{q}%"] * 3)
    sql = "SELECT * FROM scenes"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id"
    rows = conn.execute(sql, params).fetchall()
    result = [scene_to_dict(r, conn) for r in rows]
    result.sort(key=lambda x: (genre_rank(x["genre"]), x["id"]))
    conn.close()
    return result


@app.get("/api/scenes/{sid}")
def get_scene(sid: int):
    conn = get_conn()
    data = fetch_scene(conn, sid)
    conn.close()
    return data


@app.post("/api/scenes")
def create_scene(payload: SceneIn):
    conn = get_conn()
    cols = SCENE_FIELDS + ["created_at", "updated_at"]
    vals = [getattr(payload, f) for f in SCENE_FIELDS] + [now(), now()]
    cur = conn.execute(
        f"INSERT INTO scenes ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        vals,
    )
    conn.commit()
    data = fetch_scene(conn, cur.lastrowid)
    conn.close()
    return data


@app.put("/api/scenes/{sid}")
def update_scene(sid: int, payload: SceneIn):
    conn = get_conn()
    fetch_scene(conn, sid)
    sets = ", ".join(f"{f} = ?" for f in SCENE_FIELDS)
    vals = [getattr(payload, f) for f in SCENE_FIELDS] + [now(), sid]
    conn.execute(f"UPDATE scenes SET {sets}, updated_at = ? WHERE id = ?", vals)
    conn.commit()
    data = fetch_scene(conn, sid)
    conn.close()
    return data


@app.delete("/api/scenes/{sid}")
def delete_scene(sid: int):
    conn = get_conn()
    imgs = conn.execute(
        "SELECT filename FROM scene_images WHERE scene_id = ?", (sid,)
    ).fetchall()
    conn.execute("DELETE FROM scenes WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
    for i in imgs:
        path = os.path.join(IMAGES_DIR, i["filename"])
        if os.path.exists(path):
            os.remove(path)
    return {"ok": True}


@app.post("/api/scenes/{sid}/images")
async def upload_scene_image(sid: int, file: UploadFile = File(...)):
    conn = get_conn()
    fetch_scene(conn, sid)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    import uuid
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
        f.write(await file.read())
    img = _attach_scene_image(conn, sid, filename, "uploaded")
    conn.close()
    return img


@app.delete("/api/scene-images/{img_id}")
def delete_scene_image(img_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM scene_images WHERE id = ?", (img_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(404, "图片不存在")
    conn.execute("DELETE FROM scene_images WHERE id = ?", (img_id,))
    conn.execute(
        "UPDATE scenes SET cover_image_id = NULL WHERE cover_image_id = ?",
        (img_id,),
    )
    conn.commit()
    conn.close()
    path = os.path.join(IMAGES_DIR, row["filename"])
    if os.path.exists(path):
        os.remove(path)
    return {"ok": True}


@app.put("/api/scenes/{sid}/cover/{img_id}")
def set_scene_cover(sid: int, img_id: int):
    conn = get_conn()
    fetch_scene(conn, sid)
    conn.execute(
        "UPDATE scenes SET cover_image_id = ?, updated_at = ? WHERE id = ?",
        (img_id, now(), sid),
    )
    conn.commit()
    data = fetch_scene(conn, sid)
    conn.close()
    return data


@app.post("/api/scenes/generate-prompt")
def api_generate_scene_prompt(payload: ScenePromptReq):
    try:
        prompt = ai.generate_scene_prompt(payload.model_dump(), payload.description)
    except ai.AIConfigError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"提示词生成失败：{e}")
    return {"prompt": prompt}


@app.post("/api/scenes/extract-fields")
def api_extract_scene_fields(payload: ExtractReq):
    if not payload.description.strip():
        raise HTTPException(400, "自由描述为空")
    try:
        return ai.extract_scene_fields(payload.description, get_scene_options())
    except ai.AIConfigError as e:
        raise HTTPException(400, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"字段解析失败：{e}")


@app.post("/api/scenes/{sid}/generate-image")
def api_generate_scene_image(sid: int, payload: ImageGenReq):
    conn = get_conn()
    fetch_scene(conn, sid)
    try:
        filename = ai.generate_image(payload.prompt)
    except ai.AIConfigError as e:
        conn.close()
        raise HTTPException(400, str(e))
    except ValueError as e:
        conn.close()
        raise HTTPException(400, str(e))
    except Exception as e:
        conn.close()
        raise HTTPException(502, f"图片生成失败：{e}")
    img = _attach_scene_image(conn, sid, filename, "generated")
    if payload.set_cover:
        conn.execute(
            "UPDATE scenes SET cover_image_id = ?, updated_at = ? WHERE id = ?",
            (img["id"], now(), sid),
        )
        conn.commit()
    conn.close()
    return img


@app.post("/api/scenes/{sid}/generate-view")
def api_generate_scene_view(sid: int, payload: SceneViewReq):
    """图生图：以场景封面图为参考，生成正反打 / 4视图。"""
    if payload.view not in VIEW_PROMPTS:
        raise HTTPException(400, "view 取值应为 reverse 或 multiview")
    conn = get_conn()
    scene = fetch_scene(conn, sid)
    cover = scene.get("cover_filename")
    if not cover:
        conn.close()
        raise HTTPException(400, "该场景还没有图片，请先生成场景图")
    ref_path = os.path.join(IMAGES_DIR, cover)
    if not os.path.exists(ref_path):
        conn.close()
        raise HTTPException(400, "场景封面图文件缺失")

    prompt, aspect = VIEW_PROMPTS[payload.view]
    try:
        filename = ai.generate_image(prompt, ref_image_path=ref_path, aspect_override=aspect)
    except ai.AIConfigError as e:
        conn.close()
        raise HTTPException(400, str(e))
    except (ValueError, FileNotFoundError) as e:
        conn.close()
        raise HTTPException(400, str(e))
    except Exception as e:
        conn.close()
        raise HTTPException(502, f"图片生成失败：{e}")

    # 同类旧图先删（再点即替换）
    old = conn.execute(
        "SELECT filename FROM scene_images WHERE scene_id = ? AND source = ?",
        (sid, payload.view),
    ).fetchall()
    conn.execute(
        "DELETE FROM scene_images WHERE scene_id = ? AND source = ?",
        (sid, payload.view),
    )
    conn.commit()
    for o in old:
        p = os.path.join(IMAGES_DIR, o["filename"])
        if os.path.exists(p):
            os.remove(p)
    img = _attach_scene_image(conn, sid, filename, payload.view)
    conn.close()
    return img


# ========== 导出（ZIP：Excel + 原图文件夹） ==========
CHAR_EXPORT_COLS = [
    ("era", "时代"), ("type", "类型"), ("gender", "性别"), ("age", "年龄段"),
    ("persona", "人设"), ("body", "身材"), ("features", "特征"),
    ("genre", "常见题材"), ("prompt", "人物生成提示词"),
    ("__imgname__", "原图文件名"), ("__image__", "图片"),
]
SCENE_EXPORT_COLS = [
    ("name", "场景名称"), ("era", "时代"), ("scene_type", "场景类型"),
    ("genre", "题材风格"), ("mood", "氛围时段"), ("elements", "关键元素"),
    ("prompt", "场景生成提示词"),
    ("__imgname__", "原图文件名"), ("__image__", "图片"),
]


def _compress_image(path: str):
    """读封面图转 JPEG（保持原分辨率，仅压缩），返回 openpyxl 图片对象。"""
    from PIL import Image as PILImage
    from openpyxl.drawing.image import Image as XLImage

    im = PILImage.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return XLImage(buf)


def _sanitize(name: str) -> str:
    """净化字符串作文件名。"""
    s = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "_", (name or "").strip())
    return (s or "未命名")[:60]


def _export_filenames(rows: list, name_key: str) -> dict:
    """为有封面图的行分配导出文件名（按名称、去重）。返回 {row_id: 文件名}。"""
    used: set = set()
    out: dict = {}
    for row in rows:
        if not row.get("cover_filename"):
            continue
        base = _sanitize(row.get(name_key) or "")
        ext = os.path.splitext(row["cover_filename"])[1] or ".png"
        name, i = base + ext, 2
        while name in used:
            name = f"{base}_{i}{ext}"
            i += 1
        used.add(name)
        out[row["id"]] = name
    return out


def _build_xlsx(rows: list, columns: list, title: str, imgname_map: dict) -> bytes:
    """生成 xlsx：文字列 + 原图文件名 + 嵌入封面图（JPEG，原分辨率）。"""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = title
    img_col = None
    for ci, (key, label) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=ci, value=label)
        cell.font = Font(bold=True)
        letter = get_column_letter(ci)
        if key == "__image__":
            img_col = ci
            ws.column_dimensions[letter].width = 52
        elif key == "prompt":
            ws.column_dimensions[letter].width = 62
        elif key == "__imgname__":
            ws.column_dimensions[letter].width = 22
        else:
            ws.column_dimensions[letter].width = 16

    for ri, row in enumerate(rows, start=2):
        for ci, (key, label) in enumerate(columns, start=1):
            if key == "__image__":
                continue
            if key == "__imgname__":
                val = imgname_map.get(row["id"], "")
            else:
                val = row.get(key, "") or ""
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        placed = False
        if img_col:
            fn = row.get("cover_filename")
            if fn:
                path = os.path.join(IMAGES_DIR, fn)
                if os.path.exists(path):
                    try:
                        xi = _compress_image(path)
                        ratio = (xi.height / xi.width) if xi.width else 0.66
                        xi.width = 360
                        xi.height = int(360 * ratio)
                        ws.add_image(xi, f"{get_column_letter(img_col)}{ri}")
                        ws.row_dimensions[ri].height = xi.height * 0.75
                        placed = True
                    except Exception:
                        placed = False
            if not placed:
                ws.cell(row=ri, column=img_col, value="（无图）")
                ws.row_dimensions[ri].height = 56

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _build_export_zip(
    rows: list, columns: list, title: str, name_key: str
) -> bytes:
    """打包 ZIP：title.xlsx（嵌压缩图）+ 原图/ 文件夹（PNG 原图）。"""
    imgname_map = _export_filenames(rows, name_key)
    xlsx = _build_xlsx(rows, columns, title, imgname_map)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{title}.xlsx", xlsx)
        for row in rows:
            name = imgname_map.get(row["id"])
            if not name:
                continue
            path = os.path.join(IMAGES_DIR, row["cover_filename"])
            if os.path.exists(path):
                zf.write(path, f"原图/{name}")
    return buf.getvalue()


def _zip_response(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@app.get("/api/export/characters")
def export_characters(
    era: Optional[str] = None,
    type: Optional[str] = None,
    gender: Optional[str] = None,
    age: Optional[str] = None,
    genre: Optional[str] = None,
    q: Optional[str] = None,
):
    rows = list_characters(era=era, type=type, gender=gender, age=age, genre=genre, q=q)
    data = _build_export_zip(rows, CHAR_EXPORT_COLS, "角色资产库", "persona")
    return _zip_response(data, "角色资产库.zip")


@app.get("/api/export/scenes")
def export_scenes(
    era: Optional[str] = None,
    scene_type: Optional[str] = None,
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    q: Optional[str] = None,
):
    rows = list_scenes(era=era, scene_type=scene_type, genre=genre, mood=mood, q=q)
    data = _build_export_zip(rows, SCENE_EXPORT_COLS, "场景资产库", "name")
    return _zip_response(data, "场景资产库.zip")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "ai_configured": bool(os.getenv("OPENROUTER_API_KEY")),
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "1") not in ("0", "false", "False")
    uvicorn.run("main:app", host=host, port=port, reload=reload)
