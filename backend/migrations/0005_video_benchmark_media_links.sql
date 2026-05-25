CREATE TABLE IF NOT EXISTS video_benchmark_media_links (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES video_benchmark_items(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('character_image', 'scene_image', 'prop_image', 'audio_input')),
    media_id BIGINT NOT NULL REFERENCES asset_images(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (item_id, role, media_id)
);

COMMENT ON TABLE video_benchmark_media_links IS '视频 benchmark 题目多选素材关联表';
COMMENT ON COLUMN video_benchmark_media_links.role IS '素材角色：人物图/场景图/道具图/音频输入';

CREATE INDEX IF NOT EXISTS idx_video_benchmark_media_links_item_role
    ON video_benchmark_media_links(item_id, role);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_media_links_media
    ON video_benchmark_media_links(media_id);
