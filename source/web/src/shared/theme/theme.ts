export const themeStorageKey = "honeyforge-theme"

export type ThemeName = "graphite" | "terminal" | "retro"

export function isThemeName(value: string | null): value is ThemeName {
	return value === "graphite" || value === "terminal" || value === "retro"
}

export function readStoredTheme(): ThemeName {
	try {
		const stored = localStorage.getItem(themeStorageKey)
		if (isThemeName(stored)) {
			return stored
		}
	} catch {
	}
	return "graphite"
}

export function saveTheme(themeName: ThemeName): void {
	try {
		localStorage.setItem(themeStorageKey, themeName)
	} catch {
	}
}

export function applyTheme(themeName: ThemeName): void {
	document.documentElement.dataset.theme = themeName
}
