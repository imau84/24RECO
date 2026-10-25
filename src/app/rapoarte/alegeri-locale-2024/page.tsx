import ModelA from '@/components/ModelA'
import { TEME_ALEGERI } from './analize'

/* Alegeri locale 2024 — Server Component (Model A), din public/alegeri_data.json (date statice, AEP). */

const ACCENT = '#e5544b'  // culoarea plăcii Alegeri Locale 2024 de pe homepage

export default function AlegeriLocale2024Page() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Rapoarte', href: '/#rapoarte' }, { label: 'Alegeri locale 2024' }]}
      icon="🗳️"
      title="Alegeri locale 2024"
      sub="9 iunie 2024"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#fdeeed', tintBorder: '#f6c4c0', tintInk: '#8a1f18' }}
      topics={TEME_ALEGERI}
      l1Label=""
      chipsBelow
    />
  )
}
