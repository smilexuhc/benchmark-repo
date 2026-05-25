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
    CHECK (kind IN ('character', 'scene', 'audio', 'prop'));
