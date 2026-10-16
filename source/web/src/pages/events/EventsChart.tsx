import { useMemo } from "react"

import type { EventItem } from "../../shared/api/types"
import { texts } from "../../shared/texts"
import { CountBarChart } from "../../shared/ui/charts"

export function EventsChart({ items }: { items: EventItem[] }) {
	const counts = useMemo(() => {
		const map = new Map<string, number>()
		for (const item of items) {
			map.set(item.event_type, (map.get(item.event_type) ?? 0) + 1)
		}
		return { labels: [...map.keys()], values: [...map.values()] }
	}, [items])

	if (counts.labels.length === 0) {
		return <p className="text-[13px] text-muted">{texts.emptyList}</p>
	}
	return <CountBarChart labels={counts.labels} values={counts.values} seriesLabel={texts.eventsChart} />
}
