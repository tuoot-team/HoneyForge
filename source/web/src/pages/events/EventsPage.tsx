import { useQuery } from "@tanstack/react-query"
import { Fragment, useEffect, useMemo, useState } from "react"

import { exportEvents, listEventChains, listEvents, listTraps } from "../../shared/api/resources"
import type { EventItem, EventPriority } from "../../shared/api/types"
import { streamSse } from "../../shared/api/http"
import { eventSummary, formatSource, hotPayloadKeys, payloadRows } from "../../shared/lib/eventLog"
import { formatDateTime, shortId } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { chartColorAt, CountRingChart, ShareList } from "../../shared/ui/charts"
import { Button, ErrorText, Field, PageHeader, SelectInput, StatusBadge, TextInput } from "../../shared/ui/controls"
import { EventsChart } from "./EventsChart"

const priorityRank: Record<EventPriority, number> = { low: 0, medium: 1, high: 2 }

export function EventsPage() {
	const traps = useQuery({ queryKey: ["traps"], queryFn: listTraps })
	const [trapId, setTrapId] = useState("")
	const [eventType, setEventType] = useState("")
	const [sourceIp, setSourceIp] = useState("")
	const [minPriority, setMinPriority] = useState<"" | EventPriority>("")
	const [importantOnly, setImportantOnly] = useState(false)
	const [windowSec, setWindowSec] = useState(3600)
	const [live, setLive] = useState(true)
	const [liveItems, setLiveItems] = useState<EventItem[] | null>(null)
	const [streamError, setStreamError] = useState<unknown>(null)
	const [exportError, setExportError] = useState<unknown>(null)
	const [streamAttempt, setStreamAttempt] = useState(0)
	const [openEventId, setOpenEventId] = useState<number | null>(null)
	const effectivePriority = importantOnly ? "high" : minPriority
	const filters = useMemo(
		() => ({
			trap_id: trapId || undefined,
			event_type: eventType || undefined,
			source_ip: sourceIp || undefined,
			min_priority: effectivePriority || undefined,
			limit: 100,
		}),
		[effectivePriority, eventType, sourceIp, trapId],
	)
	const events = useQuery({ queryKey: ["events", filters], queryFn: () => listEvents(filters) })
	const chains = useQuery({
		queryKey: ["event-chains", trapId, windowSec],
		queryFn: () => listEventChains({ trap_id: trapId || undefined, window_sec: windowSec }),
	})
	const items = liveItems ?? events.data?.items ?? []

	useEffect(() => {
		setLiveItems(null)
	}, [filters])

	useEffect(() => {
		if (!live) {
			return
		}
		const controller = new AbortController()
		setStreamError(null)
		void streamSse(
			"/api/v1/events/stream",
			(payload) => {
				const event = normalizeEvent(payload)
				if (!event || !passesFilters(event, trapId, eventType, sourceIp, effectivePriority)) {
					return
				}
				setLiveItems((current) => {
					const base = current ?? events.data?.items ?? []
					return [event, ...base.filter((item) => item.id !== event.id)].slice(0, 200)
				})
			},
			controller.signal,
		).catch((error: unknown) => {
			if (!controller.signal.aborted) {
				setStreamError(error)
			}
		})
		return () => controller.abort()
	}, [effectivePriority, eventType, events.data?.items, live, sourceIp, streamAttempt, trapId])

	async function download(format: "csv" | "stix") {
		setExportError(null)
		try {
			const body = await exportEvents({ ...filters, format, limit: 5000 })
			const blob = new Blob([body], { type: format === "stix" ? "application/json" : "text/csv" })
			const url = URL.createObjectURL(blob)
			const link = document.createElement("a")
			link.href = url
			link.download = format === "stix" ? "events.stix.json" : "events.csv"
			link.click()
			window.setTimeout(() => URL.revokeObjectURL(url), 1000)
		} catch (error) {
			setExportError(error)
		}
	}

	const topSources = useMemo(() => countSources(items), [items])
	const priorityCounts = useMemo(() => countPriorities(items), [items])
	const hasPriorities = priorityCounts.values.some((value) => value > 0)
	const shown = texts.eventsShown
		.replace("{shown}", String(items.length))
		.replace("{total}", String(events.data?.total ?? items.length))

	return (
		<section>
			<PageHeader
				title={texts.eventsTitle}
				lead={texts.eventsLead}
				action={
					<div className="flex gap-2">
						<Button type="button" tone="ghost" onClick={() => void download("csv")}>
							{texts.eventsExportCsv}
						</Button>
						<Button type="button" tone="ghost" onClick={() => void download("stix")}>
							{texts.eventsExportStix}
						</Button>
					</div>
				}
			/>
			<form
				className="mb-4 grid gap-3 md:grid-cols-4"
				onSubmit={(event) => {
					event.preventDefault()
					void events.refetch()
				}}
			>
				<Field label={texts.eventsTrap}>
					<SelectInput value={trapId} onChange={(event) => setTrapId(event.target.value)}>
						<option value="">{texts.pairingStatusAll}</option>
						{(traps.data ?? []).map((trap) => (
							<option key={trap.id} value={trap.id}>
								{trap.name}
							</option>
						))}
					</SelectInput>
				</Field>
				<Field label={texts.fieldEventType}>
					<TextInput value={eventType} onChange={(event) => setEventType(event.target.value)} />
				</Field>
				<Field label={texts.fieldSourceIp}>
					<TextInput value={sourceIp} onChange={(event) => setSourceIp(event.target.value)} />
				</Field>
				<Field label={texts.fieldPriority}>
					<SelectInput
						value={minPriority}
						onChange={(event) => setMinPriority(event.target.value as "" | EventPriority)}
					>
						<option value="">{texts.pairingStatusAll}</option>
						<option value="low">{texts.priorityLow}</option>
						<option value="medium">{texts.priorityMedium}</option>
						<option value="high">{texts.priorityHigh}</option>
					</SelectInput>
				</Field>
				<label className="flex items-center gap-2 text-[13px]">
					<input type="checkbox" checked={importantOnly} onChange={(event) => setImportantOnly(event.target.checked)} />
					{texts.eventsImportant}
				</label>
				<label className="flex items-center gap-2 text-[13px]">
					<input type="checkbox" checked={live} onChange={(event) => setLive(event.target.checked)} />
					{texts.eventsLive}
				</label>
				<Field label={texts.fieldWindow}>
					<TextInput type="number" value={windowSec} onChange={(event) => setWindowSec(Number(event.target.value))} />
				</Field>
				<div className="flex items-end">
					<Button type="submit" tone="ghost">
						{texts.eventsApplyFilters}
					</Button>
				</div>
			</form>
			<ErrorText error={events.error || chains.error || streamError || exportError} />
			{streamError ? (
				<Button type="button" tone="ghost" className="mb-3" onClick={() => setStreamAttempt((value) => value + 1)}>
					{texts.eventsRetry}
				</Button>
			) : null}
			<div className="grid gap-3 lg:grid-cols-3">
				<article className={`${cardClass} p-4`}>
					<h2 className="mb-3 text-[13px] text-muted">{texts.eventsChart}</h2>
					<EventsChart items={items} />
				</article>
				<article className={`${cardClass} p-4`}>
					<h2 className="mb-3 text-[13px] text-muted">{texts.eventsPriorityChart}</h2>
					{hasPriorities ? (
						<>
							<CountRingChart
								labels={[texts.priorityLow, texts.priorityMedium, texts.priorityHigh]}
								values={priorityCounts.values}
								tones={["muted", "accent", "danger"]}
								centerLabel={texts.chartTotal}
							/>
						</>
					) : (
						<p className="text-[13px] text-muted">{texts.emptyList}</p>
					)}
				</article>
				<article className={`${cardClass} p-4`}>
					<h2 className="mb-3 text-[13px] text-muted">{texts.eventsSources}</h2>
					{topSources.length === 0 ? (
						<p className="text-[13px] text-muted">{texts.emptyList}</p>
					) : (
						<ShareList
							rows={topSources.map((source, index) => ({
								label: source.ip,
								value: source.count,
								color: chartColorAt(index),
							}))}
						/>
					)}
				</article>
			</div>
			<p className="mt-4 text-[12px] text-faint">{shown}</p>
			<div className="mt-2 overflow-x-auto border border-line">
				<table className="data-table min-w-[980px]">
					<thead className="text-faint">
						<tr>
							<th className="px-3 py-2 font-medium">{texts.eventsWhen}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldPriority}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldEventType}</th>
							<th className="px-3 py-2 font-medium">{texts.eventsSource}</th>
							<th className="px-3 py-2 font-medium">{texts.eventsTrap}</th>
							<th className="px-3 py-2 font-medium">{texts.eventsSummary}</th>
							<th className="px-3 py-2" />
						</tr>
					</thead>
					<tbody>
						{items.map((item) => {
							const open = openEventId === item.id
							const summary = eventSummary(item.payload)
							const trap = (traps.data ?? []).find((row) => row.id === item.trap_id)
							return (
								<Fragment key={item.id}>
									<tr className="border-t border-line align-top">
										<td className="px-3 py-2 text-muted">{formatDateTime(item.occurred_at || item.created_at)}</td>
										<td className="px-3 py-2">
											<StatusBadge value={item.priority || "low"} />
										</td>
										<td className="px-3 py-2">{item.event_type}</td>
										<td className="px-3 py-2">{formatSource(item.source_ip, item.source_port)}</td>
										<td className="px-3 py-2">
											<div>{trap?.name || texts.emptyValue}</div>
											<div className="text-[12px] text-faint">{shortId(item.trap_id)}</div>
										</td>
										<td className="max-w-md px-3 py-2 text-[12px] text-muted">{summary || texts.emptyValue}</td>
										<td className="px-3 py-2 text-right">
											<button
												type="button"
												className="text-[12px] text-accent"
												onClick={() => setOpenEventId(open ? null : item.id)}
											>
												{open ? texts.eventsHide : texts.eventsDetails}
											</button>
										</td>
									</tr>
									{open ? (
										<tr className="border-t border-line bg-sunken">
											<td className="px-3 py-3" colSpan={7}>
												<EventDetail item={item} />
											</td>
										</tr>
									) : null}
								</Fragment>
							)
						})}
					</tbody>
				</table>
				{items.length === 0 ? <p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p> : null}
			</div>
			<h2 className="mt-6 text-[14px] font-medium">{texts.eventsChains}</h2>
			<div className="mt-2 overflow-x-auto border border-line">
				<table className="data-table min-w-[980px]">
					<thead className="text-faint">
						<tr>
							<th className="px-3 py-2 font-medium">{texts.fieldSourceIp}</th>
							<th className="num px-3 py-2 font-medium">{texts.eventsCount}</th>
							<th className="px-3 py-2 font-medium">{texts.eventsPorts}</th>
							<th className="px-3 py-2 font-medium">{texts.chainsServices}</th>
							<th className="px-3 py-2 font-medium">{texts.chainsTypes}</th>
							<th className="px-3 py-2 font-medium">{texts.chainsFirst}</th>
							<th className="px-3 py-2 font-medium">{texts.chainsLast}</th>
							<th className="px-3 py-2 font-medium">{texts.fieldPriority}</th>
							<th className="px-3 py-2 font-medium">{texts.eventsLateral}</th>
						</tr>
					</thead>
					<tbody>
						{(chains.data?.items ?? []).map((chain) => (
							<tr key={`${chain.source_ip}-${chain.trap_id ?? ""}`} className="border-t border-line align-top">
								<td className="px-3 py-2">{chain.source_ip}</td>
								<td className="num px-3 py-2">{chain.event_count}</td>
								<td className="px-3 py-2 text-muted">{chain.ports.join(", ") || texts.emptyValue}</td>
								<td className="px-3 py-2 text-muted">{chain.services.join(", ") || texts.emptyValue}</td>
								<td className="px-3 py-2 text-muted">{chain.event_types.join(", ") || texts.emptyValue}</td>
								<td className="px-3 py-2 text-muted">{formatDateTime(chain.first_at)}</td>
								<td className="px-3 py-2 text-muted">{formatDateTime(chain.last_at)}</td>
								<td className="px-3 py-2">
									<StatusBadge value={chain.max_priority} />
								</td>
								<td className="px-3 py-2">{chain.is_lateral ? texts.yes : texts.no}</td>
							</tr>
						))}
					</tbody>
				</table>
				{chains.isSuccess && chains.data.items.length === 0 ? (
					<p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p>
				) : null}
			</div>
		</section>
	)
}

function normalizeEvent(payload: unknown): EventItem | null {
	if (!payload || typeof payload !== "object") {
		return null
	}
	const record = payload as Partial<EventItem>
	if (typeof record.id !== "number" || typeof record.event_type !== "string") {
		return null
	}
	const priority = record.priority === "high" || record.priority === "medium" || record.priority === "low" ? record.priority : "low"
	return {
		id: record.id,
		trap_id: record.trap_id ?? null,
		event_type: record.event_type,
		source_ip: record.source_ip ?? null,
		source_port: record.source_port ?? null,
		occurred_at: record.occurred_at ?? null,
		payload: record.payload ?? {},
		created_at: record.created_at,
		priority,
	}
}

const payloadLabels: Record<string, string> = {
	username: texts.eventsUser,
	password: texts.fieldPassword,
	command: texts.eventsCommand,
	path: texts.eventsPath,
	method: texts.eventsMethod,
	service: texts.eventsService,
	database: texts.eventsDatabase,
	banner: texts.eventsBanner,
	kind: texts.eventsKind,
	trigger: texts.eventsTrigger,
	success: texts.eventsSuccess,
	token_id: texts.eventsToken,
	port: texts.fieldPort,
	detail: texts.eventsDetail,
	ok: texts.fieldStatus,
}

function EventDetail({ item }: { item: EventItem }) {
	const rows = payloadRows(item.payload)
	return (
		<div className="grid gap-3">
			<div className="flex flex-wrap gap-x-6 gap-y-1 text-[12px] text-muted">
				<span>
					{texts.eventsId}: {item.id}
				</span>
				<span>
					{texts.eventsTrap}: {item.trap_id || texts.emptyValue}
				</span>
				<span>
					{texts.eventsWhen}: {formatDateTime(item.occurred_at || item.created_at)}
				</span>
			</div>
			{rows.length === 0 ? (
				<p className="text-[13px] text-muted">{texts.emptyList}</p>
			) : (
				<dl className="grid gap-2 sm:grid-cols-2">
					{rows.map((row) => (
						<div key={row.key} className="min-w-0">
							<dt className="text-[11px] uppercase tracking-wide text-faint">{payloadLabels[row.key] || row.key}</dt>
							<dd className={`mt-0.5 break-all text-[13px] ${hotPayloadKeys.has(row.key) ? "text-danger" : ""}`}>{row.value}</dd>
						</div>
					))}
				</dl>
			)}
			<pre className="max-h-64 overflow-auto border border-line bg-canvas p-3 text-[12px] text-muted">
				{JSON.stringify(item.payload ?? {}, null, 2)}
			</pre>
			<p className="text-[11px] text-faint">{texts.eventsRaw}</p>
		</div>
	)
}

function passesFilters(
	event: EventItem,
	trapId: string,
	eventType: string,
	sourceIp: string,
	minPriority: "" | EventPriority,
): boolean {
	if (trapId && event.trap_id !== trapId) {
		return false
	}
	if (eventType && event.event_type !== eventType) {
		return false
	}
	if (sourceIp && event.source_ip !== sourceIp) {
		return false
	}
	if (minPriority && priorityRank[event.priority] < priorityRank[minPriority]) {
		return false
	}
	return true
}

function countPriorities(items: EventItem[]) {
	const labels = [texts.priorityLow, texts.priorityMedium, texts.priorityHigh]
	const values = [0, 0, 0]
	for (const item of items) {
		const rank = priorityRank[item.priority] ?? 0
		values[rank] += 1
	}
	return { labels, values }
}

function countSources(items: EventItem[]) {
	const counts = new Map<string, number>()
	for (const item of items) {
		if (!item.source_ip) {
			continue
		}
		counts.set(item.source_ip, (counts.get(item.source_ip) ?? 0) + 1)
	}
	return [...counts.entries()]
		.sort((left, right) => right[1] - left[1])
		.slice(0, 6)
		.map(([ip, count]) => ({ ip, count }))
}
