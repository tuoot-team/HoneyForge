import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router"

import {
	createProfile,
	deleteProfile,
	getProfile,
	listFsPacks,
	listPersonalityPacks,
	updateProfile,
	validateProfile,
} from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { texts } from "../../shared/texts"
import { Button, ErrorText, PageHeader } from "../../shared/ui/controls"
import { ProfileForm } from "./ProfileForm"
import { createEmptyDraft, draftFromProfile, profileBodyFromDraft, type ProfileDraft } from "./profileDraft"

export function ProfileEditorPage() {
	const { profileId } = useParams()
	const isNew = !profileId
	const auth = useAuth()
	const navigate = useNavigate()
	const queryClient = useQueryClient()
	const canWrite = auth.hasPermission("profiles.write")
	const profile = useQuery({
		queryKey: ["profile", profileId],
		queryFn: () => getProfile(profileId ?? ""),
		enabled: Boolean(profileId),
	})
	const personalities = useQuery({ queryKey: ["personality-packs"], queryFn: listPersonalityPacks })
	const fsPacks = useQuery({ queryKey: ["fs-packs"], queryFn: listFsPacks })
	const [draft, setDraft] = useState<ProfileDraft | null>(isNew ? createEmptyDraft() : null)
	const [notice, setNotice] = useState("")
	const [loadedId, setLoadedId] = useState<string | null>(null)

	if (isNew) {
		if (loadedId !== "new") {
			setLoadedId("new")
			setDraft(createEmptyDraft())
		}
	} else if (profile.data && profile.data.id !== loadedId) {
		setLoadedId(profile.data.id)
		setDraft(draftFromProfile(profile.data))
	}

	const validate = useMutation({
		mutationFn: async () => {
			if (!draft) {
				return
			}
			await validateProfile(profileBodyFromDraft(draft))
			setNotice(texts.validateOk)
		},
	})
	const save = useMutation({
		mutationFn: async () => {
			if (!draft) {
				return null
			}
			const body = profileBodyFromDraft(draft)
			await validateProfile(body)
			if (isNew) {
				return createProfile(body)
			}
			return updateProfile(profileId ?? "", body)
		},
		onSuccess: async (saved) => {
			setNotice(texts.saved)
			await queryClient.invalidateQueries({ queryKey: ["profiles"] })
			if (saved && isNew) {
				navigate(`/profiles/${saved.id}`)
			} else if (profileId) {
				await queryClient.invalidateQueries({ queryKey: ["profile", profileId] })
			}
		},
	})
	const remove = useMutation({
		mutationFn: () => deleteProfile(profileId ?? ""),
		onSuccess: async () => {
			await queryClient.invalidateQueries({ queryKey: ["profiles"] })
			navigate("/profiles")
		},
	})

	if (profile.isLoading && !isNew) {
		return <p className="text-[13px] text-muted">{texts.loading}</p>
	}
	if (profile.isError && !isNew) {
		return <ErrorText error={profile.error} />
	}
	if (!draft) {
		return <p className="text-[13px] text-muted">{texts.profilesMissing}</p>
	}

	return (
		<section>
			<PageHeader
				title={isNew ? texts.profilesNew : draft.name || texts.profilesTitle}
				lead={canWrite ? texts.profilesLead : texts.profilesReadOnly}
				action={
					<Link to="/profiles" className="text-[13px] text-muted">
						{texts.navProfiles}
					</Link>
				}
			/>
			<ProfileForm
				draft={draft}
				onChange={setDraft}
				readOnly={!canWrite}
				personalities={personalities.data?.items ?? []}
				fsPacks={(fsPacks.data?.items ?? []).map((pack) => ({ token: pack.token, name: pack.name }))}
			/>
			<div className="mt-4 flex flex-wrap items-center gap-2">
				{canWrite ? (
					<>
						<Button type="button" tone="ghost" disabled={validate.isPending} onClick={() => validate.mutate()}>
							{texts.check}
						</Button>
						<Button type="button" disabled={save.isPending} onClick={() => save.mutate()}>
							{texts.save}
						</Button>
						{isNew ? null : (
							<Button type="button" tone="danger" disabled={remove.isPending} onClick={() => remove.mutate()}>
								{texts.delete}
							</Button>
						)}
					</>
				) : null}
				{notice ? <span className="text-[13px] text-ok">{notice}</span> : null}
				<ErrorText error={validate.error || save.error || remove.error} />
			</div>
		</section>
	)
}
