"""一次性脚本：把各题材的高频场景灌入 scenes 表（55 个）。

用法：
    python seed_scenes.py            # 表为空时灌入，非空则跳过
    python seed_scenes.py --force    # 清空 scenes 表后重新灌入
"""
import sys

from db import ASSET_SCENE, clear_assets, count_assets, get_conn, init_db, insert_data

_SUFFIX = "Photorealistic, cinematic lighting, ultra-detailed, 8k."

# (场景名称, 时代, 场景类型, 题材风格, 氛围时段, 关键元素, 提示词主体)
SCENES = [
    # ----- 中国古代 -----
    ("金銮殿", "古代", "室内", "中国古代", "白天", "龙椅、红柱、雕梁",
     "Wide establishing shot of a grand ancient Chinese imperial throne hall, golden dragon throne, towering red lacquered columns, intricately carved beams, polished stone floor, empty hall, no people, daylight through tall doorways."),
    ("古风庭院", "古代", "室外", "中国古代", "白天", "灰瓦、回廊、荷塘",
     "A traditional Chinese courtyard, gray-tiled rooftops, wooden corridors, a lotus pond, blossoming trees, a stone path, empty scene, no people, soft daylight."),
    ("客栈", "古代", "室内", "中国古代", "黄昏", "木桌、红灯笼、酒坛",
     "Interior of an ancient Chinese inn, wooden tables and benches, hanging red lanterns, a staircase to upper rooms, a counter with porcelain wine jars, empty room, no people, warm dusk light."),
    ("书房", "古代", "室内", "中国古代", "白天", "书架、竹简、笔墨纸砚",
     "An ancient Chinese scholar's study, wooden bookshelves with bamboo scrolls, an inkstone and brushes on a desk, a hanging landscape painting, empty room, no people, gentle daylight."),
    ("街市", "古代", "室外", "中国古代", "白天", "摊位、招幌、石板路",
     "A bustling ancient Chinese street market, wooden stalls, hanging banners and lanterns, tiled-roof shops along a stone-paved street, empty street, no people, bright daylight."),
    # ----- 中国玄幻 -----
    ("仙门山门", "古代", "室外", "中国玄幻", "白天", "石牌坊、悬空楼阁、玉阶",
     "A majestic immortal sect mountain gate, a towering stone archway carved with mystical runes, floating pavilions among clouds, jade steps ascending the peak, empty scene, no people, ethereal daylight."),
    ("云海仙境", "古代", "室外", "中国玄幻", "黄昏", "浮山、仙鹤、瀑布",
     "A celestial wonderland above a sea of clouds, floating mountain peaks, ancient pavilions, glowing spirit cranes, distant waterfalls, empty scene, no people, golden dusk glow."),
    ("洞府", "古代", "室内", "中国玄幻", "夜晚", "灵石、打坐台、雾气",
     "A secluded immortal cave dwelling, glowing crystal formations, a stone meditation platform, mystical mist drifting low, ancient carvings on the walls, empty cave, no people, dim magical glow."),
    ("炼丹房", "古代", "室内", "中国玄幻", "夜晚", "丹炉、药材罐、丹药",
     "An ancient Chinese alchemy chamber, a large bronze pill furnace with rising flames, shelves of herb jars and gourds, glowing elixir bottles, empty room, no people, warm firelight."),
    ("上古遗迹", "古代", "室外", "中国玄幻", "黄昏", "残破石殿、神像、玉碎",
     "Ancient mystical ruins, crumbling stone temples overgrown with glowing vines, broken statues of deities, floating shards of jade, empty scene, no people, mysterious dusk light."),
    # ----- 末世废土 -----
    ("废墟街道", "未来", "室外", "末世废土", "白天", "倒塌楼房、锈蚀汽车、尘霾",
     "A post-apocalyptic ruined city street, collapsed buildings, rusted abandoned cars, cracked asphalt with weeds, a dust haze, empty street, no people, harsh overcast daylight."),
    ("地下避难所", "未来", "室内", "末世废土", "夜晚", "混凝土墙、上下铺、补给箱",
     "An underground apocalypse shelter, concrete walls, bunk beds, stockpiled supply crates, flickering fluorescent lights, exposed pipes, empty room, no people, dim cold light."),
    ("荒漠营地", "未来", "室外", "末世废土", "黄昏", "帐篷、篝火、废铁桶",
     "A wasteland desert camp, patched tents and scrap-metal shelters, a campfire pit, barrels and salvaged junk, vast barren dunes, empty camp, no people, orange dusk light."),
    ("废弃工厂", "未来", "室内", "末世废土", "白天", "锈蚀机械、破窗、碎石",
     "An abandoned post-apocalyptic factory interior, rusted machinery, broken windows, debris and dust, shafts of light through a damaged roof, empty scene, no people, pale daylight."),
    ("废土集市", "未来", "室外", "末世废土", "白天", "简易摊位、废品货物、锈招牌",
     "A wasteland survivors' market, makeshift stalls of scrap and tarp, bartered junk goods, rusted signage, dusty ground, empty marketplace, no people, hazy daylight."),
    # ----- 欧洲中世纪 -----
    ("城堡大厅", "古代", "室内", "欧洲中世纪", "白天", "拱顶、长桌、铁吊灯",
     "A grand medieval castle great hall, vaulted stone ceilings, long wooden banquet tables, iron chandeliers, hanging banners and a large fireplace, empty hall, no people, daylight through arched windows."),
    ("中世纪村庄", "古代", "室外", "欧洲中世纪", "白天", "木屋、茅草顶、水井",
     "A medieval European village, timber-framed cottages with thatched roofs, a dirt road, a stone well, distant fields, empty village, no people, soft daylight."),
    ("教堂", "古代", "室内", "欧洲中世纪", "白天", "石柱、彩窗、长椅",
     "Interior of a medieval cathedral, towering stone columns, tall stained-glass windows casting colored light, rows of wooden pews, an altar, empty church, no people, divine daylight."),
    ("铁匠铺", "古代", "室内", "欧洲中世纪", "黄昏", "火炉、铁砧、兵器架",
     "A medieval blacksmith's forge, a glowing furnace, an anvil, hanging hammers and tongs, racks of swords and armor, empty workshop, no people, warm firelight."),
    ("集市广场", "古代", "室外", "欧洲中世纪", "白天", "鹅卵石、商贩摊位、石喷泉",
     "A medieval town market square, cobblestone ground, wooden merchant stalls with awnings, a central stone fountain, surrounding timber buildings, empty square, no people, bright daylight."),
    # ----- 现代-校园 -----
    ("教室", "现代", "室内", "现代-校园", "白天", "课桌椅、黑板、讲台",
     "A modern school classroom, rows of wooden desks and chairs, a green chalkboard, large windows, a teacher's podium, empty classroom, no people, bright natural light."),
    ("操场", "现代", "室外", "现代-校园", "白天", "跑道、球场、看台",
     "A modern school sports ground, a red running track, a green soccer field, basketball hoops, bleachers, empty field, no people, clear daylight."),
    ("图书馆", "现代", "室内", "现代-校园", "白天", "书架、阅览桌、台灯",
     "A modern school library, tall bookshelves full of books, reading tables with lamps, large windows, quiet aisles, empty library, no people, soft daylight."),
    ("宿舍", "现代", "室内", "现代-校园", "黄昏", "上下铺、书桌、海报",
     "A modern student dormitory room, bunk beds, study desks, personal posters and belongings, a window with dusk light, empty room, no people, warm evening light."),
    ("食堂", "现代", "室内", "现代-校园", "白天", "餐桌、打饭窗口、餐盘",
     "A modern school cafeteria, long dining tables and stools, a food serving counter, trays and signage, large windows, empty canteen, no people, bright daylight."),
    # ----- 现代-职场 -----
    ("开放办公区", "现代", "室内", "现代-职场", "白天", "工位、电脑、绿植",
     "A modern open-plan office, rows of desks with computers, ergonomic chairs, glass partitions, indoor plants, empty office, no people, bright daylight."),
    ("CEO办公室", "现代", "室内", "现代-职场", "白天", "大班台、皮椅、落地窗",
     "A luxurious modern CEO office, a large executive desk, a leather chair, floor-to-ceiling windows with a city skyline view, minimalist decor, empty room, no people, bright daylight."),
    ("会议室", "现代", "室内", "现代-职场", "白天", "长桌、投屏、玻璃墙",
     "A modern corporate meeting room, a long conference table with chairs, a wall-mounted screen, glass walls, empty room, no people, bright daylight."),
    ("写字楼大堂", "现代", "室内", "现代-职场", "白天", "大理石地面、前台、电梯",
     "A modern office building lobby, a polished marble floor, a reception desk, glass doors, elevators, minimalist seating, empty lobby, no people, bright daylight."),
    ("茶水间", "现代", "室内", "现代-职场", "白天", "咖啡机、橱柜、水槽",
     "A modern office pantry, a counter with a coffee machine, cabinets, a small dining table, a sink, empty room, no people, soft daylight."),
    # ----- 现代-都市 -----
    ("城市夜景街道", "现代", "室外", "现代-都市", "夜晚", "霓虹招牌、红绿灯、湿路面",
     "A modern city street at night, glowing storefronts, neon signs, traffic lights, wet asphalt reflecting the lights, tall buildings, empty street, no people, vibrant night lighting."),
    ("咖啡馆", "现代", "室内", "现代-都市", "白天", "木桌、咖啡机、吊灯",
     "A cozy modern cafe interior, wooden tables and chairs, a counter with an espresso machine, hanging lights, plants by the window, empty cafe, no people, warm daylight."),
    ("公寓客厅", "现代", "室内", "现代-都市", "黄昏", "沙发、茶几、落地窗",
     "A modern apartment living room, a comfortable sofa, a coffee table, a TV, large windows with a dusk city view, empty room, no people, warm evening light."),
    ("商场", "现代", "室内", "现代-都市", "白天", "玻璃栏杆、店铺、扶梯",
     "A modern shopping mall interior, multiple floors with glass railings, bright storefronts, escalators, a skylight ceiling, empty mall, no people, bright daylight."),
    ("地铁站", "现代", "室内", "现代-都市", "白天", "瓷砖墙、站台、指示牌",
     "A modern subway station platform, tiled walls, signage, benches, the edge of the track, fluorescent lighting, empty platform, no people, even artificial light."),
    # ----- 科幻-星际 -----
    ("飞船舰桥", "未来", "室内", "科幻-星际", "夜晚", "指挥椅、全息面板、舷窗",
     "A futuristic starship bridge, a command chair, glowing holographic control panels, a large viewport showing stars, sleek metallic walls, empty bridge, no people, cool blue lighting."),
    ("空间站舱内", "未来", "室内", "科幻-星际", "夜晚", "模块壁板、灯带、圆窗",
     "A space station interior corridor, white modular panels, glowing strip lights, circular windows showing outer space, floating cables, empty corridor, no people, cool artificial light."),
    ("外星地表", "未来", "室外", "科幻-星际", "黄昏", "异形岩石、双月、晶体植物",
     "An alien planet surface, strange rock formations, a colored sky with two moons, glowing crystalline plants, vast barren terrain, empty scene, no people, otherworldly dusk light."),
    ("机库", "未来", "室内", "科幻-星际", "白天", "停泊飞船、机械臂、地面标线",
     "A futuristic starship hangar bay, parked spacecraft, robotic arms, glowing floor markings, towering metal structures, empty hangar, no people, bright industrial light."),
    ("指挥中心", "未来", "室内", "科幻-星际", "夜晚", "全息星图、控制台、大屏",
     "A futuristic command center, large holographic star maps, rows of glowing control consoles, a wide viewing screen, empty room, no people, cool blue glow."),
    # ----- 科幻-赛博朋克 -----
    ("霓虹街道", "未来", "室外", "科幻-赛博朋克", "夜晚", "摩天楼、霓虹、全息广告",
     "A cyberpunk city street at night, towering skyscrapers, dense glowing neon signs, holographic advertisements, wet reflective pavement, empty street, no people, vivid neon lighting."),
    ("黑客地下室", "未来", "室内", "科幻-赛博朋克", "夜晚", "显示器墙、线缆、服务器",
     "A cyberpunk hacker den, walls of monitors displaying code, tangled cables, glowing servers, a dim cluttered space, empty room, no people, moody neon glow."),
    ("夜店", "未来", "室内", "科幻-赛博朋克", "夜晚", "霓虹舞池、全息装饰、激光",
     "A cyberpunk nightclub interior, a neon-lit dance floor, holographic decorations, a glowing bar, laser lights, empty club, no people, vibrant colored lighting."),
    ("义体诊所", "未来", "室内", "科幻-赛博朋克", "夜晚", "手术椅、机械义肢、医疗屏",
     "A cyberpunk cybernetics clinic, surgical chairs, robotic limbs on racks, glowing medical screens, sterile metal surfaces, empty clinic, no people, cold clinical light."),
    ("贫民窟巷弄", "未来", "室外", "科幻-赛博朋克", "夜晚", "简易棚屋、乱线、霓虹",
     "A cyberpunk slum alley, cramped makeshift dwellings, tangled wires, flickering neon signs, steam vents, piles of trash, empty alley, no people, gritty neon glow."),
    # ----- 西方玄幻 -----
    ("魔法学院", "古代", "室内", "西方玄幻", "白天", "拱窗、漂浮蜡烛、魔法符文",
     "A grand fantasy magic academy hall, towering arched windows, floating candles, ancient tomes, glowing mystical symbols on the floor, empty hall, no people, magical daylight."),
    ("精灵森林", "古代", "室外", "西方玄幻", "黄昏", "古树、萤火、林间光束",
     "An enchanted elven forest, giant ancient trees, glowing fireflies, soft moss, a winding path, beams of light through the canopy, empty forest, no people, magical dusk glow."),
    ("法师塔", "古代", "室内", "西方玄幻", "夜晚", "旋转楼梯、魔法书、水晶球",
     "Interior of a wizard's tower, a spiral staircase, shelves of spell books and potions, a glowing magical orb, arcane instruments, empty room, no people, mystical candlelight."),
    ("巨龙巢穴", "古代", "室内", "西方玄幻", "夜晚", "金币宝藏、骸骨、余烬",
     "A dragon's lair cavern, massive piles of gold and treasure, scattered bones, glowing embers, jagged rock walls, empty cave, no people, warm fiery glow."),
    ("地下城", "古代", "室内", "西方玄幻", "夜晚", "石廊、牢笼、壁炬",
     "A fantasy dungeon, dark stone corridors, iron-barred cells, flickering wall torches, chains and moss, empty dungeon, no people, dim torchlight."),
    # ----- 近代/民国 -----
    ("民国街道", "近代", "室外", "近代/民国", "白天", "石板路、招牌、黄包车",
     "A 1920s Republic-of-China street, a stone-paved road, shophouses with bilingual signs, rickshaws parked by the curb, vintage street lamps, empty street, no people, soft daylight."),
    ("洋房客厅", "近代", "室内", "近代/民国", "黄昏", "老式沙发、留声机、壁炉",
     "A Republican-era Western-style mansion living room, vintage sofas, a phonograph, patterned wallpaper, a fireplace, tall windows, empty room, no people, warm dusk light."),
    ("戏院", "近代", "室内", "近代/民国", "夜晚", "戏台、红幕、灯笼",
     "A 1930s Chinese theater interior, a wooden stage with red curtains, rows of seats, hanging lanterns, ornate balconies, empty theater, no people, warm stage lighting."),
    ("码头", "近代", "室外", "近代/民国", "黄昏", "木栈桥、停泊船只、货箱",
     "A Republican-era river dock, wooden piers, moored boats, stacked cargo crates, warehouses, distant steamships, empty dock, no people, hazy dusk light."),
    ("报社", "近代", "室内", "近代/民国", "白天", "打字机、印刷机、报纸堆",
     "A 1930s newspaper office, wooden desks with typewriters, a printing press, stacks of newspapers, filing cabinets, empty office, no people, daylight through the windows."),
]


def main() -> None:
    force = "--force" in sys.argv
    init_db()
    conn = get_conn()

    count = count_assets(conn, ASSET_SCENE)
    if count > 0 and not force:
        print(f"scenes 表已有 {count} 条数据，跳过。如需重灌请加 --force")
        conn.close()
        return
    if force:
        clear_assets(conn, ASSET_SCENE)
        conn.commit()
        print("已清空旧场景数据。")

    for name, era, stype, genre, mood, elements, body in SCENES:
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
    conn.commit()
    conn.close()
    print(f"灌入完成：{len(SCENES)} 个场景")


if __name__ == "__main__":
    main()
