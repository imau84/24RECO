import ModelA from '@/components/ModelA'
import { SURSE_CNPP } from './analize'

/* Casa Națională de Pensii Publice — Server Component (Model A): calculele rulează la build din public/cnpp_asigurati.json,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google. */

const ACCENT = '#0ea5b7'  // culoarea plăcii Casa de Pensii de pe homepage

export default function CasaPensiiPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Instituții publice', href: '/#institutii' }, { label: 'Casa de Pensii' }]}
      icon="👴"
      title="Casa Națională de Pensii Publice"
      sub="Câți salariați plătesc contribuții la pensie și cât câștigă"
      theme={{ accent: ACCENT, accent2: '#3b82f6', tint: '#e6f7f9', tintBorder: '#b7e6ec', tintInk: '#0b5f6a' }}
      sources={SURSE_CNPP}
      chipsBelow
    />
  )
}
