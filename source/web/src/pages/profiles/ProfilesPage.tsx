import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router"

import { deleteProfile, listProfiles } from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { formatDateTime, shortId } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { primaryClass } from "../../shared/ui/classes"
import { ErrorText, PageHeader, StatusBadge } from "../../shared/ui/controls"
import { useState } from "react"

export function ProfilesPage() {
	const auth = useAuth()
	const queryClient = useQueryClient()
	const canWrite = auth.hasPermission("profiles.write")
	const [confirmId, setConfirmId] = useState<string | null>(null)
	const profiles = useQuery({ queryKey: ["profiles"], queryFn: listProfiles })
	const remove = useMutation({
		mutationFn: deleteProfile,
		onSuccess: async () => {
			setConfirmId(null)
			await queryClient.invalidateQueries({ queryKey: ["profiles"] })
		},
	})

	return (
		<section>
			<PageHeader
				title={texts.profilesTitle}
				lead={texts.profilesLead}
				action={
					canWrite ? (
						<Link to="/profiles/new" className={primaryClass}>
							{texts.profilesNew}
						</Link>
					) : null
				}
			/>
			<ErrorText error={profiles.error || remove.error} />
			<div className="overflow-x-auto border border-line">
				<table className="data-table min-w-[720px]">
					<thead className="text-faint">
						<tr>
							<th className="px-3 py-2 font-medium">{texts.fieldName}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldLevel}</th>
							<th className="num px-3 py-2 font-medium">{texts.fieldVersion}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldHash}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldSeen}</th>
							<th className="px-3 py-2" />
						</tr>
					</thead>
					<tbody>
						{(profiles.data ?? []).map((profile) => (
							<tr key={profile.id} className="border-t border-line">
								<td className="px-3 py-2">
									<Link to={`/profiles/${profile.id}`} className="text-fg">
										{profile.name}
									</Link>
								</td>
								<td className="px-3 py-2">
									<StatusBadge value={profile.interaction_level} />
								</td>
								<td className="num px-3 py-2">{profile.config_version}</td>
								<td className="px-3 py-2 text-muted">{shortId(profile.config_hash)}</td>
								<td className="px-3 py-2 text-muted">{formatDateTime(profile.updated_at)}</td>
								<td className="px-3 py-2 text-right">
									{canWrite ? (
										confirmId === profile.id ? (
											<button type="button" className="text-danger" onClick={() => remove.mutate(profile.id)}>
												{texts.confirmDelete}
											</button>
										) : (
											<button type="button" className="text-muted" onClick={() => setConfirmId(profile.id)}>
												{texts.delete}
											</button>
										)
									) : null}
								</td>
							</tr>
						))}
					</tbody>
				</table>
				{profiles.data && profiles.data.length === 0 ? (
					<p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p>
				) : null}
			</div>
		</section>
	)
}
