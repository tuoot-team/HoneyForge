import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { bindTrapProfile, listProfiles, listTraps, listUsers, setTrapCourierSsh, setTrapOwner, trapVmAction } from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { formatDateTime, shortId } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { Button, ErrorText, Field, PageHeader, SelectInput, StatusBadge, TextInput } from "../../shared/ui/controls"

const vmActions = ["ensure", "start", "stop", "revert", "status"] as const

export function TrapsPage() {
	const auth = useAuth()
	const queryClient = useQueryClient()
	const canWrite = auth.hasPermission("traps.write")
	const canUsers = auth.hasPermission("users.write")
	const traps = useQuery({ queryKey: ["traps"], queryFn: listTraps })
	const profiles = useQuery({
		queryKey: ["profiles"],
		queryFn: listProfiles,
		enabled: auth.hasPermission("profiles.read"),
	})
	const users = useQuery({ queryKey: ["users"], queryFn: listUsers, enabled: canUsers })
	const [profileByTrap, setProfileByTrap] = useState<Record<string, string>>({})
	const [ownerByTrap, setOwnerByTrap] = useState<Record<string, string>>({})
	const [sshTrapId, setSshTrapId] = useState<string | null>(null)
	const [host, setHost] = useState("")
	const [userName, setUserName] = useState("root")
	const [port, setPort] = useState(22)
	const [password, setPassword] = useState("")
	const [privateKey, setPrivateKey] = useState("")
	const [remoteDir, setRemoteDir] = useState("/var/lib/metricsd")
	const [notice, setNotice] = useState("")

	const refresh = async () => {
		await queryClient.invalidateQueries({ queryKey: ["traps"] })
	}
	const bind = useMutation({
		mutationFn: ({ trapId, profileId }: { trapId: string; profileId: string }) => bindTrapProfile(trapId, profileId),
		onSuccess: async () => {
			setNotice(texts.saved)
			await refresh()
		},
	})
	const owner = useMutation({
		mutationFn: ({ trapId, userId }: { trapId: string; userId: string }) => setTrapOwner(trapId, userId),
		onSuccess: async () => {
			setNotice(texts.saved)
			await refresh()
		},
	})
	const vm = useMutation({
		mutationFn: ({ trapId, action }: { trapId: string; action: string }) => trapVmAction(trapId, action),
		onSuccess: async () => {
			setNotice(texts.saved)
			await refresh()
		},
	})
	const ssh = useMutation({
		mutationFn: () =>
			setTrapCourierSsh(sshTrapId ?? "", {
				host,
				user: userName,
				port,
				password: password || null,
				private_key: privateKey || null,
				remote_data_dir: remoteDir,
			}),
		onSuccess: async () => {
			setNotice(texts.saved)
			await refresh()
		},
	})

	return (
		<section>
			<PageHeader title={texts.trapsTitle} lead={texts.trapsLead} />
			{notice ? <p className="mb-3 text-[13px] text-ok">{notice}</p> : null}
			<ErrorText error={traps.error || bind.error || owner.error || vm.error || ssh.error} />
			<div className="overflow-x-auto border border-line">
				<table className="data-table min-w-[860px]">
					<thead className="text-faint">
						<tr>
							<th className="px-3 py-2 font-medium">{texts.fieldName}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldStatus}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldProfile}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldSeen}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldOwner}</th>
						</tr>
					</thead>
					<tbody>
						{(traps.data ?? []).map((trap) => (
							<tr key={trap.id} className="border-t border-line align-top">
								<td className="px-3 py-2">
									<div>{trap.name}</div>
									<div className="text-[12px] text-faint">{shortId(trap.id)}</div>
									{trap.courier_ssh_host ? (
										<div className="text-[12px] text-muted">{trap.courier_ssh_host}</div>
									) : null}
								</td>
								<td className="px-3 py-2">
									<StatusBadge value={trap.status} />
								</td>
								<td className="px-3 py-2">
									{canWrite ? (
										<div className="flex flex-wrap gap-2">
											<SelectInput
												value={profileByTrap[trap.id] ?? trap.profile_id ?? ""}
												onChange={(event) => setProfileByTrap({ ...profileByTrap, [trap.id]: event.target.value })}
											>
												<option value="">{texts.trapsNoProfile}</option>
												{(profiles.data ?? []).map((profile) => (
													<option key={profile.id} value={profile.id}>
														{profile.name}
													</option>
												))}
											</SelectInput>
											<Button
												type="button"
												tone="ghost"
												onClick={() => {
													const profileId = profileByTrap[trap.id] ?? trap.profile_id ?? ""
													if (profileId) {
														bind.mutate({ trapId: trap.id, profileId })
													}
												}}
											>
												{texts.trapsBind}
											</Button>
										</div>
									) : (
										shortId(trap.profile_id)
									)}
									{canWrite ? (
										<div className="mt-2 flex flex-wrap gap-2">
											{vmActions.map((action) => (
												<button
													key={action}
													type="button"
													className="text-[12px] text-muted"
													onClick={() => vm.mutate({ trapId: trap.id, action })}
												>
													{action}
												</button>
											))}
											<button type="button" className="text-[12px] text-accent" onClick={() => setSshTrapId(trap.id)}>
												{texts.trapsCourierSsh}
											</button>
										</div>
									) : null}
								</td>
								<td className="px-3 py-2 text-muted">{formatDateTime(trap.last_seen_at)}</td>
								<td className="px-3 py-2">
									{canWrite && canUsers ? (
										<div className="flex flex-wrap gap-2">
											<SelectInput
												value={ownerByTrap[trap.id] ?? trap.owner_user_id ?? ""}
												onChange={(event) => setOwnerByTrap({ ...ownerByTrap, [trap.id]: event.target.value })}
											>
												<option value="">{texts.emptyValue}</option>
												{(users.data ?? []).map((user) => (
													<option key={user.id} value={user.id}>
														{user.username}
													</option>
												))}
											</SelectInput>
											<Button
												type="button"
												tone="ghost"
												onClick={() => {
													const userId = ownerByTrap[trap.id] ?? trap.owner_user_id ?? ""
													if (userId) {
														owner.mutate({ trapId: trap.id, userId })
													}
												}}
											>
												{texts.trapsOwner}
											</Button>
										</div>
									) : (
										shortId(trap.owner_user_id)
									)}
								</td>
							</tr>
						))}
					</tbody>
				</table>
				{traps.data && traps.data.length === 0 ? <p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p> : null}
			</div>
			{sshTrapId ? (
				<form
					className="mt-4 grid max-w-xl gap-3 border border-line p-4"
					onSubmit={(event) => {
						event.preventDefault()
						ssh.mutate()
					}}
				>
					<h2 className="text-[14px] font-medium">{texts.trapsCourierSsh}</h2>
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
					<Field label={texts.trapsKey}>
						<textarea className="min-h-20 w-full rounded-[var(--radius)] border border-line bg-sunken px-2 py-1 text-[13px]" value={privateKey} onChange={(event) => setPrivateKey(event.target.value)} />
					</Field>
					<Field label={texts.trapsRemoteDir}>
						<TextInput value={remoteDir} onChange={(event) => setRemoteDir(event.target.value)} />
					</Field>
					<div className="flex gap-2">
						<Button type="submit">{texts.save}</Button>
						<Button type="button" tone="ghost" onClick={() => setSshTrapId(null)}>
							{texts.cancel}
						</Button>
					</div>
				</form>
			) : null}
		</section>
	)
}
