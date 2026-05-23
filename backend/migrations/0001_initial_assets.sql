CREATE TABLE IF NOT EXISTS assets (
    id BIGSERIAL PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('character', 'scene')),
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    cover_image_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS asset_images (
    id BIGSERIAL PRIMARY KEY,
    asset_id BIGINT NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    object_key TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'generated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);
CREATE INDEX IF NOT EXISTS idx_assets_data ON assets USING GIN (data);
CREATE INDEX IF NOT EXISTS idx_asset_images_asset ON asset_images(asset_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'assets_cover_image_fk'
    ) THEN
        ALTER TABLE assets
        ADD CONSTRAINT assets_cover_image_fk
        FOREIGN KEY (cover_image_id) REFERENCES asset_images(id)
        ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;
