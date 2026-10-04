import type { Analysis, Source } from '@/components/ModelA'
import al from '../../../../public/alegeri_data.json'
import { cap, fmt0, fmt1, fmt2 } from '../../industrii/agricultura/util'

/* Alegeri locale 2024 — rezultatele pentru consiliile județene (procese-verbale centralizate de AEP / BEC).
   Date statice (public/alegeri_data.json). Coduri din procese-verbale: a = înscriși, b = prezenți, c = voturi valabile,
   d = voturi nule, e = buletine primite, f = buletine neîntrebuințate și anulate. */

type Judet = { id: number; name: string; prezenta: number } & Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'a1' | 'a2' | 'a3' | 'a4' | 'b1' | 'b2' | 'b3' | 'b4', number>
const D = al as unknown as { COUNTIES: Judet[]; PARTIES: [string, number][]; PARTY_COLORS: string[]; LEGENDS: { code: string; text: string }[] }

const C = '#e5544b'
const MAJUSCULE = new Set(['PSD', 'PNL', 'USR', 'PMP', 'UDMR', 'S.O.S.', 'FD'])
/** „PARTIDUL NAȚIONAL LIBERAL” → „Partidul Național Liberal” (siglele rămân cu majuscule) */
const frumos = (s: string) => s.split(/(\s+|-)/).map(w => (MAJUSCULE.has(w) || w.length <= 2 ? w : w.charAt(0) + w.slice(1).toLowerCase())).join('')
/** „BISTRIŢA-NĂSĂUD” → „Bistrița-Năsăud” (și ş/ţ cu sedilă → ș/ț cu virgulă) */
const JUDET = (s: string) => s.replace(/Ş/g, 'Ș').replace(/Ţ/g, 'Ț').split(/(\s+|-)/).map(w => cap(w.toLowerCase())).join('')
const mil = (v: number) => `${fmt2(v / 1e6)} mil.`

const t = D.COUNTIES.reduce((s, c) => ({ a: s.a + c.a, b: s.b + c.b, c: s.c + c.c, d: s.d + c.d, e: s.e + c.e, f: s.f + c.f }), { a: 0, b: 0, c: 0, d: 0, e: 0, f: 0 })
const prezenta = t.b / t.a * 100
const totVot = D.PARTIES.reduce((s, p) => s + p[1], 0)
const prz = D.COUNTIES.slice().sort((x, y) => y.prezenta - x.prezenta)

const SURSA = {
  credit: 'Autoritatea Electorală Permanentă', link: 'prezenta.roaep.ro', url: 'https://prezenta.roaep.ro/locale09062024/', freq: 'o singură dată (alegeri 9 iunie 2024)',
  chips: ['🗳️ 9 iunie 2024', '🏛️ Consilii județene', `📍 ${D.COUNTIES.length} de județe, fără București`],
}
const NOTA = 'Rezultate finale pentru consiliile județene din cele 41 de județe, din procesele-verbale centralizate. Municipiul București (Consiliul General) nu e inclus în acest set de date.'

function sumar(): Analysis {
  const top = D.PARTIES.slice(0, 10)
  return {
    name: 'Pe scurt',
    type: 'bar',
    unit: 'voturi pentru consiliile județene',
    plain: `La alegerile pentru consiliile județene din 9 iunie 2024 au votat ${mil(t.b)} de oameni din ${mil(t.a)} înscriși pe liste în cele ${D.COUNTIES.length} de județe (fără București) — o prezență de ${fmt1(prezenta)}%. ` +
      `${frumos(D.PARTIES[0][0])} a luat cele mai multe voturi pentru consiliile județene (${fmt1(D.PARTIES[0][1] / totVot * 100)}%), urmat de ${frumos(D.PARTIES[1][0])} (${fmt1(D.PARTIES[1][1] / totVot * 100)}%).`,
    labels: top.map(p => frumos(p[0])),
    series: [{ name: 'Voturi', data: top.map(p => p[1]), colors: top.map((_, i) => D.PARTY_COLORS[i] ?? '#9aa3b8') }],
    labelCol: 'Partid / alianță',
    share: true,
    kpis: [
      { label: 'Au votat', value: mil(t.b), chg: `${fmt1(prezenta)}% prezență`, hint: `din ${mil(t.a)} de alegători înscriși` },
      { label: 'Voturi valabile', value: mil(t.c), hint: `${fmt1(t.c / t.b * 100)}% din cei care au votat` },
      { label: 'Voturi nule', value: fmt0(t.d), hint: `${fmt1(t.d / t.b * 100)}% din cei care au votat` },
    ],
    footnote: NOTA,
  }
}

function partide(): Analysis {
  return {
    name: 'Toate partidele',
    type: 'bar',
    unit: 'voturi pentru consiliile județene',
    plain: `Primele două partide au strâns împreună ${fmt0((D.PARTIES[0][1] + D.PARTIES[1][1]) / totVot * 100)}% din voturi. ` +
      `Alianțele locale (ex. PSD-PNL în unele județe) apar separat de partidele care le formează.`,
    labels: D.PARTIES.map(p => frumos(p[0])),
    series: [{ name: 'Voturi', data: D.PARTIES.map(p => p[1]), colors: D.PARTIES.map((_, i) => D.PARTY_COLORS[i] ?? '#9aa3b8') }],
    labelCol: 'Partid / alianță',
    share: true,
    kpis: D.PARTIES.slice(0, 3).map(p => ({ label: frumos(p[0]), value: `${fmt1(p[1] / totVot * 100)}%`, hint: `${fmt0(p[1])} voturi` })),
    footnote: `Ponderea e calculată din voturile partidelor din listă (${D.PARTIES.length} partide și alianțe). ${NOTA}`,
  }
}

function prezentaJudete(): Analysis {
  const sus = prz[0], jos = prz[prz.length - 1]
  return {
    name: 'Prezența pe județe',
    type: 'bar',
    unit: '% din alegătorii înscriși care au votat',
    plain: `Cea mai mare prezență a fost în ${JUDET(sus.name)} (${fmt1(sus.prezenta)}%), cea mai mică în ${JUDET(jos.name)} (${fmt1(jos.prezenta)}%). ` +
      `Prezența e mai mică acolo unde mulți oameni sunt înscriși pe liste, dar lucrează în altă parte sau în străinătate.`,
    labels: prz.map(c => JUDET(c.name)),
    series: [{ name: 'Prezență', data: prz.map(c => c.prezenta), colors: prz.map(c => (c.prezenta >= 55 ? '#22b07d' : c.prezenta >= 45 ? '#e0a020' : C)) }],
    labelCol: 'Județ',
    valueSuffix: '%',
    zoomY: false,
    extraCols: [{ name: 'Înscriși', values: prz.map(c => fmt0(c.a)) }, { name: 'Au votat', values: prz.map(c => fmt0(c.b)) }],
    kpis: [
      { label: 'Prezență pe țară', value: `${fmt1(prezenta)}%` },
      { label: `Cea mai mare: ${JUDET(sus.name)}`, value: `${fmt1(sus.prezenta)}%` },
      { label: `Cea mai mică: ${JUDET(jos.name)}`, value: `${fmt1(jos.prezenta)}%` },
    ],
    footnote: `Verde = peste 55%, galben = 45–55%, roșu = sub 45%. ${NOTA}`,
  }
}

function proceseVerbale(): Analysis {
  const r = D.COUNTIES.slice().sort((x, y) => y.a - x.a)
  return {
    name: 'Procesele-verbale pe județe',
    type: 'table',
    unit: 'număr de alegători, voturi și buletine',
    plain: 'Cifrele din procesele-verbale ale fiecărui județ. Literele (a, b, c…) sunt codurile folosite în procesele-verbale; vezi „Ce înseamnă coloanele”.',
    labels: r.map(c => JUDET(c.name)),
    series: [
      { name: 'a — Înscriși', data: r.map(c => c.a) }, { name: 'b — Au votat', data: r.map(c => c.b) },
      { name: 'c — Voturi valabile', data: r.map(c => c.c) }, { name: 'd — Voturi nule', data: r.map(c => c.d) },
      { name: 'e — Buletine primite', data: r.map(c => c.e) }, { name: 'f — Buletine nefolosite și anulate', data: r.map(c => c.f) },
    ],
    labelCol: 'Județ',
    extraCols: [{ name: 'Prezență', values: r.map(c => `${fmt2(c.prezenta)}%`) }],
    kpis: [
      { label: 'Buletine primite', value: mil(t.e) },
      { label: 'Buletine nefolosite și anulate', value: mil(t.f), hint: `${fmt1(t.f / t.e * 100)}% din cele primite` },
      { label: 'Județe', value: String(D.COUNTIES.length), hint: 'Fără Municipiul București' },
    ],
    footnote: NOTA,
  }
}

function legenda(): Analysis {
  return {
    name: 'Ce înseamnă coloanele',
    type: 'table',
    unit: 'codurile din procesele-verbale',
    plain: 'Procesele-verbale ale birourilor electorale folosesc litere pentru fiecare rând. Aici e explicația fiecăreia și totalul pe toată țara.',
    labels: D.LEGENDS.map(l => l.code),
    series: [{ name: 'Total pe țară', data: D.LEGENDS.map(l => D.COUNTIES.reduce((s, c) => s + ((c as unknown as Record<string, number>)[l.code] ?? 0), 0)) }],
    labelCol: 'Cod',
    extraCols: [{ name: 'Ce înseamnă', values: D.LEGENDS.map(l => l.text) }],
    kpis: [],
    footnote: NOTA,
  }
}

export const SURSE_ALEGERI: Source[] = [
  { key: 'rezultate', label: '📊 Rezultate', ...SURSA, analyses: [sumar(), partide()] },
  { key: 'judete', label: '📍 Județe', ...SURSA, analyses: [prezentaJudete(), proceseVerbale(), legenda()] },
]
