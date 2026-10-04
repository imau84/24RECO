import ModelA from '@/components/ModelA'
import { eurostatTopic, infrastructuraTopic } from './topics'

/* Pagina e Server Component (Model A): datele se citesc la build din src/data/it/date.json.
   Nivel 1 = sursa (Eurostat, Infrastructură), nivel 2 = câte o statistică. */

const ACCENT = '#6366f1'  // culoarea plăcii IT&Comunicații de pe homepage

export default function ItComunicatiiPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'IT&Comunicații' }]}
      icon="💻"
      title="IT&Comunicații"
      sub="Cât crește IT-ul românesc și cât de bun e internetul"
      theme={{ accent: ACCENT, accent2: '#12a5b8', tint: '#eef0fe', tintBorder: '#c9cdfb', tintInk: '#3730a3' }}
      topics={[eurostatTopic(ACCENT), infrastructuraTopic(ACCENT)]}
      l1Label=""
      chipsBelow
    />
  )
}
