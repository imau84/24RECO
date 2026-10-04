import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'

/* Tab-uri Model A generate dintr-un JSON de forma { cheie_temă: { label, icon, intro, seturi: [EurostatSet + icon] } }
   (scris de scripturile fetch_finante.py, fetch_energie.py). Fiecare set devine un subtab cu EurostatExplorer. */

export type SetCuIcon = EurostatSet & { icon: string }
export type Tema = { label: string; icon: string; intro: string; seturi: SetCuIcon[] }

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const FREQ = { M: 'lunar', Q: 'trimestrial', S: 'semestrial' } as const

const ultima = (s: EurostatSet) => {
  const p = s.perioade[s.perioade.length - 1]
  if (p.includes('Q')) return `trimestrul ${p.slice(-1)} ${p.slice(0, 4)}`
  if (p.includes('S')) return `semestrul ${p.slice(-1)} ${p.slice(0, 4)}`
  return `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`
}

export function temeDinJson(teme: Record<string, Tema>, accent: string): Topic[] {
  return Object.entries(teme).map(([key, t]) => ({
    key, label: t.label, icon: t.icon, intro: t.intro,
    sources: t.seturi.map((s): Source => ({
      key: s.key,
      label: `${s.icon} ${s.scurt}`,
      credit: s.sursa ?? 'Eurostat', link: new URL(s.url).hostname.replace(/^www\./, ''), url: s.url,
      freq: FREQ[s.freq],
      chips: [`● Ultimele date: ${ultima(s)}`, `🔁 ${FREQ[s.freq]}`, `📅 din ${s.perioade[0].slice(0, 4)}`],
      analyses: [],
      content: <EurostatExplorer set={s} accent={accent} />,
    })),
  }))
}
