"""一次性脚本：把常见道具灌入 props（assets kind=prop）。

按名称幂等：只插入库里还没有的名字，不动（也不清空）已有数据。
用法：
    python seed_props.py
"""
from db import (
    ASSET_PROP,
    find_asset_summaries_by_field,
    get_conn,
    init_db,
    insert_data,
)

_SUFFIX = "product photography, studio lighting, photorealistic, ultra-detailed, 8k."

# (名称, 类别, 提示词主体)
PROPS = [
    ("公文包", "日用品",
     "A single classic leather briefcase, rich brown grain leather, brass clasps and handle, centered on a clean solid white background, no people"),
    ("雨伞", "日用品",
     "A single elegant umbrella, partially open, smooth canopy fabric with a curved wooden handle, centered on a clean solid white background, no people"),
    ("药瓶", "医疗",
     "A single amber glass medicine bottle with a white cap and a printed paper label, centered on a clean solid white background, no people"),
    ("包子", "食物",
     "A single freshly steamed Chinese baozi bun, soft pleated white dough, slight glossy sheen, on a small bamboo steamer, centered on a clean solid white background, no people"),
    ("玉扳指", "饰品",
     "A single ancient Chinese jade archer's thumb ring, smooth translucent green jade with subtle natural veins, polished cylindrical form, centered on a clean solid white background, no people"),
    # ----- 影视剧常见道具 -----
    ("手枪", "武器",
     "A single modern semi-automatic pistol, matte black metal finish, detailed slide and textured grip, centered on a clean solid white background, no people"),
    ("宝剑", "武器",
     "A single ancient Chinese straight sword (jian), polished double-edged steel blade, ornate brass guard and silk-wrapped handle, scabbard lying beside it, centered on a clean solid white background, no people"),
    ("折扇", "饰品",
     "A single traditional Chinese folding fan, half open, slender bamboo ribs with an ink-wash landscape painted on rice paper, centered on a clean solid white background, no people"),
    ("怀表", "饰品",
     "A single vintage pocket watch, polished gold case with an ornately engraved cover, white enamel dial with roman numerals, attached chain coiled beside it, centered on a clean solid white background, no people"),
    ("圣旨", "文书",
     "A single ancient Chinese imperial edict scroll, partially unrolled golden silk brocade with dragon patterns and calligraphy, dark wooden rollers, centered on a clean solid white background, no people"),
    ("书信", "文书",
     "A single handwritten letter on aged parchment paper, folded once with a deep red wax seal, slightly worn edges, centered on a clean solid white background, no people"),
    ("灯笼", "日用品",
     "A single traditional Chinese red paper lantern glowing with warm light, gold trim and hanging tassels, bamboo frame, centered on a clean solid white background, no people"),
    ("茶壶", "日用品",
     "A single traditional Chinese Yixing purple-clay teapot, rich earthy brown texture, gracefully curved spout and handle, centered on a clean solid white background, no people"),
    ("智能手机", "数码",
     "A single modern smartphone, sleek black glass front with thin bezels, screen off, lying flat, centered on a clean solid white background, no people"),
    ("手铐", "工具",
     "A pair of polished stainless steel police handcuffs, two ratchet cuffs joined by short chain links, centered on a clean solid white background, no people"),
]


def main() -> None:
    init_db()
    conn = get_conn()

    existing = set(find_asset_summaries_by_field(conn, ASSET_PROP, "name"))
    added = 0
    for name, category, body in PROPS:
        if name in existing:
            print(f"已存在「{name}」，跳过")
            continue
        prompt = f"{body}. {_SUFFIX}"
        insert_data(
            conn,
            ASSET_PROP,
            {
                "name": name,
                "category": category,
                "prompt": prompt,
                "description": "",
            },
        )
        added += 1
    conn.commit()
    conn.close()
    print(f"灌入完成：新增 {added} 个道具（已存在的已跳过）")


if __name__ == "__main__":
    main()
