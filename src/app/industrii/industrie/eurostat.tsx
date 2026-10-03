import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import data from '@/data/industrie/eurostat.json'

/* Tab-ul „Eurostat” — 6 statistici lunare despre industrie (4 Eurostat + 2 despre electricitate: Ember și energy-charts.info).
   src/data/industrie/eurostat.json e actualizat lunar de scripts/fetch_eurostat_industrie.py (GitHub Actions). */

const SETURI = (data as unknown as { seturi: EurostatSet[] }).seturi
const ICON: Record<string, string> = { productie: '🏭', ramuri: '🚗', preturi: '🏷️', munca: '👷', electricitate: '⚡', consum: '🔌' }
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const ultima = (s: EurostatSet) => {
  const p = s.perioade[s.perioade.length - 1]
  return `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`
}

export function eurostatTopic(accent: string): Topic {
  const sources: Source[] = SETURI.map(s => {
    const credit = s.sursa ? s.sursa.split(' — ')[0].split(' (')[0] : 'Eurostat'
    return {
      key: s.key,
      label: `${ICON[s.key] ?? '📊'} ${s.scurt}`,
      credit, link: new URL(s.url).hostname.replace(/^www\./, ''), url: s.url,
      freq: 'lunar',
      chips: [`● Ultimele date: ${ultima(s)}`, '🔁 lunar', `📅 din ${s.perioade[0].slice(0, 4)}`],
      analyses: [],
      content: <EurostatExplorer set={s} accent={accent} />,
    }
  })
  return { key: 'eurostat', label: 'Eurostat', icon: '📊', sources }
}
