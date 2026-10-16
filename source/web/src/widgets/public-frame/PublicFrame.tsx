import type { ReactNode } from "react"
import { Link } from "react-router"

import { useAuth } from "../../shared/auth/AuthProvider"
import { texts } from "../../shared/texts"
import { primaryClass } from "../../shared/ui/classes"
import { ThemeToggle } from "../theme-toggle/ThemeToggle"

export function PublicFrame({ children }: { children: ReactNode }) {
	const auth = useAuth()
	return (
		<div className="min-h-screen bg-canvas text-fg">
			<header className="sticky top-0 z-20 flex h-12 items-center justify-between gap-3 border-b border-line bg-canvas px-4 min-[960px]:px-8">
				<Link to="/" className="flex min-w-0 items-center gap-3">
					<span className="grid h-7 w-7 shrink-0 place-items-center border border-line-strong text-[11px] font-semibold text-accent">
						HF
					</span>
					<span className="brand-caret truncate text-[14px] font-semibold">{texts.appName}</span>
				</Link>
				<div className="flex shrink-0 items-center gap-3">
					<div className="hidden sm:block">
						<ThemeToggle />
					</div>
					{auth.status === "ready" ? (
						<Link to="/home" className={primaryClass}>
							{texts.openPanel}
						</Link>
					) : (
						<Link to="/login" className={primaryClass}>
							{texts.login}
						</Link>
					)}
				</div>
			</header>
			<main className="px-4 py-10 min-[960px]:px-8">{children}</main>
		</div>
	)
}
