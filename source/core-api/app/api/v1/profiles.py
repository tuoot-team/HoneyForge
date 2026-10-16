from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, DbSession, require_Permission
from app.domains.profiles import service as profile_service
from app.domains.profiles.schemas import (
	AuthMode,
	InteractionLevel,
	ProfileBlocks,
	ProfileCreate,
	ProfileOut,
	ProfileSchemaDoc,
	ProfileUpdate,
	SshServiceBlock,
)
from app.domains.rbac import service as rbac_service
from app.domains.rbac.permissions import PERM_PROFILES_READ, PERM_PROFILES_WRITE

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/schema", response_model=ProfileSchemaDoc)
def get_ProfileSchema() -> ProfileSchemaDoc:
	"""Документация блоков конструктора для CLI/Web."""
	example = ProfileCreate(
		name="demo-medium-ssh",
		description="example medium profile",
		interaction_level=InteractionLevel.medium,
		blocks=ProfileBlocks(
			services=[SshServiceBlock(port=22)],
		),
	)
	return ProfileSchemaDoc(
		interaction_levels=[level.value for level in InteractionLevel],
		block_keys=["services", "credentials", "baits", "honeytokens", "emulation", "logging", "mask"],
		service_types=["ssh", "http", "tcp_banner", "postgres", "redis", "mysql", "container"],
		auth_modes=[mode.value for mode in AuthMode],
		mask_methods=[
			"courier",
			"jitter",
			"cover",
			"path_rotation",
			"mimicry",
			"process_mask",
		],
		example=example,
	)


@router.post("/validate")
def validate_Profile(_body: ProfileCreate) -> dict:
	return {"valid": True}


@router.get("/", response_model=list[ProfileOut])
def list_Profiles(
	db: DbSession,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> list[ProfileOut]:
	return profile_service.list_Profiles(db)


@router.post("/", response_model=ProfileOut, status_code=201)
def create_Profile(
	db: DbSession,
	body: ProfileCreate,
	operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_WRITE)),
) -> ProfileOut:
	out = profile_service.create_Profile(db, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="profile.create",
		resource_type="profile",
		resource_id=str(out.id),
		payload={"name": out.name},
	)
	return out


@router.get("/{profile_id}", response_model=ProfileOut)
def get_Profile(
	db: DbSession,
	profile_id: UUID,
	_operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_READ)),
) -> ProfileOut:
	return profile_service.get_Profile(db, profile_id)


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_Profile(
	db: DbSession,
	profile_id: UUID,
	body: ProfileUpdate,
	operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_WRITE)),
) -> ProfileOut:
	out = profile_service.update_Profile(db, profile_id, body)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="profile.update",
		resource_type="profile",
		resource_id=str(out.id),
	)
	return out


@router.delete("/{profile_id}", status_code=204)
def delete_Profile(
	db: DbSession,
	profile_id: UUID,
	operator: CurrentUser = Depends(require_Permission(PERM_PROFILES_WRITE)),
) -> None:
	profile_service.delete_Profile(db, profile_id)
	rbac_service.write_Audit(
		db,
		actor=operator.username,
		action="profile.delete",
		resource_type="profile",
		resource_id=str(profile_id),
	)
