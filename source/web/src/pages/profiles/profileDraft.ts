import type {
	AuthMode,
	CredentialRecord,
	InteractionLevel,
	Profile,
	ProfileBlocks,
	ServiceRecord,
	ServiceType,
} from "../../shared/api/types"
import { splitList } from "../../shared/lib/format"

export type ServiceDraft = {
	type: ServiceType
	id: string
	port: number
	enabled: boolean
	banner: string
	httpTitle: string
	authEnabled: boolean
	authMode: AuthMode
	credentialIds: string
	delayMin: number
	delayMax: number
	shellEnabled: boolean
	fsPack: string
	image: string
	containerPort: number
}

export type CredentialDraft = {
	id: string
	username: string
	password: string
	note: string
}

export type ProfileDraft = {
	name: string
	description: string
	interactionLevel: InteractionLevel
	services: ServiceDraft[]
	credentials: CredentialDraft[]
	baits: unknown[]
	honeytokens: unknown[]
	expose: unknown[]
	captureCredentials: boolean
	capturePayloads: boolean
	captureSourceMeta: boolean
	courierEnabled: boolean
	collectIntervalSec: number
	jitterEnabled: boolean
	beaconIntervalSec: number
	jitterPct: number
	coverEnabled: boolean
	coverUrls: string
	pathRotationEnabled: boolean
	paths: string
	mimicryEnabled: boolean
	userAgent: string
	tlsProfile: string
	processMaskEnabled: boolean
	processName: string
	decoyContentSeed: string
	servicePersonality: string
	emulationEnabled: boolean
	imageToken: string
	vmName: string
	vmCpus: number
	vmMemoryMb: number
}

const serviceTypes: ServiceType[] = ["ssh", "http", "tcp_banner", "postgres", "redis", "mysql", "container"]

export function createServiceDraft(type: ServiceType, index: number): ServiceDraft {
	const interactive = type !== "tcp_banner"
	return {
		type,
		id: `${type}-${index}`,
		port: defaultPort(type),
		enabled: true,
		banner: defaultBanner(type),
		httpTitle: "IIS Windows Server",
		authEnabled: interactive && type !== "container",
		authMode: "allow_all",
		credentialIds: "",
		delayMin: 0,
		delayMax: 0,
		shellEnabled: type === "ssh",
		fsPack: "ubuntu-22.04",
		image: "nginx:1.24",
		containerPort: 80,
	}
}

export function createEmptyDraft(): ProfileDraft {
	return {
		name: "",
		description: "",
		interactionLevel: "medium",
		services: [createServiceDraft("ssh", 1)],
		credentials: [],
		baits: [],
		honeytokens: [],
		expose: [],
		captureCredentials: true,
		capturePayloads: true,
		captureSourceMeta: true,
		courierEnabled: false,
		collectIntervalSec: 300,
		jitterEnabled: true,
		beaconIntervalSec: 30,
		jitterPct: 30,
		coverEnabled: true,
		coverUrls: "/favicon.ico, /robots.txt",
		pathRotationEnabled: true,
		paths: "/v1/metrics, /cdn/edge-check",
		mimicryEnabled: true,
		userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
		tlsProfile: "browser-like",
		processMaskEnabled: true,
		processName: "metricsd",
		decoyContentSeed: "",
		servicePersonality: "",
		emulationEnabled: false,
		imageToken: "",
		vmName: "hf-guest",
		vmCpus: 2,
		vmMemoryMb: 4096,
	}
}

export function draftFromProfile(profile: Profile): ProfileDraft {
	const blocks = profile.blocks ?? {}
	const mask = blocks.mask ?? {}
	const base = createEmptyDraft()
	return {
		...base,
		name: profile.name,
		description: profile.description ?? "",
		interactionLevel: profile.interaction_level,
		services: (blocks.services ?? []).map((service, index) => serviceFromApi(service, index + 1)),
		credentials: (blocks.credentials ?? []).map(credentialFromApi),
		baits: blocks.baits ?? [],
		honeytokens: blocks.honeytokens ?? [],
		expose: blocks.emulation?.expose ?? [],
		captureCredentials: blocks.logging?.capture_credentials !== false,
		capturePayloads: blocks.logging?.capture_payloads !== false,
		captureSourceMeta: blocks.logging?.capture_source_meta !== false,
		courierEnabled: Boolean(mask.courier?.enabled) || mask.collection_mode === "courier",
		collectIntervalSec: mask.courier?.collect_interval_sec ?? 300,
		jitterEnabled: mask.jitter?.enabled !== false && mask.collection_mode !== "courier",
		beaconIntervalSec: mask.jitter?.beacon_interval_sec ?? 30,
		jitterPct: mask.jitter?.jitter_pct ?? 30,
		coverEnabled: Boolean(mask.cover?.enabled),
		coverUrls: (mask.cover?.urls ?? []).join(", "),
		pathRotationEnabled: Boolean(mask.path_rotation?.enabled),
		paths: (mask.path_rotation?.paths ?? []).join(", "),
		mimicryEnabled: mask.mimicry?.enabled !== false && mask.collection_mode !== "courier",
		userAgent: mask.mimicry?.user_agent ?? base.userAgent,
		tlsProfile: mask.mimicry?.tls_fingerprint_profile ?? "browser-like",
		processMaskEnabled: Boolean(mask.process_mask?.enabled),
		processName: mask.process_mask?.name || "metricsd",
		decoyContentSeed: mask.decoy_content_seed ?? "",
		servicePersonality: mask.service_personality ?? "",
		emulationEnabled: Boolean(blocks.emulation?.enabled),
		imageToken: blocks.emulation?.image_token ?? "",
		vmName: blocks.emulation?.vm_name || "hf-guest",
		vmCpus: blocks.emulation?.cpus ?? 2,
		vmMemoryMb: blocks.emulation?.memory_mb ?? 4096,
	}
}

export function profileBodyFromDraft(draft: ProfileDraft) {
	const blocks: ProfileBlocks = {
		services: draft.services.map(serviceToApi),
		credentials: draft.credentials.map(credentialToApi),
		baits: draft.baits,
		honeytokens: draft.honeytokens,
		logging: {
			capture_credentials: draft.captureCredentials,
			capture_payloads: draft.capturePayloads,
			capture_source_meta: draft.captureSourceMeta,
		},
		mask: {
			collection_mode: draft.courierEnabled ? "courier" : "agent",
			courier: {
				enabled: draft.courierEnabled,
				collect_interval_sec: numberOr(draft.collectIntervalSec, 300),
			},
			jitter: {
				enabled: draft.jitterEnabled && !draft.courierEnabled,
				beacon_interval_sec: numberOr(draft.beaconIntervalSec, 30),
				jitter_pct: numberOr(draft.jitterPct, 0),
			},
			cover: {
				enabled: draft.coverEnabled && !draft.courierEnabled,
				urls: splitList(draft.coverUrls),
			},
			path_rotation: {
				enabled: draft.pathRotationEnabled && !draft.courierEnabled,
				paths: splitList(draft.paths),
			},
			mimicry: {
				enabled: draft.mimicryEnabled && !draft.courierEnabled,
				user_agent: draft.userAgent,
				tls_fingerprint_profile: draft.tlsProfile || "browser-like",
			},
			process_mask: {
				enabled: draft.processMaskEnabled && !draft.courierEnabled,
				name: draft.processName || "metricsd",
			},
			decoy_content_seed: draft.decoyContentSeed,
			service_personality: draft.servicePersonality,
		},
		emulation: {
			enabled: draft.emulationEnabled,
			runtime: "virtualbox",
			image_token: draft.imageToken.trim(),
			vm_name: draft.vmName.trim() || "hf-guest",
			cpus: numberOr(draft.vmCpus, 2),
			memory_mb: numberOr(draft.vmMemoryMb, 4096),
			snapshot: "clean",
			expose: draft.expose,
			auto_start: true,
		},
	}
	return {
		name: draft.name.trim(),
		description: draft.description,
		interaction_level: draft.interactionLevel,
		blocks,
	}
}

export function suggestInteractionLevel(draft: ProfileDraft): InteractionLevel {
	if (draft.emulationEnabled) {
		return "high"
	}
	let level: InteractionLevel = "low"
	for (const service of draft.services) {
		if (!service.enabled) {
			continue
		}
		if (service.type !== "ssh" && service.type !== "tcp_banner") {
			return "medium"
		}
		if (service.type === "ssh" && (service.authEnabled || service.shellEnabled)) {
			level = "medium"
		}
	}
	return level
}

function serviceToApi(service: ServiceDraft): ServiceRecord {
	const common = {
		id: service.id.trim() || service.type,
		port: numberOr(service.port, 1),
		enabled: service.enabled,
	}
	if (service.type === "tcp_banner") {
		return { type: "tcp_banner", ...common, modules: { banner: service.banner } }
	}
	if (service.type === "container") {
		return {
			type: "container",
			...common,
			modules: { image: service.image.trim(), container_port: numberOr(service.containerPort, 0) },
		}
	}
	const auth = {
		enabled: service.authEnabled,
		mode: service.authMode,
		credential_ids: splitList(service.credentialIds),
		delay_ms_min: numberOr(service.delayMin, 0),
		delay_ms_max: numberOr(service.delayMax, 0),
	}
	if (service.type === "ssh") {
		return {
			type: "ssh",
			...common,
			modules: {
				banner: { enabled: true, version: service.banner },
				auth,
				shell: { enabled: service.shellEnabled, fs_pack: service.fsPack || "ubuntu-22.04" },
			},
		}
	}
	if (service.type === "http") {
		return {
			type: "http",
			...common,
			modules: {
				personality: {
					enabled: true,
					server: service.banner || "nginx/1.24.0",
					title: service.httpTitle,
				},
				auth: { ...auth, path: "/admin", realm: "Restricted" },
				routes: { routes: [], default_status: 404, default_body: "404 - File or directory not found." },
			},
		}
	}
	return {
		type: service.type,
		...common,
		modules: {
			banner: { enabled: true, version: service.banner },
			auth,
			session: { enabled: true, max_session_sec: 120 },
		},
	}
}

function serviceFromApi(service: ServiceRecord, index: number): ServiceDraft {
	const type = isServiceType(service.type) ? service.type : "tcp_banner"
	const draft = createServiceDraft(type, index)
	const modules = service.modules ?? {}
	const auth = asRecord(modules.auth)
	const ids = Array.isArray(auth.credential_ids) ? auth.credential_ids.map(String) : []
	const banner = readBanner(type, modules)
	const shell = asRecord(modules.shell)
	return {
		...draft,
		type,
		id: service.id || draft.id,
		port: Number(service.port) || draft.port,
		enabled: service.enabled !== false,
		banner: banner.banner,
		httpTitle: banner.httpTitle || draft.httpTitle,
		authEnabled: Boolean(auth.enabled),
		authMode: isAuthMode(auth.mode) ? auth.mode : "allow_all",
		credentialIds: ids.join(", "),
		delayMin: Number(auth.delay_ms_min ?? 0),
		delayMax: Number(auth.delay_ms_max ?? 0),
		shellEnabled: Boolean(shell.enabled),
		fsPack: String(shell.fs_pack ?? draft.fsPack),
		image: String(modules.image ?? draft.image),
		containerPort: Number(modules.container_port ?? draft.containerPort),
	}
}

function credentialToApi(item: CredentialDraft): CredentialRecord {
	return {
		id: item.id.trim(),
		username: item.username,
		password: item.password,
		note: item.note,
	}
}

function credentialFromApi(item: CredentialRecord): CredentialDraft {
	return {
		id: item.id,
		username: item.username ?? "",
		password: item.password ?? "",
		note: item.note ?? "",
	}
}

function readBanner(type: ServiceType, modules: Record<string, unknown>) {
	if (type === "tcp_banner") {
		return { banner: typeof modules.banner === "string" ? modules.banner : "", httpTitle: "" }
	}
	if (type === "http") {
		const personality = asRecord(modules.personality)
		return { banner: String(personality.server ?? ""), httpTitle: String(personality.title ?? "") }
	}
	const banner = asRecord(modules.banner)
	return { banner: String(banner.version ?? ""), httpTitle: "" }
}

function asRecord(value: unknown): Record<string, unknown> {
	return value && typeof value === "object" ? (value as Record<string, unknown>) : {}
}

function isServiceType(value: string): value is ServiceType {
	return serviceTypes.includes(value as ServiceType)
}

function isAuthMode(value: unknown): value is AuthMode {
	return value === "allow_all" || value === "allow_listed" || value === "second_attempt_sticky"
}

function numberOr(value: number, fallback: number): number {
	return Number.isFinite(Number(value)) ? Number(value) : fallback
}

function defaultPort(type: ServiceType): number {
	if (type === "http") return 80
	if (type === "postgres") return 5432
	if (type === "redis") return 6379
	if (type === "mysql") return 3306
	if (type === "container") return 8080
	return 22
}

function defaultBanner(type: ServiceType): string {
	if (type === "http") return "Microsoft-IIS/10.0"
	if (type === "tcp_banner") return ""
	if (type === "postgres") return "PostgreSQL 14.0"
	if (type === "redis") return "6.2.6"
	if (type === "mysql") return "5.7.33"
	if (type === "ssh") return "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"
	return ""
}
