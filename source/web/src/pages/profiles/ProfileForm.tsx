import type { PersonalityPack, ServiceType } from "../../shared/api/types"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, Field, SelectInput, TextInput } from "../../shared/ui/controls"
import {
	createServiceDraft,
	suggestInteractionLevel,
	type CredentialDraft,
	type ProfileDraft,
	type ServiceDraft,
} from "./profileDraft"

export type ProfileFormPart = "all" | "modules" | "conceal"

const serviceOptions: { type: ServiceType; label: string }[] = [
	{ type: "ssh", label: texts.serviceSsh },
	{ type: "http", label: texts.serviceHttp },
	{ type: "tcp_banner", label: texts.serviceTcp },
	{ type: "postgres", label: texts.servicePostgres },
	{ type: "redis", label: texts.serviceRedis },
	{ type: "mysql", label: texts.serviceMysql },
	{ type: "container", label: texts.serviceContainer },
]

export function ProfileForm({
	draft,
	onChange,
	readOnly,
	personalities,
	fsPacks,
	part = "all",
}: {
	draft: ProfileDraft
	onChange: (next: ProfileDraft) => void
	readOnly: boolean
	personalities: PersonalityPack[]
	fsPacks: { token: string; name: string }[]
	part?: ProfileFormPart
}) {
	const showIdentity = part === "all"
	const showModules = part === "all" || part === "modules"
	const showConceal = part === "all" || part === "conceal"
	const suggested = suggestInteractionLevel(draft)
	function patch(partial: Partial<ProfileDraft>) {
		onChange({ ...draft, ...partial })
	}
	function patchService(index: number, partial: Partial<ServiceDraft>) {
		const services = draft.services.map((service, serviceIndex) => {
			if (serviceIndex !== index) {
				return service
			}
			const next = { ...service, ...partial }
			if (partial.authEnabled === false) {
				next.shellEnabled = false
			}
			return next
		})
		onChange({ ...draft, services })
	}

	return (
		<div className="grid gap-4">
			{showIdentity ? (
			<section className={`${cardClass} grid gap-3 p-4 md:grid-cols-2`}>
				<Field label={texts.fieldName}>
					<TextInput value={draft.name} disabled={readOnly} onChange={(event) => patch({ name: event.target.value })} />
				</Field>
				<Field label={texts.fieldLevel}>
					<SelectInput
						value={draft.interactionLevel}
						disabled={readOnly}
						onChange={(event) => patch({ interactionLevel: event.target.value as ProfileDraft["interactionLevel"] })}
					>
						<option value="low">{texts.levelLow}</option>
						<option value="medium">{texts.levelMedium}</option>
						<option value="high">{texts.levelHigh}</option>
					</SelectInput>
				</Field>
				<div className="md:col-span-2">
					<Field label={texts.fieldDescription}>
						<TextInput
							value={draft.description}
							disabled={readOnly}
							onChange={(event) => patch({ description: event.target.value })}
						/>
					</Field>
				</div>
				<p className="text-[12px] text-faint md:col-span-2">
					{texts.levelHint}: {suggested}
					{readOnly ? null : (
						<button
							type="button"
							className="ml-3 text-accent"
							onClick={() => patch({ interactionLevel: suggested })}
						>
							{texts.levelApply}
						</button>
					)}
				</p>
			</section>
			) : null}

			{showModules ? (
			<>
			<section className={`${cardClass} p-4`}>
				<div className="mb-3 flex items-center justify-between gap-3">
					<h2 className="text-[14px] font-medium">{texts.sectionServices}</h2>
					{readOnly ? null : (
						<Button
							type="button"
							tone="ghost"
							onClick={() => patch({ services: [...draft.services, createServiceDraft("ssh", draft.services.length + 1)] })}
						>
							{texts.add}
						</Button>
					)}
				</div>
				<div className="grid gap-3">
					{draft.services.map((service, index) => (
						<ServiceCard
							key={`${service.id}-${index}`}
							listId={`fs-packs-${index}`}
							service={service}
							readOnly={readOnly}
							fsPacks={fsPacks}
							onChange={(partial) => patchService(index, partial)}
							onRemove={() => patch({ services: draft.services.filter((_, serviceIndex) => serviceIndex !== index) })}
						/>
					))}
				</div>
			</section>

			<section className={`${cardClass} p-4`}>
				<div className="mb-3 flex items-center justify-between gap-3">
					<h2 className="text-[14px] font-medium">{texts.sectionCredentials}</h2>
					{readOnly ? null : (
						<Button
							type="button"
							tone="ghost"
							onClick={() =>
								patch({
									credentials: [
										...draft.credentials,
										{ id: `cred-${draft.credentials.length + 1}`, username: "", password: "", note: "" },
									],
								})
							}
						>
							{texts.add}
						</Button>
					)}
				</div>
				<div className="grid gap-3">
					{draft.credentials.map((credential, index) => (
						<CredentialCard
							key={`${credential.id}-${index}`}
							credential={credential}
							readOnly={readOnly}
							onChange={(partial) => {
								const credentials = draft.credentials.map((item, itemIndex) =>
									itemIndex === index ? { ...item, ...partial } : item,
								)
								patch({ credentials })
							}}
							onRemove={() =>
								patch({ credentials: draft.credentials.filter((_, itemIndex) => itemIndex !== index) })
							}
						/>
					))}
				</div>
			</section>
			</>
			) : null}

			{showConceal ? (
			<section className={`${cardClass} grid gap-3 p-4`}>
				<h2 className="text-[14px] font-medium">{texts.sectionMask}</h2>
				<Check
					label={texts.maskCourier}
					checked={draft.courierEnabled}
					disabled={readOnly}
					onChange={(courierEnabled) => patch({ courierEnabled })}
				/>
				{draft.courierEnabled ? (
					<Field label={texts.maskInterval}>
						<TextInput
							type="number"
							disabled={readOnly}
							value={draft.collectIntervalSec}
							onChange={(event) => patch({ collectIntervalSec: Number(event.target.value) })}
						/>
					</Field>
				) : (
					<div className="grid gap-3 md:grid-cols-2">
						<Check label={texts.maskJitter} checked={draft.jitterEnabled} disabled={readOnly} onChange={(jitterEnabled) => patch({ jitterEnabled })} />
						<Field label={texts.maskBeacon}>
							<TextInput type="number" disabled={readOnly} value={draft.beaconIntervalSec} onChange={(event) => patch({ beaconIntervalSec: Number(event.target.value) })} />
						</Field>
						<Field label={texts.maskJitterPct}>
							<TextInput type="number" disabled={readOnly} value={draft.jitterPct} onChange={(event) => patch({ jitterPct: Number(event.target.value) })} />
						</Field>
						<Check label={texts.maskCover} checked={draft.coverEnabled} disabled={readOnly} onChange={(coverEnabled) => patch({ coverEnabled })} />
						<Field label={texts.maskCover}>
							<TextInput disabled={readOnly} value={draft.coverUrls} onChange={(event) => patch({ coverUrls: event.target.value })} />
						</Field>
						<Check label={texts.maskPaths} checked={draft.pathRotationEnabled} disabled={readOnly} onChange={(pathRotationEnabled) => patch({ pathRotationEnabled })} />
						<Field label={texts.maskPaths}>
							<TextInput disabled={readOnly} value={draft.paths} onChange={(event) => patch({ paths: event.target.value })} />
						</Field>
						<Check label={texts.maskMimicry} checked={draft.mimicryEnabled} disabled={readOnly} onChange={(mimicryEnabled) => patch({ mimicryEnabled })} />
						<Field label={texts.maskUserAgent}>
							<TextInput disabled={readOnly} value={draft.userAgent} onChange={(event) => patch({ userAgent: event.target.value })} />
						</Field>
						<Field label={texts.maskTls}>
							<TextInput disabled={readOnly} value={draft.tlsProfile} onChange={(event) => patch({ tlsProfile: event.target.value })} />
						</Field>
						<Check label={texts.maskProcessEnabled} checked={draft.processMaskEnabled} disabled={readOnly} onChange={(processMaskEnabled) => patch({ processMaskEnabled })} />
						<Field label={texts.maskProcess}>
							<TextInput disabled={readOnly} value={draft.processName} onChange={(event) => patch({ processName: event.target.value })} />
						</Field>
					</div>
				)}
				<Field label={texts.maskSeed}>
					<TextInput disabled={readOnly} value={draft.decoyContentSeed} onChange={(event) => patch({ decoyContentSeed: event.target.value })} />
				</Field>
				<Field label={texts.maskPersonality}>
					<TextInput
						list="personality-packs"
						disabled={readOnly}
						value={draft.servicePersonality}
						onChange={(event) => patch({ servicePersonality: event.target.value })}
					/>
					<datalist id="personality-packs">
						{personalities.map((pack) => (
							<option key={pack.key} value={pack.key}>
								{pack.title}
							</option>
						))}
					</datalist>
				</Field>
			</section>
			) : null}

			{showIdentity ? (
			<>
			<section className={`${cardClass} grid gap-2 p-4`}>
				<h2 className="text-[14px] font-medium">{texts.sectionLogging}</h2>
				<Check label={texts.logCredentials} checked={draft.captureCredentials} disabled={readOnly} onChange={(captureCredentials) => patch({ captureCredentials })} />
				<Check label={texts.logPayloads} checked={draft.capturePayloads} disabled={readOnly} onChange={(capturePayloads) => patch({ capturePayloads })} />
				<Check label={texts.logSource} checked={draft.captureSourceMeta} disabled={readOnly} onChange={(captureSourceMeta) => patch({ captureSourceMeta })} />
			</section>

			<section className={`${cardClass} grid gap-3 p-4 md:grid-cols-2`}>
				<h2 className="text-[14px] font-medium md:col-span-2">{texts.sectionEmulation}</h2>
				<div className="md:col-span-2">
					<Check label={texts.emulationOn} checked={draft.emulationEnabled} disabled={readOnly} onChange={(emulationEnabled) => patch({ emulationEnabled })} />
				</div>
				<Field label={texts.emulationImage}>
					<TextInput disabled={readOnly} value={draft.imageToken} onChange={(event) => patch({ imageToken: event.target.value })} />
				</Field>
				<Field label={texts.emulationVmName}>
					<TextInput disabled={readOnly} value={draft.vmName} onChange={(event) => patch({ vmName: event.target.value })} />
				</Field>
				<Field label={texts.emulationCpus}>
					<TextInput type="number" disabled={readOnly} value={draft.vmCpus} onChange={(event) => patch({ vmCpus: Number(event.target.value) })} />
				</Field>
				<Field label={texts.emulationMemory}>
					<TextInput type="number" disabled={readOnly} value={draft.vmMemoryMb} onChange={(event) => patch({ vmMemoryMb: Number(event.target.value) })} />
				</Field>
			</section>
			</>
			) : null}
		</div>
	)
}

function ServiceCard({
	service,
	readOnly,
	listId,
	fsPacks,
	onChange,
	onRemove,
}: {
	service: ServiceDraft
	readOnly: boolean
	listId: string
	fsPacks: { token: string; name: string }[]
	onChange: (partial: Partial<ServiceDraft>) => void
	onRemove: () => void
}) {
	const showAuth = service.type !== "tcp_banner" && service.type !== "container"
	return (
		<div className="grid gap-3 border border-line p-3 md:grid-cols-3">
			<Field label={texts.fieldType}>
				<SelectInput
					value={service.type}
					disabled={readOnly}
					onChange={(event) => onChange({ type: event.target.value as ServiceType })}
				>
					{serviceOptions.map((option) => (
						<option key={option.type} value={option.type}>
							{option.label}
						</option>
					))}
				</SelectInput>
			</Field>
			<Field label={texts.fieldId}>
				<TextInput value={service.id} disabled={readOnly} onChange={(event) => onChange({ id: event.target.value })} />
			</Field>
			<Field label={texts.fieldPort}>
				<TextInput type="number" value={service.port} disabled={readOnly} onChange={(event) => onChange({ port: Number(event.target.value) })} />
			</Field>
			<div className="md:col-span-3">
				<Check label={texts.fieldEnabled} checked={service.enabled} disabled={readOnly} onChange={(enabled) => onChange({ enabled })} />
			</div>
			{service.type !== "container" ? (
				<Field label={texts.fieldBanner}>
					<TextInput value={service.banner} disabled={readOnly} onChange={(event) => onChange({ banner: event.target.value })} />
				</Field>
			) : null}
			{service.type === "http" ? (
				<Field label={texts.fieldTitle}>
					<TextInput value={service.httpTitle} disabled={readOnly} onChange={(event) => onChange({ httpTitle: event.target.value })} />
				</Field>
			) : null}
			{service.type === "container" ? (
				<>
					<Field label={texts.fieldImage}>
						<TextInput value={service.image} disabled={readOnly} onChange={(event) => onChange({ image: event.target.value })} />
					</Field>
					<Field label={texts.fieldContainerPort}>
						<TextInput type="number" value={service.containerPort} disabled={readOnly} onChange={(event) => onChange({ containerPort: Number(event.target.value) })} />
					</Field>
				</>
			) : null}
			{showAuth ? (
				<>
					<div className="md:col-span-3">
						<Check label={texts.fieldAuth} checked={service.authEnabled} disabled={readOnly} onChange={(authEnabled) => onChange({ authEnabled })} />
					</div>
					<Field label={texts.fieldAuthMode}>
						<SelectInput value={service.authMode} disabled={readOnly || !service.authEnabled} onChange={(event) => onChange({ authMode: event.target.value as ServiceDraft["authMode"] })}>
							<option value="allow_all">{texts.authAllowAll}</option>
							<option value="allow_listed">{texts.authAllowListed}</option>
							<option value="second_attempt_sticky">{texts.authSticky}</option>
						</SelectInput>
					</Field>
					<Field label={texts.fieldCredentialIds}>
						<TextInput value={service.credentialIds} disabled={readOnly || !service.authEnabled} onChange={(event) => onChange({ credentialIds: event.target.value })} />
					</Field>
					<Field label={texts.fieldDelayMin}>
						<TextInput type="number" value={service.delayMin} disabled={readOnly} onChange={(event) => onChange({ delayMin: Number(event.target.value) })} />
					</Field>
					<Field label={texts.fieldDelayMax}>
						<TextInput type="number" value={service.delayMax} disabled={readOnly} onChange={(event) => onChange({ delayMax: Number(event.target.value) })} />
					</Field>
				</>
			) : null}
			{service.type === "ssh" ? (
				<>
					<div className="md:col-span-3">
						<Check label={texts.fieldShell} checked={service.shellEnabled} disabled={readOnly || !service.authEnabled} onChange={(shellEnabled) => onChange({ shellEnabled })} />
					</div>
					<Field label={texts.fieldFsPack}>
						<TextInput list={listId} value={service.fsPack} disabled={readOnly} onChange={(event) => onChange({ fsPack: event.target.value })} />
						<datalist id={listId}>
							<option value="ubuntu-22.04" />
							{fsPacks.map((pack) => (
								<option key={pack.token} value={pack.token}>
									{pack.name}
								</option>
							))}
						</datalist>
					</Field>
				</>
			) : null}
			{readOnly ? null : (
				<div className="md:col-span-3">
					<Button type="button" tone="ghost" onClick={onRemove}>
						{texts.remove}
					</Button>
				</div>
			)}
		</div>
	)
}

function CredentialCard({
	credential,
	readOnly,
	onChange,
	onRemove,
}: {
	credential: CredentialDraft
	readOnly: boolean
	onChange: (partial: Partial<CredentialDraft>) => void
	onRemove: () => void
}) {
	return (
		<div className="grid gap-3 border border-line p-3 md:grid-cols-4">
			<Field label={texts.fieldId}>
				<TextInput value={credential.id} disabled={readOnly} onChange={(event) => onChange({ id: event.target.value })} />
			</Field>
			<Field label={texts.fieldUsername}>
				<TextInput value={credential.username} disabled={readOnly} onChange={(event) => onChange({ username: event.target.value })} />
			</Field>
			<Field label={texts.fieldPassword}>
				<TextInput value={credential.password} disabled={readOnly} onChange={(event) => onChange({ password: event.target.value })} />
			</Field>
			<Field label={texts.fieldNote}>
				<TextInput value={credential.note} disabled={readOnly} onChange={(event) => onChange({ note: event.target.value })} />
			</Field>
			{readOnly ? null : (
				<div className="md:col-span-4">
					<Button type="button" tone="ghost" onClick={onRemove}>
						{texts.remove}
					</Button>
				</div>
			)}
		</div>
	)
}

function Check({
	label,
	checked,
	disabled,
	onChange,
}: {
	label: string
	checked: boolean
	disabled: boolean
	onChange: (next: boolean) => void
}) {
	return (
		<label className="flex items-center gap-2 text-[13px]">
			<input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
			{label}
		</label>
	)
}
