import ModelA, { type Source, type Topic } from '@/components/ModelA'
import { EduBac, EduElevi, EduEvaluare } from './EduApp'

/* Ministerul Educației — Model A. Tab-urile: Elevi, Evaluarea Națională 2025, Bacalaureat 2025;
   fiecare subtab e o componentă interactivă din EduApp.tsx (datele mari se încarcă din browser, la cerere). */

const ACCENT = '#63a615'  // culoarea plăcii Min. Educației de pe homepage

const sursa = (key: string, label: string, content: JSX.Element, chips: string[], link: string, url: string): Source =>
  ({ key, label, credit: 'Ministerul Educației', link, url, freq: 'anual', chips, analyses: [], content })

const SIIIR = ['● An școlar 2025–2026', '🔁 anual', '🏫 toate unitățile de învățământ']
const EN = ['● Iunie 2025', '🔁 anual', '🎓 clasa a VIII-a']
const BAC = ['● Sesiunea iunie–iulie 2025', '🔁 anual', '🎓 clasa a XII-a']
const GOV = 'https://data.gov.ro/organization/ministerul-educatiei'

const topics: Topic[] = [
  {
    key: 'elevi', label: 'Elevi', icon: '👧',
    intro: 'Câți copii sunt înscriși la grădiniță, școală și liceu, în fiecare județ și localitate, în anul școlar 2025–2026.',
    sources: [
      sursa('national', '🇷🇴 Toată țara', <EduElevi vedere="national" />, SIIIR, 'data.gov.ro', GOV),
      sursa('filtru', '🔍 Pe localități și unități', <EduElevi vedere="filtru" />, SIIIR, 'data.gov.ro', GOV),
      sursa('unitate', '🏫 Caută o școală', <EduElevi vedere="unitate" />, SIIIR, 'data.gov.ro', GOV),
    ],
  },
  {
    key: 'evaluare', label: 'Evaluarea Națională 2025', icon: '📝',
    intro: 'Notele de la examenul de la sfârșitul clasei a VIII-a (română și matematică), pe țară, pe județe și pe școli.',
    sources: [
      sursa('national', '🇷🇴 Toată țara', <EduEvaluare vedere="national" />, EN, 'evaluare.edu.ro', 'https://evaluare.edu.ro'),
      sursa('judete', '🏆 Clasamentul județelor', <EduEvaluare vedere="judete" />, EN, 'evaluare.edu.ro', 'https://evaluare.edu.ro'),
      sursa('scoli', '🔍 Caută o școală', <EduEvaluare vedere="scoli" />, EN, 'evaluare.edu.ro', 'https://evaluare.edu.ro'),
    ],
  },
  {
    key: 'bac', label: 'Bacalaureat 2025', icon: '🎓',
    intro: 'Câți elevi au luat bacalaureatul în 2025 și cu ce medii, pe țară, pe județe și pe licee.',
    sources: [
      sursa('national', '🇷🇴 Toată țara', <EduBac vedere="national" />, BAC, 'bacalaureat.edu.ro', 'https://bacalaureat.edu.ro'),
      sursa('judete', '🏆 Clasamentul județelor', <EduBac vedere="judete" />, BAC, 'bacalaureat.edu.ro', 'https://bacalaureat.edu.ro'),
      sursa('licee', '🔍 Caută un liceu', <EduBac vedere="licee" />, BAC, 'bacalaureat.edu.ro', 'https://bacalaureat.edu.ro'),
    ],
  },
]

export default function EducatiePage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Instituții publice', href: '/#institutii' }, { label: 'Ministerul Educației' }]}
      icon="📚"
      title="Ministerul Educației"
      sub="Câți elevi sunt în fiecare școală și cum au ieșit la examene"
      theme={{ accent: ACCENT, accent2: '#22b07d', tint: '#f0f8e8', tintBorder: '#cfe8b5', tintInk: '#3b6b0c' }}
      topics={topics}
      l1Label=""
      chipsBelow
    />
  )
}
