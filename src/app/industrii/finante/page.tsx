import ModelA from '@/components/ModelA'
import { finanteTopics } from './topics'

/* Pagina e Server Component (Model A): datele se citesc la build din src/data/finante/date.json.
   Nivel 1 = domeniul (bursă, bănci, asigurări, investiții, pensii private), nivel 2 = câte o statistică. */

const ACCENT = '#b8860b'  // culoarea plăcii Finanțe de pe homepage

export default function FinantePage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Finanțe' }]}
      icon="💰"
      title="Finanțe"
      sub="Bursă, bănci, asigurări, investiții și pensii private"
      theme={{ accent: ACCENT, accent2: '#e0a020', tint: '#fdf6e3', tintBorder: '#f0dca8', tintInk: '#7a5600' }}
      topics={finanteTopics(ACCENT)}
      l1Label=""
      chipsBelow
    />
  )
}
