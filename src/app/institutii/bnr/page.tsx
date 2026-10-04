import ModelA, { type Source } from '@/components/ModelA'
import EurostatExplorer from '@/components/EurostatExplorer'
import { SETURI_BNR } from './serii'

/* BNR — Server Component (Model A): seriile lunare se citesc la build din public/bnr_data.json.
   Un sub-tab pentru fiecare grup de serii, fiecare cu explorator (indicator, ani, grafic, tabel). */

const ACCENT = '#334670'  // culoarea plăcii BNR de pe homepage
const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']

const sources: Source[] = SETURI_BNR.map(s => {
  const p = s.perioade[s.perioade.length - 1]
  return {
    key: s.key, label: `${s.icon} ${s.scurt}`, credit: 'Banca Națională a României', link: 'bnr.ro', url: s.url, freq: 'lunar',
    chips: [`● Ultimele date: ${LUNI[+p.slice(5, 7) - 1]} ${p.slice(0, 4)}`, '🔁 lunar', `📅 din ${s.perioade[0].slice(0, 4)}`],
    analyses: [],
    content: <EurostatExplorer set={s} accent={ACCENT} locale="ro-RO" />,
  }
})

export default function BnrPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Instituții publice', href: '/#institutii' }, { label: 'BNR' }]}
      icon="🏦"
      title="Banca Națională a României"
      sub="Bani care intră și ies din țară, investiții străine, depozite și credite"
      theme={{ accent: ACCENT, accent2: '#3b82f6', tint: '#eef1f8', tintBorder: '#c9d2e6', tintInk: '#1f2b4d' }}
      sources={sources}
      chipsBelow
    />
  )
}
