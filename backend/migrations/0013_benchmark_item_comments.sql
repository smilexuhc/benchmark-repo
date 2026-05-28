ALTER TABLE video_benchmark_items
    ADD COLUMN IF NOT EXISTS needs_revision BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS benchmark_item_comments (
    id BIGSERIAL PRIMARY KEY,
    item_id BIGINT NOT NULL REFERENCES video_benchmark_items(id) ON DELETE CASCADE,
    author TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_item_comments_item
    ON benchmark_item_comments(item_id);
