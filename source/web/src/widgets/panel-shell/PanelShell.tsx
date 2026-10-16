import { useEffect, useState } from "react"
import { Link, NavLink, Outlet, useLocation } from "react-router"

import { useAuth } from "../../shared/auth/AuthProvider"
import { texts } from "../../shared/texts"
import { primaryClass } from "../../shared/ui/classes"
import { ThemeToggle } from "../theme-toggle/ThemeToggle"
import { accessNav, centerNav, collectNav, overviewNav, serviceNav, type NavItem } from "./panelNav"

const groups = [
	{ title: texts.navOverview, items: overviewNav },
	{ title: texts.navCenter, items: centerNav },
	{ title: texts.navCollect, items: collectNav },
	{ title: texts.navAccess, items: accessNav },
	{ title: texts.navService, items: serviceNav },
]

export function PanelShell() {
	const auth = useAuth()
	const location = useLocation()
	const [isSidebarOpen, setIsSidebarOpen] = useState(false)

	useEffect(() => {
		setIsSidebarOpen(false)
	}, [location.pathname])

	useEffect(() => {
		function onKeyDown(event: KeyboardEvent) {
			if (event.key === "Escape") {
				setIsSidebarOpen(false)
			}
		}
		window.addEventListener("keydown", onKeyDown)
		return () => window.removeEventListener("keydown", onKeyDown)
	}, [])

	const sessionLabel =
		auth.status === "ready" && auth.me
			? [auth.me.username, auth.me.role].filter(Boolean).join(" / ")
			: auth.status === "unknown"
				? texts.loading
				: texts.sessionNone

	return (
		<div className="flex min-h-screen bg-canvas text-fg">
			{isSidebarOpen ? (
				<button
					type="button"
					className="fixed inset-0 z-30 bg-black/50 min-[960px]:hidden"
					aria-label={texts.closeMenu}
					onClick={() => setIsSidebarOpen(false)}
				/>
			) : null}
			<aside
				className={`fixed inset-y-0 left-0 z-40 h-screen w-[260px] flex-col overflow-y-auto border-r border-line bg-sunken min-[960px]:sticky min-[960px]:top-0 min-[960px]:flex ${
					isSidebarOpen ? "flex" : "hidden min-[960px]:flex"
				}`}
			>
				<div className="flex h-12 items-center gap-3 border-b border-line px-4">
					<span className="grid h-7 w-7 place-items-center border border-line-strong text-[11px] font-semibold text-accent">
						HF
					</span>
					<div>
						<div className="brand-caret text-[14px] font-semibold leading-none">{texts.appName}</div>
						<div className="mt-1 text-[11px] text-faint">{texts.appRole}</div>
					</div>
				</div>
				<nav className="flex-1 px-2 py-3">
					{groups.map((group) => {
						const items = group.items.filter((item) => isItemVisible(item, auth.status, auth.hasPermission))
						if (items.length === 0) {
							return null
						}
						return (
							<div key={group.title} className="mb-4">
								<div className="px-3 pb-1 text-[11px] uppercase tracking-wide text-faint">{group.title}</div>
								{items.map((item) => (
									<NavLink
										key={item.path}
										to={item.path}
										end={item.path === "/home"}
										className={({ isActive }) =>
											`flex items-center gap-2 border-l-2 px-3 py-2 text-[13px] ${
												isActive
													? "border-accent bg-surface-hover text-fg"
													: "border-transparent text-muted hover:bg-surface-hover hover:text-fg"
											}`
										}
									>
										<item.icon className="h-4 w-4 shrink-0" />
										{item.label}
									</NavLink>
								))}
							</div>
						)
					})}
				</nav>
				<div className="border-t border-line px-4 py-3 text-[11px] text-faint">{texts.shellFooter}</div>
			</aside>
			<div className="flex min-w-0 flex-1 flex-col">
				<header className="sticky top-0 z-20 flex h-12 items-center justify-between gap-3 border-b border-line bg-canvas px-4">
					<button
						type="button"
						className="h-8 border border-line px-2 text-[12px] min-[960px]:hidden"
						aria-expanded={isSidebarOpen}
						onClick={() => setIsSidebarOpen((open) => !open)}
					>
						{isSidebarOpen ? texts.closeMenu : texts.openMenu}
					</button>
					<div className="ml-auto flex items-center gap-3">
						<span className="hidden text-[12px] text-faint sm:inline">{sessionLabel}</span>
						<ThemeToggle />
						{auth.status === "ready" ? (
							<button type="button" className={primaryClass} onClick={() => void auth.logout()}>
								{texts.logout}
							</button>
						) : (
							<Link to="/login" className={primaryClass}>
								{texts.login}
							</Link>
						)}
					</div>
				</header>
				<main className="min-w-0 flex-1 px-4 py-6 min-[960px]:px-8">
					<Outlet />
				</main>
			</div>
		</div>
	)
}

function isItemVisible(
	item: NavItem,
	status: "unknown" | "anonymous" | "ready",
	hasPermission: (permission: string) => boolean,
): boolean {
	if (status !== "ready" || !item.permission) {
		return true
	}
	return hasPermission(item.permission)
}
