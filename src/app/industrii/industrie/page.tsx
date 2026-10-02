import ModelA from '@/components/ModelA'
import { exporturiTopic } from './exporturi'

/* Pagina e Server Component: calculele rulează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google.
   Nivel 1 = tema (deocamdată doar Exporturi), nivel 2 = secțiunea, nivel 3 = analize. */

const ACCENT = '#3b82f6'

export default function IndustriePage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Industrie' }]}
      icon="🏭"
      title="Industrie"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#eef2fe', tintBorder: '#cfdaf9', tintInk: '#1e3a8a' }}
      topics={[exporturiTopic(ACCENT)]}  /* aici se adaugă alte teme (producție industrială etc.) */
      l1Label=""
      chipsBelow
    />
  )
}
