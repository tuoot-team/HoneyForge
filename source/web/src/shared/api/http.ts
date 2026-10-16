import { apiBaseUrl, isDebugEnabled } from "../config/env"

const tokenStorageKey = "honeyforge-access-token"

export class ApiError extends Error {
	statusCode: number | null

	constructor(message: string, statusCode: number | null = null) {
		super(message)
		this.statusCode = statusCode
	}
}

export function getStoredToken(): string | null {
	try {
		return sessionStorage.getItem(tokenStorageKey)
	} catch {
		return null
	}
}

export function saveStoredToken(token: string): void {
	sessionStorage.setItem(tokenStorageKey, token)
}

export function clearStoredToken(): void {
	try {
		sessionStorage.removeItem(tokenStorageKey)
	} catch {
	}
	window.dispatchEvent(new Event("honeyforge-unauthorized"))
}

type QueryValue = string | number | boolean | null | undefined

export function withQuery(path: string, params: Record<string, QueryValue> = {}): string {
	const search = new URLSearchParams()
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === "") {
			continue
		}
		search.set(key, String(value))
	}
	const query = search.toString()
	return query ? `${path}?${query}` : path
}

function resolveApiUrl(path: string): string {
	const base = apiBaseUrl()
	if (!base) {
		return path
	}
	return `${base}${path.startsWith("/") ? path : `/${path}`}`
}

function readDetail(payload: unknown, fallback: string): string {
	if (!payload || typeof payload !== "object" || !("detail" in payload)) {
		return fallback
	}
	const detail = (payload as { detail: unknown }).detail
	if (typeof detail === "string" && detail.trim()) {
		return detail
	}
	if (Array.isArray(detail)) {
		return detail
			.map((item) => {
				if (item && typeof item === "object" && "msg" in item) {
					const message = String(item.msg)
					const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : ""
					return loc ? `${loc}: ${message}` : message
				}
				return String(item)
			})
			.join("; ")
	}
	if (detail === undefined) {
		return fallback
	}
	return JSON.stringify(detail)
}

type RequestOptions = {
	body?: unknown
	form?: FormData
	auth?: boolean
	accept?: string
}

async function sendRequest(method: string, path: string, options: RequestOptions = {}): Promise<Response> {
	const headers: Record<string, string> = {}
	if (options.accept) {
		headers.Accept = options.accept
	}
	const useAuth = options.auth !== false
	if (useAuth) {
		const token = getStoredToken()
		if (!token) {
			throw new ApiError("нет токена, сначала вход")
		}
		headers.Authorization = `Bearer ${token}`
	}
	let body: BodyInit | undefined
	if (options.form) {
		body = options.form
	} else if (options.body !== undefined) {
		headers["Content-Type"] = "application/json"
		body = JSON.stringify(options.body)
	}
	const url = resolveApiUrl(path)
	if (isDebugEnabled()) {
		console.info("[DEBUG]", method, url)
	}
	try {
		return await fetch(url, { method, headers, body })
	} catch (error) {
		const name = error instanceof Error ? error.name : "network"
		throw new ApiError(`сеть: ${name}`)
	}
}

async function assertOk(response: Response, path: string): Promise<void> {
	if (response.status < 400) {
		return
	}
	let detail = response.statusText || "ошибка"
	try {
		detail = readDetail(await response.json(), detail)
	} catch {
	}
	if (response.status === 401 && path !== "/api/v1/auth/login") {
		clearStoredToken()
	}
	throw new ApiError(detail, response.status)
}

export async function requestApi<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
	const response = await sendRequest(method, path, { ...options, accept: options.accept ?? "application/json" })
	await assertOk(response, path)
	if (response.status === 204) {
		return undefined as T
	}
	const text = await response.text()
	if (!text) {
		return undefined as T
	}
	return JSON.parse(text) as T
}

export async function requestApiText(method: string, path: string, options: RequestOptions = {}): Promise<string> {
	const response = await sendRequest(method, path, { ...options, accept: options.accept ?? "*/*" })
	await assertOk(response, path)
	return response.text()
}

export type SseHandler = (payload: unknown) => void

// EventSource не умеет Authorization, поэтому поток читается через fetch.
export async function streamSse(path: string, onPayload: SseHandler, signal: AbortSignal): Promise<void> {
	const response = await sendRequest("GET", path, { accept: "text/event-stream" })
	await assertOk(response, path)
	if (!response.body) {
		throw new ApiError("пустой поток")
	}
	const reader = response.body.getReader()
	const decoder = new TextDecoder()
	let buffer = ""
	while (!signal.aborted) {
		const chunk = await reader.read()
		if (chunk.done) {
			break
		}
		buffer += decoder.decode(chunk.value, { stream: true })
		const frames = buffer.split("\n\n")
		buffer = frames.pop() ?? ""
		for (const frame of frames) {
			const dataLine = frame
				.split("\n")
				.filter((line) => line.startsWith("data:"))
				.map((line) => line.slice(5).trim())
				.join("\n")
			if (!dataLine) {
				continue
			}
			onPayload(JSON.parse(dataLine) as unknown)
		}
	}
}
