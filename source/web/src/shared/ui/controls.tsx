import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react"

import { ApiError } from "../api/http"
import { texts } from "../texts"
import { dangerClass, ghostClass, inputClass, primaryClass } from "./classes"

export function Field({ label, children }: { label: string; children: ReactNode }) {
	return (
		<label className="block text-[13px]">
			<span className="mb-1 block text-muted">{label}</span>
			{children}
		</label>
	)
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
	return <input {...props} className={`${inputClass} ${props.className ?? ""}`} />
}

export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) {
	return <select {...props} className={`${inputClass} ${props.className ?? ""}`} />
}

export function Button({
	tone = "primary",
	...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "primary" | "ghost" | "danger" }) {
	const toneClass = tone === "danger" ? dangerClass : tone === "ghost" ? ghostClass : primaryClass
	return <button {...props} className={`${toneClass} ${props.className ?? ""}`} />
}

export function ErrorText({ error }: { error: unknown }) {
	if (!error) {
		return null
	}
	const message = error instanceof ApiError ? error.message : texts.actionFailed
	return <p className="text-[13px] text-danger">{message}</p>
}

export function PageHeader({ title, lead, action }: { title: string; lead?: string; action?: ReactNode }) {
	return (
		<header className="mb-5 flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 className="text-[20px] font-semibold tracking-tight">{title}</h1>
				{lead ? <p className="mt-1 max-w-2xl text-[14px] text-muted">{lead}</p> : null}
			</div>
			{action}
		</header>
	)
}

export function StatusBadge({ value }: { value: string }) {
	const tone =
		value === "online" || value === "high" || value === "completed"
			? "text-ok"
			: value === "offline" || value === "expired"
				? "text-danger"
				: "text-accent"
	return <span className={`text-[12px] ${tone}`}>{value}</span>
}
