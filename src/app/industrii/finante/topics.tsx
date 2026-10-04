import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import data from '@/data/finante/date.json'

/* 5 teme (Piața de capital, Bănci, Asigurări, Investiții financiare, Pensii private), 20 de statistici.
   src/data/finante/date.json e actualizat lunar de scripts/fetch_finante.py (GitHub Actions),
   care rulează pachetul scripts/financiara/ (Eurostat, BCE, BIS, BVB, ASF, EIOPA). */

type Set = EurostatSet & { icon: string }
type Tema = { label: string; icon: string; intro: string; seturi: Set[] }

const TEME = data as unknown as Record<string, Tema>
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const ultima = (s: EurostatSet) => {
  const p = s.perioade[s.perioade.length - 1]
  return p.includes('Q') ? `trimestrul ${p.slice(-1)} ${p.slice(0, 4)}` : `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`
}

export function finanteTopics(accent: string): Topic[] {
  return Object.entries(TEME).map(([key, t]) => ({
    key, label: t.label, icon: t.icon, intro: t.intro,
    sources: t.seturi.map((s): Source => {
      const freq = s.freq === 'Q' ? 'trimestrial' : 'lunar'
      return {
        key: s.key,
        label: `${s.icon} ${s.scurt}`,
        credit: s.sursa, link: new URL(s.url).hostname.replace(/^www\./, ''), url: s.url,
        freq,
        chips: [`● Ultimele date: ${ultima(s)}`, `🔁 ${freq}`, `📅 din ${s.perioade[0].slice(0, 4)}`],
        analyses: [],
        content: <EurostatExplorer set={s} accent={accent} />,
      }
    }),
  }))
}
