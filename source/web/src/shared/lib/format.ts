import { texts } from "../texts"

export function formatDateTime(value: string | null | undefined): string {
	if (!value) {
		return texts.emptyValue
	}
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) {
		return value
	}
	return date.toLocaleString("ru-RU", { hour12: false })
}

export function formatBytes(size: number): string {
	if (size < 1024) {
		return `${size} B`
	}
	if (size < 1024 * 1024) {
		return `${(size / 1024).toFixed(1)} KiB`
	}
	return `${(size / (1024 * 1024)).toFixed(1)} MiB`
}

export function splitList(value: string): string[] {
	return value
		.split(/[\n,]/)
		.map((item) => item.trim())
		.filter(Boolean)
}

export function shortId(value: string | null | undefined): string {
	if (!value) {
		return texts.emptyValue
	}
	return value.slice(0, 8)
}
