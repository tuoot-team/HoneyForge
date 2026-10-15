-- Образы High VM (OVA для VirtualBox).

CREATE TABLE IF NOT EXISTS vm_images (
	id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	token               TEXT NOT NULL UNIQUE,
	name                TEXT NOT NULL,
	original_filename   TEXT NOT NULL DEFAULT '',
	format              TEXT NOT NULL,
	size_bytes          BIGINT NOT NULL DEFAULT 0,
	sha256              TEXT NOT NULL DEFAULT '',
	created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT vm_images_format_check CHECK (format IN ('ova', 'vdi', 'vmdk'))
);

CREATE INDEX IF NOT EXISTS idx_vm_images_token ON vm_images (token);
CREATE INDEX IF NOT EXISTS idx_vm_images_created_at ON vm_images (created_at DESC);
