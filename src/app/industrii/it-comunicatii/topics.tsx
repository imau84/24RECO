import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import data from '@/data/it/date.json'

/* Tab-urile „Eurostat” (4 statistici) și „Infrastructură” (RIPE NCC, APNIC Labs).
   src/data/it/date.json e actualizat lunar de scripts/fetch_it.py (GitHub Actions). */

const DATE = data as unknown as { eurostat: EurostatSet[]; infrastructura: EurostatSet[] }
const ICON: Record<string, string> = { cifra: '💻', munca: '👩‍💻', export: '🌍', preturi: '📱', ripe: '🛰️', ipv6: '🔢' }
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const ultima = (s: EurostatSet) => {
  const p = s.perioade[s.perioade.length - 1]
  return p.includes('Q') ? `trimestrul ${p.slice(-1)} ${p.slice(0, 4)}` : `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`
}

const surse = (seturi: EurostatSet[], accent: string): Source[] => seturi.map(s => {
  const credit = s.sursa ? s.sursa.split(' — ')[0] : 'Eurostat'
  const freq = s.freq === 'Q' ? 'trimestrial' : 'lunar'
  return {
    key: s.key,
    label: `${ICON[s.key] ?? '📊'} ${s.scurt}`,
    credit, link: new URL(s.url).hostname.replace(/^www\./, ''), url: s.url,
    freq,
    chips: [`● Ultimele date: ${ultima(s)}`, `🔁 ${freq}`, `📅 din ${s.perioade[0].slice(0, 4)}`],
    analyses: [],
    content: <EurostatExplorer set={s} accent={accent} />,
  }
})

export const eurostatTopic = (accent: string): Topic => ({
  key: 'eurostat', label: 'Eurostat', icon: '📊', sources: surse(DATE.eurostat, accent),
  intro: 'Cât încasează firmele de IT și telecom, câți oameni lucrează în domeniu și cât câștigă, cât exportăm și cât plătim pentru telefon și internet.',
})

export const infrastructuraTopic = (accent: string): Topic => ({
  key: 'infrastructura', label: 'Infrastructură', icon: '🛰️', sources: surse(DATE.infrastructura, accent),
  intro: 'Câte rețele și adrese de internet are România și cât de repede trece la IPv6, noua generație de adrese.',
})
