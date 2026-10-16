import { texts } from "../texts"

const summaryKeys = [
	"username",
	"password",
	"success",
	"command",
	"database",
	"service",
	"path",
	"method",
	"port",
	"banner",
	"token_id",
	"kind",
	"trigger",
	"detail",
	"ok",
] as const

export const hotPayloadKeys = new Set(["username", "password", "command", "token_id"])

export function formatSource(ip: string | null | undefined, port: number | null | undefined): string {
	if (!ip && (port === null || port === undefined)) {
		return texts.emptyValue
	}
	if (ip && port !== null && port !== undefined) {
		return `${ip}:${port}`
	}
	return ip || String(port)
}

function valueText(value: unknown): string {
	if (typeof value === "string") {
		return value
	}
	if (typeof value === "number" || typeof value === "boolean") {
		return String(value)
	}
	return JSON.stringify(value)
}

export function eventSummary(payload: Record<string, unknown> | null | undefined): string {
	if (!payload) {
		return ""
	}
	const parts: string[] = []
	for (const key of summaryKeys) {
		const value = payload[key]
		if (value === undefined || value === null || value === "") {
			continue
		}
		const text = valueText(value)
		parts.push(`${key}=${text.length > 80 ? `${text.slice(0, 77)}...` : text}`)
	}
	if (parts.length > 0) {
		return parts.join("  ")
	}
	const extra: Record<string, unknown> = {}
	for (const [key, value] of Object.entries(payload)) {
		if (key === "raw" || value === undefined || value === null || value === "") {
			continue
		}
		extra[key] = value
	}
	const dumped = JSON.stringify(extra)
	if (!dumped || dumped === "{}") {
		return ""
	}
	return dumped.length > 140 ? `${dumped.slice(0, 137)}...` : dumped
}

export function payloadRows(payload: Record<string, unknown> | null | undefined): { key: string; value: string }[] {
	if (!payload) {
		return []
	}
	const rows: { key: string; value: string }[] = []
	const seen = new Set<string>()
	for (const key of summaryKeys) {
		const value = payload[key]
		if (value === undefined || value === null || value === "") {
			continue
		}
		seen.add(key)
		rows.push({ key, value: valueText(value) })
	}
	for (const [key, value] of Object.entries(payload)) {
		if (seen.has(key) || key === "raw" || value === undefined || value === null || value === "") {
			continue
		}
		rows.push({ key, value: valueText(value) })
	}
	return rows
}
