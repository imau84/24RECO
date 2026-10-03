import ModelA from '@/components/ModelA'
import { inmatriculariTopic, vanzariTopic, inflatieTopic, crediteTopic } from './topics'

/* Pagina e Server Component (Model A): datele se citesc la build din JSON-urile actualizate lunar,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google.
   Nivel 1 = tema, nivel 2 = setul de date, apoi exploratorul (indicator, ani/perioadă, grafic + tabel). */

const ACCENT = '#e5544b'  // culoarea plăcii Comerț de pe homepage

export default function ComertPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Comerț' }]}
      icon="🛍️"
      title="Comerț"
      sub="Mașini înmatriculate, vânzări în magazine, prețuri și credite"
      theme={{ accent: ACCENT, accent2: '#e0a020', tint: '#fdf1f0', tintBorder: '#f6d0cc', tintInk: '#8a2a22' }}
      topics={[inmatriculariTopic(ACCENT), vanzariTopic(ACCENT), inflatieTopic(ACCENT), crediteTopic(ACCENT)]}
      l1Label=""
      chipsBelow
    />
  )
}
