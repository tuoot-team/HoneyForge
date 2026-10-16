import { ArcElement, BarController, BarElement, CategoryScale, Chart, DoughnutController, LinearScale, Tooltip } from "chart.js"
import { useEffect, useRef } from "react"

import { useTheme } from "../theme/ThemeProvider"

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, DoughnutController, ArcElement)

type Tone = "accent" | "ok" | "danger" | "muted"

const paletteOrder: Tone[] = ["accent", "ok", "danger", "muted"]

function readVar(name: string, fallback: string): string {
	return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

function readTone(tone: Tone): string {
	const fallback: Record<Tone, string> = {
		accent: "#e2a23a",
		ok: "#3dbe7a",
		danger: "#e15b64",
		muted: "#9aa1aa",
	}
	const name = tone === "accent" ? "--accent" : tone === "ok" ? "--ok" : tone === "danger" ? "--danger" : "--text-muted"
	return readVar(name, fallback[tone])
}

function withAlpha(color: string, alpha: number): string {
	const hex = color.trim()
	if (!/^#[0-9a-fA-F]{6}$/.test(hex)) {
		return color
	}
	const red = Number.parseInt(hex.slice(1, 3), 16)
	const green = Number.parseInt(hex.slice(3, 5), 16)
	const blue = Number.parseInt(hex.slice(5, 7), 16)
	return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}

export function chartColorAt(index: number): string {
	const tone = paletteOrder[index % paletteOrder.length]
	const color = readTone(tone)
	if (index < paletteOrder.length) {
		return color
	}
	return withAlpha(color, 0.62)
}

function chartMotion(): false | { duration: number } {
	if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		return false
	}
	return { duration: 560 }
}

function tooltipOptions() {
	const radius = Number.parseFloat(readVar("--radius", "8")) || 0
	return {
		enabled: true,
		backgroundColor: readVar("--bg-sunken", "#0d0f12"),
		titleColor: readVar("--text", "#eceef1"),
		bodyColor: readVar("--text-muted", "#9aa1aa"),
		borderColor: readVar("--line-strong", "#3a4048"),
		borderWidth: 1,
		padding: 10,
		cornerRadius: radius,
		displayColors: true,
		boxPadding: 4,
	}
}

function axisFont() {
	return {
		family: getComputedStyle(document.body).fontFamily,
		size: 12,
	}
}

const valueLabels = {
	id: "valueLabels",
	afterDatasetsDraw(chart: Chart) {
		const dataset = chart.data.datasets[0]
		if (!dataset) {
			return
		}
		const { ctx } = chart
		ctx.save()
		ctx.fillStyle = readVar("--text-muted", "#9aa1aa")
		ctx.font = `12px ${getComputedStyle(document.body).fontFamily}`
		ctx.textBaseline = "middle"
		chart.getDatasetMeta(0).data.forEach((element, index) => {
			const raw = dataset.data[index]
			const value = typeof raw === "number" ? raw : 0
			const point = element as unknown as { x: number; y: number }
			ctx.fillText(String(value), point.x + 8, point.y)
		})
		ctx.restore()
	},
}

export function ShareList({ rows }: { rows: { label: string; value: number; color: string }[] }) {
	const total = rows.reduce((sum, row) => sum + row.value, 0) || 1
	return (
		<ul className="grid gap-2.5">
			{rows.map((row) => {
				const share = Math.round((row.value / total) * 100)
				return (
					<li key={row.label}>
						<div className="flex items-center gap-2 text-[13px]">
							<span className="h-2.5 w-2.5 shrink-0 rounded-[var(--radius)]" style={{ background: row.color }} />
							<span className="min-w-0 flex-1 truncate">{row.label}</span>
							<span className="num text-muted">{row.value}</span>
							<span className="num w-9 text-right text-faint">{share}%</span>
						</div>
						<div className="mt-1.5 h-1 overflow-hidden rounded-[var(--radius)] bg-sunken">
							<div className="chart-share" style={{ width: `${share}%`, background: row.color }} />
						</div>
					</li>
				)
			})}
		</ul>
	)
}

export function CountBarChart({
	labels,
	values,
	seriesLabel,
}: {
	labels: string[]
	values: number[]
	seriesLabel: string
}) {
	const canvasRef = useRef<HTMLCanvasElement | null>(null)
	const { themeName } = useTheme()
	const ranked = labels
		.map((label, index) => ({ label, value: values[index] ?? 0 }))
		.sort((left, right) => right.value - left.value || left.label.localeCompare(right.label))
	const labelKey = ranked.map((row) => row.label).join("\n")
	const valueKey = ranked.map((row) => row.value).join(",")
	const height = Math.min(380, Math.max(168, ranked.length * 36 + 16))

	useEffect(() => {
		const canvas = canvasRef.current
		if (!canvas || ranked.length === 0) {
			return
		}
		const text = readVar("--text", "#eceef1")
		const line = withAlpha(readVar("--line", "#2c3138"), 0.9)
		const colors = ranked.map((_, index) => chartColorAt(index))
		const chart = new Chart(canvas, {
			type: "bar",
			plugins: [valueLabels],
			data: {
				labels: ranked.map((row) => row.label),
				datasets: [
					{
						label: seriesLabel,
						data: ranked.map((row) => row.value),
						backgroundColor: colors,
						hoverBackgroundColor: colors.map((color) => withAlpha(color, 0.82)),
						borderRadius: Number.parseFloat(readVar("--radius", "8")) > 0 ? 6 : 0,
						borderSkipped: false,
						maxBarThickness: 16,
						barPercentage: 0.72,
						categoryPercentage: 0.8,
					},
				],
			},
			options: {
				indexAxis: "y",
				responsive: true,
				maintainAspectRatio: false,
				animation: chartMotion(),
				layout: { padding: { right: 40, left: 4, top: 4, bottom: 4 } },
				plugins: {
					tooltip: tooltipOptions(),
				},
				scales: {
					x: {
						beginAtZero: true,
						grace: "22%",
						border: { display: false },
						grid: { color: line },
						ticks: { display: false },
					},
					y: {
						border: { display: false },
						grid: { display: false },
						ticks: {
							color: text,
							font: axisFont(),
							callback(value) {
								const label = String(this.getLabelForValue(Number(value)))
								return label.length > 24 ? `${label.slice(0, 22)}...` : label
							},
						},
					},
				},
			},
		})
		return () => chart.destroy()
	}, [labelKey, seriesLabel, themeName, valueKey])

	return (
		<div style={{ height }}>
			<canvas ref={canvasRef} />
		</div>
	)
}

export function CountRingChart({
	labels,
	values,
	tones,
	centerLabel,
}: {
	labels: string[]
	values: number[]
	tones: Tone[]
	centerLabel: string
}) {
	const canvasRef = useRef<HTMLCanvasElement | null>(null)
	const { themeName } = useTheme()
	const rows = labels.map((label, index) => ({
		label,
		value: values[index] ?? 0,
		color: readTone(tones[index] ?? "muted"),
	}))
	const slices = rows.filter((row) => row.value > 0)
	const total = rows.reduce((sum, row) => sum + row.value, 0)
	const labelKey = slices.map((row) => row.label).join("\n")
	const valueKey = slices.map((row) => row.value).join(",")
	const colorKey = slices.map((row) => row.color).join("|")

	useEffect(() => {
		const canvas = canvasRef.current
		if (!canvas || slices.length === 0) {
			return
		}
		const surface = readVar("--surface", "#1a1d22")
		const chart = new Chart(canvas, {
			type: "doughnut",
			data: {
				labels: slices.map((row) => row.label),
				datasets: [
					{
						data: slices.map((row) => row.value),
						backgroundColor: slices.map((row) => row.color),
						hoverBackgroundColor: slices.map((row) => withAlpha(row.color, 0.82)),
						borderColor: surface,
						borderWidth: 3,
						hoverOffset: 6,
						spacing: 2,
					},
				],
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: "70%",
				animation: chartMotion(),
				plugins: { tooltip: tooltipOptions() },
			},
		})
		return () => chart.destroy()
	}, [colorKey, labelKey, themeName, valueKey])

	return (
		<div>
			<div className="relative mx-auto h-52 max-w-[220px]">
				<canvas ref={canvasRef} />
				<div className="pointer-events-none absolute inset-0 grid place-items-center">
					<div className="text-center">
						<div className="text-[28px] font-semibold leading-none tracking-tight">{total}</div>
						<div className="mt-1 text-[11px] uppercase tracking-wide text-faint">{centerLabel}</div>
					</div>
				</div>
			</div>
			<div className="mt-4">
				<ShareList rows={rows} />
			</div>
		</div>
	)
}
