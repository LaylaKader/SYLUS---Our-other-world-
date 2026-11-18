-- Keep the database's accepted formats aligned with server-side signature detection.
DO $$
DECLARE constraint_name TEXT;
BEGIN
    FOR constraint_name IN
        SELECT c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'visual_reference_images'
          AND c.contype = 'c'
          AND pg_get_constraintdef(c.oid) ILIKE '%content_type%'
    LOOP
        EXECUTE format('ALTER TABLE visual_reference_images DROP CONSTRAINT %I', constraint_name);
    END LOOP;
END $$;

ALTER TABLE visual_reference_images
    ADD CONSTRAINT visual_reference_images_content_type_check
    CHECK (content_type IN (
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
        'image/avif',
        'image/heic'
    ));
