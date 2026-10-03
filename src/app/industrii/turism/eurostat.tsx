import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import data from '@/data/turism/eurostat.json'

/* Tab-ul „Eurostat” — 4 statistici lunare despre turism (HoReCa, pasageri aerieni, prețuri, grad de ocupare).
   src/data/turism/eurostat.json e actualizat lunar de scripts/fetch_eurostat_turism.py (GitHub Actions). */

const SETURI = (data as unknown as { seturi: EurostatSet[] }).seturi
const ICON: Record<string, string> = { horeca: '🍽️', aerian: '✈️', preturi: '🏷️', ocupare: '🛏️' }
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const ultima = (s: EurostatSet) => {
  const p = s.perioade[s.perioade.length - 1]
  return `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`
}

export function eurostatTopic(accent: string): Topic {
  const sources: Source[] = SETURI.map(s => ({
    key: s.key,
    label: `${ICON[s.key] ?? '📊'} ${s.scurt}`,
    credit: 'Eurostat', link: 'ec.europa.eu/eurostat', url: s.url,
    freq: 'lunar',
    chips: [`● Ultimele date: ${ultima(s)}`, '🔁 lunar', `📅 din ${s.perioade[0].slice(0, 4)}`],
    analyses: [],
    content: <EurostatExplorer set={s} accent={accent} />,
  }))
  return {
    key: 'eurostat', label: 'Eurostat', icon: '📊', sources,
    intro: 'Bani încasați de hoteluri și restaurante, pasageri în aeroporturi, prețurile vacanțelor și cât de pline sunt hotelurile față de alte țări.',
  }
}
