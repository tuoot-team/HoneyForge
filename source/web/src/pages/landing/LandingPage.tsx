import { texts } from "../../shared/texts"
import { cardClass } from "../../shared/ui/classes"
import { PublicFrame } from "../../widgets/public-frame/PublicFrame"

const points = [
	{ title: texts.landingPointProfileTitle, body: texts.landingPointProfileBody },
	{ title: texts.landingPointAgentTitle, body: texts.landingPointAgentBody },
	{ title: texts.landingPointCoverTitle, body: texts.landingPointCoverBody },
	{ title: texts.landingPointFeedTitle, body: texts.landingPointFeedBody },
]

export function LandingPage() {
	return (
		<PublicFrame>
			<section className="mx-auto max-w-3xl">
				<p className="text-[12px] uppercase tracking-wide text-faint">{texts.landingKicker}</p>
				<h1 className="home-title mt-2 max-w-2xl text-[28px] font-semibold leading-tight tracking-tight">
					{texts.landingTitle}
				</h1>
				<p className="mt-4 max-w-2xl text-[15px] text-muted">{texts.landingLead}</p>
				<div className="mt-8 grid gap-3 md:grid-cols-2">
					{points.map((point) => (
						<article key={point.title} className={`${cardClass} px-4 py-3`}>
							<h2 className="text-[14px] font-medium">{point.title}</h2>
							<p className="mt-1 text-[13px] text-muted">{point.body}</p>
						</article>
					))}
				</div>
				<p className="mt-6 text-[13px] text-faint">{texts.landingClose}</p>
			</section>
		</PublicFrame>
	)
}
