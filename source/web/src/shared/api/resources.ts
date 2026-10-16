import { requestApi, requestApiText, withQuery } from "./http"
import type {
	CourierPairing,
	CourierRecord,
	DeployResult,
	EventChain,
	EventItem,
	Me,
	PackRecord,
	PairingSession,
	PersonalityPack,
	Profile,
	RoleRecord,
	Trap,
	UserRecord,
	WipeResult,
} from "./types"

export function loginRequest(username: string, password: string) {
	return requestApi<{ access_token: string }>("POST", "/api/v1/auth/login", {
		auth: false,
		body: { username, password },
	})
}

export function logoutRequest() {
	return requestApi<{ ok: boolean }>("POST", "/api/v1/auth/logout")
}

export function fetchMe() {
	return requestApi<Me>("GET", "/api/v1/auth/me")
}

export function listProfiles() {
	return requestApi<Profile[]>("GET", "/api/v1/profiles/")
}

export function getProfile(profileId: string) {
	return requestApi<Profile>("GET", `/api/v1/profiles/${profileId}`)
}

export function validateProfile(body: unknown) {
	return requestApi<{ valid: boolean }>("POST", "/api/v1/profiles/validate", { auth: false, body })
}

export function createProfile(body: unknown) {
	return requestApi<Profile>("POST", "/api/v1/profiles/", { body })
}

export function updateProfile(profileId: string, body: unknown) {
	return requestApi<Profile>("PATCH", `/api/v1/profiles/${profileId}`, { body })
}

export function deleteProfile(profileId: string) {
	return requestApi<void>("DELETE", `/api/v1/profiles/${profileId}`)
}

export function listTraps() {
	return requestApi<Trap[]>("GET", "/api/v1/traps/")
}

export function bindTrapProfile(trapId: string, profileId: string) {
	return requestApi<Trap>("POST", `/api/v1/traps/${trapId}/bind-profile`, {
		body: { profile_id: profileId },
	})
}

export function setTrapOwner(trapId: string, userId: string) {
	return requestApi<Trap>("PATCH", `/api/v1/traps/${trapId}/owner`, {
		body: { user_id: userId },
	})
}

export function trapVmAction(trapId: string, action: string) {
	return requestApi<Trap>("POST", `/api/v1/traps/${trapId}/vm/${action}`)
}

export function setTrapCourierSsh(trapId: string, body: unknown) {
	return requestApi<{ ok?: boolean; trap_id?: string; host?: string }>(
		"PATCH",
		`/api/v1/traps/${trapId}/courier-ssh`,
		{ body },
	)
}

export function listPairings(status: string) {
	return requestApi<{ total: number; items: PairingSession[] }>(
		"GET",
		withQuery("/api/v1/pairing/", { status }),
	)
}

export function confirmPairing(body: unknown) {
	return requestApi<Record<string, unknown>>("POST", "/api/v1/pairing/confirm", { body })
}

export function deployAgent(body: unknown) {
	return requestApi<DeployResult>("POST", "/api/v1/deploy/agent", { body })
}

export function listEvents(params: Record<string, string | number | undefined>) {
	return requestApi<{ items: EventItem[]; total: number }>("GET", withQuery("/api/v1/events/", params))
}

export function listEventChains(params: Record<string, string | number | undefined>) {
	return requestApi<{ items: EventChain[]; total: number }>("GET", withQuery("/api/v1/events/chains", params))
}

export function exportEvents(params: Record<string, string | number | undefined>) {
	return requestApiText("GET", withQuery("/api/v1/events/export", params))
}

export function listCouriers() {
	return requestApi<CourierRecord[]>("GET", "/api/v1/couriers/")
}

export function listCourierPairings(status: string) {
	return requestApi<{ total: number; items: CourierPairing[] }>(
		"GET",
		withQuery("/api/v1/courier-pairing/", { status }),
	)
}

export function confirmCourier(body: unknown) {
	return requestApi<Record<string, unknown>>("POST", "/api/v1/courier-pairing/confirm", { body })
}

export function deployCourier(body: unknown) {
	return requestApi<DeployResult>("POST", "/api/v1/deploy/courier", { body })
}

export function listFsPacks() {
	return requestApi<{ items: PackRecord[]; total: number }>("GET", "/api/v1/fs-packs/")
}

export function uploadFsPack(file: File, name: string) {
	const form = new FormData()
	form.set("file", file)
	if (name.trim()) {
		form.set("name", name.trim())
	}
	return requestApi<PackRecord>("POST", "/api/v1/fs-packs/", { form })
}

export function deleteFsPack(token: string) {
	return requestApi<void>("DELETE", `/api/v1/fs-packs/${token}`)
}

export function listVmImages() {
	return requestApi<{ items: PackRecord[]; total: number }>("GET", "/api/v1/vm-images/")
}

export function uploadVmImage(file: File, name: string) {
	const form = new FormData()
	form.set("file", file)
	if (name.trim()) {
		form.set("name", name.trim())
	}
	return requestApi<PackRecord>("POST", "/api/v1/vm-images/", { form })
}

export function deleteVmImage(token: string) {
	return requestApi<void>("DELETE", `/api/v1/vm-images/${token}`)
}

export function listPersonalityPacks() {
	return requestApi<{ items: PersonalityPack[]; total: number }>("GET", "/api/v1/personality-packs/")
}

export function listUsers() {
	return requestApi<UserRecord[]>("GET", "/api/v1/users/")
}

export function createUser(body: unknown) {
	return requestApi<UserRecord>("POST", "/api/v1/users/", { body })
}

export function updateUser(userId: string, body: unknown) {
	return requestApi<UserRecord>("PATCH", `/api/v1/users/${userId}`, { body })
}

export function listRoles() {
	return requestApi<RoleRecord[]>("GET", "/api/v1/roles/")
}

export function listPermissionCatalog() {
	return requestApi<{ permissions: string[] }>("GET", "/api/v1/roles/permissions")
}

export function createRole(body: unknown) {
	return requestApi<RoleRecord>("POST", "/api/v1/roles/", { body })
}

export function updateRole(roleId: string, body: unknown) {
	return requestApi<RoleRecord>("PATCH", `/api/v1/roles/${roleId}`, { body })
}

export function deleteRole(roleId: string) {
	return requestApi<void>("DELETE", `/api/v1/roles/${roleId}`)
}

export function clearLogs() {
	return requestApi<WipeResult>("POST", "/api/v1/maintenance/clear-logs")
}

export function resetDatabase() {
	return requestApi<WipeResult>("POST", "/api/v1/maintenance/reset")
}
