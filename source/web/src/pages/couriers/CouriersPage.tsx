import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { confirmCourier, deployCourier, listCourierPairings, listCouriers } from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { formatDateTime } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, Field, PageHeader, StatusBadge, TextInput } from "../../shared/ui/controls"

export function CouriersPage() {
	const auth = useAuth()
	const queryClient = useQueryClient()
	const canWrite = auth.hasPermission("couriers.write") || auth.hasPermission("pairing.write")
	const canDeploy = auth.hasPermission("deploy.write")
	const couriers = useQuery({ queryKey: ["couriers"], queryFn: listCouriers })
	const pairings = useQuery({ queryKey: ["courier-pairings"], queryFn: () => listCourierPairings("all") })
	const [deviceCode, setDeviceCode] = useState("")
	const [name, setName] = useState("courier")
	const [host, setHost] = useState("")
	const [userName, setUserName] = useState("root")
	const [password, setPassword] = useState("")
	const [port, setPort] = useState(22)
	const [centerUrl, setCenterUrl] = useState("")
	const [result, setResult] = useState("")
	const confirm = useMutation({
		mutationFn: () => confirmCourier({ device_code: deviceCode.trim(), name: name.trim() || "courier" }),
		onSuccess: async (payload) => {
			setResult(JSON.stringify(payload, null, 2))
			await queryClient.invalidateQueries({ queryKey: ["couriers"] })
			await queryClient.invalidateQueries({ queryKey: ["courier-pairings"] })
		},
	})
	const deploy = useMutation({
		mutationFn: () =>
			deployCourier({
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
			<PageHeader title={texts.couriersTitle} lead={texts.couriersLead} />
			<div className="grid gap-4 lg:grid-cols-2">
				{canWrite ? (
					<form
						className={`${cardClass} grid gap-3 p-4`}
						onSubmit={(event) => {
							event.preventDefault()
							confirm.mutate()
						}}
					>
						<h2 className="text-[14px] font-medium">{texts.couriersConfirm}</h2>
						<Field label={texts.fieldDeviceCode}>
							<TextInput value={deviceCode} onChange={(event) => setDeviceCode(event.target.value)} />
						</Field>
						<Field label={texts.fieldName}>
							<TextInput value={name} onChange={(event) => setName(event.target.value)} />
						</Field>
						<Button type="submit">{texts.couriersConfirm}</Button>
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
						<h2 className="text-[14px] font-medium">{texts.couriersDeploy}</h2>
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
						<Button type="submit">{texts.couriersDeploy}</Button>
					</form>
				) : null}
			</div>
			{result ? <pre className={`${cardClass} mt-4 overflow-x-auto p-4 text-[12px]`}>{result}</pre> : null}
			<ErrorText error={couriers.error || pairings.error || confirm.error || deploy.error} />
			<h2 className="mt-6 text-[14px] font-medium">{texts.navCouriers}</h2>
			<RecordTable
				rows={(couriers.data ?? []).map((courier) => ({
					id: courier.id,
					primary: courier.name,
					status: courier.status,
					when: formatDateTime(courier.last_seen_at),
				}))}
			/>
			<h2 className="mt-6 text-[14px] font-medium">{texts.couriersPairings}</h2>
			<RecordTable
				rows={(pairings.data?.items ?? []).map((item) => ({
					id: item.id,
					primary: item.device_code,
					status: item.status,
					when: formatDateTime(item.created_at),
				}))}
			/>
		</section>
	)
}

function RecordTable({ rows }: { rows: { id: string; primary: string; status: string; when: string }[] }) {
	return (
		<div className="mt-2 overflow-x-auto border border-line">
			<table className="data-table min-w-[560px]">
				<tbody>
					{rows.map((row) => (
						<tr key={row.id} className="border-t border-line">
							<td className="px-3 py-2">{row.primary}</td>
							<td className="px-3 py-2">
								<StatusBadge value={row.status} />
							</td>
							<td className="px-3 py-2 text-muted">{row.when}</td>
						</tr>
					))}
				</tbody>
			</table>
			{rows.length === 0 ? <p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p> : null}
		</div>
	)
}
