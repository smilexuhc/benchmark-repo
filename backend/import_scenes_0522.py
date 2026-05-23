"""一次性脚本：追加「自然环境」场景资产（0522 新增，10 个）。

用法：
    python import_scenes_0522.py        # 追加，按场景名称去重，已存在则跳过

时代列按现有库词汇归一：当代->现代、古装->古代、科幻->未来、近代不变。
"""
from db import ASSET_SCENE, find_asset_summaries_by_field, get_conn, init_db, insert_data

_SUFFIX = "Photorealistic, cinematic lighting, ultra-detailed, 8k."

# (场景名称, 时代, 场景类型[室内/室外], 题材风格, 氛围时段, 关键元素, 提示词主体)
SCENES = [
    ("海边日落沙滩", "现代", "室外", "自然环境", "黄昏", "海浪、礁石、夕阳、棕榈树",
     "A seaside beach at sunset, gentle waves rolling onto golden sand, scattered "
     "weathered rocks, palm trees swaying in the breeze, a glowing orange sun low "
     "on the horizon, empty beach, no people, warm dusk light."),
    ("星空下的草原", "现代", "室外", "自然环境", "深夜", "萤火虫、野花、银河、帐篷",
     "A vast grassland under a starry night sky, the Milky Way arching overhead, "
     "glowing fireflies drifting above wildflowers, a lone tent on the meadow, "
     "empty scene, no people, deep starlit night."),
    ("迷雾森林小径", "现代", "室外", "自然环境", "雨天", "苔藓、枯木、藤蔓、蘑菇",
     "A misty forest trail on a rainy day, moss-covered ground, fallen dead trees, "
     "hanging vines, clusters of mushrooms, fog drifting between the trunks, empty "
     "path, no people, soft overcast light."),
    ("山顶云海日出", "现代", "室外", "自然环境", "清晨", "云雾、松树、悬崖、霞光",
     "A mountain summit above a sea of clouds at sunrise, drifting mist, pine trees "
     "clinging to a cliff edge, glowing rosy dawn light spreading across the "
     "horizon, empty scene, no people, soft morning glow."),
    ("阳光穿透的竹林", "现代", "室外", "自然环境", "午后", "竹叶、光影、石阶、溪流",
     "A bamboo grove with sunlight filtering through the leaves, dappled light and "
     "shadow on the ground, mossy stone steps, a small clear stream, empty grove, "
     "no people, bright afternoon light."),
    ("月光下的湖泊", "现代", "室外", "自然环境", "夜晚", "倒影、芦苇、荷花、薄雾",
     "A tranquil lake under moonlight, the bright moon reflected on the still "
     "water, reeds along the shore, blooming lotus flowers, thin mist drifting "
     "low, empty scene, no people, cool moonlit night."),
    ("大漠孤烟戈壁", "古代", "室外", "自然环境", "黄昏", "沙丘、骆驼、风蚀岩、残阳",
     "A vast desert gobi at dusk, rolling sand dunes, wind-eroded rock formations, "
     "distant camels crossing the sand, a setting sun casting long shadows, empty "
     "desert, no people, golden dusk light."),
    ("幽深竹林古道", "古代", "室外", "自然环境", "阴天", "竹影、石碑、落叶、山雾",
     "A deep ancient path through a bamboo forest on an overcast day, dense bamboo "
     "casting shadows, a weathered stone stele, fallen leaves on the trail, "
     "mountain mist, empty path, no people, soft grey light."),
    ("薄雾笼罩的芦苇荡", "近代", "室外", "自然环境", "清晨", "芦苇、水鸟、木船、晨露",
     "A reed marsh shrouded in morning mist, tall swaying reeds, water birds, an "
     "old wooden boat moored among the reeds, dew glistening on the leaves, empty "
     "wetland, no people, pale dawn light."),
    ("冰原极光雪地", "未来", "室外", "自然环境", "极夜", "冰裂缝、极光、雪丘、寒星",
     "A polar ice field during the polar night, cracked glacial ice, glowing green "
     "aurora dancing across the sky, snow-covered hills, cold distant stars, empty "
     "frozen landscape, no people, eerie aurora light."),
]


def main() -> None:
    init_db()
    conn = get_conn()

    existing = set(find_asset_summaries_by_field(conn, ASSET_SCENE, "name"))
    added = skipped = 0
    for name, era, stype, genre, mood, elements, body in SCENES:
        if name in existing:
            print(f"  跳过（已存在）：{name}")
            skipped += 1
            continue
        prompt = f"{body} {_SUFFIX}"
        insert_data(
            conn,
            ASSET_SCENE,
            {
                "name": name,
                "era": era,
                "scene_type": stype,
                "genre": genre,
                "mood": mood,
                "elements": elements,
                "prompt": prompt,
                "description": "",
            },
        )
        added += 1
    conn.commit()
    conn.close()
    print(f"完成：新增 {added} 个，跳过 {skipped} 个")


if __name__ == "__main__":
    main()
