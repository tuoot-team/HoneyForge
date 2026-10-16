import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
	deleteFsPack,
	deleteVmImage,
	listFsPacks,
	listPersonalityPacks,
	listVmImages,
	uploadFsPack,
	uploadVmImage,
} from "../../shared/api/resources"
import type { PackRecord } from "../../shared/api/types"
import { ApiError } from "../../shared/api/http"
import { useAuth } from "../../shared/auth/AuthProvider"
import { formatBytes, formatDateTime } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, PageHeader, TextInput } from "../../shared/ui/controls"

export function AssetsPage() {
	const auth = useAuth()
	const canFs = auth.hasPermission("fs_packs.write")
	const canVm = auth.hasPermission("vm_images.write")
	const fsPacks = useQuery({ queryKey: ["fs-packs"], queryFn: listFsPacks })
	const vmImages = useQuery({ queryKey: ["vm-images"], queryFn: listVmImages })
	const personalities = useQuery({ queryKey: ["personality-packs"], queryFn: listPersonalityPacks })

	return (
		<section>
			<PageHeader title={texts.assetsTitle} lead={texts.assetsLead} />
			<ErrorText error={fsPacks.error || vmImages.error || personalities.error} />
			<PackSection
				title={texts.assetsFs}
				items={fsPacks.data?.items ?? []}
				canWrite={canFs}
				queryKey="fs-packs"
				upload={uploadFsPack}
				remove={deleteFsPack}
			/>
			<PackSection
				title={texts.assetsVm}
				items={vmImages.data?.items ?? []}
				canWrite={canVm}
				queryKey="vm-images"
				upload={uploadVmImage}
				remove={deleteVmImage}
			/>
			<h2 className="mt-6 text-[14px] font-medium">{texts.assetsPersonality}</h2>
			<ul className={`${cardClass} mt-2 divide-y divide-[var(--line)]`}>
				{(personalities.data?.items ?? []).map((pack) => (
					<li key={pack.key} className="flex justify-between gap-3 px-4 py-2 text-[13px]">
						<span>{pack.key}</span>
						<span className="text-muted">{pack.title}</span>
					</li>
				))}
			</ul>
		</section>
	)
}

function PackSection({
	title,
	items,
	canWrite,
	queryKey,
	upload,
	remove,
}: {
	title: string
	items: PackRecord[]
	canWrite: boolean
	queryKey: string
	upload: (file: File, name: string) => Promise<PackRecord>
	remove: (token: string) => Promise<void>
}) {
	const queryClient = useQueryClient()
	const [name, setName] = useState("")
	const [file, setFile] = useState<File | null>(null)
	const [confirmToken, setConfirmToken] = useState<string | null>(null)
	const send = useMutation({
		mutationFn: () => {
			if (!file) {
				throw new ApiError(texts.fieldFile)
			}
			return upload(file, name)
		},
		onSuccess: async () => {
			setFile(null)
			setName("")
			await queryClient.invalidateQueries({ queryKey: [queryKey] })
		},
	})
	const drop = useMutation({
		mutationFn: remove,
		onSuccess: async () => {
			setConfirmToken(null)
			await queryClient.invalidateQueries({ queryKey: [queryKey] })
		},
	})

	return (
		<section className="mt-4">
			<h2 className="text-[14px] font-medium">{title}</h2>
			{canWrite ? (
				<form
					className="mt-2 flex flex-wrap items-end gap-3"
					onSubmit={(event) => {
						event.preventDefault()
						send.mutate()
					}}
				>
					<Field label={texts.fieldName}>
						<TextInput value={name} onChange={(event) => setName(event.target.value)} />
					</Field>
					<Field label={texts.fieldFile}>
						<input
							type="file"
							className="text-[13px]"
							onChange={(event) => setFile(event.target.files?.[0] ?? null)}
						/>
					</Field>
					<Button type="submit" disabled={!file || send.isPending}>
						{texts.assetsUpload}
					</Button>
				</form>
			) : null}
			<ErrorText error={send.error || drop.error} />
			<div className="mt-2 overflow-x-auto border border-line">
				<table className="data-table min-w-[640px]">
					<thead className="text-faint">
						<tr>
							<th className="px-3 py-2 font-medium">{texts.fieldName}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldToken}</th>
							<th className="px-3 py-2 font-medium">{texts.assetsFormat}</th>
							<th className="px-3 py-2 font-medium">{texts.assetsSize}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldSeen}</th>
							<th />
						</tr>
					</thead>
					<tbody>
						{items.map((item) => (
							<tr key={item.token} className="border-t border-line">
								<td className="px-3 py-2">{item.name}</td>
								<td className="px-3 py-2 text-muted">{item.token}</td>
								<td className="px-3 py-2">{item.format}</td>
								<td className="px-3 py-2">{formatBytes(item.size_bytes)}</td>
								<td className="px-3 py-2 text-muted">{formatDateTime(item.created_at)}</td>
								<td className="px-3 py-2 text-right">
									{canWrite ? (
										confirmToken === item.token ? (
											<button type="button" className="text-danger" onClick={() => drop.mutate(item.token)}>
												{texts.confirmDelete}
											</button>
										) : (
											<button type="button" className="text-muted" onClick={() => setConfirmToken(item.token)}>
												{texts.delete}
											</button>
										)
									) : null}
								</td>
							</tr>
						))}
					</tbody>
				</table>
				{items.length === 0 ? <p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p> : null}
			</div>
		</section>
	)
}
