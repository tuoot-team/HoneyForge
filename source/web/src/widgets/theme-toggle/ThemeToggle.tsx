import { texts } from "../../shared/texts"
import { useTheme } from "../../shared/theme/ThemeProvider"
import type { ThemeName } from "../../shared/theme/theme"

export function ThemeToggle() {
	const { themeName, setThemeName } = useTheme()
	return (
		<div role="group" aria-label={texts.themeLabel} className="inline-flex border border-line">
			<ThemeChoice name="graphite" current={themeName} label={texts.themeGraphite} onSelect={setThemeName} />
			<ThemeChoice name="terminal" current={themeName} label={texts.themeTerminal} onSelect={setThemeName} />
			<ThemeChoice name="retro" current={themeName} label={texts.themeRetro} onSelect={setThemeName} />
		</div>
	)
}

function ThemeChoice({
	name,
	current,
	label,
	onSelect,
}: {
	name: ThemeName
	current: ThemeName
	label: string
	onSelect: (next: ThemeName) => void
}) {
	const selected = name === current
	return (
		<button
			type="button"
			aria-pressed={selected}
			onClick={() => onSelect(name)}
			className={`h-8 px-2.5 text-[12px] ${selected ? "bg-[var(--accent-soft)] text-fg" : "text-muted"}`}
		>
			{label}
		</button>
	)
}
