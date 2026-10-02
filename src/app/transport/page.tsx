import ModelA from '@/components/ModelA'
import { firmeTopic } from './firme'
import { motorinaTopic } from './motorina'
import { eurostatTopic } from './eurostat'

/* Pagina e Server Component: calculele rulează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google.
   Nivel 1 = tema (firme / motorină / Eurostat), nivel 2 = secțiunea, nivel 3 = analize. */

const ACCENT = '#12a5b8'

export default function TransportPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Transport' }]}
      icon="🚛"
      title="Transport de marfă"
      sub="Câte firme de transport are România, cât de mari sunt și cât costă motorina"
      theme={{ accent: ACCENT, accent2: '#3cc4d4', tint: '#e6f6f8', tintBorder: '#bfe6ec', tintInk: '#0b5f6a' }}
      topics={[firmeTopic(), motorinaTopic(), eurostatTopic(ACCENT)]}
      l1Label=""
      chipsBelow
    />
  )
}
