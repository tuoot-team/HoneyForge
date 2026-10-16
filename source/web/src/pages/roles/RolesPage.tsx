import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { createRole, deleteRole, listPermissionCatalog, listRoles, updateRole } from "../../shared/api/resources"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, PageHeader, TextInput } from "../../shared/ui/controls"

export function RolesPage() {
	const queryClient = useQueryClient()
	const roles = useQuery({ queryKey: ["roles"], queryFn: listRoles })
	const catalog = useQuery({ queryKey: ["permissions"], queryFn: listPermissionCatalog })
	const [name, setName] = useState("")
	const [selected, setSelected] = useState<string[]>([])
	const [notice, setNotice] = useState("")
	const [confirmId, setConfirmId] = useState<string | null>(null)
	const refresh = async () => {
		await queryClient.invalidateQueries({ queryKey: ["roles"] })
	}
	const create = useMutation({
		mutationFn: () => createRole({ name: name.trim(), permissions: selected }),
		onSuccess: async () => {
			setName("")
			setSelected([])
			setNotice(texts.saved)
			await refresh()
		},
	})
	const save = useMutation({
		mutationFn: ({ roleId, permissions }: { roleId: string; permissions: string[] }) =>
			updateRole(roleId, { permissions }),
		onSuccess: async () => {
			setNotice(texts.saved)
			await refresh()
		},
	})
	const remove = useMutation({
		mutationFn: deleteRole,
		onSuccess: async () => {
			setConfirmId(null)
			await refresh()
		},
	})

	return (
		<section>
			<PageHeader title={texts.rolesTitle} lead={texts.rolesLead} />
			<form
				className={`${cardClass} grid gap-3 p-4`}
				onSubmit={(event) => {
					event.preventDefault()
					create.mutate()
				}}
			>
				<h2 className="text-[14px] font-medium">{texts.rolesCreate}</h2>
				<Field label={texts.fieldName}>
					<TextInput value={name} onChange={(event) => setName(event.target.value)} />
				</Field>
				<PermissionGrid
					catalog={catalog.data?.permissions ?? []}
					selected={selected}
					onChange={setSelected}
				/>
				<Button type="submit" disabled={!name.trim() || create.isPending}>
					{texts.create}
				</Button>
			</form>
			{notice ? <p className="mt-3 text-[13px] text-ok">{notice}</p> : null}
			<ErrorText error={roles.error || catalog.error || create.error || save.error || remove.error} />
			<div className="mt-4 grid gap-3">
				{(roles.data ?? []).map((role) => (
					<RoleCard
						key={role.id}
						roleId={role.id}
						name={role.name}
						isSystem={role.is_system}
						permissions={role.permissions}
						catalog={catalog.data?.permissions ?? role.permissions}
						confirming={confirmId === role.id}
						onAskDelete={() => setConfirmId(role.id)}
						onDelete={() => remove.mutate(role.id)}
						onSave={(permissions) => save.mutate({ roleId: role.id, permissions })}
					/>
				))}
			</div>
		</section>
	)
}

function RoleCard({
	name,
	isSystem,
	permissions,
	catalog,
	confirming,
	onAskDelete,
	onDelete,
	onSave,
}: {
	roleId: string
	name: string
	isSystem: boolean
	permissions: string[]
	catalog: string[]
	confirming: boolean
	onAskDelete: () => void
	onDelete: () => void
	onSave: (permissions: string[]) => void
}) {
	const [selected, setSelected] = useState(permissions)
	return (
		<article className={`${cardClass} p-4`}>
			<div className="mb-3 flex flex-wrap items-center justify-between gap-2">
				<h2 className="text-[14px] font-medium">{name}</h2>
				{isSystem ? (
					<span className="text-[12px] text-faint">{texts.rolesSystem}</span>
				) : (
					<div className="flex gap-2">
						<Button type="button" tone="ghost" onClick={() => onSave(selected)}>
							{texts.rolesSavePerms}
						</Button>
						{confirming ? (
							<Button type="button" tone="danger" onClick={onDelete}>
								{texts.confirmDelete}
							</Button>
						) : (
							<Button type="button" tone="ghost" onClick={onAskDelete}>
								{texts.delete}
							</Button>
						)}
					</div>
				)}
			</div>
			<PermissionGrid catalog={catalog} selected={selected} disabled={isSystem} onChange={setSelected} />
		</article>
	)
}

function PermissionGrid({
	catalog,
	selected,
	disabled = false,
	onChange,
}: {
	catalog: string[]
	selected: string[]
	disabled?: boolean
	onChange: (next: string[]) => void
}) {
	return (
		<div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
			{catalog.map((permission) => {
				const checked = selected.includes(permission)
				return (
					<label key={permission} className="flex items-center gap-2 text-[13px]">
						<input
							type="checkbox"
							checked={checked}
							disabled={disabled}
							onChange={() => {
								onChange(checked ? selected.filter((item) => item !== permission) : [...selected, permission])
							}}
						/>
						{permission}
					</label>
				)
			})}
		</div>
	)
}
