ALTER TABLE video_benchmark_items
    ADD COLUMN IF NOT EXISTS judging_criteria TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN video_benchmark_items.judging_criteria IS '评判标准';
