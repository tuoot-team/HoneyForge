import { useState, type FormEvent } from "react"
import { Link, useNavigate } from "react-router"

import { ApiError } from "../../shared/api/http"
import { useAuth } from "../../shared/auth/AuthProvider"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, TextInput } from "../../shared/ui/controls"
import { PublicFrame } from "../../widgets/public-frame/PublicFrame"

export function LoginPage() {
	const auth = useAuth()
	const navigate = useNavigate()
	const [username, setUsername] = useState("")
	const [password, setPassword] = useState("")
	const [error, setError] = useState<unknown>(null)
	const [pending, setPending] = useState(false)

	async function onSubmit(event: FormEvent) {
		event.preventDefault()
		if (!username.trim() || !password) {
			setError(new ApiError(texts.loginRequired))
			return
		}
		setPending(true)
		setError(null)
		try {
			await auth.login(username, password)
			navigate("/home")
		} catch (submitError) {
			setError(submitError)
		} finally {
			setPending(false)
		}
	}

	return (
		<PublicFrame>
			<section className="mx-auto max-w-md">
				<h1 className="text-[20px] font-semibold">{texts.loginTitle}</h1>
				<p className="mt-2 text-[14px] text-muted">{texts.loginLead}</p>
				{auth.status === "ready" ? (
					<p className="mt-4 text-[13px]">
						{texts.loginAlready}. <Link to="/home" className="text-accent">{texts.openPanel}</Link>
					</p>
				) : (
					<form className={`${cardClass} mt-4 grid gap-3 p-4`} onSubmit={(event) => void onSubmit(event)}>
						<Field label={texts.loginUsername}>
							<TextInput autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} />
						</Field>
						<Field label={texts.loginPassword}>
							<TextInput
								type="password"
								autoComplete="current-password"
								value={password}
								onChange={(event) => setPassword(event.target.value)}
							/>
						</Field>
						<ErrorText error={error} />
						<Button type="submit" disabled={pending}>
							{texts.login}
						</Button>
					</form>
				)}
			</section>
		</PublicFrame>
	)
}
