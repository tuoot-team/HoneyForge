import type { ReactNode } from "react"

export function Rise({
	delay = 0,
	className = "",
	children,
}: {
	delay?: number
	className?: string
	children: ReactNode
}) {
	return (
		<div className={`rise-in ${className}`} style={delay > 0 ? { animationDelay: `${delay}ms` } : undefined}>
			{children}
		</div>
	)
}
