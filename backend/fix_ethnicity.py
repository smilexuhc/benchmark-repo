"""给缺少人种描述的人类角色提示词补上人种。

图片模型在 close-up 不写人种时会默认画西方人，导致与「类型」字段不符。
本脚本按 type 字段，把人种词插入 close-up 主体（沿用已匹配样本的写法）。
已含人种的提示词跳过；幂等：重复运行结果不变。

用法： python fix_ethnicity.py
"""
import re

from db import ASSET_CHARACTER, CHARACTER_FIELDS, all_assets, get_conn, init_db, update_data_fields

# 类型 -> (人种词, 冠词)
ETHNICITY = {
    "亚洲人": ("East Asian", "an"),
    "欧洲人": ("European", "a"),
    "非洲人": ("African", "an"),
    "拉美人": ("Latino", "a"),
    "混血": ("mixed-race", "a"),
}

# 判断提示词是否已含人种描述
ETH_KEYWORDS = [
    "asian", "chinese", "japanese", "korean", "european", "caucasian",
    "african", "latino", "latina", "hispanic", "mixed-race", "mixed race",
    "eurasian", "indian", "middle eastern", "nordic", "slavic",
]


def has_ethnicity(prompt: str) -> bool:
    low = prompt.lower()
    return any(k in low for k in ETH_KEYWORDS)


def main() -> None:
    init_db()
    conn = get_conn()
    rows = all_assets(conn, ASSET_CHARACTER, CHARACTER_FIELDS)
    changed = skipped = 0
    for row in rows:
        cid, ctype, prompt = row["id"], row["type"], row["prompt"]
        if ctype not in ETHNICITY or not (prompt or "").strip():
            continue
        if has_ethnicity(prompt):
            continue
        eth, art = ETHNICITY[ctype]
        new, n = re.subn(
            r"close-up of an? ", f"close-up of {art} {eth} ", prompt, count=1
        )
        if n == 0:
            print(f"  ⚠ id{cid}: 未找到 close-up 短语，跳过")
            skipped += 1
            continue
        update_data_fields(conn, ASSET_CHARACTER, cid, {"prompt": new})
        changed += 1
    conn.commit()
    conn.close()
    print(f"已补人种 {changed} 条" + (f"，跳过 {skipped} 条" if skipped else ""))


if __name__ == "__main__":
    main()
