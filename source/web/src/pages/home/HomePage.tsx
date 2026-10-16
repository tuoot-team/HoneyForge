import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router"

import { listEvents, listProfiles, listTraps } from "../../shared/api/resources"
import { useAuth } from "../../shared/auth/AuthProvider"
import { eventSummary, formatSource } from "../../shared/lib/eventLog"
import { formatDateTime, shortId } from "../../shared/lib/format"
import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { CountRingChart } from "../../shared/ui/charts"
import { StatusBadge } from "../../shared/ui/controls"
import { Rise } from "../../shared/ui/rise"
import { EventsChart } from "../events/EventsChart"

const tiles = [
	{ path: "/profiles", title: texts.tileProfilesTitle, body: texts.tileProfilesBody },
	{ path: "/traps", title: texts.tileTrapsTitle, body: texts.tileTrapsBody },
	{ path: "/pairing", title: texts.tilePairingTitle, body: texts.tilePairingBody },
	{ path: "/events", title: texts.tileEventsTitle, body: texts.tileEventsBody },
]

const steps = [
	{ title: texts.stepLoginTitle, body: texts.stepLoginBody },
	{ title: texts.stepProfileTitle, body: texts.stepProfileBody },
	{ title: texts.stepBindTitle, body: texts.stepBindBody },
	{ title: texts.stepFeedTitle, body: texts.stepFeedBody },
]

const trapStatuses = ["online", "pending", "offline"] as const

export function HomePage() {
	const auth = useAuth()
	const canWrite = auth.hasPermission("profiles.write")
	const canProfiles = auth.hasPermission("profiles.read")
	const canTraps = auth.hasPermission("traps.read")
	const canEvents = auth.hasPermission("events.read")
	const profiles = useQuery({ queryKey: ["profiles"], queryFn: listProfiles, enabled: canProfiles })
	const traps = useQuery({ queryKey: ["traps"], queryFn: listTraps, enabled: canTraps })
	const events = useQuery({
		queryKey: ["events", "home"],
		queryFn: () => listEvents({ limit: 100 }),
		enabled: canEvents,
	})
	const eventItems = events.data?.items ?? []
	const statusValues = trapStatuses.map((status) => (traps.data ?? []).filter((trap) => trap.status === status).length)
	const hasTrapChart = canTraps && (traps.data?.length ?? 0) > 0

	const stats = [
		statCard(texts.statProfiles, auth.status === "ready", canProfiles, profiles.isLoading, profiles.isError, profiles.data?.length),
		statCard(texts.statTraps, auth.status === "ready", canTraps, traps.isLoading, traps.isError, traps.data?.length),
		statCard(texts.statEvents, auth.status === "ready", canEvents, events.isLoading, events.isError, events.data?.total),
	]

	return (
		<section>
			<Rise>
				<div className="flex items-start justify-between gap-3">
					<div>
						<p className="text-[12px] text-faint">
							<span>{texts.appName}</span>
							<span className="px-1.5">/</span>
							<span className="text-muted">{texts.homeTitle}</span>
						</p>
						<h1 className="home-title mt-1 text-[20px] font-semibold tracking-tight">{texts.homeTitle}</h1>
						<p className="mt-2 max-w-2xl text-[14px] text-muted">{texts.homeLead}</p>
						<p className="mt-1 max-w-2xl text-[12px] text-faint">{texts.homeNote}</p>
					</div>
					{canWrite ? (
						<Link
							to="/setup"
							aria-label={texts.setupOpen}
							className="grid h-8 w-8 shrink-0 place-items-center rounded-[var(--radius)] bg-accent text-[18px] font-medium leading-none text-accent-text"
						>
							+
						</Link>
					) : null}
				</div>
			</Rise>

			<Rise delay={60}>
				<div className="mt-6 grid gap-3 sm:grid-cols-3">
					{stats.map((stat) => (
						<article key={stat.label} className={`${cardClass} px-4 py-3`}>
							<div className="text-[12px] text-muted">{stat.label}</div>
							<div className="mt-2 text-[22px] font-semibold tracking-tight">{stat.value}</div>
							<div className="mt-1 text-[12px] text-faint">{stat.hint}</div>
						</article>
					))}
				</div>
			</Rise>

			<Rise delay={120}>
				<div className="mt-6 grid gap-3 lg:grid-cols-2">
					<article className={`${cardClass} p-4`}>
						<h2 className="mb-3 text-[13px] text-muted">{texts.homeStatusChart}</h2>
						{hasTrapChart ? (
							<>
								<CountRingChart
									labels={[texts.statusOnline, texts.statusPending, texts.statusOffline]}
									values={statusValues}
									tones={["ok", "accent", "danger"]}
									centerLabel={texts.chartTotal}
								/>
							</>
						) : (
							<p className="text-[13px] text-muted">{chartHint(auth.status === "ready", canTraps, traps.isLoading, traps.isError)}</p>
						)}
					</article>
					<article className={`${cardClass} p-4`}>
						<h2 className="mb-3 text-[13px] text-muted">{texts.homeEventsChart}</h2>
						{canEvents && eventItems.length > 0 ? (
							<EventsChart items={eventItems} />
						) : (
							<p className="text-[13px] text-muted">{chartHint(auth.status === "ready", canEvents, events.isLoading, events.isError)}</p>
						)}
					</article>
				</div>
			</Rise>

			<Rise delay={180}>
				<h2 className="mt-8 text-[12px] uppercase tracking-wide text-faint">{texts.homeRecent}</h2>
				<div className="mt-3 overflow-x-auto border border-line">
					<table className="data-table min-w-[860px]">
						<thead className="text-faint">
							<tr>
								<th className="px-3 py-2 font-medium">{texts.eventsWhen}</th>
								<th className="px-3 py-2 font-medium">{texts.fieldPriority}</th>
								<th className="px-3 py-2 font-medium">{texts.fieldEventType}</th>
								<th className="px-3 py-2 font-medium">{texts.eventsSource}</th>
								<th className="px-3 py-2 font-medium">{texts.eventsSummary}</th>
								<th className="px-3 py-2 font-medium">{texts.eventsTrap}</th>
							</tr>
						</thead>
						<tbody>
							{eventItems.slice(0, 8).map((item) => {
								const trap = (traps.data ?? []).find((row) => row.id === item.trap_id)
								return (
									<tr key={item.id} className="border-t border-line align-top">
										<td className="px-3 py-2 text-muted">{formatDateTime(item.occurred_at || item.created_at)}</td>
										<td className="px-3 py-2">
											<StatusBadge value={item.priority || "low"} />
										</td>
										<td className="px-3 py-2">{item.event_type}</td>
										<td className="px-3 py-2">{formatSource(item.source_ip, item.source_port)}</td>
										<td className="max-w-md px-3 py-2 text-[12px] text-muted">{eventSummary(item.payload) || texts.emptyValue}</td>
										<td className="px-3 py-2 text-muted">{trap?.name || shortId(item.trap_id)}</td>
									</tr>
								)
							})}
						</tbody>
					</table>
					{canEvents && !events.isLoading && eventItems.length === 0 ? (
						<p className="px-3 py-4 text-[13px] text-muted">{texts.emptyList}</p>
					) : null}
					{!canEvents ? <p className="px-3 py-4 text-[13px] text-muted">{chartHint(auth.status === "ready", false, false, false)}</p> : null}
				</div>
			</Rise>

			<Rise delay={240}>
				<h2 className="mt-8 text-[12px] uppercase tracking-wide text-faint">{texts.homeSectionsTitle}</h2>
				<div className="mt-3 grid gap-3 md:grid-cols-2">
					{tiles.map((tile) => (
						<Link key={tile.path} to={tile.path} className={`${cardClass} block px-4 py-3 hover:bg-surface-hover`}>
							<div className="flex items-center justify-between gap-3">
								<h3 className="text-[14px] font-medium">{tile.title}</h3>
								<span className="text-[12px] text-faint">{texts.open}</span>
							</div>
							<p className="mt-1 text-[13px] text-muted">{tile.body}</p>
						</Link>
					))}
				</div>
			</Rise>

			<Rise delay={300}>
				<h2 className="mt-8 text-[12px] uppercase tracking-wide text-faint">{texts.homeFlowTitle}</h2>
				<ol className="mt-3 grid gap-3 lg:grid-cols-4">
					{steps.map((step, index) => (
						<li key={step.title} className={`${cardClass} px-4 py-3`}>
							<div className="grid h-7 w-7 place-items-center border border-line text-[12px]">{index + 1}</div>
							<h3 className="mt-3 text-[14px] font-medium">{step.title}</h3>
							<p className="mt-1 text-[13px] text-muted">{step.body}</p>
						</li>
					))}
				</ol>
			</Rise>
		</section>
	)
}

function chartHint(ready: boolean, allowed: boolean, loading: boolean, failed: boolean) {
	if (!ready) {
		return texts.statHint
	}
	if (!allowed) {
		return texts.statHintDenied
	}
	if (loading) {
		return texts.loading
	}
	if (failed) {
		return texts.statHintError
	}
	return texts.emptyList
}

function statCard(
	label: string,
	ready: boolean,
	allowed: boolean,
	loading: boolean,
	failed: boolean,
	count: number | undefined,
) {
	if (!ready) {
		return { label, value: texts.statEmpty, hint: texts.statHint }
	}
	if (!allowed) {
		return { label, value: texts.statEmpty, hint: texts.statHintDenied }
	}
	if (loading) {
		return { label, value: texts.loadingShort, hint: texts.statHintReady }
	}
	if (failed) {
		return { label, value: texts.statEmpty, hint: texts.statHintError }
	}
	return { label, value: String(count ?? 0), hint: texts.statHintReady }
}
