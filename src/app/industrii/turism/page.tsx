import ModelA from '@/components/ModelA'
import { sosiriTopic } from './sosiri'
import { eurostatTopic } from './eurostat'

/* Pagina e Server Component (Model A): datele INS se citesc și se compactează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google.
   Nivel 1 = tema (Sosiri, Eurostat; aici se adaugă alte teme, ex. înnoptări), nivel 2 = subtab-urile de pe vechea pagină. */

const ACCENT = '#e0559c'  // culoarea plăcii Turism de pe homepage

export default function TurismPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Turism' }]}
      icon="✈️"
      title="Turism"
      sub="Câți turiști vin și unde se cazează"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#fdf0f6', tintBorder: '#f6cde1', tintInk: '#8a1d52' }}
      topics={[sosiriTopic(ACCENT), eurostatTopic(ACCENT)]}
      l1Label=""
      chipsBelow
    />
  )
}
