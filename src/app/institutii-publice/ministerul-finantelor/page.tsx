import ModelA from '@/components/ModelA'
import { executieTopic } from './executie'
import { datorieTopic } from './datorie'

/* Ministerul Finanțelor — Server Component (Model A): calculele rulează la build din JSON-urile din public/.
   Nivel 1 = Execuție Bugetară / Datorie Publică, nivel 2 = secțiunea, nivel 3 = analize. */

const ACCENT = '#f0883e'  // culoarea plăcii Min. Finanțe de pe homepage

export default function MinisterulFinantelorPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Instituții publice', href: '/#institutii' }, { label: 'Ministerul Finanțelor' }]}
      icon="🏛️"
      title="Ministerul Finanțelor"
      sub="Câți bani încasează și cheltuie statul și cât datorează"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#fff4ec', tintBorder: '#fbd5b8', tintInk: '#8a3c0b' }}
      topics={[executieTopic(), datorieTopic()]}
      l1Label=""
      chipsBelow
    />
  )
}
