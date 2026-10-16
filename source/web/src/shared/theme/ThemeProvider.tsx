import { useEffect, useMemo, useState, type ReactNode } from "react"
import { createContext, useContext } from "react"

import { isDebugEnabled } from "../config/env"
import { applyTheme, readStoredTheme, saveTheme, type ThemeName } from "./theme"

type ThemeContextValue = {
	themeName: ThemeName
	setThemeName: (next: ThemeName) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
	const [themeName, setThemeName] = useState<ThemeName>(() => readStoredTheme())

	useEffect(() => {
		applyTheme(themeName)
		saveTheme(themeName)
		if (isDebugEnabled()) {
			console.info("[DEBUG] theme", themeName)
		}
	}, [themeName])

	const value = useMemo(
		() => ({
			themeName,
			setThemeName,
		}),
		[themeName],
	)

	return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeContextValue {
	const value = useContext(ThemeContext)
	if (!value) {
		throw new Error("useTheme вне ThemeProvider")
	}
	return value
}
