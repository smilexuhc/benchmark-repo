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
        "created_at": _normalize_time(row.get("created_at")),
    }


def image_key(row: dict) -> str:
    return row["object_key"] if "object_key" in row else row["filename"]


def list_images(conn, asset_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, object_key, source, created_at FROM asset_images WHERE asset_id = %s ORDER BY id",
        (asset_id,),
    ).fetchall()
    return [_image_to_dict(row) for row in rows]


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
        INSERT INTO asset_images (asset_id, object_key, source, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id, object_key, source, created_at
        """,
        (asset_id, object_key, source, now()),
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


def health_check() -> bool:
    with get_conn() as conn:
        conn.execute("SELECT 1").fetchone()
    return True


def close_pool() -> None:
    POOL.close()
