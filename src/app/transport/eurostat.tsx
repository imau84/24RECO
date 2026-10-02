import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import data from '@/data/transport/eurostat.json'

/* Tab-ul „Eurostat” — 5 statistici de transport pentru România.
   src/data/transport/eurostat.json e actualizat lunar de scripts/fetch_eurostat_transport.py (GitHub Actions). */

const SETURI = (data as unknown as { seturi: EurostatSet[] }).seturi
const ICON: Record<string, string> = { cifra: '💼', pasageri: '✈️', marfa_aer: '📦', preturi: '🏷️', porturi: '⚓' }
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const ultima = (s: EurostatSet) => {
  const p = s.perioade[s.perioade.length - 1]
  return p.includes('Q') ? `trimestrul ${p.slice(-1)} ${p.slice(0, 4)}` : `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`
}

export function eurostatTopic(accent: string): Topic {
  const sources: Source[] = SETURI.map(s => ({
    key: s.key,
    label: `${ICON[s.key] ?? '📊'} ${s.scurt}`,
    credit: 'Eurostat', link: 'ec.europa.eu/eurostat', url: s.url,
    freq: s.freq === 'Q' ? 'trimestrial' : 'lunar',
    chips: [`● Ultimele date: ${ultima(s)}`, `🔁 ${s.freq === 'Q' ? 'trimestrial' : 'lunar'}`, `📅 din ${s.perioade[0].slice(0, 4)}`],
    analyses: [],
    content: <EurostatExplorer set={s} accent={accent} />,
  }))
  return { key: 'eurostat', label: 'Eurostat', icon: '📊', sources }
}
