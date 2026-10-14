import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base


class AuditLog(Base):
	__tablename__ = "audit_log"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	actor: Mapped[str | None] = mapped_column(Text, nullable=True)
	action: Mapped[str] = mapped_column(Text, nullable=False)
	resource_type: Mapped[str | None] = mapped_column(Text, nullable=True)
	resource_id: Mapped[str | None] = mapped_column(Text, nullable=True)
	payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Profile(Base):
	__tablename__ = "profiles"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	name: Mapped[str] = mapped_column(Text, nullable=False)
	description: Mapped[str] = mapped_column(Text, nullable=False, default="")
	interaction_level: Mapped[str] = mapped_column(Text, nullable=False)
	blocks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
	config_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
	config_hash: Mapped[str] = mapped_column(Text, nullable=False, default="")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
	)


class Trap(Base):
	__tablename__ = "traps"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	name: Mapped[str] = mapped_column(Text, nullable=False)
	profile_id: Mapped[uuid.UUID | None] = mapped_column(
		Uuid, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
	)
	status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
	agent_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
	last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
	)


class PairingSession(Base):
	__tablename__ = "pairing_sessions"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	device_code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
	trap_id: Mapped[uuid.UUID | None] = mapped_column(
		Uuid, ForeignKey("traps.id", ondelete="CASCADE"), nullable=True
	)
	status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
	registration_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
	pending_agent_token: Mapped[str | None] = mapped_column(Text, nullable=True)
	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base):
	__tablename__ = "events"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	trap_id: Mapped[uuid.UUID | None] = mapped_column(
		Uuid, ForeignKey("traps.id", ondelete="SET NULL"), nullable=True
	)
	event_type: Mapped[str] = mapped_column(Text, nullable=False)
	# строка вместо INET - совместимо с SQLite и Postgres
	source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
	source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
	occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrapCommand(Base):
	"""Очередь команд центр -> агент (reload/rotate)."""

	__tablename__ = "trap_commands"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	trap_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("traps.id", ondelete="CASCADE"))
	command_type: Mapped[str] = mapped_column(Text, nullable=False)
	payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
	status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FsPack(Base):
	__tablename__ = "fs_packs"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
	name: Mapped[str] = mapped_column(Text, nullable=False)
	original_filename: Mapped[str] = mapped_column(Text, nullable=False, default="")
	format: Mapped[str] = mapped_column(Text, nullable=False)
	size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
	sha256: Mapped[str] = mapped_column(Text, nullable=False, default="")
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
	__tablename__ = "roles"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
	is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	permissions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
	__tablename__ = "users"

	id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
	username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
	password_hash: Mapped[str] = mapped_column(Text, nullable=False)
	is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	role_id: Mapped[uuid.UUID] = mapped_column(
		Uuid, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
	)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
