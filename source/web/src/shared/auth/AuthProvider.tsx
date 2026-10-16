import { useQueryClient } from "@tanstack/react-query"
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { fetchMe, loginRequest, logoutRequest } from "../api/resources"
import { ApiError, clearStoredToken, getStoredToken, saveStoredToken } from "../api/http"
import type { Me } from "../api/types"

type AuthStatus = "unknown" | "anonymous" | "ready"

type AuthContextValue = {
	status: AuthStatus
	me: Me | null
	login: (username: string, password: string) => Promise<void>
	logout: () => Promise<void>
	hasPermission: (permission: string) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

// Старый /auth/me отдаёт только role и authenticated, без каталога прав.
// Это единственный оператор центра, ему видны все разделы.
function sessionFromMe(raw: Me, username?: string): Me {
	if (Array.isArray(raw.permissions)) {
		return raw
	}
	return {
		authenticated: raw.authenticated ?? true,
		username: raw.username || username || "",
		role: raw.role || "operator",
		role_id: raw.role_id || "",
		is_superadmin: true,
		permissions: [],
	}
}

export function AuthProvider({ children }: { children: ReactNode }) {
	const queryClient = useQueryClient()
	const [status, setStatus] = useState<AuthStatus>("unknown")
	const [me, setMe] = useState<Me | null>(null)

	useEffect(() => {
		let cancelled = false
		async function restore() {
			if (!getStoredToken()) {
				if (!cancelled) {
					setMe(null)
					setStatus("anonymous")
				}
				return
			}
			try {
				const next = sessionFromMe(await fetchMe())
				if (!cancelled) {
					setMe(next)
					setStatus("ready")
				}
			} catch {
				clearStoredToken()
				if (!cancelled) {
					setMe(null)
					setStatus("anonymous")
				}
			}
		}
		void restore()
		const onUnauthorized = () => {
			setMe(null)
			setStatus("anonymous")
			queryClient.clear()
		}
		window.addEventListener("honeyforge-unauthorized", onUnauthorized)
		return () => {
			cancelled = true
			window.removeEventListener("honeyforge-unauthorized", onUnauthorized)
		}
	}, [queryClient])

	const value = useMemo<AuthContextValue>(() => {
		return {
			status,
			me,
			hasPermission(permission: string) {
				if (me?.is_superadmin) {
					return true
				}
				return (me?.permissions ?? []).includes(permission)
			},
			async login(username: string, password: string) {
				const result = await loginRequest(username.trim(), password)
				saveStoredToken(result.access_token)
				try {
					const next = sessionFromMe(await fetchMe(), username.trim())
					setMe(next)
					setStatus("ready")
				} catch (error) {
					clearStoredToken()
					setMe(null)
					setStatus("anonymous")
					throw error instanceof ApiError ? error : new ApiError("не удалось прочитать сессию")
				}
			},
			async logout() {
				try {
					await logoutRequest()
				} catch {
				}
				clearStoredToken()
				setMe(null)
				setStatus("anonymous")
				queryClient.clear()
			},
		}
	}, [me, queryClient, status])

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
	const value = useContext(AuthContext)
	if (!value) {
		throw new Error("useAuth вне AuthProvider")
	}
	return value
}
