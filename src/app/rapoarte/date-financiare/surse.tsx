import type { ModelAProps, Source } from '@/components/ModelA'
import FinanciareExplorer from './FinanciareExplorer'
import IdentificareExplorer from './IdentificareExplorer'

/* Pagina „Situații financiare” (Model A) cu două căutări peste baza ANAF din Neon (/api/firme):
   bilanțul unei firme și registrul de identificare. Aceeași pagină e servită la două adrese,
   fiecare deschisă pe subtab-ul ei (/rapoarte/date-financiare și /rapoarte/date-identificare). */

const ACCENT = '#5a6178'  // culoarea plăcii Situații Financiare de pe homepage
const comun = { credit: 'ANAF / data.gov.ro', link: 'data.gov.ro', url: 'https://data.gov.ro/organization/anaf', freq: 'anual', analyses: [] }

const FINANCIARE: Source = {
  key: 'financiare', label: '📊 Bilanțul unei firme', ...comun,
  chips: ['● Situații financiare 2025', '🔁 anual', '🏢 toate firmele care au depus bilanț'],
  content: <FinanciareExplorer />,
}
const IDENTIFICARE: Source = {
  key: 'identificare', label: '🪪 Date de identificare', ...comun,
  chips: ['● Registrul plătitorilor, iunie 2026', '🔁 anual', '📍 pe județ, localitate, stradă'],
  content: <IdentificareExplorer />,
}

export function propsSituatii(prima: 'financiare' | 'identificare'): ModelAProps {
  return {
    crumbs: [{ label: 'Acasă', href: '/' }, { label: 'Rapoarte', href: '/#rapoarte' }, { label: 'Situații financiare' }],
    icon: '📊',
    title: 'Situații financiare',
    sub: 'Cât vinde, cât câștigă și câți angajați are orice firmă din România',
    theme: { accent: ACCENT, accent2: '#1D9E75', tint: '#eef0f4', tintBorder: '#d3d7e0', tintInk: '#2f3447' },
    sources: prima === 'financiare' ? [FINANCIARE, IDENTIFICARE] : [IDENTIFICARE, FINANCIARE],
    chipsBelow: true,
  }
}
