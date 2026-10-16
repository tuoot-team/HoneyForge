import type { ReactNode } from "react"
import { Link } from "react-router"

import { useAuth } from "../auth/AuthProvider"
import { texts } from "../texts"
import { primaryClass } from "../ui/classes"

export function AccessNotice({ kind }: { kind: "login" | "forbidden" | "loading" }) {
	if (kind === "loading") {
		return <p className="text-[13px] text-muted">{texts.loading}</p>
	}
	const title = kind === "login" ? texts.needLoginTitle : texts.forbiddenTitle
	const body = kind === "login" ? texts.needLoginBody : texts.forbiddenBody
	return (
		<article className="max-w-lg">
			<h1 className="text-[20px] font-semibold">{title}</h1>
			<p className="mt-2 text-[14px] text-muted">{body}</p>
			{kind === "login" ? (
				<Link to="/login" className={`${primaryClass} mt-4`}>
					{texts.login}
				</Link>
			) : (
				<Link to="/home" className="mt-4 inline-flex text-[13px] text-accent">
					{texts.backHome}
				</Link>
			)}
		</article>
	)
}

export function RequirePermission({
	permission,
	children,
}: {
	permission: string
	children: ReactNode
}) {
	const auth = useAuth()
	if (auth.status === "unknown") {
		return <AccessNotice kind="loading" />
	}
	if (auth.status === "anonymous") {
		return <AccessNotice kind="login" />
	}
	if (!auth.hasPermission(permission)) {
		return <AccessNotice kind="forbidden" />
	}
	return children
}
