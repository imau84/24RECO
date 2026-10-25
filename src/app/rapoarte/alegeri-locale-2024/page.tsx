import ModelA, { type Source, type Topic } from '@/components/ModelA'
import { TEMA_CONSILIU } from './analize'
import { PrimariJudete, PrimariLocalitati, PrimariPartide, PrimariPeScurt } from './primari'
import { ConsiliuJudete, ConsiliuLocalitati, ConsiliuPartide, ConsiliuPeScurt, ConsiliuPrimar } from './consiliu-local'

/* Alegeri locale 2024 — Server Component (Model A). Tab-uri de nivel 1 = tipul de alegere:
   Consiliu județean (public/alegeri_data.json, analize statice), Primar (primari.tsx, încarcă
   public/data/alegeri-locale-2024/primari.json în browser) și Consiliu local (consiliu-local.tsx,
   consiliu-local.json). Un tip nou de alegere = o temă nouă în TEME. */

const ACCENT = '#e5544b'  // culoarea plăcii Alegeri Locale 2024 de pe homepage

const SURSA_PRIMARI = {
  credit: 'Autoritatea Electorală Permanentă', link: 'prezenta.roaep.ro', url: 'https://prezenta.roaep.ro/locale09062024v2/romania/pv-final',
  freq: 'o singură dată (alegeri 9 iunie 2024)', analyses: [],
  chips: ['🗳️ 9 iunie 2024', '👤 Primari', '📍 3.186 de primării (inclusiv sectoarele), fără Primarul General'],
}
const PRIMARI: Source[] = [
  { key: 'primari-pe-scurt', label: '📊 Pe scurt', ...SURSA_PRIMARI, content: <PrimariPeScurt /> },
  { key: 'primari-partide', label: '🏛️ Partide', ...SURSA_PRIMARI, content: <PrimariPartide /> },
  { key: 'primari-judete', label: '📍 Județe', ...SURSA_PRIMARI, content: <PrimariJudete /> },
  { key: 'primari-localitati', label: '🔎 Localități', ...SURSA_PRIMARI, content: <PrimariLocalitati /> },
]

const SURSA_CL = {
  ...SURSA_PRIMARI,
  chips: ['🗳️ 9 iunie 2024', '🪑 39.858 de consilieri locali', '📍 3.186 de consilii (inclusiv sectoarele), fără Consiliul General'],
}
const CONSILIU_LOCAL: Source[] = [
  { key: 'cl-pe-scurt', label: '📊 Pe scurt', ...SURSA_CL, content: <ConsiliuPeScurt /> },
  { key: 'cl-partide', label: '🏛️ Partide', ...SURSA_CL, content: <ConsiliuPartide /> },
  { key: 'cl-judete', label: '📍 Județe', ...SURSA_CL, content: <ConsiliuJudete /> },
  { key: 'cl-localitati', label: '🔎 Localități', ...SURSA_CL, content: <ConsiliuLocalitati /> },
  { key: 'cl-primar', label: '🤝 Primar vs consiliu', ...SURSA_CL, content: <ConsiliuPrimar /> },
]

const TEME: Topic[] = [
  TEMA_CONSILIU,
  { key: 'primar', label: 'Primar', icon: '👤', sources: PRIMARI },
  { key: 'consiliu-local', label: 'Consiliu local', icon: '🪑', sources: CONSILIU_LOCAL },
]

export default function AlegeriLocale2024Page() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Rapoarte', href: '/#rapoarte' }, { label: 'Alegeri locale 2024' }]}
      icon="🗳️"
      title="Alegeri locale 2024"
      sub="9 iunie 2024"
      theme={{ accent: ACCENT, accent2: '#7c5ce6', tint: '#fdeeed', tintBorder: '#f6c4c0', tintInk: '#8a1f18' }}
      topics={TEME}
      l1Label=""
      chipsBelow
    />
  )
}
