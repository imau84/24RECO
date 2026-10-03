import type { Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import InmatriculariExplorer, { type ComertData } from './InmatriculariExplorer'
import comertData from '../../../public/comert_data.json'
import eurostat from '@/data/comert/eurostat.json'

/* Temele paginii Comerț:
   - Înmatriculări autoturisme: public/comert_data.json (DRPCIV, scripts/fetch_comert.py, lunar pe 10)
   - restul: src/data/comert/eurostat.json (Eurostat + BCE, scripts/fetch_eurostat_comert.py, lunar) */

const SETURI = (eurostat as unknown as { seturi: EurostatSet[] }).seturi
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const ultima = (p: string) => `${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`

export function inmatriculariTopic(accent: string): Topic {
  const d = comertData as unknown as ComertData
  const ultimaK = Object.keys(d.months).sort().pop()!
  return {
    key: 'inmatriculari', label: 'Înmatriculări autoturisme', icon: '🚗',
    intro: 'Câte mașini se înmatriculează în fiecare lună: ce mărci, în ce județe, pe ce combustibil și cine le cumpără.',
    sources: [{
      key: 'drpciv', label: '🚗 DRPCIV', credit: 'DGPCI / DRPCIV', link: 'dgpci.mai.gov.ro', url: 'https://dgpci.mai.gov.ro/news-and-media/statistica',
      freq: 'lunar',
      chips: [`● Ultimele date: ${ultima(ultimaK.replace('_', '-'))}`, '🔁 lunar', `📅 din ${ultima(Object.keys(d.months).sort()[0].replace('_', '-'))}`],
      analyses: [],
      content: <InmatriculariExplorer data={d} accent={accent} />,
    }],
  }
}

const ICON: Record<string, string> = { vanzari: '🛒', online: '📦', inflatie: '🏷️', credite: '💳', dobanzi: '📈' }

/** o temă din câteva seturi Eurostat/BCE, fiecare cu exploratorul lui */
function setTopic(key: string, label: string, icon: string, chei: string[], accent: string, intro: string): Topic {
  const sources: Source[] = chei.map(k => SETURI.find(s => s.key === k)).filter((s): s is EurostatSet => !!s).map(s => ({
    key: s.key,
    label: `${ICON[s.key] ?? '📊'} ${s.scurt}`,
    credit: s.sursa ? 'BCE (date BNR)' : 'Eurostat', link: new URL(s.url).hostname, url: s.url,
    freq: 'lunar',
    chips: [`● Ultimele date: ${ultima(s.perioade[s.perioade.length - 1])}`, '🔁 lunar', `📅 din ${s.perioade[0].slice(0, 4)}`],
    analyses: [],
    content: <EurostatExplorer set={s} accent={accent} />,
  }))
  return { key, label, icon, sources, intro }
}

export const vanzariTopic = (accent: string) => setTopic('vanzari', 'Vânzări în magazine', '🛒', ['vanzari', 'online'], accent,
  'Cât cumpără românii din magazine, benzinării și online — în cantitate, fără efectul scumpirilor.')
export const inflatieTopic = (accent: string) => setTopic('inflatie', 'Prețuri și inflație', '🏷️', ['inflatie'], accent,
  'Cât de repede se scumpesc alimentele, energia, bunurile și serviciile în România, comparat cu media Uniunii Europene.')
export const crediteTopic = (accent: string) => setTopic('credite', 'Credite și dobânzi', '💳', ['credite', 'dobanzi'], accent,
  'Cât au de dat românii băncilor și ce dobândă plătesc la un credit nou.')
