import ModelA from '@/components/ModelA'
import { exporturiTopic } from './exporturi'
import { salariatiTopic } from './salariati'
import { eurostatTopic } from './eurostat'

/* Pagina e Server Component: calculele rulează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google.
   Nivel 1 = tema (Exporturi, Salariați, Eurostat), nivel 2 = secțiunea, nivel 3 = analize. */

const ACCENT = '#3b82f6'

export default function IndustriePage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Industrie' }]}
      icon="🏭"
      title="Industrie"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#eef2fe', tintBorder: '#cfdaf9', tintInk: '#1e3a8a' }}
      topics={[exporturiTopic(ACCENT), salariatiTopic(ACCENT), eurostatTopic(ACCENT)]}  /* aici se adaugă alte teme */
      l1Label=""
      chipsBelow
    />
  )
}
