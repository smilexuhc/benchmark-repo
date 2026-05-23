"""一次性脚本：导入 0522 补充的 14 个角色（7 动物 + 7 婴幼儿）。

数据来自表格截图，结构与角色库一致。动物类型归「动物/宠物」、题材留空；
提示词用 LLM 逐个生成（动物走真实野生动物摄影风格）。
幂等：人设已存在且有提示词则跳过，无提示词则补上。

用法： python import_supplement_0522.py
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

# (时代, 类型, 性别, 年龄段, 人设, 身材, 特征, 题材)
ROWS = [
    ("现代", "动物/宠物", "男", "成年", "草原雄狮", "健壮",
     "金黄色鬃毛浓密、鼻头黑色宽大、四肢肌肉发达、尾巴末端有深色毛球、常卧在岩石上", ""),
    ("现代", "动物/宠物", "女", "老年", "象群首领", "庞大",
     "灰色粗糙皮肤、大扇形耳朵边缘有裂口、长象牙略有磨损、眼神沉稳、缓慢行走", ""),
    ("现代", "动物/宠物", "男", "青年", "长颈鹿", "高瘦",
     "黄色带不规则斑点皮肤、极长脖颈、头顶一对骨质角、眼睛大而睫毛长、优雅迈步", ""),
    ("现代", "动物/宠物", "男", "成年", "北极熊", "厚重",
     "全身乳白色厚毛、黑色鼻头和爪垫、体型浑圆壮硕、缓缓在冰面上行走、低头嗅雪", ""),
    ("现代", "动物/宠物", "女", "幼年", "熊猫", "圆胖",
     "黑白分明毛色、大黑眼圈、圆滚滚身体、正抱着竹子啃、躺在地上翻滚", ""),
    ("现代", "动物/宠物", "女", "成年", "白鲸", "巨大",
     "蓝黑色背部、白色腹部、极长胸鳍像翅膀、头部有瘤状突起、跃出海面扬起水花", ""),
    ("现代", "动物/宠物", "女", "成年", "雪鸮", "敦实",
     "纯白色羽毛有稀疏黑斑、黄色圆眼睛、宽大羽翼、无声飞行、蹲在雪地木桩上", ""),
    ("现代", "亚洲人", "男", "0-12个月", "襁褓睡婴", "圆润",
     "稀疏黑发、大而亮的眼睛、皮肤白皙、穿着浅蓝色连体衣/睡袋、常被抱在怀中", "现代-都市"),
    # 表里时代误填「古代」，已确认改为「现代」
    ("现代", "欧洲人", "女", "0-12个月", "蕾丝裙婴儿", "圆润",
     "金色胎毛、浅蓝或灰色瞳孔、皮肤白皙泛红、穿着白色法式蕾丝边婴儿裙或碎花连体衣", "现代-都市"),
    ("现代", "非洲人", "女", "1-2岁", "小辫萌娃", "匀称",
     "扎满头彩色小辫子、大眼睛亮晶晶、皮肤深褐色有光泽、穿碎花连衣裙、戴亮色发卡", "现代-都市"),
    ("现代", "亚洲人", "男", "3-5岁", "元气小王子", "匀称",
     "黑色短发、大眼睛、皮肤白皙、穿卡通T恤配短裤小球鞋、背小书包、蹦蹦跳跳", "现代-都市"),
    ("现代", "欧洲人", "女", "3-5岁", "甜美小公主", "纤细",
     "金色长发编麻花辫或双马尾、蓝色瞳孔、皮肤白皙、穿蓬蓬裙配小皮鞋、抱洋娃娃", "现代-都市"),
    ("古代", "拉美人", "女", "3-5岁", "沙漠小精灵", "娇小",
     "黑色长发扎高马尾、深褐色大眼睛、皮肤蜜色、穿亮色长裙配凉鞋、喜欢跳舞", "西方玄幻"),
    ("古代", "欧洲人", "女", "3-5岁", "小淑女", "纤细",
     "金色卷发垂肩或戴蝴蝶结粉帽、穿多层衬裙的小礼服、手拿小花篮、站在乡村花园前", "欧洲中世纪"),
]

FIELDS = ["era", "type", "gender", "age", "persona", "body", "features", "genre"]


def main() -> None:
    init_db()
    conn = get_conn()
    existing = find_asset_summaries_by_field(conn, ASSET_CHARACTER, "persona")
    added = filled = skipped = failed = 0

    for vals in ROWS:
        char = dict(zip(FIELDS, vals))
        char["description"] = ""
        persona = char["persona"]

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
        print(f"  + {persona}  [{char['type']}/{char['age']}]"
              f" {char['genre'] or '(无题材)'}")

    conn.close()
    print(f"\n完成：新增 {added}，补提示词 {filled}，跳过 {skipped}，失败 {failed}")


if __name__ == "__main__":
    main()
