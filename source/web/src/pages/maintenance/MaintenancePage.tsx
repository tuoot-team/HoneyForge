import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { clearLogs, resetDatabase } from "../../shared/api/resources"
import type { WipeResult } from "../../shared/api/types"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { Button, ErrorText, PageHeader } from "../../shared/ui/controls"

export function MaintenancePage() {
	const [confirm, setConfirm] = useState<"clear" | "reset" | null>(null)
	const [result, setResult] = useState<WipeResult | null>(null)
	const clear = useMutation({
		mutationFn: clearLogs,
		onSuccess: (payload) => {
			setResult(payload)
			setConfirm(null)
		},
	})
	const reset = useMutation({
		mutationFn: resetDatabase,
		onSuccess: (payload) => {
			setResult(payload)
			setConfirm(null)
		},
	})

	return (
		<section>
			<PageHeader title={texts.maintenanceTitle} lead={texts.maintenanceLead} />
			<div className="flex flex-wrap gap-3">
				{confirm === "clear" ? (
					<Button type="button" tone="danger" onClick={() => clear.mutate()}>
						{texts.maintenanceClearConfirm}
					</Button>
				) : (
					<Button type="button" tone="ghost" onClick={() => setConfirm("clear")}>
						{texts.maintenanceClear}
					</Button>
				)}
				{confirm === "reset" ? (
					<Button type="button" tone="danger" onClick={() => reset.mutate()}>
						{texts.maintenanceResetConfirm}
					</Button>
				) : (
					<Button type="button" tone="danger" onClick={() => setConfirm("reset")}>
						{texts.maintenanceReset}
					</Button>
				)}
			</div>
			<ErrorText error={clear.error || reset.error} />
			{result ? (
				<div className={`${cardClass} mt-4 p-4 text-[13px]`}>
					<div className="mb-2 text-muted">{texts.maintenanceDeleted}</div>
					<ul>
						{Object.entries(result.deleted).map(([key, count]) => (
							<li key={key}>
								{key}: {count}
							</li>
						))}
					</ul>
				</div>
			) : null}
		</section>
	)
}
