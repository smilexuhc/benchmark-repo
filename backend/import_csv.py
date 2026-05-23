"""一次性导入脚本：把 ../角色资料库数据.csv 灌入 Postgres/Neon。

用法：
    python import_csv.py            # 库为空时导入，非空则跳过
    python import_csv.py --force    # 清空 characters 表后重新导入
"""
import csv
import os
import sys

from db import ASSET_CHARACTER, count_assets, clear_assets, get_conn, init_db, insert_data

CSV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "角色资料库数据.csv"
)

# CSV 列名 -> 数据库字段
COLUMN_MAP = {
    "时代": "era",
    "类型": "type",
    "性别": "gender",
    "年龄段": "age",
    "人设（服装造型风格）": "persona",
    "身材": "body",
    "特征": "features",
    "常见题材": "genre",
    "人物生成提示词": "prompt",
}


# 分类归一化：合并重复项与碎项（人种、独立年龄段保留）
NORMALIZE = {
    "type": {
        "机器人/傀儡": "机器人",
        "宠物狗": "动物/宠物",
        "宠物/生物": "动物/宠物",
        "兽": "动物/宠物",
    },
    "age": {
        "成年人": "成年",
        "成年犬": "成年",
        "幼年": "儿童",
    },
    "era": {
        "古代/幻想": "古代",
    },
}


def clean(text: str) -> str:
    """去掉首尾空白与残留的包裹引号。"""
    s = (text or "").strip()
    while len(s) >= 2 and s[0] == s[-1] == '"':
        s = s[1:-1].strip()
    return s


def main() -> None:
    force = "--force" in sys.argv
    init_db()
    conn = get_conn()

    count = count_assets(conn, ASSET_CHARACTER)
    if count > 0 and not force:
        print(f"characters 表已有 {count} 条数据，跳过导入。如需重导请加 --force")
        conn.close()
        return
    if force:
        clear_assets(conn, ASSET_CHARACTER)
        conn.commit()
        print("已清空旧数据。")

    if not os.path.exists(CSV_PATH):
        print(f"找不到 CSV：{CSV_PATH}")
        conn.close()
        return

    fields = list(COLUMN_MAP.values())
    inserted = 0
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            values = [clean(row.get(cn, "")) for cn in COLUMN_MAP]
            for i, field in enumerate(fields):
                if field in NORMALIZE:
                    values[i] = NORMALIZE[field].get(values[i], values[i])
            insert_data(conn, ASSET_CHARACTER, dict(zip(fields, values)) | {"description": ""})
            inserted += 1
    conn.commit()
    conn.close()
    print(f"导入完成：{inserted} 个角色 -> Postgres assets")


if __name__ == "__main__":
    main()
