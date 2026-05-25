ALTER TABLE asset_images
    ADD COLUMN IF NOT EXISTS media_type TEXT NOT NULL DEFAULT 'image';

DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'assets'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%kind%'
      AND pg_get_constraintdef(oid) LIKE '%character%'
      AND pg_get_constraintdef(oid) LIKE '%scene%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE assets DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE assets
    ADD CONSTRAINT assets_kind_check
    CHECK (kind IN ('character', 'scene', 'audio'));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'asset_images_media_type_check'
          AND conrelid = 'asset_images'::regclass
    ) THEN
        ALTER TABLE asset_images
            ADD CONSTRAINT asset_images_media_type_check
            CHECK (media_type IN ('image', 'audio'));
    END IF;
END $$;

ALTER TABLE video_benchmark_items
    ADD COLUMN IF NOT EXISTS character_image_id BIGINT,
    ADD COLUMN IF NOT EXISTS scene_image_id BIGINT,
    ADD COLUMN IF NOT EXISTS prop_image_id BIGINT,
    ADD COLUMN IF NOT EXISTS audio_input_id BIGINT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'video_benchmark_character_image_fk'
          AND conrelid = 'video_benchmark_items'::regclass
    ) THEN
        ALTER TABLE video_benchmark_items
            ADD CONSTRAINT video_benchmark_character_image_fk
            FOREIGN KEY (character_image_id) REFERENCES asset_images(id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'video_benchmark_scene_image_fk'
          AND conrelid = 'video_benchmark_items'::regclass
    ) THEN
        ALTER TABLE video_benchmark_items
            ADD CONSTRAINT video_benchmark_scene_image_fk
            FOREIGN KEY (scene_image_id) REFERENCES asset_images(id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'video_benchmark_prop_image_fk'
          AND conrelid = 'video_benchmark_items'::regclass
    ) THEN
        ALTER TABLE video_benchmark_items
            ADD CONSTRAINT video_benchmark_prop_image_fk
            FOREIGN KEY (prop_image_id) REFERENCES asset_images(id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'video_benchmark_audio_input_fk'
          AND conrelid = 'video_benchmark_items'::regclass
    ) THEN
        ALTER TABLE video_benchmark_items
            ADD CONSTRAINT video_benchmark_audio_input_fk
            FOREIGN KEY (audio_input_id) REFERENCES asset_images(id)
            ON DELETE SET NULL;
    END IF;
END $$;

COMMENT ON COLUMN asset_images.media_type IS '媒体类型：image/audio';
COMMENT ON COLUMN video_benchmark_items.character_image_id IS '人物图片素材关联 asset_images.id';
COMMENT ON COLUMN video_benchmark_items.scene_image_id IS '场景图片素材关联 asset_images.id';
COMMENT ON COLUMN video_benchmark_items.prop_image_id IS '道具图片素材关联 asset_images.id';
COMMENT ON COLUMN video_benchmark_items.audio_input_id IS '音频输入素材关联 asset_images.id';

CREATE INDEX IF NOT EXISTS idx_asset_images_media_type
    ON asset_images(media_type);

CREATE INDEX IF NOT EXISTS idx_asset_images_object_key
    ON asset_images(object_key);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_character_image_id
    ON video_benchmark_items(character_image_id);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_scene_image_id
    ON video_benchmark_items(scene_image_id);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_prop_image_id
    ON video_benchmark_items(prop_image_id);

CREATE INDEX IF NOT EXISTS idx_video_benchmark_items_audio_input_id
    ON video_benchmark_items(audio_input_id);
