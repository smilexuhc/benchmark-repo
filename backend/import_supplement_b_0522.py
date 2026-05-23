"""一次性脚本：导入 0522 补充第二批 12 个角色（神话/外星）。

时代「神话」归古代；类型全归「神话生物」；性别 雄性→男/雌性→女/无性→中性；
题材 科幻→科幻-星际、中世纪→欧洲中世纪、恐怖→西方玄幻、神话史诗按文化拆。
提示词：纯异兽（龙/凤凰/独角兽/狮鹫/麒麟）用幻想生物风格，人形用人物风格。
幂等：人设已存在且有提示词则跳过。

用法： python import_supplement_b_0522.py
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

# (时代, 类型, 性别, 年龄段, 人设, 身材, 特征, 题材, 是否纯异兽)
ROWS = [
    ("未来", "神话生物", "中性", "中年", "友好小灰人", "矮瘦",
     "灰色光滑皮肤、大光头、杏仁形黑色大眼睛、小鼻子小嘴、四肢细长、穿银色连体服、常使用光笔或平板翻译器",
     "科幻-星际", False),
    ("古代", "神话生物", "男", "成年", "优雅贵族吸血鬼", "修长挺拔",
     "苍白皮肤、黑发梳脑后、血红瞳孔、尖长犬齿、穿黑色维多利亚风格礼服配深红领巾、戴银色戒指、常持红酒杯（盛血）",
     "欧洲中世纪", False),
    ("古代", "神话生物", "男", "青年", "狂暴狼人", "魁梧多毛",
     "人形时高大壮硕多毛、变身时完全狼形态或半人半狼（狼头+人类身体）、灰色/黑色厚重毛发、黄色竖瞳、獠牙、利爪、常常披着破布衣物或全裸",
     "西方玄幻", False),
    ("古代", "神话生物", "女", "青年", "月精灵公主", "高挑优雅",
     "银白色长发及腰、尖长耳朵、淡紫色瞳孔、皮肤散发淡淡月光般莹白光晕、穿轻盈纱质长裙缀满星光、额戴银色月冠",
     "西方玄幻", False),
    ("古代", "神话生物", "男", "青年", "部落半兽人战士", "魁梧粗犷",
     "灰绿色粗糙皮肤、下獠牙突出嘴唇、扁塌鼻、小眼睛深陷、头戴兽角头盔、身穿铁甲皮甲混搭、手持巨斧/狼牙棒",
     "西方玄幻", False),
    ("古代", "神话生物", "男", "成年", "行尸走肉", "干瘪枯瘦",
     "腐败皮肤呈灰绿色或褐色、部分露出白骨、眼神空洞浑浊、嘴唇干裂露出牙龈、穿破烂不整的旧衣、行动僵硬蹒跚、喉中发出低吼",
     "西方玄幻", False),
    ("古代", "神话生物", "中性", "成年", "浴火重生之凤凰", "巨大优雅（翼展约5-8米）",
     "全身燃烧不灭的金红色火焰、羽毛由火焰构成呈红橙黄三色渐变、修长尾羽如彩虹般拖曳身后、金色竖瞳、冠羽如皇冠、啼声如凤鸣清亮",
     "中国玄幻", True),
    ("古代", "神话生物", "男", "成年", "圣洁森林守护者", "优美矫健（肩高约2米）",
     "纯白如雪的皮毛、额前一螺旋金角发出柔和光芒、鬃毛和尾巴呈银蓝色流动状、紫色瞳孔带虹彩、四蹄踏过处开出花朵、常出没于月光下的森林",
     "西方玄幻", True),
    ("古代", "神话生物", "男", "成年", "上古雨师神龙", "蜿蜒巨大（长约50米）",
     "青蓝色龙鳞、鹿角、牛头、蛇身、鱼鳞、鹰爪、虎掌、须发飘扬、周身云雾缭绕、可腾云驾雾、行云布雨、常与雷雨相伴",
     "中国玄幻", True),
    ("古代", "神话生物", "男", "成年", "高山天空之王", "壮硕威猛（翼展约10米）",
     "前半身为鹰（灰色羽毛、钩状喙、金色锐眼）、后半身为狮（黄褐色皮毛、长尾有穗）、鹰翼巨大有力、前爪为鹰爪、后腿为狮爪、叫声如鹰啸",
     "西方玄幻", True),
    ("古代", "神话生物", "女", "成年", "绝色妖媚之狐", "纤细灵巧（人形时约1.68米）",
     "火红色皮毛、九条长尾各自灵动、可化为绝世美人（狐耳保留）、金色狐眼、眼尾上挑带妖异红晕、指尖有红色指甲、穿红衣或白衣",
     "中国玄幻", False),
    ("古代", "神话生物", "男", "成年", "至仁至德祥瑞", "优雅端庄（肩高约2.5米）",
     "龙头、鹿角、狮眼、虎背、熊腰、蛇鳞、牛尾、马蹄、全身覆盖五彩鳞甲（以青绿色为主）、蹄下生五彩祥云、性情温和不踩活物",
     "中国玄幻", True),
]

FIELDS = ["era", "type", "gender", "age", "persona", "body", "features", "genre"]


def main() -> None:
    init_db()
    conn = get_conn()
    existing = find_asset_summaries_by_field(conn, ASSET_CHARACTER, "persona")
    added = filled = skipped = failed = 0

    for vals in ROWS:
        char = dict(zip(FIELDS, vals[:8]))
        char["description"] = ""
        is_creature = vals[8]
        persona = char["persona"]
        force = ai.CREATURE_PROMPT_SYSTEM if is_creature else ""

        if persona in existing:
            cid, old_prompt = existing[persona]
            if old_prompt.strip():
                skipped += 1
                continue
            try:
                prompt = ai.generate_prompt(char, "", force_system=force)
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
            prompt = ai.generate_prompt(char, "", force_system=force)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {persona}: 提示词失败（{e}），留空")
            prompt = ""
            failed += 1
        insert_data(conn, ASSET_CHARACTER, char | {"prompt": prompt})
        conn.commit()
        existing[persona] = (None, prompt)
        added += 1
        kind = "幻想生物" if is_creature else "人形"
        print(f"  + {persona}  [{char['gender']}/{char['genre']}] {kind}")

    conn.close()
    print(f"\n完成：新增 {added}，补提示词 {filled}，跳过 {skipped}，失败 {failed}")


if __name__ == "__main__":
    main()
