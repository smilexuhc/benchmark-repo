"""SQLite 连接与建表。单文件数据库，随项目目录走。"""
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("BENCHMARK_ASSET_DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "app.db")
IMAGES_DIR = os.path.join(DATA_DIR, "images")

# 角色的结构化字段（与 CSV 列、前端筛选一一对应）
CHARACTER_FIELDS = [
    "era",       # 时代
    "type",      # 类型
    "gender",    # 性别
    "age",       # 年龄段
    "persona",   # 人设（服装造型风格）
    "body",      # 身材
    "features",  # 特征
    "genre",     # 常见题材
    "prompt",    # 人物生成提示词
    "description",  # 自由描述（给 AI 写提示词用）
]

# 可作为筛选维度的字段
FILTER_FIELDS = ["era", "type", "gender", "age", "genre"]

# 场景的结构化字段
SCENE_FIELDS = [
    "name",        # 场景名称
    "era",         # 时代
    "scene_type",  # 场景类型（室内/室外）
    "genre",       # 题材风格
    "mood",        # 氛围时段
    "elements",    # 关键元素
    "prompt",      # 场景生成提示词
    "description", # 自由描述
]

# 场景可筛选维度
SCENE_FILTER_FIELDS = ["era", "scene_type", "genre", "mood"]

# 列表中题材的排序：现代 -> 古代 -> 玄幻 -> 科幻/未来
GENRE_ORDER = [
    "现代-职场", "现代-校园", "现代-都市",
    "中国古代", "欧洲中世纪", "近代/民国",
    "中国玄幻", "西方玄幻",
    "科幻-星际", "科幻-赛博朋克", "末世废土",
]


def genre_rank(genre: str) -> int:
    """题材在列表中的排序权重；未知题材排最后。"""
    try:
        return GENRE_ORDER.index(genre or "")
    except ValueError:
        return len(GENRE_ORDER)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            era TEXT DEFAULT '',
            type TEXT DEFAULT '',
            gender TEXT DEFAULT '',
            age TEXT DEFAULT '',
            persona TEXT DEFAULT '',
            body TEXT DEFAULT '',
            features TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            prompt TEXT DEFAULT '',
            description TEXT DEFAULT '',
            cover_image_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            source TEXT DEFAULT 'generated',
            created_at TEXT,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT '',
            era TEXT DEFAULT '',
            scene_type TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            mood TEXT DEFAULT '',
            elements TEXT DEFAULT '',
            prompt TEXT DEFAULT '',
            description TEXT DEFAULT '',
            cover_image_id INTEGER,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS scene_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scene_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            source TEXT DEFAULT 'generated',
            created_at TEXT,
            FOREIGN KEY (scene_id) REFERENCES scenes(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()
