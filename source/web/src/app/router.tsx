import { createBrowserRouter } from "react-router"

import { RequirePermission } from "../shared/auth/RequirePermission"
import { AssetsPage } from "../pages/assets/AssetsPage"
import { CouriersPage } from "../pages/couriers/CouriersPage"
import { EventsPage } from "../pages/events/EventsPage"
import { HomePage } from "../pages/home/HomePage"
import { LandingPage } from "../pages/landing/LandingPage"
import { LoginPage } from "../pages/login/LoginPage"
import { MaintenancePage } from "../pages/maintenance/MaintenancePage"
import { PairingPage } from "../pages/pairing/PairingPage"
import { ProfileEditorPage } from "../pages/profiles/ProfileEditorPage"
import { ProfilesPage } from "../pages/profiles/ProfilesPage"
import { RolesPage } from "../pages/roles/RolesPage"
import { SetupPage } from "../pages/setup/SetupPage"
import { TrapsPage } from "../pages/traps/TrapsPage"
import { UsersPage } from "../pages/users/UsersPage"
import { PanelShell } from "../widgets/panel-shell/PanelShell"

export const router = createBrowserRouter([
	{ path: "/", element: <LandingPage /> },
	{ path: "/login", element: <LoginPage /> },
	{
		element: <PanelShell />,
		children: [
			{ path: "home", element: <HomePage /> },
			{
				path: "setup",
				element: (
					<RequirePermission permission="profiles.write">
						<SetupPage />
					</RequirePermission>
				),
			},
			{
				path: "profiles",
				element: (
					<RequirePermission permission="profiles.read">
						<ProfilesPage />
					</RequirePermission>
				),
			},
			{
				path: "profiles/new",
				element: (
					<RequirePermission permission="profiles.write">
						<ProfileEditorPage />
					</RequirePermission>
				),
			},
			{
				path: "profiles/:profileId",
				element: (
					<RequirePermission permission="profiles.read">
						<ProfileEditorPage />
					</RequirePermission>
				),
			},
			{
				path: "traps",
				element: (
					<RequirePermission permission="traps.read">
						<TrapsPage />
					</RequirePermission>
				),
			},
			{
				path: "pairing",
				element: (
					<RequirePermission permission="traps.read">
						<PairingPage />
					</RequirePermission>
				),
			},
			{
				path: "events",
				element: (
					<RequirePermission permission="events.read">
						<EventsPage />
					</RequirePermission>
				),
			},
			{
				path: "couriers",
				element: (
					<RequirePermission permission="couriers.read">
						<CouriersPage />
					</RequirePermission>
				),
			},
			{
				path: "assets",
				element: (
					<RequirePermission permission="profiles.read">
						<AssetsPage />
					</RequirePermission>
				),
			},
			{
				path: "users",
				element: (
					<RequirePermission permission="users.write">
						<UsersPage />
					</RequirePermission>
				),
			},
			{
				path: "roles",
				element: (
					<RequirePermission permission="roles.write">
						<RolesPage />
					</RequirePermission>
				),
			},
			{
				path: "maintenance",
				element: (
					<RequirePermission permission="maintenance.write">
						<MaintenancePage />
					</RequirePermission>
				),
			},
		],
	},
])
