ALTER TABLE video_benchmark_items
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;

COMMENT ON COLUMN video_benchmark_items.deleted_at IS '逻辑删除时间，NULL = 未删除';

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_active
    ON video_benchmark_items(id)
 WHERE deleted_at IS NULL;
