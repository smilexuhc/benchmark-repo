"""一次性脚本：导入 0522 补充第三批 6 个「动物拟人」角色。

类型「动物拟人」；题材 古风-武侠→中国古代、科幻-太空冒险/科幻-未来部落→科幻-星际。
提示词用拟人化动物风格（generate_prompt 见类型即自动选 ANTHRO_PROMPT_SYSTEM）。
幂等：人设已存在且有提示词则跳过。

用法： python import_supplement_c_0522.py
"""
import os

from dotenv import load_dotenv

_BACKEND = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BACKEND, ".env"))
for _p in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
           "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_p, None)

import ai
from db import ASSET_CHARACTER, find_asset_summaries_by_field, get_conn, init_db, insert_data, update_data_fields

# (时代, 性别, 年龄段, 人设, 身材, 特征, 题材) —— 类型统一「动物拟人」
ROWS = [
    ("古代", "男", "中年", "武林宗师熊猫", "圆润敦实",
     "黑白相间毛色、穿粗布对襟练功服、腰系红色布带、手持长棍、神态憨厚沉稳、眼神藏锋",
     "中国古代"),
    ("古代", "男", "青年", "剑客白鹤", "瘦高修长",
     "通体雪白长羽、穿素白劲装、背负长剑、动作飘逸、眼神清冷孤傲",
     "中国古代"),
    ("古代", "男", "中年", "大力金刚牛", "魁梧壮硕",
     "赤褐色毛皮、双角粗壮、肌肉虬结、赤裸上身披兽皮、手持巨锤、咆哮怒目",
     "中国古代"),
    ("未来", "男", "中年", "改造雇佣兵獾", "矮壮敦实",
     "黑白条纹粗毛、左眼机械义眼泛红光、穿破旧战术背心、肩扛改装能量步枪、嘴里嚼着东西、表情痞气不羁",
     "科幻-星际"),
    ("未来", "N/A", "青年", "赏金猎人鬣蜥", "修长矫健",
     "翠绿带银纹鳞片、头顶骨质冠饰、穿暗色机能皮甲、腰挎双能量匕首、竖瞳冷漠、神情致命",
     "科幻-星际"),
    ("未来", "男", "中年", "部落守护者黑犀", "魁梧壮硕",
     "深灰色厚皮、犀角包金属护套、身披部落图腾披风、胸前佩戴能量项圈、赤脚踏地、神态威严",
     "科幻-星际"),
]


def main() -> None:
    init_db()
    conn = get_conn()
    existing = find_asset_summaries_by_field(conn, ASSET_CHARACTER, "persona")
    added = filled = skipped = failed = 0

    for era, gender, age, persona, body, features, genre in ROWS:
        char = {
            "era": era, "type": "动物拟人", "gender": gender, "age": age,
            "persona": persona, "body": body, "features": features,
            "genre": genre, "description": "",
        }

        if persona in existing:
            cid, old_prompt = existing[persona]
            if old_prompt.strip():
                skipped += 1
                continue
            try:
                prompt = ai.generate_prompt(char, "")
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠ {persona}: 提示词失败（{e}）")
                failed += 1
                continue
            update_data_fields(conn, ASSET_CHARACTER, cid, {"prompt": prompt})
            conn.commit()
            filled += 1
            print(f"  ✎ {persona}: 已补提示词")
            continue

        try:
            prompt = ai.generate_prompt(char, "")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {persona}: 提示词失败（{e}），留空")
            prompt = ""
            failed += 1
        insert_data(conn, ASSET_CHARACTER, char | {"prompt": prompt})
        conn.commit()
        existing[persona] = (None, prompt)
        added += 1
        print(f"  + {persona}  [动物拟人/{age}] {genre}")

    conn.close()
    print(f"\n完成：新增 {added}，补提示词 {filled}，跳过 {skipped}，失败 {failed}")


if __name__ == "__main__":
    main()
