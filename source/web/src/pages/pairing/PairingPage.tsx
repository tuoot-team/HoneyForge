import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { confirmPairing, deployAgent, listPairings, listProfiles } from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { formatDateTime } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, PageHeader, SelectInput, StatusBadge, TextInput } from "../../shared/ui/controls"

export function PairingPage() {
	const auth = useAuth()
	const queryClient = useQueryClient()
	const canPair = auth.hasPermission("pairing.write")
	const canDeploy = auth.hasPermission("deploy.write")
	const [status, setStatus] = useState("pending")
	const [deviceCode, setDeviceCode] = useState("")
	const [trapName, setTrapName] = useState("trap")
	const [profileId, setProfileId] = useState("")
	const [host, setHost] = useState("")
	const [userName, setUserName] = useState("root")
	const [password, setPassword] = useState("")
	const [port, setPort] = useState(22)
	const [centerUrl, setCenterUrl] = useState("")
	const [result, setResult] = useState("")
	const pairings = useQuery({ queryKey: ["pairings", status], queryFn: () => listPairings(status) })
	const profiles = useQuery({
		queryKey: ["profiles"],
		queryFn: listProfiles,
		enabled: auth.hasPermission("profiles.read"),
	})
	const confirm = useMutation({
		mutationFn: () =>
			confirmPairing({
				device_code: deviceCode.trim(),
				trap_name: trapName.trim() || "trap",
				profile_id: profileId || null,
			}),
		onSuccess: async (payload) => {
			setResult(JSON.stringify(payload, null, 2))
			await queryClient.invalidateQueries({ queryKey: ["pairings"] })
			await queryClient.invalidateQueries({ queryKey: ["traps"] })
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
			setResult(JSON.stringify(payload, null, 2))
			if (payload.device_code) {
				setDeviceCode(payload.device_code)
			}
		},
	})

	return (
		<section>
			<PageHeader title={texts.pairingTitle} lead={texts.pairingLead} />
			<div className="grid gap-4 lg:grid-cols-2">
				{canPair ? (
					<form
						className={`${cardClass} grid gap-3 p-4`}
						onSubmit={(event) => {
							event.preventDefault()
							confirm.mutate()
						}}
					>
						<h2 className="text-[14px] font-medium">{texts.pairingConfirm}</h2>
						<Field label={texts.fieldDeviceCode}>
							<TextInput value={deviceCode} onChange={(event) => setDeviceCode(event.target.value)} />
						</Field>
						<Field label={texts.fieldTrapName}>
							<TextInput value={trapName} onChange={(event) => setTrapName(event.target.value)} />
						</Field>
						<Field label={texts.fieldProfile}>
							<SelectInput value={profileId} onChange={(event) => setProfileId(event.target.value)}>
								<option value="">{texts.trapsNoProfile}</option>
								{(profiles.data ?? []).map((profile) => (
									<option key={profile.id} value={profile.id}>
										{profile.name}
									</option>
								))}
							</SelectInput>
						</Field>
						<Button type="submit" disabled={confirm.isPending}>
							{texts.pairingConfirm}
						</Button>
					</form>
				) : null}
				{canDeploy ? (
					<form
						className={`${cardClass} grid gap-3 p-4`}
						onSubmit={(event) => {
							event.preventDefault()
							deploy.mutate()
						}}
					>
						<h2 className="text-[14px] font-medium">{texts.pairingDeploy}</h2>
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
						<Button type="submit" disabled={deploy.isPending}>
							{texts.pairingDeploy}
						</Button>
					</form>
				) : null}
			</div>
			{result ? (
				<pre className={`${cardClass} mt-4 overflow-x-auto p-4 text-[12px] text-muted`}>{result}</pre>
			) : null}
			<div className="mt-4">
				<ErrorText error={pairings.error || confirm.error || deploy.error} />
				<div className="mb-3 flex items-center gap-2">
					<span className="text-[13px] text-muted">{texts.pairingList}</span>
					<SelectInput className="max-w-40" value={status} onChange={(event) => setStatus(event.target.value)}>
						<option value="pending">pending</option>
						<option value="confirmed">confirmed</option>
						<option value="completed">completed</option>
						<option value="expired">expired</option>
						<option value="all">{texts.pairingStatusAll}</option>
					</SelectInput>
				</div>
				<div className="overflow-x-auto border border-line">
					<table className="data-table min-w-[640px]">
						<thead className="text-faint">
							<tr>
								<th className="px-3 py-2 font-medium">{texts.fieldDeviceCode}</th>
								<th className="px-3 py-2 font-medium">{texts.fieldStatus}</th>
								<th className="px-3 py-2 font-medium">{texts.fieldSeen}</th>
							</tr>
						</thead>
						<tbody>
							{(pairings.data?.items ?? []).map((item) => (
								<tr key={item.pairing_id} className="border-t border-line">
									<td className="px-3 py-2">{item.device_code}</td>
									<td className="px-3 py-2">
										<StatusBadge value={item.status} />
									</td>
									<td className="px-3 py-2 text-muted">{formatDateTime(item.created_at)}</td>
								</tr>
							))}
						</tbody>
					</table>
					{pairings.data && pairings.data.items.length === 0 ? (
						<p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p>
					) : null}
				</div>
			</div>
		</section>
	)
}
