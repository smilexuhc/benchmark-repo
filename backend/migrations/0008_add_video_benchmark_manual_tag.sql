ALTER TABLE video_benchmark_items
    ADD COLUMN IF NOT EXISTS manual_tag TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN video_benchmark_items.manual_tag IS '测试点人工标注';
