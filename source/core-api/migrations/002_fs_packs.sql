-- Пакеты файловой системы для fake shell (архивы zip / tar.gz).

CREATE TABLE IF NOT EXISTS fs_packs (
	id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	token               TEXT NOT NULL UNIQUE,
	name                TEXT NOT NULL,
	original_filename   TEXT NOT NULL DEFAULT '',
	format              TEXT NOT NULL,
	size_bytes          BIGINT NOT NULL DEFAULT 0,
	sha256              TEXT NOT NULL DEFAULT '',
	created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	CONSTRAINT fs_packs_format_check CHECK (format IN ('zip', 'tar_gz'))
);

CREATE INDEX IF NOT EXISTS idx_fs_packs_token ON fs_packs (token);
CREATE INDEX IF NOT EXISTS idx_fs_packs_created_at ON fs_packs (created_at DESC);
