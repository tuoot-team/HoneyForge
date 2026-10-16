export function isDebugEnabled(): boolean {
	const raw = (import.meta.env.VITE_DEBUG ?? "").toLowerCase()
	return raw === "1" || raw === "true" || raw === "yes"
}

// Dev остаётся на своём origin: адрес из .env забирает прокси Vite.
// В собранной панели пустой VITE_API_BASE значит /api того же :80/:443.
export function apiBaseUrl(): string {
	if (import.meta.env.DEV) {
		return ""
	}
	return String(import.meta.env.VITE_API_BASE ?? "").trim().replace(/\/+$/, "")
}
