"""Каталог прав операторского API."""

from __future__ import annotations

PERM_PROFILES_READ = "profiles.read"
PERM_PROFILES_WRITE = "profiles.write"
PERM_TRAPS_READ = "traps.read"
PERM_TRAPS_WRITE = "traps.write"
PERM_EVENTS_READ = "events.read"
PERM_PAIRING_WRITE = "pairing.write"
PERM_DEPLOY_WRITE = "deploy.write"
PERM_FS_PACKS_WRITE = "fs_packs.write"
PERM_USERS_WRITE = "users.write"
PERM_ROLES_WRITE = "roles.write"
PERM_AUDIT_READ = "audit.read"
PERM_MAINTENANCE_WRITE = "maintenance.write"

ALL_PERMISSIONS: tuple[str, ...] = (
	PERM_PROFILES_READ,
	PERM_PROFILES_WRITE,
	PERM_TRAPS_READ,
	PERM_TRAPS_WRITE,
	PERM_EVENTS_READ,
	PERM_PAIRING_WRITE,
	PERM_DEPLOY_WRITE,
	PERM_FS_PACKS_WRITE,
	PERM_USERS_WRITE,
	PERM_ROLES_WRITE,
	PERM_AUDIT_READ,
	PERM_MAINTENANCE_WRITE,
)

# Системные роли: имя -> список прав (admin = все).
SYSTEM_ROLE_ADMIN = "admin"
SYSTEM_ROLE_OPERATOR = "operator"
SYSTEM_ROLE_VIEWER = "viewer"

OPERATOR_PERMISSIONS: tuple[str, ...] = (
	PERM_PROFILES_READ,
	PERM_PROFILES_WRITE,
	PERM_TRAPS_READ,
	PERM_TRAPS_WRITE,
	PERM_EVENTS_READ,
	PERM_PAIRING_WRITE,
	PERM_DEPLOY_WRITE,
	PERM_FS_PACKS_WRITE,
	PERM_AUDIT_READ,
)

VIEWER_PERMISSIONS: tuple[str, ...] = (
	PERM_PROFILES_READ,
	PERM_TRAPS_READ,
	PERM_EVENTS_READ,
	PERM_AUDIT_READ,
)


def is_Known_Permission(name: str) -> bool:
	return name in ALL_PERMISSIONS
