DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'assets'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%kind%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE assets DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE assets
    ADD CONSTRAINT assets_kind_check
    CHECK (kind IN ('character', 'scene', 'audio', 'prop', 'video'));

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'asset_images'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%media_type%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE asset_images DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE asset_images
    ADD CONSTRAINT asset_images_media_type_check
    CHECK (media_type IN ('image', 'audio', 'video'));

ALTER TABLE video_benchmark_items
    ADD COLUMN IF NOT EXISTS video_input_id BIGINT,
    ADD COLUMN IF NOT EXISTS video_output_id BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'video_benchmark_video_input_fk'
          AND conrelid = 'video_benchmark_items'::regclass
    ) THEN
        ALTER TABLE video_benchmark_items
            ADD CONSTRAINT video_benchmark_video_input_fk
            FOREIGN KEY (video_input_id) REFERENCES asset_images(id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'video_benchmark_video_output_fk'
          AND conrelid = 'video_benchmark_items'::regclass
    ) THEN
        ALTER TABLE video_benchmark_items
            ADD CONSTRAINT video_benchmark_video_output_fk
            FOREIGN KEY (video_output_id) REFERENCES asset_images(id)
            ON DELETE SET NULL;
    END IF;
END $$;

COMMENT ON COLUMN asset_images.media_type IS '媒体类型：image/audio/video';
COMMENT ON COLUMN video_benchmark_items.video_input_id IS '视频输入素材关联 asset_images.id';
COMMENT ON COLUMN video_benchmark_items.video_output_id IS '视频输出素材关联 asset_images.id';

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_video_input_id
    ON video_benchmark_items(video_input_id);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_video_output_id
    ON video_benchmark_items(video_output_id);

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'video_benchmark_media_links'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%role%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE video_benchmark_media_links DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE video_benchmark_media_links
    ADD CONSTRAINT video_benchmark_media_links_role_check
    CHECK (role IN ('character_image', 'scene_image', 'prop_image', 'audio_input', 'video_input', 'video_output'));
