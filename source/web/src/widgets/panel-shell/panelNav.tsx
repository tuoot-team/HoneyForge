import type { ComponentType, SVGProps } from "react"

import { texts } from "../../shared/texts"
import {
	AssetsIcon,
	CouriersIcon,
	EventsIcon,
	HomeIcon,
	MaintenanceIcon,
	PairingIcon,
	ProfilesIcon,
	RolesIcon,
	TrapsIcon,
	UsersIcon,
} from "../../shared/ui/icons"

export type NavItem = {
	path: string
	label: string
	permission: string | null
	icon: ComponentType<SVGProps<SVGSVGElement>>
}

export const overviewNav: NavItem[] = [
	{ path: "/home", label: texts.navHome, permission: null, icon: HomeIcon },
]

export const centerNav: NavItem[] = [
	{ path: "/profiles", label: texts.navProfiles, permission: "profiles.read", icon: ProfilesIcon },
	{ path: "/traps", label: texts.navTraps, permission: "traps.read", icon: TrapsIcon },
	{ path: "/pairing", label: texts.navPairing, permission: "traps.read", icon: PairingIcon },
	{ path: "/events", label: texts.navEvents, permission: "events.read", icon: EventsIcon },
]

export const collectNav: NavItem[] = [
	{ path: "/couriers", label: texts.navCouriers, permission: "couriers.read", icon: CouriersIcon },
	{ path: "/assets", label: texts.navAssets, permission: "profiles.read", icon: AssetsIcon },
]

export const accessNav: NavItem[] = [
	{ path: "/users", label: texts.navUsers, permission: "users.write", icon: UsersIcon },
	{ path: "/roles", label: texts.navRoles, permission: "roles.write", icon: RolesIcon },
]

export const serviceNav: NavItem[] = [
	{ path: "/maintenance", label: texts.navMaintenance, permission: "maintenance.write", icon: MaintenanceIcon },
]
