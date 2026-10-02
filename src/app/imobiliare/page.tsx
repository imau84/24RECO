import ModelA from '@/components/ModelA'
import { autorizatiiTopic } from './autorizatii'
import { ancpiTopic } from './ancpi'

/* Pagina e Server Component: calculele rulează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google.
   Nivel 1 = sursa (Autorizații INS / ANCPI), nivel 2 = zona (țară, județe, orașe…), nivel 3 = analize. */

export default function ImobiliarePage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Imobiliare' }]}
      icon="🏠"
      title="Imobiliare"
      sub="Ce se construiește și ce se vinde în România — case, apartamente, terenuri"
      theme={{ accent: '#3b82f6', accent2: '#60a5fa', tint: '#eaf2fe', tintBorder: '#c9ddfb', tintInk: '#1e4a8a' }}
      topics={[autorizatiiTopic(), ancpiTopic()]}
      l1Label=""
      chipsBelow
    />
  )
}
