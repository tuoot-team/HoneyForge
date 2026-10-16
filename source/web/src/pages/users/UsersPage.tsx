import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { createUser, listRoles, listUsers, updateUser } from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, PageHeader, SelectInput, TextInput } from "../../shared/ui/controls"

export function UsersPage() {
	const auth = useAuth()
	const queryClient = useQueryClient()
	const users = useQuery({ queryKey: ["users"], queryFn: listUsers })
	const roles = useQuery({ queryKey: ["roles"], queryFn: listRoles, enabled: auth.hasPermission("roles.write") })
	const [username, setUsername] = useState("")
	const [password, setPassword] = useState("")
	const [roleId, setRoleId] = useState("")
	const [isSuperadmin, setIsSuperadmin] = useState(false)
	const [notice, setNotice] = useState("")
	const refresh = async () => {
		await queryClient.invalidateQueries({ queryKey: ["users"] })
	}
	const create = useMutation({
		mutationFn: () =>
			createUser({
				username: username.trim(),
				password,
				role_id: roleId,
				is_superadmin: isSuperadmin,
			}),
		onSuccess: async () => {
			setUsername("")
			setPassword("")
			setNotice(texts.saved)
			await refresh()
		},
	})
	const patch = useMutation({
		mutationFn: ({ userId, body }: { userId: string; body: unknown }) => updateUser(userId, body),
		onSuccess: async () => {
			setNotice(texts.saved)
			await refresh()
		},
	})

	return (
		<section>
			<PageHeader title={texts.usersTitle} lead={texts.usersLead} />
			<form
				className={`${cardClass} grid gap-3 p-4 md:grid-cols-2`}
				onSubmit={(event) => {
					event.preventDefault()
					create.mutate()
				}}
			>
				<h2 className="text-[14px] font-medium md:col-span-2">{texts.usersCreate}</h2>
				<Field label={texts.fieldUsername}>
					<TextInput value={username} onChange={(event) => setUsername(event.target.value)} />
				</Field>
				<Field label={texts.fieldPassword}>
					<TextInput type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
				</Field>
				<Field label={texts.fieldRole}>
					{roles.data ? (
						<SelectInput value={roleId} onChange={(event) => setRoleId(event.target.value)}>
							<option value="">{texts.emptyValue}</option>
							{roles.data.map((role) => (
								<option key={role.id} value={role.id}>
									{role.name}
								</option>
							))}
						</SelectInput>
					) : (
						<TextInput value={roleId} onChange={(event) => setRoleId(event.target.value)} />
					)}
				</Field>
				{auth.me?.is_superadmin ? (
					<label className="flex items-center gap-2 text-[13px]">
						<input type="checkbox" checked={isSuperadmin} onChange={(event) => setIsSuperadmin(event.target.checked)} />
						{texts.fieldSuperadmin}
					</label>
				) : null}
				<div className="md:col-span-2">
					<Button type="submit" disabled={create.isPending || !roleId}>
						{texts.create}
					</Button>
				</div>
			</form>
			{notice ? <p className="mt-3 text-[13px] text-ok">{notice}</p> : null}
			<ErrorText error={users.error || create.error || patch.error || roles.error} />
			<div className="mt-4 overflow-x-auto border border-line">
				<table className="data-table min-w-[720px]">
					<thead className="text-faint">
						<tr>
							<th className="px-3 py-2 font-medium">{texts.fieldUsername}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldRole}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldDisabled}</th>
							<th />
						</tr>
					</thead>
					<tbody>
						{(users.data ?? []).map((user) => (
							<tr key={user.id} className="border-t border-line">
								<td className="px-3 py-2">
									{user.username}
									{user.is_superadmin ? <span className="ml-2 text-[12px] text-faint">superadmin</span> : null}
								</td>
								<td className="px-3 py-2">
									{roles.data ? (
										<SelectInput
											value={user.role_id}
											onChange={(event) => patch.mutate({ userId: user.id, body: { role_id: event.target.value } })}
										>
											{roles.data.map((role) => (
												<option key={role.id} value={role.id}>
													{role.name}
												</option>
											))}
										</SelectInput>
									) : (
										user.role_name
									)}
								</td>
								<td className="px-3 py-2">{user.disabled ? texts.yes : texts.no}</td>
								<td className="px-3 py-2 text-right">
									<button
										type="button"
										className="text-muted"
										onClick={() => patch.mutate({ userId: user.id, body: { disabled: !user.disabled } })}
									>
										{user.disabled ? texts.usersEnable : texts.usersDisable}
									</button>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</section>
	)
}
