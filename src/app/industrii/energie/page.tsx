import ModelA from '@/components/ModelA'
import { energieTopics } from './topics'

/* Pagina e Server Component (Model A): datele se citesc la build din src/data/energie/date.json.
   Nivel 1 = sursa datelor (Eurostat, Ember, Comisia Europeană, OPCOM), nivel 2 = câte o statistică. */

const ACCENT = '#16a34a'  // culoarea plăcii Energie de pe homepage

export default function EnergiePage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Energie' }]}
      icon="⚡"
      title="Energie"
      sub="Electricitate, gaze, petrol, cărbune și prețurile lor"
      theme={{ accent: ACCENT, accent2: '#e0a020', tint: '#ecfdf3', tintBorder: '#bbe8cb', tintInk: '#14532d' }}
      topics={energieTopics(ACCENT)}
      l1Label=""
      chipsBelow
    />
  )
}
