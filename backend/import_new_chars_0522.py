"""一次性脚本：把 ../新增分类人物角色0522.xlsx 的「未包含分类明细」导入角色库。

映射规则：
- 类型：东亚/东南亚/南亚→亚洲人，非裔→非洲人，欧美→欧洲人，中东·拉丁→拉美人
- 题材：见 map_genre()
- 提示词：用 LLM 按「原始描述」逐个生成（split-screen 真人风格）
幂等：人设(persona)已存在则跳过。

用法： python import_new_chars_0522.py
"""
import os

import openpyxl
from dotenv import load_dotenv

_BACKEND = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BACKEND, ".env"))  # 独立脚本需自行加载 .env

# 只访问 OpenRouter（国内直连）；清掉 shell 代理避免 httpx 报错
for _p in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
           "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_p, None)

import ai
from db import ASSET_CHARACTER, find_asset_summaries_by_field, get_conn, init_db, insert_data, update_data_fields

XLSX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "新增分类人物角色0522.xlsx"
)
SHEET = "未包含分类明细"

RACE_TYPE = {
    "东亚": "亚洲人", "东南亚": "亚洲人", "南亚": "亚洲人",
    "非裔": "非洲人", "欧美": "欧洲人", "中东·拉丁": "拉美人",
}

GENRE_ERA = {
    "现代-都市": "现代", "现代-职场": "现代", "军事战争": "现代",
    "中国古代": "古代", "欧洲中世纪": "古代", "中国玄幻": "古代", "西方玄幻": "古代",
    "近代/民国": "近代",
    "科幻-星际": "未来", "科幻-赛博朋克": "未来", "末世废土": "未来",
}


def map_genre(cat: str, race: str, persona: str) -> str:
    if cat == "现代都市服饰":
        return "现代-都市"
    if cat == "职场商务服饰":
        return "现代-职场"
    if cat == "近代服装":
        return "近代/民国"
    if cat == "军事战争服饰":
        return "军事战争"
    if cat == "古代服装":
        return {"东亚": "中国古代", "欧美": "欧洲中世纪"}.get(race, "西方玄幻")
    if cat == "仙侠玄幻服饰":
        return "中国玄幻" if race == "东亚" else "西方玄幻"
    if cat == "科幻未来服装":
        if any(k in persona for k in ("赛博", "义体", "机车", "黑客", "贫民窟")):
            return "科幻-赛博朋克"
        if any(k in persona for k in ("废土", "拾荒", "反抗")):
            return "末世废土"
        return "科幻-星际"
    return "现代-都市"


def main() -> None:
    init_db()
    ws = openpyxl.load_workbook(XLSX, data_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    idx = {name: i for i, name in enumerate(rows[0])}

    conn = get_conn()
    # persona -> (id, prompt)
    existing = find_asset_summaries_by_field(conn, ASSET_CHARACTER, "persona")
    added = filled = skipped = failed = 0

    for row in rows[1:]:
        def cell(name):
            return str(row[idx[name]] or "").strip()

        persona = cell("新分类人设")
        if not persona:
            continue

        cat = cell("一级分类")
        race = cell("人种")
        genre = map_genre(cat, race, persona)
        char = {
            "era": GENRE_ERA.get(genre, "现代"),
            "type": RACE_TYPE.get(race, "亚洲人"),
            "gender": cell("性别"),
            "age": cell("年龄段"),
            "persona": persona,
            "body": cell("体型"),
            "features": cell("服饰描述"),
            "genre": genre,
            "description": cell("原始描述"),
        }

        # 已存在：有提示词则跳过，无提示词则补上
        if persona in existing:
            cid, old_prompt = existing[persona]
            if old_prompt.strip():
                skipped += 1
                continue
            try:
                prompt = ai.generate_prompt(char, description=char["description"])
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠ {persona}: 提示词生成失败（{e}）")
                failed += 1
                continue
            update_data_fields(conn, ASSET_CHARACTER, cid, {"prompt": prompt})
            conn.commit()
            filled += 1
            print(f"  ✎ {persona}: 已补提示词")
            continue

        # 不存在：新增
        try:
            prompt = ai.generate_prompt(char, description=char["description"])
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {persona}: 提示词生成失败（{e}），留空")
            prompt = ""
            failed += 1
        insert_data(conn, ASSET_CHARACTER, char | {"prompt": prompt})
        conn.commit()
        existing[persona] = (None, prompt)
        added += 1
        print(f"  + {persona}  [{char['type']}/{char['age']}/{char['gender']}]"
              f" {genre}" + ("  (无提示词)" if not prompt else ""))

    conn.close()
    print(f"\n完成：新增 {added}，补提示词 {filled}，跳过 {skipped}，失败 {failed}")


if __name__ == "__main__":
    main()
