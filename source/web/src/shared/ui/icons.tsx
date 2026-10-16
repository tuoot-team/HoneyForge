import type { ReactNode, SVGProps } from "react"

type IconProps = SVGProps<SVGSVGElement>

function IconBase({ children, ...props }: IconProps & { children: ReactNode }) {
	return (
		<svg viewBox="0 0 16 16" fill="none" aria-hidden="true" {...props}>
			{children}
		</svg>
	)
}

const stroke = { stroke: "currentColor", strokeWidth: 1.2 } as const

export function HomeIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M2.5 7.2 8 2.8l5.5 4.4V13a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5V7.2Z" {...stroke} />
		</IconBase>
	)
}

export function ProfilesIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M3 4.5h10M3 8h10M3 11.5h6" {...stroke} />
		</IconBase>
	)
}

export function TrapsIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<rect x="3" y="3" width="10" height="10" rx="1.2" {...stroke} />
			<path d="M6 8h4" {...stroke} />
		</IconBase>
	)
}

export function PairingIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M6.2 9.5 4.5 11a2 2 0 0 1-2.8-2.8L3.4 6.5M9.8 6.5 11.5 5a2 2 0 0 1 2.8 2.8L12.6 9.5M6.5 9.5l3-3" {...stroke} />
		</IconBase>
	)
}

export function EventsIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M3 12.5 6.2 8l2.2 2.2L13 4.5" {...stroke} />
		</IconBase>
	)
}

export function CouriersIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M2.5 10.5h11M4 10.5V6.2h5.2L11.5 8.5V10.5" {...stroke} />
			<circle cx="5" cy="12" r="1" {...stroke} />
			<circle cx="11" cy="12" r="1" {...stroke} />
		</IconBase>
	)
}

export function AssetsIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M3 5.5 8 3l5 2.5v6L8 14l-5-2.5v-6Z" {...stroke} />
		</IconBase>
	)
}

export function UsersIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<circle cx="8" cy="5.5" r="2" {...stroke} />
			<path d="M3.5 12.5c.8-2 2.4-3 4.5-3s3.7 1 4.5 3" {...stroke} />
		</IconBase>
	)
}

export function RolesIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<path d="M8 2.8 12.5 4.5v3.2c0 2.6-1.8 4.4-4.5 5.5-2.7-1.1-4.5-2.9-4.5-5.5V4.5L8 2.8Z" {...stroke} />
		</IconBase>
	)
}

export function MaintenanceIcon(props: IconProps) {
	return (
		<IconBase {...props}>
			<circle cx="8" cy="8" r="2" {...stroke} />
			<path d="M8 2.8v1.6M8 11.6v1.6M2.8 8h1.6M11.6 8h1.6M4.2 4.2l1.1 1.1M10.7 10.7l1.1 1.1M11.8 4.2l-1.1 1.1M5.3 10.7l-1.1 1.1" {...stroke} />
		</IconBase>
	)
}
