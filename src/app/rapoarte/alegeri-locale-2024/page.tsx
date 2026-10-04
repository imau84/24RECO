import ModelA from '@/components/ModelA'
import { SURSE_ALEGERI } from './analize'

/* Alegeri locale 2024 — Server Component (Model A), din public/alegeri_data.json (date statice, AEP). */

const ACCENT = '#e5544b'  // culoarea plăcii Alegeri Locale 2024 de pe homepage

export default function AlegeriLocale2024Page() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Rapoarte', href: '/#rapoarte' }, { label: 'Alegeri locale 2024' }]}
      icon="🗳️"
      title="Alegeri locale 2024"
      sub="Cine a câștigat consiliile județene și câți oameni au votat"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#fdeeed', tintBorder: '#f6c4c0', tintInk: '#8a1f18' }}
      sources={SURSE_ALEGERI}
      chipsBelow
    />
  )
}
