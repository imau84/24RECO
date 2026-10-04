import type { Analysis, Source, Topic } from '@/components/ModelA'
import dp from '../../../../public/datorie-publica_data.json'
import { LUNI, LUNI_SCURT, fmt0, fmt1, pct, semn } from '../../industrii/agricultura/util'

/* Datoria guvernamentală (metodologia UE) — fișierul Excel lunar al Trezoreriei / Ministerului Finanțelor.
   public/datorie-publica_data.json e actualizat de scripts/fetch_datorie_publica.py (GitHub Actions, săptămânal).
   Perioade: anii 2010–2025 (sold la 31 decembrie), apoi lunile anului curent. Valori în mil. lei; pctPIB e fracție (0,58 = 58%). */

type Detaliu = Record<'total' | 'pctPIB' | 'termenScurt' | 'termenMediuLung' | 'numerarDepozite' | 'titluriStat' | 'imprumuturi' | 'lei' | 'euro' | 'usd' | 'altii', (number | null)[]>
const D = dp as unknown as {
  periods: string[]; pib: number[]; total: number[]; pctPIB: number[]; interna: number[]; externa: number[]
  detailed_from: string; total_detail: Detaliu; lastUpdated: string
}

const C_TOT = '#7c5ce6', C_INT = '#3b82f6', C_EXT = '#e0a020', C_PIB = '#e5544b'
const et = (p: string) => (p.includes('-') ? `${LUNI_SCURT[+p.slice(5) - 1]} ${p.slice(2, 4)}` : p)
const etLung = (p: string) => (p.includes('-') ? `${LUNI[+p.slice(5) - 1]} ${p.slice(0, 4)}` : `31 decembrie ${p}`)
const mld = (v: number) => `${fmt1(v / 1000)} mld. lei`
const r1 = (v: number | null) => (v == null ? null : Math.round(v / 100) / 10) // mil. → mld., o zecimală

const n = D.periods.length - 1
const ultim = D.periods[n]
const anCompar = D.periods.indexOf(String(+ultim.slice(0, 4) - 1)) // sfârșitul anului trecut
const tot = D.total[n], pib = D.pctPIB[n] * 100
const pib10 = D.pctPIB[0] * 100

const SURSA = {
  credit: 'Ministerul Finanțelor', link: 'mfinante.gov.ro',
  url: 'https://mfinante.gov.ro/ro/domenii/datoria-publica/rapoarte-statistici', freq: 'lunar',
  chips: [`● Ultimele date: ${etLung(ultim)}`, '🔁 lunar', `📅 din ${D.periods[0]}`],
}
const NOTA = 'Datoria guvernamentală după metodologia UE (cea folosită pentru criteriul de 60% din PIB). Până în 2025: soldul la 31 decembrie; din 2026: soldul la sfârșitul fiecărei luni.'

function evolutie(): Analysis {
  return {
    name: 'Cât datorează statul',
    type: 'bar',
    unit: 'miliarde lei',
    plain: `La ${etLung(ultim)}, statul român datora ${mld(tot)} — cam ${fmt0(tot * 1e6 / 19e6)} lei pentru fiecare locuitor. ` +
      `În ${D.periods[0]} datoria era de ${mld(D.total[0])}; de atunci ${tot / D.total[0] >= 2 ? `s-a mărit de ${fmt1(tot / D.total[0])} ori` : `a crescut cu ${fmt0(pct(tot, D.total[0]))}%`}.`,
    labels: D.periods.map(et),
    labelsLong: D.periods.map(etLung),
    series: [{ name: 'Datorie totală', color: C_TOT, data: D.total.map(r1) }],
    labelCol: 'Data',
    tableNewestFirst: true,
    kpis: [
      { label: `Datorie totală (${etLung(ultim)})`, value: mld(tot),
        chg: anCompar >= 0 ? `${semn(pct(tot, D.total[anCompar]))} față de 31 dec. ${D.periods[anCompar]}` : undefined, dir: 'down' },
      { label: 'Din PIB', value: `${fmt1(pib)}%`, hint: 'PIB = valoarea a tot ce produce economia într-un an.' },
      { label: 'Pe locuitor', value: `${fmt0(tot * 1e6 / 19e6)} lei`, hint: 'Datoria împărțită la ~19 milioane de locuitori.' },
    ],
    footnote: NOTA,
  }
}

function procentPib(): Analysis {
  return {
    name: 'Datoria ca procent din PIB',
    type: 'line',
    unit: '% din PIB',
    plain: `Datoria a urcat de la ${fmt1(pib10)}% din PIB în ${D.periods[0]} la ${fmt1(pib)}% acum. ` +
      `Regula UE spune că datoria ar trebui să rămână sub 60% din PIB${pib >= 60 ? ' — România a ajuns la acest prag' : ''}.`,
    labels: D.periods.map(et),
    labelsLong: D.periods.map(etLung),
    series: [{ name: 'Datorie / PIB', color: C_PIB, data: D.pctPIB.map(v => (v == null ? null : Math.round(v * 1000) / 10)) }],
    labelCol: 'Data',
    valueSuffix: '%',
    tableNewestFirst: true,
    kpis: [
      { label: 'Acum', value: `${fmt1(pib)}%`, chg: `${pib - pib10 >= 0 ? '+' : '−'}${fmt1(Math.abs(pib - pib10))} puncte față de ${D.periods[0]}`, dir: 'down' },
      { label: 'Pragul UE', value: '60%', hint: 'Criteriul din Tratatul de la Maastricht.' },
      { label: 'Cel mai mic nivel', value: `${fmt1(Math.min(...D.pctPIB) * 100)}%`, hint: D.periods[D.pctPIB.indexOf(Math.min(...D.pctPIB))] },
    ],
    footnote: NOTA,
  }
}

function internaExterna(): Analysis {
  const pInt = D.interna[n] / tot * 100
  return {
    name: 'Internă și externă',
    type: 'bar',
    unit: 'miliarde lei',
    plain: `${fmt0(pInt)}% din datorie e internă (împrumutată de la bănci și investitori din România, mai ales prin titluri de stat), ` +
      `iar ${fmt0(100 - pInt)}% e externă (de la investitori străini, Comisia Europeană, FMI, Banca Mondială).`,
    labels: D.periods.map(et),
    labelsLong: D.periods.map(etLung),
    series: [
      { name: 'Internă', color: C_INT, data: D.interna.map(r1) },
      { name: 'Externă', color: C_EXT, data: D.externa.map(r1) },
    ],
    labelCol: 'Data',
    tableNewestFirst: true,
    kpis: [
      { label: 'Datorie internă', value: mld(D.interna[n]), hint: `${fmt0(pInt)}% din total` },
      { label: 'Datorie externă', value: mld(D.externa[n]), hint: `${fmt0(100 - pInt)}% din total` },
      { label: `Externă în ${D.periods[0]}`, value: `${fmt0(D.externa[0] / D.total[0] * 100)}% din total` },
    ],
    footnote: NOTA,
  }
}

/* ── Structura (detaliată din 2020) ── */
const iDet = D.periods.indexOf(D.detailed_from)
const perDet = D.periods.slice(iDet)
const T = D.total_detail
const u = T.total.length - 1

function structura(tip: 'instrument' | 'valuta'): Analysis {
  const serii = tip === 'instrument'
    ? [{ name: 'Titluri de stat (obligațiuni)', color: C_TOT, k: 'titluriStat' as const },
       { name: 'Împrumuturi', color: C_EXT, k: 'imprumuturi' as const },
       { name: 'Numerar și depozite', color: '#22b07d', k: 'numerarDepozite' as const }]
    : [{ name: 'Lei', color: '#22b07d', k: 'lei' as const }, { name: 'Euro', color: C_INT, k: 'euro' as const },
       { name: 'Dolari americani', color: C_EXT, k: 'usd' as const }, { name: 'Alte valute', color: '#9aa3b8', k: 'altii' as const }]
  const totU = T.total[u] ?? tot
  const p = (k: keyof Detaliu) => ((T[k][u] ?? 0) / totU * 100)
  return {
    name: tip === 'instrument' ? 'Cum se împrumută statul' : 'În ce monedă',
    type: 'bar',
    unit: 'miliarde lei',
    plain: tip === 'instrument'
      ? `Statul se împrumută mai ales vânzând titluri de stat (obligațiuni) — ${fmt0(p('titluriStat'))}% din datorie, inclusiv cele cumpărate de populație (Tezaur, Fidelis). Restul sunt împrumuturi de la instituții (${fmt0(p('imprumuturi'))}%).`
      : `${fmt0(p('lei'))}% din datorie e în lei și ${fmt0(p('euro'))}% în euro. Partea în valută se scumpește când leul se depreciază.`,
    labels: perDet.map(et),
    labelsLong: perDet.map(etLung),
    series: serii.map(s => ({ name: s.name, color: s.color, data: T[s.k].map(r1) })),
    labelCol: 'Data',
    tableNewestFirst: true,
    kpis: serii.slice(0, 3).map(s => ({ label: s.name, value: mld(T[s.k][u] ?? 0), hint: `${fmt0(p(s.k))}% din total` })),
    footnote: `Defalcarea detaliată e disponibilă din ${D.detailed_from}. ${NOTA}`,
  }
}

function termen(): Analysis {
  const s = T.termenScurt[u] ?? 0, l = T.termenMediuLung[u] ?? 0
  return {
    name: 'Pe termen scurt și lung',
    type: 'bar',
    unit: 'miliarde lei',
    plain: `${fmt0(l / (s + l) * 100)}% din datorie trebuie dată înapoi în mai mult de un an. ` +
      `Datoria pe termen scurt (sub un an) trebuie refinanțată des, deci e mai sensibilă la creșterea dobânzilor.`,
    labels: perDet.map(et),
    labelsLong: perDet.map(etLung),
    series: [
      { name: 'Termen mediu și lung (peste 1 an)', color: C_TOT, data: T.termenMediuLung.map(r1) },
      { name: 'Termen scurt (sub 1 an)', color: C_PIB, data: T.termenScurt.map(r1) },
    ],
    labelCol: 'Data',
    tableNewestFirst: true,
    kpis: [
      { label: 'Termen mediu și lung', value: mld(l) },
      { label: 'Termen scurt', value: mld(s) },
      { label: 'Ponderea termenului scurt', value: `${fmt1(s / (s + l) * 100)}%` },
    ],
    footnote: `Defalcarea detaliată e disponibilă din ${D.detailed_from}. ${NOTA}`,
  }
}

export function datorieTopic(): Topic {
  const sources: Source[] = [
    { key: 'evolutie', label: '📈 Evoluție', ...SURSA, analyses: [evolutie(), procentPib(), internaExterna()] },
    { key: 'structura', label: '🧩 Structură', ...SURSA, analyses: [structura('instrument'), structura('valuta'), termen()] },
  ]
  return {
    key: 'datorie', label: 'Datorie Publică', icon: '📈', sources,
    intro: `Câți bani datorează statul român, cât înseamnă din economie și de la cine s-a împrumutat. Date actualizate ${D.lastUpdated.split('-').reverse().join('.')}.`,
  }
}
