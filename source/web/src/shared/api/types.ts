export type PermissionName =
	| "profiles.read"
	| "profiles.write"
	| "traps.read"
	| "traps.write"
	| "traps.all"
	| "events.read"
	| "pairing.write"
	| "deploy.write"
	| "fs_packs.write"
	| "vm_images.write"
	| "users.write"
	| "roles.write"
	| "audit.read"
	| "maintenance.write"
	| "couriers.read"
	| "couriers.write"

export type InteractionLevel = "low" | "medium" | "high"
export type EventPriority = "low" | "medium" | "high"
export type AuthMode = "allow_all" | "allow_listed" | "second_attempt_sticky"
export type ServiceType = "ssh" | "http" | "tcp_banner" | "postgres" | "redis" | "mysql" | "container"

export type Me = {
	authenticated: boolean
	username: string
	role: string
	role_id: string
	is_superadmin: boolean
	permissions: string[]
}

export type Profile = {
	id: string
	name: string
	description: string
	interaction_level: InteractionLevel
	blocks: ProfileBlocks
	config_version: number
	config_hash: string
	created_at: string
	updated_at: string
}

export type ProfileBlocks = {
	services?: ServiceRecord[]
	credentials?: CredentialRecord[]
	baits?: unknown[]
	honeytokens?: unknown[]
	emulation?: EmulationRecord
	logging?: LoggingRecord
	mask?: MaskRecord
}

export type ServiceRecord = {
	type: ServiceType | string
	id: string
	port: number
	enabled?: boolean
	modules?: Record<string, unknown>
}

export type CredentialRecord = {
	id: string
	username: string
	password: string
	note?: string
}

export type LoggingRecord = {
	capture_credentials?: boolean
	capture_payloads?: boolean
	capture_source_meta?: boolean
}

export type MaskRecord = {
	collection_mode?: "agent" | "courier"
	courier?: { enabled?: boolean; collect_interval_sec?: number }
	jitter?: { enabled?: boolean; beacon_interval_sec?: number; jitter_pct?: number }
	cover?: { enabled?: boolean; urls?: string[] }
	path_rotation?: { enabled?: boolean; paths?: string[] }
	mimicry?: { enabled?: boolean; user_agent?: string; tls_fingerprint_profile?: string }
	process_mask?: { enabled?: boolean; name?: string }
	decoy_content_seed?: string
	service_personality?: string
}

export type EmulationRecord = {
	enabled?: boolean
	runtime?: string
	image_token?: string
	vm_name?: string
	cpus?: number
	memory_mb?: number
	snapshot?: string
	expose?: unknown[]
	auto_start?: boolean
}

export type Trap = {
	id: string
	name: string
	profile_id: string | null
	owner_user_id: string | null
	status: "pending" | "online" | "offline"
	last_seen_at: string | null
	meta: Record<string, unknown>
	has_courier_ssh: boolean
	courier_ssh_host: string | null
	created_at: string
	updated_at: string
}

export type PairingSession = {
	pairing_id: string
	device_code: string
	status: string
	trap_id: string | null
	expires_at: string
	created_at: string
	completed_at: string | null
}

export type EventItem = {
	id: number
	trap_id: string | null
	event_type: string
	source_ip: string | null
	source_port: number | null
	occurred_at: string | null
	payload: Record<string, unknown>
	created_at?: string
	priority: EventPriority
}

export type EventChain = {
	trap_id: string | null
	source_ip: string
	event_count: number
	ports: number[]
	services: string[]
	event_types: string[]
	first_at: string | null
	last_at: string | null
	is_lateral: boolean
	max_priority: EventPriority
}

export type UserRecord = {
	id: string
	username: string
	is_superadmin: boolean
	disabled: boolean
	role_id: string
	role_name: string
	created_at: string | null
}

export type RoleRecord = {
	id: string
	name: string
	is_system: boolean
	permissions: string[]
	created_at: string | null
}

export type CourierRecord = {
	id: string
	name: string
	status: "pending" | "online" | "offline"
	owner_user_id: string | null
	last_seen_at: string | null
	created_at: string
	updated_at: string
}

export type CourierPairing = {
	id: string
	device_code: string
	status: string
	courier_id: string | null
	expires_at: string
	created_at: string
}

export type PackRecord = {
	token: string
	name: string
	original_filename: string
	format: string
	size_bytes: number
	sha256: string
	created_at: string
}

export type PersonalityPack = {
	key: string
	title: string
}

export type DeployResult = {
	device_code?: string | null
	host?: string
	user?: string
	port?: number
	center_url?: string
	ok?: boolean
	detail?: string
}

export type WipeResult = {
	deleted: Record<string, number>
}
