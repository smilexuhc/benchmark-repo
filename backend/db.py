"""Postgres/Neon data access for the benchmark asset library.

The app stores unstable business fields in JSONB so the internal experiment can
keep evolving without running a migration for every new form field.
"""
import json
import os
from datetime import datetime
from typing import Iterable

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required for Neon/Postgres storage")

POOL = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=10,
    kwargs={"row_factory": dict_row},
    check=ConnectionPool.check_connection,
)

ASSET_CHARACTER = "character"
ASSET_SCENE = "scene"
ASSET_AUDIO = "audio"
ASSET_PROP = "prop"
MEDIA_IMAGE = "image"
MEDIA_AUDIO = "audio"
MEDIA_ASSET_KINDS = {ASSET_CHARACTER, ASSET_SCENE, ASSET_AUDIO, ASSET_PROP}

# 角色的结构化字段（与 CSV 列、前端筛选一一对应）
CHARACTER_FIELDS = [
    "era",       # 时代
    "type",      # 类型
    "gender",    # 性别
    "age",       # 年龄段
    "persona",   # 人设（服装造型风格）
    "body",      # 身材
    "features",  # 特征
    "genre",     # 常见题材
    "prompt",    # 人物生成提示词
    "description",  # 自由描述（给 AI 写提示词用）
]

FILTER_FIELDS = ["era", "type", "gender", "age", "genre"]

SCENE_FIELDS = [
    "name",        # 场景名称
    "era",         # 时代
    "scene_type",  # 场景类型（室内/室外）
    "genre",       # 题材风格
    "mood",        # 氛围时段
    "elements",    # 关键元素
    "prompt",      # 场景生成提示词
    "description", # 自由描述
]

SCENE_FILTER_FIELDS = ["era", "scene_type", "genre", "mood"]

VIDEO_BENCHMARK_FIELDS = [
    "shot_type",
    "task_type",
    "question_type",
    "scene",
    "screen_size",
    "character_image_asset",
    "scene_image_asset",
    "prop_image_asset",
    "audio_input",
    "video_input",
    "text_prompt",
    "judging_criteria",
    "video_output",
    "score",
    "character_image_id",
    "scene_image_id",
    "prop_image_id",
    "audio_input_id",
]

VIDEO_BENCHMARK_FILTER_FIELDS = [
    "shot_type",
    "task_type",
    "question_type",
    "scene",
    "screen_size",
]

VIDEO_BENCHMARK_SEARCH_FIELDS = [
    "shot_type",
    "task_type",
    "question_type",
    "scene",
    "screen_size",
    "text_prompt",
    "judging_criteria",
    "video_output",
]

VIDEO_BENCHMARK_MEDIA_ROLES = {
    "character_image": {
        "id_field": "character_image_id",
        "snapshot_field": "character_image_asset",
        "media_type": MEDIA_IMAGE,
        "asset_kind": ASSET_CHARACTER,
    },
    "scene_image": {
        "id_field": "scene_image_id",
        "snapshot_field": "scene_image_asset",
        "media_type": MEDIA_IMAGE,
        "asset_kind": ASSET_SCENE,
    },
    "prop_image": {
        "id_field": "prop_image_id",
        "snapshot_field": "prop_image_asset",
        "media_type": MEDIA_IMAGE,
        "asset_kind": None,
    },
    "audio_input": {
        "id_field": "audio_input_id",
        "snapshot_field": "audio_input",
        "media_type": MEDIA_AUDIO,
        "asset_kind": None,
    },
}

GENRE_ORDER = [
    "现代-职场", "现代-校园", "现代-都市", "军事战争",
    "中国古代", "欧洲中世纪", "近代/民国",
    "中国玄幻", "西方玄幻",
    "科幻-星际", "科幻-赛博朋克", "末世废土",
]

TYPE_ORDER = [
    "亚洲人", "欧洲人", "非洲人", "拉美人", "混血",
    "动物/宠物", "动物拟人",
    "机器人", "神话生物",
]

AGE_ORDER = ["婴儿", "儿童", "青少年", "青年", "成年", "中年", "老年", "N/A"]

_FIELD_ORDER = {"type": TYPE_ORDER, "genre": GENRE_ORDER, "age": AGE_ORDER}


def genre_rank(genre: str) -> int:
    try:
        return GENRE_ORDER.index(genre or "")
    except ValueError:
        return len(GENRE_ORDER)


def order_filter_values(field: str, values: list) -> list:
    order = _FIELD_ORDER.get(field)
    if not order:
        return sorted(values)
    rank = {v: i for i, v in enumerate(order)}
    return sorted(values, key=lambda v: (rank.get(v, len(order)), v))


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class PooledConnection:
    def __init__(self):
        self._ctx = POOL.connection()
        self._conn = self._ctx.__enter__()
        self._closed = False

    def __enter__(self):
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        self.close(exc_type, exc, tb)

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self, exc_type=None, exc=None, tb=None):
        if not self._closed:
            self._ctx.__exit__(exc_type, exc, tb)
            self._closed = True


def get_conn():
    """Yield a pooled psycopg connection.

    Existing scripts use ``with get_conn()`` and FastAPI routes close
    connections explicitly less often now that pool lifecycle is handled here.
    """
    return PooledConnection()


def init_db() -> None:
    from migrate_schema import apply_migrations

    apply_migrations()


def _json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def _normalize_time(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat(timespec="seconds")
    return str(value)


def _asset_row_to_dict(row: dict, fields: list[str]) -> dict:
    data = row.get("data") or {}
    out = {field: str(data.get(field, "") or "") for field in fields}
    out.update(
        {
            "id": row["id"],
            "cover_image_id": row.get("cover_image_id"),
            "created_at": _normalize_time(row.get("created_at")),
            "updated_at": _normalize_time(row.get("updated_at")),
        }
    )
    return out


def _image_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "filename": row["object_key"],
        "source": row["source"],
        "media_type": row.get("media_type", MEDIA_IMAGE),
        "created_at": _normalize_time(row.get("created_at")),
    }


def _media_to_dict(row: dict | None) -> dict | None:
    if row is None:
        return None
    object_key = row.get("object_key") or ""
    data = row.get("data") or {}
    title = (
        data.get("title")
        or data.get("persona")
        or data.get("name")
        or object_key.split("/")[-1]
        or object_key
    )
    subtitle_parts = [
        value for value in [
            data.get("era"),
            data.get("type"),
            data.get("scene_type"),
            data.get("genre"),
            row.get("source"),
        ] if value
    ]
    return {
        "id": row["id"],
        "asset_id": row["asset_id"],
        "asset_kind": row["asset_kind"],
        "object_key": object_key,
        "filename": object_key,
        "title": str(title),
        "subtitle": " · ".join(str(part) for part in subtitle_parts),
        "source": row["source"],
        "media_type": row.get("media_type", MEDIA_IMAGE),
        "url": f"/images/{object_key}" if object_key else "",
        "thumbnail_url": f"/images/{object_key}" if object_key and row.get("media_type", MEDIA_IMAGE) == MEDIA_IMAGE else "",
        "created_at": _normalize_time(row.get("created_at")),
    }


def image_key(row: dict) -> str:
    return row["object_key"] if "object_key" in row else row["filename"]


def list_images(conn, asset_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, object_key, source, media_type, created_at
        FROM asset_images
        WHERE asset_id = %s AND media_type = %s
        ORDER BY id
        """,
        (asset_id, MEDIA_IMAGE),
    ).fetchall()
    return [_image_to_dict(row) for row in rows]


def get_media_asset(conn, media_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT
            i.id, i.asset_id, a.kind AS asset_kind, i.object_key,
            i.source, i.media_type, i.created_at, a.data
        FROM asset_images i
        JOIN assets a ON a.id = i.asset_id
        WHERE i.id = %s
        """,
        (media_id,),
    ).fetchone()
    return _media_to_dict(row)


def list_media_assets(
    conn,
    *,
    media_type: str | None,
    asset_kind: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> dict:
    where = ["TRUE"]
    params: list = []
    if media_type:
        where.append("i.media_type = %s")
        params.append(media_type)
    if asset_kind:
        where.append("a.kind = %s")
        params.append(asset_kind)
    if q:
        where.append(
            """
            (
                i.object_key ILIKE %s
                OR i.source ILIKE %s
                OR a.kind ILIKE %s
                OR a.data::text ILIKE %s
            )
            """
        )
        params.extend([f"%{q}%"] * 4)

    where_sql = " AND ".join(where)
    total_row = conn.execute(
        f"""
        SELECT COUNT(*) AS c
        FROM asset_images i
        JOIN assets a ON a.id = i.asset_id
        WHERE {where_sql}
        """,
        params,
    ).fetchone()
    rows = conn.execute(
        f"""
        SELECT
            i.id, i.asset_id, a.kind AS asset_kind, i.object_key,
            i.source, i.media_type, i.created_at, a.data
        FROM asset_images i
        JOIN assets a ON a.id = i.asset_id
        WHERE {where_sql}
        ORDER BY i.id DESC
        LIMIT %s OFFSET %s
        """,
        [*params, limit, offset],
    ).fetchall()
    return {
        "items": [_media_to_dict(row) for row in rows],
        "total": int(total_row["c"]),
        "limit": limit,
        "offset": offset,
    }


def _asset_dict_with_images(row: dict, fields: list[str], imgs: list[dict], view_sources: set[str] | None = None) -> dict:
    d = _asset_row_to_dict(row, fields)
    view_sources = view_sources or set()
    if view_sources:
        d["images"] = [i for i in imgs if i["source"] not in view_sources]
        d["views"] = {
            source: next((i for i in reversed(imgs) if i["source"] == source), None)
            for source in sorted(view_sources)
        }
    else:
        d["images"] = imgs
    cover = next((i for i in d["images"] if i["id"] == d["cover_image_id"]), None)
    if cover is None and d["images"]:
        cover = d["images"][0]
    d["cover_filename"] = cover["filename"] if cover else None
    return d


def asset_to_dict(conn, row: dict, fields: list[str], view_sources: set[str] | None = None) -> dict:
    return _asset_dict_with_images(row, fields, list_images(conn, row["id"]), view_sources)


def get_asset(conn, kind: str, asset_id: int) -> dict | None:
    return conn.execute(
        "SELECT * FROM assets WHERE kind = %s AND id = %s",
        (kind, asset_id),
    ).fetchone()


def create_asset(conn, kind: str, fields: list[str], payload) -> int:
    data = {field: getattr(payload, field, "") for field in fields}
    row = conn.execute(
        "INSERT INTO assets (kind, data, created_at, updated_at) VALUES (%s, %s::jsonb, %s, %s) RETURNING id",
        (kind, _json(data), now(), now()),
    ).fetchone()
    return row["id"]


def create_media_asset(conn, kind: str, media_type: str, object_key: str, title: str, source: str = "uploaded") -> dict:
    if kind not in MEDIA_ASSET_KINDS:
        raise ValueError("invalid_asset_kind")
    if media_type not in {MEDIA_IMAGE, MEDIA_AUDIO}:
        raise ValueError("invalid_media_type")
    if media_type == MEDIA_AUDIO and kind != ASSET_AUDIO:
        raise ValueError("audio_requires_audio_kind")
    if media_type == MEDIA_IMAGE and kind == ASSET_AUDIO:
        raise ValueError("image_cannot_use_audio_kind")
    asset_id = insert_data(conn, kind, {"title": title, "name": title})
    row = conn.execute(
        """
        INSERT INTO asset_images (asset_id, object_key, source, media_type, created_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (asset_id, object_key, source, media_type, now()),
    ).fetchone()
    return get_media_asset(conn, row["id"])


def update_asset(conn, kind: str, asset_id: int, fields: list[str], payload) -> None:
    data = {field: getattr(payload, field, "") for field in fields}
    conn.execute(
        "UPDATE assets SET data = %s::jsonb, updated_at = %s WHERE kind = %s AND id = %s",
        (_json(data), now(), kind, asset_id),
    )


def delete_asset(conn, kind: str, asset_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT i.object_key
        FROM asset_images i
        JOIN assets a ON a.id = i.asset_id
        WHERE a.kind = %s AND a.id = %s
        """,
        (kind, asset_id),
    ).fetchall()
    conn.execute("DELETE FROM assets WHERE kind = %s AND id = %s", (kind, asset_id))
    return [r["object_key"] for r in rows]


def attach_image(conn, asset_id: int, object_key: str, source: str) -> dict:
    row = conn.execute(
        """
        INSERT INTO asset_images (asset_id, object_key, source, media_type, created_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, object_key, source, media_type, created_at
        """,
        (asset_id, object_key, source, MEDIA_IMAGE, now()),
    ).fetchone()
    cover = conn.execute(
        "SELECT cover_image_id FROM assets WHERE id = %s",
        (asset_id,),
    ).fetchone()
    if cover and cover["cover_image_id"] is None:
        conn.execute("UPDATE assets SET cover_image_id = %s WHERE id = %s", (row["id"], asset_id))
    return _image_to_dict(row)


def delete_image(conn, image_id: int, asset_kind: str | None = None) -> str | None:
    if asset_kind:
        row = conn.execute(
            """
            SELECT i.id, i.object_key
            FROM asset_images i
            JOIN assets a ON a.id = i.asset_id
            WHERE i.id = %s AND a.kind = %s
            """,
            (image_id, asset_kind),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, object_key FROM asset_images WHERE id = %s",
            (image_id,),
        ).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM asset_images WHERE id = %s", (image_id,))
    conn.execute(
        "UPDATE assets SET cover_image_id = NULL WHERE cover_image_id = %s",
        (image_id,),
    )
    return row["object_key"]


def set_cover(conn, kind: str, asset_id: int, image_id: int) -> None:
    row = conn.execute(
        """
        SELECT i.id
        FROM asset_images i
        JOIN assets a ON a.id = i.asset_id
        WHERE i.id = %s AND i.asset_id = %s AND a.kind = %s
        """,
        (image_id, asset_id, kind),
    ).fetchone()
    if row is None:
        raise KeyError("image_not_found")
    conn.execute(
        "UPDATE assets SET cover_image_id = %s, updated_at = %s WHERE kind = %s AND id = %s",
        (image_id, now(), kind, asset_id),
    )


def replace_source_images(conn, asset_id: int, source: str) -> list[str]:
    rows = conn.execute(
        "SELECT object_key FROM asset_images WHERE asset_id = %s AND source = %s",
        (asset_id, source),
    ).fetchall()
    conn.execute(
        "DELETE FROM asset_images WHERE asset_id = %s AND source = %s",
        (asset_id, source),
    )
    return [r["object_key"] for r in rows]


def _filters_sql(kind: str, filters: Iterable[tuple[str, str | None]], q: str | None, q_fields: list[str]):
    where = ["kind = %s"]
    params: list = [kind]
    for field, raw in filters:
        if raw:
            vals = [v for v in raw.split(",") if v]
            if vals:
                where.append(f"data->>%s = ANY(%s)")
                params.extend([field, vals])
    if q:
        clauses = [f"data->>%s ILIKE %s" for _ in q_fields]
        where.append("(" + " OR ".join(clauses) + ")")
        for field in q_fields:
            params.extend([field, f"%{q}%"])
    return " AND ".join(where), params


def list_assets(
    conn,
    kind: str,
    fields: list[str],
    filters: list[tuple[str, str | None]],
    q: str | None,
    q_fields: list[str],
    view_sources: set[str] | None = None,
) -> list[dict]:
    where, params = _filters_sql(kind, filters, q, q_fields)
    rows = conn.execute(f"SELECT * FROM assets WHERE {where} ORDER BY id", params).fetchall()
    if not rows:
        return []

    asset_ids = [row["id"] for row in rows]
    image_rows = conn.execute(
        """
        SELECT id, asset_id, object_key, source, created_at
        FROM asset_images
        WHERE asset_id = ANY(%s)
        ORDER BY asset_id, id
        """,
        (asset_ids,),
    ).fetchall()
    images_by_asset = {asset_id: [] for asset_id in asset_ids}
    for image in image_rows:
        images_by_asset[image["asset_id"]].append(_image_to_dict(image))

    return [
        _asset_dict_with_images(row, fields, images_by_asset.get(row["id"], []), view_sources)
        for row in rows
    ]


def get_options(conn, kind: str, fields: list[str]) -> dict:
    out = {}
    for field in fields:
        rows = conn.execute(
            """
            SELECT DISTINCT data->>%s AS value
            FROM assets
            WHERE kind = %s AND COALESCE(data->>%s, '') != ''
            """,
            (field, kind, field),
        ).fetchall()
        out[field] = order_filter_values(field, [r["value"] for r in rows])
    return out


def count_assets(conn, kind: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM assets WHERE kind = %s", (kind,)).fetchone()
    return int(row["c"])


def clear_assets(conn, kind: str) -> None:
    conn.execute("DELETE FROM assets WHERE kind = %s", (kind,))


def find_assets_by_field(conn, kind: str, field: str, fields: list[str]) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT * FROM assets WHERE kind = %s AND COALESCE(data->>%s, '') != ''",
        (kind, field),
    ).fetchall()
    return {row["data"].get(field, ""): _asset_row_to_dict(row, fields) for row in rows}


def find_asset_summaries_by_field(conn, kind: str, field: str) -> dict[str, tuple[int, str]]:
    rows = conn.execute(
        "SELECT id, data FROM assets WHERE kind = %s AND COALESCE(data->>%s, '') != ''",
        (kind, field),
    ).fetchall()
    return {
        row["data"].get(field, ""): (row["id"], row["data"].get("prompt", "") or "")
        for row in rows
    }


def insert_data(conn, kind: str, data: dict) -> int:
    row = conn.execute(
        "INSERT INTO assets (kind, data, created_at, updated_at) VALUES (%s, %s::jsonb, %s, %s) RETURNING id",
        (kind, _json(data), now(), now()),
    ).fetchone()
    return row["id"]


def update_data_fields(conn, kind: str, asset_id: int, changes: dict) -> None:
    row = get_asset(conn, kind, asset_id)
    if row is None:
        return
    data = dict(row.get("data") or {})
    data.update(changes)
    conn.execute(
        "UPDATE assets SET data = %s::jsonb, updated_at = %s WHERE kind = %s AND id = %s",
        (_json(data), now(), kind, asset_id),
    )


def all_assets(conn, kind: str, fields: list[str]) -> list[dict]:
    rows = conn.execute("SELECT * FROM assets WHERE kind = %s ORDER BY id", (kind,)).fetchall()
    return [_asset_row_to_dict(row, fields) for row in rows]


def _media_object_key(
    conn,
    media_id: int | None,
    *,
    media_type: str,
    asset_kind: str | None = None,
) -> str:
    if media_id is None:
        return ""
    media = get_media_asset(conn, media_id)
    if media is None:
        raise ValueError("media_not_found")
    if media["media_type"] != media_type:
        raise ValueError(f"media_type_mismatch:{media_type}")
    if asset_kind and media["asset_kind"] != asset_kind:
        raise ValueError(f"asset_kind_mismatch:{asset_kind}")
    return media["object_key"]


def _payload_media_ids(payload, role: str, fallback_id: int | None) -> list[int]:
    value = getattr(payload, f"{role}_ids", None)
    if value is None and role == "audio_input":
        value = getattr(payload, "audio_input_media_ids", None)
    if value is None:
        value = [fallback_id] if fallback_id is not None else []
    return [int(media_id) for media_id in value if media_id is not None]


def _validate_media_ids(conn, media_ids: list[int], *, media_type: str, asset_kind: str | None = None) -> list[dict]:
    media_items = []
    for media_id in media_ids:
        media = get_media_asset(conn, media_id)
        if media is None:
            raise ValueError("media_not_found")
        if media["media_type"] != media_type:
            raise ValueError(f"media_type_mismatch:{media_type}")
        if asset_kind and media["asset_kind"] != asset_kind:
            raise ValueError(f"asset_kind_mismatch:{asset_kind}")
        media_items.append(media)
    return media_items


def prepare_video_benchmark_media(conn, payload, data: dict) -> dict[str, list[dict]]:
    selected: dict[str, list[dict]] = {}
    for role, config in VIDEO_BENCHMARK_MEDIA_ROLES.items():
        media_ids = _payload_media_ids(payload, role, data.get(config["id_field"]))
        media_items = _validate_media_ids(
            conn,
            media_ids,
            media_type=config["media_type"],
            asset_kind=config["asset_kind"],
        )
        selected[role] = media_items
        data[config["id_field"]] = media_items[0]["id"] if media_items else None
        data[config["snapshot_field"]] = "\n".join(item["object_key"] for item in media_items)
    return selected


def replace_video_benchmark_media_links(conn, item_id: int, selected: dict[str, list[dict]]) -> None:
    conn.execute("DELETE FROM video_benchmark_media_links WHERE item_id = %s", (item_id,))
    for role, media_items in selected.items():
        for index, media in enumerate(media_items):
            conn.execute(
                """
                INSERT INTO video_benchmark_media_links (item_id, role, media_id, sort_order, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (item_id, role, media_id)
                DO UPDATE SET sort_order = EXCLUDED.sort_order
                """,
                (item_id, role, media["id"], index, now()),
            )


def _video_benchmark_media_map(conn, rows: list[dict]) -> dict[int, dict | None]:
    ids: set[int] = set()
    for row in rows:
        for field in ("character_image_id", "scene_image_id", "prop_image_id", "audio_input_id"):
            value = row.get(field)
            if value is not None:
                ids.add(value)
    if not ids:
        return {}
    media_rows = conn.execute(
        """
        SELECT
            i.id, i.asset_id, a.kind AS asset_kind, i.object_key,
            i.source, i.media_type, i.created_at, a.data
        FROM asset_images i
        JOIN assets a ON a.id = i.asset_id
        WHERE i.id = ANY(%s)
        """,
        (list(ids),),
    ).fetchall()
    return {row["id"]: _media_to_dict(row) for row in media_rows}


def _video_benchmark_link_map(conn, item_ids: list[int]) -> dict[int, dict[str, list[dict]]]:
    if not item_ids:
        return {}
    rows = conn.execute(
        """
        SELECT
            l.item_id, l.role,
            i.id, i.asset_id, a.kind AS asset_kind, i.object_key,
            i.source, i.media_type, i.created_at, a.data,
            l.sort_order
        FROM video_benchmark_media_links l
        JOIN asset_images i ON i.id = l.media_id
        JOIN assets a ON a.id = i.asset_id
        WHERE l.item_id = ANY(%s)
        ORDER BY l.item_id, l.role, l.sort_order, l.id
        """,
        (item_ids,),
    ).fetchall()
    out: dict[int, dict[str, list[dict]]] = {}
    for row in rows:
        item = out.setdefault(row["item_id"], {role: [] for role in VIDEO_BENCHMARK_MEDIA_ROLES})
        item[row["role"]].append(_media_to_dict(row))
    return out


def _attach_video_benchmark_media(
    item: dict,
    media_by_id: dict[int, dict | None],
    links_by_item: dict[int, dict[str, list[dict]]] | None = None,
) -> dict:
    item_links = (links_by_item or {}).get(item["id"], {})
    item["character_image"] = media_by_id.get(item.get("character_image_id"))
    item["scene_image"] = media_by_id.get(item.get("scene_image_id"))
    item["prop_image"] = media_by_id.get(item.get("prop_image_id"))
    item["audio_input_media"] = media_by_id.get(item.get("audio_input_id"))
    item["character_image_media"] = item_links.get("character_image") or ([item["character_image"]] if item["character_image"] else [])
    item["scene_image_media"] = item_links.get("scene_image") or ([item["scene_image"]] if item["scene_image"] else [])
    item["prop_image_media"] = item_links.get("prop_image") or ([item["prop_image"]] if item["prop_image"] else [])
    item["audio_input_media_items"] = item_links.get("audio_input") or ([item["audio_input_media"]] if item["audio_input_media"] else [])
    item["character_image_ids"] = [media["id"] for media in item["character_image_media"]]
    item["scene_image_ids"] = [media["id"] for media in item["scene_image_media"]]
    item["prop_image_ids"] = [media["id"] for media in item["prop_image_media"]]
    item["audio_input_media_ids"] = [media["id"] for media in item["audio_input_media_items"]]
    return item


def _video_benchmark_row_to_dict(row: dict) -> dict:
    out = {field: row.get(field) for field in VIDEO_BENCHMARK_FIELDS}
    out.update(
        {
            "id": row["id"],
            "created_at": _normalize_time(row.get("created_at")),
            "updated_at": _normalize_time(row.get("updated_at")),
        }
    )
    return out


def _video_benchmark_payload(payload) -> dict:
    data = {}
    for field in VIDEO_BENCHMARK_FIELDS:
        value = getattr(payload, field, None)
        if field.endswith("_id") or field == "score":
            data[field] = value
        else:
            data[field] = "" if value is None else value
    return data


def get_video_benchmark_item(conn, item_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM video_benchmark_items WHERE id = %s",
        (item_id,),
    ).fetchone()
    if row is None:
        return None
    item = _video_benchmark_row_to_dict(row)
    return _attach_video_benchmark_media(
        item,
        _video_benchmark_media_map(conn, [row]),
        _video_benchmark_link_map(conn, [row["id"]]),
    )


def create_video_benchmark_item(conn, payload) -> int:
    data = _video_benchmark_payload(payload)
    selected = prepare_video_benchmark_media(conn, payload, data)
    row = conn.execute(
        """
        INSERT INTO video_benchmark_items (
            shot_type, task_type, question_type, scene, screen_size,
            character_image_asset, scene_image_asset, prop_image_asset,
            audio_input, video_input, text_prompt, judging_criteria, video_output, score,
            character_image_id, scene_image_id, prop_image_id, audio_input_id,
            created_at, updated_at
        )
        VALUES (
            %(shot_type)s, %(task_type)s, %(question_type)s, %(scene)s, %(screen_size)s,
            %(character_image_asset)s, %(scene_image_asset)s, %(prop_image_asset)s,
            %(audio_input)s, %(video_input)s, %(text_prompt)s, %(judging_criteria)s, %(video_output)s, %(score)s,
            %(character_image_id)s, %(scene_image_id)s, %(prop_image_id)s, %(audio_input_id)s,
            %(now)s, %(now)s
        )
        RETURNING id
        """,
        {**data, "now": now()},
    ).fetchone()
    replace_video_benchmark_media_links(conn, row["id"], selected)
    return row["id"]


def update_video_benchmark_item(conn, item_id: int, payload) -> bool:
    data = _video_benchmark_payload(payload)
    selected = prepare_video_benchmark_media(conn, payload, data)
    result = conn.execute(
        """
        UPDATE video_benchmark_items
        SET
            shot_type = %(shot_type)s,
            task_type = %(task_type)s,
            question_type = %(question_type)s,
            scene = %(scene)s,
            screen_size = %(screen_size)s,
            character_image_asset = %(character_image_asset)s,
            scene_image_asset = %(scene_image_asset)s,
            prop_image_asset = %(prop_image_asset)s,
            audio_input = %(audio_input)s,
            video_input = %(video_input)s,
            text_prompt = %(text_prompt)s,
            judging_criteria = %(judging_criteria)s,
            video_output = %(video_output)s,
            score = %(score)s,
            character_image_id = %(character_image_id)s,
            scene_image_id = %(scene_image_id)s,
            prop_image_id = %(prop_image_id)s,
            audio_input_id = %(audio_input_id)s,
            updated_at = %(now)s
        WHERE id = %(id)s
        """,
        {**data, "id": item_id, "now": now()},
    )
    if result.rowcount > 0:
        replace_video_benchmark_media_links(conn, item_id, selected)
    return result.rowcount > 0


def delete_video_benchmark_item(conn, item_id: int) -> bool:
    result = conn.execute(
        "DELETE FROM video_benchmark_items WHERE id = %s",
        (item_id,),
    )
    return result.rowcount > 0


def _video_benchmark_filters_sql(filters: dict, q: str | None):
    where = ["TRUE"]
    params: list = []
    for field in VIDEO_BENCHMARK_FILTER_FIELDS:
        raw = filters.get(field)
        if raw:
            vals = [v for v in raw.split(",") if v]
            if vals:
                where.append(f"{field} = ANY(%s)")
                params.append(vals)
    if filters.get("score") is not None:
        where.append("score = %s")
        params.append(filters["score"])
    if q:
        clauses = [f"{field} ILIKE %s" for field in VIDEO_BENCHMARK_SEARCH_FIELDS]
        where.append("(" + " OR ".join(clauses) + ")")
        params.extend([f"%{q}%" for _ in VIDEO_BENCHMARK_SEARCH_FIELDS])
    return " AND ".join(where), params


def list_video_benchmark_items(
    conn,
    *,
    limit: int,
    offset: int,
    q: str | None = None,
    shot_type: str | None = None,
    task_type: str | None = None,
    question_type: str | None = None,
    scene: str | None = None,
    screen_size: str | None = None,
    score: int | None = None,
) -> dict:
    where, params = _video_benchmark_filters_sql(
        {
            "shot_type": shot_type,
            "task_type": task_type,
            "question_type": question_type,
            "scene": scene,
            "screen_size": screen_size,
            "score": score,
        },
        q,
    )
    total_row = conn.execute(
        f"SELECT COUNT(*) AS c FROM video_benchmark_items WHERE {where}",
        params,
    ).fetchone()
    rows = conn.execute(
        f"""
        SELECT *
        FROM video_benchmark_items
        WHERE {where}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        [*params, limit, offset],
    ).fetchall()
    media_by_id = _video_benchmark_media_map(conn, rows)
    links_by_item = _video_benchmark_link_map(conn, [row["id"] for row in rows])
    return {
        "items": [
            _attach_video_benchmark_media(_video_benchmark_row_to_dict(row), media_by_id, links_by_item)
            for row in rows
        ],
        "total": int(total_row["c"]),
        "limit": limit,
        "offset": offset,
    }


def health_check() -> bool:
    with get_conn() as conn:
        conn.execute("SELECT 1").fetchone()
    return True


def close_pool() -> None:
    POOL.close()
