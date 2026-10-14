-- Владелец ловушки (операторский user).

ALTER TABLE traps
	ADD COLUMN IF NOT EXISTS owner_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_traps_owner_user_id ON traps (owner_user_id);
