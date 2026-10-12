from uuid import UUID

from fastapi import APIRouter

from app.deps import DbSession, Operator
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
		block_keys=["services", "credentials", "logging", "mask"],
		service_types=["ssh", "http", "tcp_banner", "postgres", "redis", "mysql"],
		auth_modes=[mode.value for mode in AuthMode],
		mask_methods=["jitter", "cover", "path_rotation", "mimicry", "process_mask"],
		example=example,
	)


@router.post("/validate")
def validate_Profile(_body: ProfileCreate) -> dict:
	return {"valid": True}


@router.get("/", response_model=list[ProfileOut])
def list_Profiles(db: DbSession, _operator: Operator) -> list[ProfileOut]:
	return profile_service.list_Profiles(db)


@router.post("/", response_model=ProfileOut, status_code=201)
def create_Profile(db: DbSession, _operator: Operator, body: ProfileCreate) -> ProfileOut:
	return profile_service.create_Profile(db, body)


@router.get("/{profile_id}", response_model=ProfileOut)
def get_Profile(db: DbSession, _operator: Operator, profile_id: UUID) -> ProfileOut:
	return profile_service.get_Profile(db, profile_id)


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_Profile(
	db: DbSession, _operator: Operator, profile_id: UUID, body: ProfileUpdate
) -> ProfileOut:
	return profile_service.update_Profile(db, profile_id, body)


@router.delete("/{profile_id}", status_code=204)
def delete_Profile(db: DbSession, _operator: Operator, profile_id: UUID) -> None:
	profile_service.delete_Profile(db, profile_id)
