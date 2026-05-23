"""Migrate legacy SQLite + local images into Neon Postgres + TOS.

Usage:
    python migrate_sqlite_to_neon_tos.py --sqlite backend/data/app.db --images backend/data/images
    python migrate_sqlite_to_neon_tos.py --sqlite /data/benchmarkAsset/app.db --images /data/benchmarkAsset/images
"""
import argparse
import mimetypes
import os
import sqlite3

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import storage
from db import (
    ASSET_CHARACTER,
    ASSET_SCENE,
    CHARACTER_FIELDS,
    SCENE_FIELDS,
    attach_image,
    clear_assets,
    get_conn,
    init_db,
    insert_data,
)


def _preflight_storage() -> None:
    key = storage.new_object_key(".txt", "migration-preflight")
    storage.put_bytes(key, b"ok", "text/plain")
    storage.delete_object(key)


def _row_data(row: sqlite3.Row, fields: list[str]) -> dict:
    return {field: row[field] or "" for field in fields}


def _copy_image(images_dir: str, filename: str) -> str:
    source = os.path.join(images_dir, filename)
    if not os.path.exists(source):
        raise FileNotFoundError(source)
    ext = os.path.splitext(filename)[1] or ".png"
    key = storage.new_object_key(ext)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(source, "rb") as f:
        storage.put_bytes(key, f.read(), content_type)
    return key


def _migrate_kind(sqlite_conn, pg_conn, kind: str, table: str, image_table: str, fk: str, fields: list[str], images_dir: str) -> tuple[int, int]:
    id_map: dict[int, int] = {}
    image_map: dict[int, int] = {}
    asset_count = image_count = 0
    rows = sqlite_conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
    image_rows = sqlite_conn.execute(f"SELECT * FROM {image_table} ORDER BY id").fetchall()

    print(f"{kind}: inserting {len(rows)} assets", flush=True)
    for row in rows:
        new_id = insert_data(pg_conn, kind, _row_data(row, fields))
        id_map[row["id"]] = new_id
        asset_count += 1

    print(f"{kind}: uploading {len(image_rows)} images", flush=True)
    for idx, row in enumerate(image_rows, start=1):
        old_asset_id = row[fk]
        if old_asset_id not in id_map:
            continue
        try:
            key = _copy_image(images_dir, row["filename"])
        except FileNotFoundError:
            print(f"missing image skipped: {row['filename']}")
            continue
        image = attach_image(pg_conn, id_map[old_asset_id], key, row["source"] or "generated")
        image_map[row["id"]] = image["id"]
        image_count += 1
        if idx % 10 == 0 or idx == len(image_rows):
            print(f"{kind}: uploaded {idx}/{len(image_rows)} images", flush=True)

    for row in sqlite_conn.execute(f"SELECT id, cover_image_id FROM {table} WHERE cover_image_id IS NOT NULL").fetchall():
        old_cover = row["cover_image_id"]
        if row["id"] in id_map and old_cover in image_map:
            pg_conn.execute(
                "UPDATE assets SET cover_image_id = %s WHERE id = %s",
                (image_map[old_cover], id_map[row["id"]]),
            )

    return asset_count, image_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default=os.path.join(os.path.dirname(__file__), "data", "app.db"))
    parser.add_argument("--images", default=os.path.join(os.path.dirname(__file__), "data", "images"))
    parser.add_argument("--force", action="store_true", help="clear target assets before migrating")
    args = parser.parse_args()

    init_db()
    _preflight_storage()
    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row

    with get_conn() as pg_conn:
        if args.force:
            clear_assets(pg_conn, ASSET_CHARACTER)
            clear_assets(pg_conn, ASSET_SCENE)
        chars, char_images = _migrate_kind(
            sqlite_conn, pg_conn, ASSET_CHARACTER, "characters", "images", "character_id", CHARACTER_FIELDS, args.images
        )
        scenes, scene_images = _migrate_kind(
            sqlite_conn, pg_conn, ASSET_SCENE, "scenes", "scene_images", "scene_id", SCENE_FIELDS, args.images
        )
        pg_conn.commit()

    sqlite_conn.close()
    print(
        f"迁移完成：角色 {chars} / 图片 {char_images}，"
        f"场景 {scenes} / 图片 {scene_images}"
    )


if __name__ == "__main__":
    main()
