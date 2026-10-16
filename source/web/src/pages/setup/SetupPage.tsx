import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Link } from "react-router"

import { confirmPairing, createProfile, deployAgent, listFsPacks, listPersonalityPacks, listTraps, setTrapCourierSsh, updateProfile, validateProfile } from "../../shared/api/resources"
import { ApiError } from "../../shared/api/http"
import { useAuth } from "../../shared/auth/AuthProvider"
import { formatDateTime, shortId } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, PageHeader, StatusBadge, TextInput } from "../../shared/ui/controls"
import { ProfileForm } from "../profiles/ProfileForm"
import { createEmptyDraft, profileBodyFromDraft, type ProfileDraft } from "../profiles/profileDraft"

const stepTitles = [
	texts.setupStepObject,
	texts.setupStepModules,
	texts.setupStepConceal,
	texts.setupStepInstall,
	texts.setupStepLive,
]

function freshDraft(): ProfileDraft {
	const draft = createEmptyDraft()
	draft.name = "dmz-ssh-01"
	draft.description = "lab-dmz"
	return draft
}

export function SetupPage() {
	const auth = useAuth()
	const queryClient = useQueryClient()
	const canDeploy = auth.hasPermission("deploy.write")
	const canPair = auth.hasPermission("pairing.write")
	const [step, setStep] = useState(0)
	const [draft, setDraft] = useState<ProfileDraft>(freshDraft)
	const [profileId, setProfileId] = useState<string | null>(null)
	const [installMode, setInstallMode] = useState<"ssh" | "code">(canDeploy ? "ssh" : "code")
	const [host, setHost] = useState("")
	const [userName, setUserName] = useState("root")
	const [password, setPassword] = useState("")
	const [port, setPort] = useState(22)
	const [centerUrl, setCenterUrl] = useState("")
	const [deviceCode, setDeviceCode] = useState("")
	const [trapId, setTrapId] = useState<string | null>(null)
	const [courierHost, setCourierHost] = useState("")
	const [courierUser, setCourierUser] = useState("root")
	const [courierPassword, setCourierPassword] = useState("")
	const [courierPort, setCourierPort] = useState(22)
	const [courierKey, setCourierKey] = useState("")
	const [courierDir, setCourierDir] = useState("/var/lib/metricsd")
	const [courierDone, setCourierDone] = useState(false)
	const [localError, setLocalError] = useState<unknown>(null)

	const fsPacks = useQuery({ queryKey: ["fs-packs"], queryFn: listFsPacks, enabled: step === 1 })
	const personalities = useQuery({ queryKey: ["personality-packs"], queryFn: listPersonalityPacks, enabled: step === 2 })
	const traps = useQuery({
		queryKey: ["traps"],
		queryFn: listTraps,
		enabled: Boolean(trapId),
		refetchInterval: step === 4 ? 5000 : false,
	})
	const liveTrap = traps.data?.find((item) => item.id === trapId) ?? null

	const save = useMutation({
		mutationFn: async () => {
			const body = profileBodyFromDraft(draft)
			await validateProfile(body)
			if (profileId) {
				return updateProfile(profileId, body)
			}
			return createProfile(body)
		},
		onSuccess: async (saved) => {
			if (saved?.id) {
				setProfileId(saved.id)
			}
			await queryClient.invalidateQueries({ queryKey: ["profiles"] })
		},
	})
	const deploy = useMutation({
		mutationFn: () =>
			deployAgent({
				host: host.trim(),
				user: userName.trim() || "root",
				password,
				port,
				center_url: centerUrl.trim() || null,
			}),
		onSuccess: (payload) => {
			if (payload.device_code) {
				setDeviceCode(payload.device_code)
			}
		},
	})
	const confirm = useMutation({
		mutationFn: async () => {
			if (!profileId) {
				throw new ApiError(texts.setupNeedProfile)
			}
			if (!deviceCode.trim()) {
				throw new ApiError(texts.setupNeedCode)
			}
			return confirmPairing({
				device_code: deviceCode.trim(),
				trap_name: draft.name.trim() || "trap",
				profile_id: profileId,
			})
		},
		onSuccess: async (payload) => {
			const nextId = typeof payload.trap_id === "string" ? payload.trap_id : ""
			if (nextId) {
				setTrapId(nextId)
			}
			await queryClient.invalidateQueries({ queryKey: ["traps"] })
			await queryClient.invalidateQueries({ queryKey: ["pairings"] })
		},
	})
	const courier = useMutation({
		mutationFn: () =>
			setTrapCourierSsh(trapId ?? "", {
				host: courierHost.trim(),
				user: courierUser.trim() || "root",
				port: courierPort,
				password: courierPassword || null,
				private_key: courierKey || null,
				remote_data_dir: courierDir,
			}),
		onSuccess: () => setCourierDone(true),
	})

	function goBack() {
		setLocalError(null)
		setStep((current) => Math.max(0, current - 1))
	}

	function goNext() {
		setLocalError(null)
		if (step === 0 && !draft.name.trim()) {
			setLocalError(new ApiError(texts.setupNeedName))
			return
		}
		if (step === 1 && draft.services.length === 0) {
			setLocalError(new ApiError(texts.setupNeedService))
			return
		}
		if (step === 3) {
			if (!trapId) {
				setLocalError(new ApiError(texts.setupNeedTrap))
				return
			}
			if (draft.courierEnabled && !courierDone) {
				setLocalError(new ApiError(texts.setupNeedCourier))
				return
			}
		}
		setStep((current) => Math.min(stepTitles.length - 1, current + 1))
	}

	const progress = texts.setupProgress.replace("{current}", String(step + 1)).replace("{total}", String(stepTitles.length))
	const actionError = localError || save.error || deploy.error || confirm.error || courier.error

	return (
		<section>
			<PageHeader
				title={texts.setupTitle}
				lead={texts.setupLead}
				action={
					<Link to="/home" className="text-[13px] text-muted">
						{texts.cancel}
					</Link>
				}
			/>
			<p className="text-[12px] uppercase tracking-wide text-faint">{progress}</p>
			<ol className="mt-2 mb-4 flex flex-wrap gap-2">
				{stepTitles.map((title, index) => (
					<li
						key={title}
						className={`rounded-[var(--radius)] border px-2 py-1 text-[12px] ${index === step ? "border-accent text-accent" : "border-line text-faint"}`}
					>
						{index + 1}. {title}
					</li>
				))}
			</ol>
			<div key={step} className="rise-in">
				{step === 0 ? (
					<div className={`${cardClass} grid max-w-xl gap-3 p-4`}>
						<p className="text-[13px] text-muted">{texts.setupTipObject}</p>
						<Field label={texts.setupCallsign}>
							<TextInput value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
						</Field>
						<Field label={texts.setupSegment}>
							<TextInput
								value={draft.description}
								onChange={(event) => setDraft({ ...draft, description: event.target.value })}
							/>
						</Field>
					</div>
				) : null}
				{step === 1 ? (
					<div className="grid gap-3">
						<p className="text-[13px] text-muted">{texts.setupTipModules}</p>
						<ProfileForm
							part="modules"
							draft={draft}
							onChange={setDraft}
							readOnly={false}
							personalities={[]}
							fsPacks={(fsPacks.data?.items ?? []).map((pack) => ({ token: pack.token, name: pack.name }))}
						/>
					</div>
				) : null}
				{step === 2 ? (
					<div className="grid gap-3">
						<p className="text-[13px] text-muted">{texts.setupTipConceal}</p>
						<ProfileForm
							part="conceal"
							draft={draft}
							onChange={setDraft}
							readOnly={false}
							personalities={personalities.data?.items ?? []}
							fsPacks={[]}
						/>
					</div>
				) : null}
				{step === 3 ? (
					<div className="grid max-w-xl gap-4">
						<p className="text-[13px] text-muted">{texts.setupTipInstall}</p>
						<div className="flex flex-wrap items-center gap-2">
							<Button type="button" disabled={save.isPending} onClick={() => save.mutate()}>
								{texts.setupSaveProfile}
							</Button>
							{profileId ? <span className="text-[13px] text-ok">{texts.setupProfileSaved} {shortId(profileId)}</span> : null}
						</div>
						{canDeploy ? (
							<div className="flex gap-2">
								<Button type="button" tone={installMode === "ssh" ? "primary" : "ghost"} onClick={() => setInstallMode("ssh")}>
									{texts.setupInstallSsh}
								</Button>
								<Button type="button" tone={installMode === "code" ? "primary" : "ghost"} onClick={() => setInstallMode("code")}>
									{texts.setupInstallCode}
								</Button>
							</div>
						) : null}
						{canDeploy && installMode === "ssh" ? (
							<form
								className={`${cardClass} grid gap-3 p-4`}
								onSubmit={(event) => {
									event.preventDefault()
									deploy.mutate()
								}}
							>
								<p className="text-[13px] text-muted">{texts.setupTipSsh}</p>
								<Field label={texts.fieldHost}>
									<TextInput value={host} onChange={(event) => setHost(event.target.value)} />
								</Field>
								<div className="grid grid-cols-2 gap-3">
									<Field label={texts.fieldUser}>
										<TextInput value={userName} onChange={(event) => setUserName(event.target.value)} />
									</Field>
									<Field label={texts.fieldPort}>
										<TextInput type="number" value={port} onChange={(event) => setPort(Number(event.target.value))} />
									</Field>
								</div>
								<Field label={texts.fieldPassword}>
									<TextInput type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
								</Field>
								<Field label={texts.fieldCenterUrl}>
									<TextInput value={centerUrl} onChange={(event) => setCenterUrl(event.target.value)} />
								</Field>
								<Button type="submit" disabled={deploy.isPending || !profileId}>
									{texts.setupDeploy}
								</Button>
							</form>
						) : null}
						<form
							className={`${cardClass} grid gap-3 p-4`}
							onSubmit={(event) => {
								event.preventDefault()
								if (!canPair) {
									setLocalError(new ApiError(texts.forbiddenBody))
									return
								}
								confirm.mutate()
							}}
						>
							<Field label={texts.fieldDeviceCode}>
								<TextInput value={deviceCode} onChange={(event) => setDeviceCode(event.target.value)} />
							</Field>
							<Button type="submit" disabled={confirm.isPending || !canPair}>
								{texts.setupConfirm}
							</Button>
							{trapId ? <p className="text-[13px] text-ok">{texts.setupDone}: {shortId(trapId)}</p> : null}
						</form>
						{draft.courierEnabled && trapId ? (
							<form
								className={`${cardClass} grid gap-3 p-4`}
								onSubmit={(event) => {
									event.preventDefault()
									courier.mutate()
								}}
							>
								<p className="text-[13px] text-muted">{texts.setupCourierAfter}</p>
								<Field label={texts.fieldHost}>
									<TextInput value={courierHost} onChange={(event) => setCourierHost(event.target.value)} />
								</Field>
								<div className="grid grid-cols-2 gap-3">
									<Field label={texts.fieldUser}>
										<TextInput value={courierUser} onChange={(event) => setCourierUser(event.target.value)} />
									</Field>
									<Field label={texts.fieldPort}>
										<TextInput type="number" value={courierPort} onChange={(event) => setCourierPort(Number(event.target.value))} />
									</Field>
								</div>
								<Field label={texts.fieldPassword}>
									<TextInput type="password" value={courierPassword} onChange={(event) => setCourierPassword(event.target.value)} />
								</Field>
								<Field label={texts.trapsKey}>
									<textarea
										className="min-h-20 w-full rounded-[var(--radius)] border border-line bg-sunken px-2 py-1 text-[13px]"
										value={courierKey}
										onChange={(event) => setCourierKey(event.target.value)}
									/>
								</Field>
								<Field label={texts.trapsRemoteDir}>
									<TextInput value={courierDir} onChange={(event) => setCourierDir(event.target.value)} />
								</Field>
								<div className="flex flex-wrap gap-2">
									<Button type="submit" disabled={courier.isPending}>
										{texts.setupSaveCourier}
									</Button>
									<Button type="button" tone="ghost" onClick={() => setCourierDone(true)}>
										{texts.setupSkipCourier}
									</Button>
								</div>
							</form>
						) : null}
					</div>
				) : null}
				{step === 4 ? (
					<div className={`${cardClass} grid max-w-xl gap-3 p-4`}>
						<h2 className="text-[16px] font-medium">{texts.setupDone}: {draft.name}</h2>
						<p className="text-[13px] text-muted">{texts.setupDoneHint}</p>
						<p className="text-[13px] text-muted">{texts.setupProbe}</p>
						<div className="grid gap-1 text-[13px]">
							<div>
								{texts.fieldStatus}: {liveTrap ? <StatusBadge value={liveTrap.status} /> : texts.statusPending}
							</div>
							<div className="text-muted">
								{texts.fieldSeen}: {formatDateTime(liveTrap?.last_seen_at)}
							</div>
							<div className="text-muted">
								{texts.fieldProfile}: {shortId(profileId)}
							</div>
						</div>
						<Link to="/events" className="text-[13px] text-accent">
							{texts.setupOpenEvents}
						</Link>
					</div>
				) : null}
			</div>
			<ErrorText error={actionError} />
			<div className="mt-4 flex flex-wrap gap-2">
				{step > 0 ? (
					<Button type="button" tone="ghost" onClick={goBack}>
						{texts.setupBack}
					</Button>
				) : null}
				{step < stepTitles.length - 1 ? (
					<Button type="button" onClick={goNext}>
						{texts.setupNext}
					</Button>
				) : (
					<Link to="/home" className="inline-flex h-8 items-center rounded-[var(--radius)] bg-accent px-3 text-[13px] font-medium text-accent-text">
						{texts.backHome}
					</Link>
				)}
			</div>
		</section>
	)
}
