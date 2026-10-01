import ModelA from '@/components/ModelA'
import { autorizatiiTopic } from './autorizatii'
import { cosMaterialeTopic } from './cos-materiale'

/* Pagina e Server Component: calculele rulează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google. */

export default function ConstructiiPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Construcții' }]}
      icon="🏗️"
      title="Construcții"
      sub="Cât se construiește în România, pe înțelesul tuturor"
      theme={{ accent: '#e0a020', accent2: '#f0c050', tint: '#fdf5e3', tintBorder: '#f5e1b0', tintInk: '#7a5410' }}
      topics={[autorizatiiTopic(), cosMaterialeTopic()]}
    />
  )
}
