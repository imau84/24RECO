import type { Analysis, Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import salariatiData from '@/data/industrie/salariati_data.json'
import { LUNI, LUNI_SCURT, fmt0, fmt1, pct, semn, cap } from '../agricultura/util'

/* Salariații din industrie — INS TEMPO, FOM105I (efectivul salariaților la sfârșitul lunii, CAEN Rev.3), lunar din ianuarie 2025.
   src/data/industrie/salariati_data.json e actualizat de scripts/fetch_salariati_industrie.py (GitHub Actions, pe 5 și 20 ale lunii).
   Valorile din sursă sunt în mii persoane. Textele se calculează din date. */

type Luni = Record<string, Record<string, number | null>>  // an → lună → mii persoane
const D = salariatiData as unknown as {
  ordine: string[]
  serii: Record<string, { nume: string; luni: Luni }>
  ultima_actualizare: string
}

const C_MAIN = '#3b82f6', C_PREV = '#9aa3b8', C_UP = '#1a9d6e', C_DOWN = '#e5544b'

/* ── Nume pe înțeles ── */
const NUME: Record<string, string> = {
  '05-39': 'Toată industria',
  B: 'Mine și cariere', C: 'Fabrici (industria prelucrătoare)', D: 'Energie și gaze', E: 'Apă, canalizare și deșeuri',
  '05': 'Mine de cărbune', '06': 'Petrol și gaze (extracție)', '07': 'Minereuri metalice', '08': 'Cariere (piatră, nisip, sare)', '09': 'Servicii pentru extracție',
  '10': 'Alimente', '11': 'Băuturi', '12': 'Tutun', '13': 'Textile', '14': 'Haine', '15': 'Încălțăminte și pielărie',
  '16': 'Lemn (fără mobilă)', '17': 'Hârtie', '18': 'Tipografii', '19': 'Rafinării', '20': 'Chimicale', '21': 'Medicamente',
  '22': 'Cauciuc și mase plastice', '23': 'Sticlă, ciment, ceramică', '24': 'Metalurgie', '25': 'Construcții metalice și piese din metal',
  '26': 'Electronice și calculatoare', '27': 'Echipamente electrice', '28': 'Mașini și utilaje', '29': 'Mașini și piese auto',
  '30': 'Avioane, nave, trenuri', '31': 'Mobilă', '32': 'Alte produse (bijuterii, jucării…)', '33': 'Reparații și montaj de utilaje',
  '36': 'Apă potabilă', '37': 'Canalizare', '38': 'Deșeuri și reciclare', '39': 'Decontaminare',
}
const nume = (c: string) => NUME[c] ?? cap(D.serii[c].nume.toLowerCase())

/* ── Ajutoare ── */
type K = { an: number; luna: number } // luna: 1..12
const cheie = (k: K) => `${k.an}-${String(k.luna).padStart(2, '0')}`
const numeL = (k: K) => `${LUNI[k.luna - 1]} ${k.an}`
const etL = (k: K) => `${LUNI_SCURT[k.luna - 1]} ${String(k.an).slice(2)}`
const v = (c: string, k: K) => D.serii[c]?.luni[String(k.an)]?.[String(k.luna)] ?? null
const inapoi = (k: K, n: number): K => { const t = k.an * 12 + k.luna - 1 - n; return { an: Math.floor(t / 12), luna: (t % 12) + 1 } }
const ultimaLuna = (l: Luni): K => {
  let b: K = { an: 0, luna: 0 }
  for (const [a, m] of Object.entries(l)) for (const [x, y] of Object.entries(m)) if (y != null && (+a > b.an || (+a === b.an && +x > b.luna))) b = { an: +a, luna: +x }
  return b
}
/** 1.212,4 mii → „1.212.400 de oameni” (valorile sunt rotunjite la sute, deci mereu „de”) */
const oameni = (x: number) => `${fmt0(Math.round(x * 1000))} de oameni`
const dif = (x: number) => `${x > 0 ? '+' : x < 0 ? '−' : ''}${fmt0(Math.round(Math.abs(x) * 1000))}`
const sageata = (p: number) => (p > 0 ? '▲' : p < 0 ? '▼' : '=')
const dir = (p: number) => (p > 0 ? 'up' as const : 'down' as const)

const NOTA = 'Salariați cu contract de muncă, la sfârșitul lunii (fără patroni, PFA-uri sau zilieri). Datele sunt pe noua clasificare CAEN Rev.3, publicate de INS începând cu ianuarie 2025; ultimele luni sunt provizorii.'

/* ═══════════ Toată industria ═══════════ */
const IND = '05-39'
const U = ultimaLuna(D.serii[IND].luni)
const P = inapoi(U, 12)                                    // aceeași lună, anul trecut
const an0 = Object.keys(D.serii[IND].luni).sort()[0]
const START: K = { an: +an0, luna: Math.min(...Object.keys(D.serii[IND].luni[an0]).map(Number)) }  // prima lună cu date
const REF = v(IND, P) != null ? P : START                  // reperul de comparație
const refTxt = REF === P ? `față de ${numeL(P)}` : `față de ${numeL(START)}`
const ramuri = ['B', 'C', 'D', 'E'].filter(c => D.serii[c])
const diviziuni = D.ordine.filter(c => /^\d{2}$/.test(c) && v(c, U) != null)

function analizaEvolutie(): Analysis {
  const ks: K[] = []
  for (let k = START; cheie(k) <= cheie(U); k = inapoi(k, -1)) ks.push(k)
  const vU = v(IND, U)!, vR = v(IND, REF)!, v0 = v(IND, START)!
  const p = pct(vU, vR)
  return {
    name: 'Evoluție lunară',
    type: 'line',
    unit: 'mii salariați, la sfârșitul lunii',
    plain: `La sfârșitul lui ${numeL(U)}, în industrie lucrau ${oameni(vU)} cu contract de muncă — ` +
      `cu ${fmt0(Math.abs(vU - vR) * 1000)} ${vU >= vR ? 'mai mulți' : 'mai puțini'} decât în ${numeL(REF)} (${semn(p)}). ` +
      (vU < v0 ? `Numărul lor scade aproape lună de lună din ${numeL(START)}: ${fmt0((v0 - vU) * 1000)} de locuri de muncă mai puțin.` : `Față de ${numeL(START)}, sunt ${fmt0((vU - v0) * 1000)} de salariați în plus.`),
    labels: ks.map(etL), labelsLong: ks.map(k => cap(numeL(k))),
    series: [{ name: 'Salariați în industrie (mii)', color: C_MAIN, data: ks.map(k => v(IND, k)) }],
    labelCol: 'Luna', tableNewestFirst: true, zoomY: true,
    kpis: [
      { label: `Salariați (${numeL(U)})`, value: `${fmt1(vU)} mii`, chg: `${sageata(p)} ${semn(p)} ${refTxt}`, dir: dir(p) },
      { label: 'Diferența într-un an', value: dif(vU - vR), chg: 'de locuri de muncă', dir: dir(vU - vR), hint: `Comparat cu ${numeL(REF)}.` },
      { label: `Din ${numeL(START)}`, value: dif(vU - v0), chg: `${sageata(pct(vU, v0))} ${semn(pct(vU, v0))}`, dir: dir(vU - v0) },
    ],
    footnote: NOTA,
  }
}

function analizaRamuri(): Analysis {
  const a = ramuri.map(c => v(c, U) ?? 0), b = ramuri.map(c => v(c, REF) ?? 0)
  const pC = (v('C', U) ?? 0) / v(IND, U)! * 100
  const d = ramuri.map((_, i) => pct(a[i], b[i]))
  const r = (c: string) => ramuri.indexOf(c)
  const scad = d.filter(p => p < 0).length
  return {
    name: 'Pe ramuri',
    type: 'bar',
    unit: `mii salariați, ${numeL(U)}`,
    plain: `Cam ${Math.round(pC / 10)} din 10 salariați din industrie lucrează în fabrici (${fmt0(pC)}%). ` +
      `Restul sunt în energie, apă și deșeuri și în mine și cariere. ` +
      (scad === ramuri.length ? `Toate cele ${scad} ramuri au` : `${scad} din ${ramuri.length} ramuri au`) + ` mai puțini oameni decât în ${numeL(REF)}.`,
    labels: ramuri.map(nume), labelsLong: ramuri.map(c => `${nume(c)} (secțiunea ${c})`),
    series: [{ name: `Salariați ${numeL(U)} (mii)`, data: a }],
    labelCol: 'Ramura', share: true,
    extraCols: [{ name: `Schimbare ${refTxt}`, values: d.map((p, i) => `${sageata(p)} ${semn(p)} (${dif(a[i] - b[i])})`) }],
    kpis: [
      { label: nume('C'), value: `${fmt1(a[r('C')])} mii`, chg: `${sageata(d[r('C')])} ${semn(d[r('C')])} ${refTxt}`, dir: dir(d[r('C')]) },
      { label: nume('E'), value: `${fmt1(a[r('E')])} mii`, chg: `${sageata(d[r('E')])} ${semn(d[r('E')])}`, dir: dir(d[r('E')]) },
      { label: `${nume('D')} + ${nume('B').toLowerCase()}`, value: `${fmt1(a[r('D')] + a[r('B')])} mii`, hint: 'Ramuri mici ca număr de oameni, dar esențiale.' },
    ],
    footnote: `Secțiunile CAEN: B = industria extractivă, C = industria prelucrătoare, D = energie, E = apă și deșeuri. ${NOTA}`,
  }
}

function analizaEconomie(): Analysis {
  const tot = v('TOTAL', U)!, ind = v(IND, U)!, totR = v('TOTAL', REF)!
  const rest = tot - ind, p = ind / tot * 100
  const pR = v(IND, REF)! / totR * 100
  const pT = pct(tot, totR)
  return {
    name: 'Locul în economie',
    type: 'pie',
    unit: numeL(U),
    plain: `Cam 1 din ${Math.round(100 / p)} salariați din România lucrează în industrie (${fmt1(p)}% din ${fmt0(tot)} de mii). ` +
      `Ponderea ${p < pR - 0.05 ? 'a scăzut' : p > pR + 0.05 ? 'a crescut' : 'a rămas cam la fel'} față de ${numeL(REF)} (${fmt1(pR)}%).`,
    labels: ['Industrie', 'Restul economiei'],
    series: [{ name: 'Salariați (mii)', data: [ind, Math.round(rest * 10) / 10] }],
    labelCol: 'Unde lucrează', share: true,
    kpis: [
      { label: 'Toți salariații din țară', value: `${fmt1(tot)} mii`, chg: `${sageata(pT)} ${semn(pT)} ${refTxt}`, dir: dir(pT) },
      { label: 'În industrie', value: `${fmt1(ind)} mii` },
      { label: 'Ponderea industriei', value: `${fmt1(p)}%`, hint: `În ${numeL(REF)}: ${fmt1(pR)}%.` },
    ],
    footnote: NOTA,
  }
}

/* ═══════════ Pe domenii (diviziuni CAEN 05–39) ═══════════ */
const dom = diviziuni.map(c => {
  const a = v(c, U)!, b = v(c, REF)
  return { c, nume: nume(c), a, b, d: b == null ? null : a - b, p: b ? pct(a, b) : null }
}).sort((x, y) => y.a - x.a)
const TOT = v(IND, U)!

function analizaTopDomenii(top = 12): Analysis {
  const sel = dom.slice(0, top)
  const [a, b, c] = dom
  const top3 = (a.a + b.a + c.a) / TOT * 100
  return {
    name: 'Unde lucrează cei mai mulți',
    type: 'bar',
    unit: `mii salariați, ${numeL(U)}`,
    plain: `Cei mai mulți salariați din industrie lucrează în ${a.nume.toLowerCase()} (${oameni(a.a)}), urmați de ${b.nume.toLowerCase()} (${fmt0(b.a)} de mii) ` +
      `și ${c.nume.toLowerCase()} (${fmt0(c.a)} de mii). Împreună, primele trei domenii au ${fmt0(top3)}% din salariații industriei.`,
    labels: sel.map(x => x.nume), labelsLong: sel.map(x => `${x.nume} (CAEN ${x.c})`),
    series: [{ name: 'Salariați (mii)', data: sel.map(x => x.a) }],
    labelCol: 'Domeniul',
    extraCols: [{ name: 'Pondere în industrie', values: sel.map(x => `${fmt1(x.a / TOT * 100)}%`) }],
    kpis: [
      { label: 'Locul 1', value: a.nume, chg: `${fmt1(a.a)} mii · ${fmt0(a.a / TOT * 100)}%` },
      { label: 'Locul 2', value: b.nume, chg: `${fmt1(b.a)} mii · ${fmt0(b.a / TOT * 100)}%` },
      { label: 'Locul 3', value: c.nume, chg: `${fmt1(c.a)} mii · ${fmt0(c.a / TOT * 100)}%` },
    ],
    footnote: `Primele ${top} din ${dom.length} domenii (diviziuni CAEN 05–39). ${NOTA}`,
  }
}

function analizaCastiguri(n = 6): Analysis {
  const cu = dom.filter((x): x is typeof x & { d: number; p: number } => x.d != null && x.p != null)
  const ord = [...cu].sort((x, y) => x.d - y.d)
  const jos = ord.slice(0, n), sus = ord.slice(-n).reverse().filter(x => x.d > 0)
  const sel = [...sus, ...jos.reverse()]
  const cresc = cu.filter(x => x.d > 0).length
  const w = ord[0], b = ord[ord.length - 1]
  return {
    name: 'Cine angajează, cine pierde',
    type: 'bar',
    unit: `diferența de salariați, ${numeL(U)} ${refTxt}`,
    plain: `Doar ${cresc} din ${cu.length} domenii au mai mulți salariați decât în ${numeL(REF)}. ` +
      `Cea mai mare scădere: ${w.nume.toLowerCase()} (${dif(w.d)} oameni, ${semn(w.p)}). ` +
      (b.d > 0 ? `Cea mai mare creștere: ${b.nume.toLowerCase()} (${dif(b.d)}, ${semn(b.p)}).` : ''),
    labels: sel.map(x => x.nume), labelsLong: sel.map(x => `${x.nume} (CAEN ${x.c})`),
    series: [{ name: 'Diferența (salariați)', data: sel.map(x => Math.round(x.d * 1000)), colors: sel.map(x => (x.d >= 0 ? C_UP : C_DOWN)) }],
    labelCol: 'Domeniul',
    extraCols: [{ name: 'Schimbare', values: sel.map(x => `${sageata(x.p)} ${semn(x.p)}`) }],
    kpis: [
      { label: 'Domenii în creștere', value: `${cresc} din ${cu.length}` },
      { label: 'Cea mai mare creștere', value: b.d > 0 ? b.nume : '—', chg: b.d > 0 ? `${dif(b.d)} oameni` : undefined, dir: 'up' },
      { label: 'Cea mai mare scădere', value: w.nume, chg: `${dif(w.d)} oameni`, dir: 'down' },
    ],
    footnote: `Verde = mai mulți salariați, roșu = mai puțini. ${NOTA}`,
  }
}

function analizaTabel(): Analysis {
  return {
    name: 'Toate domeniile',
    type: 'table',
    unit: `salariați, ${numeL(U)} vs. ${numeL(REF)}`,
    plain: `Tabelul arată toate cele ${dom.length} de domenii industriale, de la cel mai mare la cel mai mic. ` +
      `Coloana „Diferența” spune câți oameni au fost angajați (+) sau au plecat (−) într-un an.`,
    labels: dom.map(x => x.nume), labelsLong: dom.map(x => `${x.nume} (CAEN ${x.c})`),
    series: [
      { name: `${cap(numeL(U))} (mii)`, data: dom.map(x => x.a) },
      { name: `${cap(numeL(REF))} (mii)`, data: dom.map(x => x.b) },
    ],
    extraCols: [
      { name: 'Diferența', values: dom.map(x => (x.d == null ? '—' : dif(x.d))) },
      { name: 'Schimbare', values: dom.map(x => (x.p == null ? '—' : `${sageata(x.p)} ${semn(x.p)}`)) },
      { name: 'Pondere', values: dom.map(x => `${fmt1(x.a / TOT * 100)}%`) },
    ],
    labelCol: 'Domeniul',
    kpis: [
      { label: 'Domenii', value: String(dom.length), hint: 'Diviziunile CAEN 05–39.' },
      { label: 'Cel mai mare', value: dom[0].nume, chg: `${fmt1(dom[0].a)} mii` },
      { label: 'Toată industria', value: `${fmt1(TOT)} mii`, chg: `${sageata(pct(TOT, v(IND, REF)!))} ${semn(pct(TOT, v(IND, REF)!))} ${refTxt}`, dir: dir(pct(TOT, v(IND, REF)!)) },
    ],
    footnote: NOTA,
  }
}

/* ═══════════ Explorator ═══════════ */
function setExplorator(): EurostatSet {
  const coduri = [IND, ...ramuri, ...[...diviziuni].sort((a, b) => nume(a).localeCompare(nume(b), 'ro'))]
  const perioade = Array.from(new Set(coduri.flatMap(c => Object.entries(D.serii[c].luni).flatMap(([a, m]) => Object.keys(m).map(l => cheie({ an: +a, luna: +l })))))).sort()
  return {
    key: 'salariati', scurt: 'Salariați în industrie', titlu: 'Salariați în industrie, pe domenii',
    descriere: 'Alege industria totală, o ramură sau un domeniu și anii pe care vrei să-i compari.',
    cod: 'FOM105I', freq: 'M', unitate: 'mii salariați', zecimale: 1, agregare: 'medie',
    note: [NOTA], url: 'http://statistici.insse.ro:8077/tempo-online/', sursa: 'INS (TEMPO-Online)', actualizat: D.ultima_actualizare,
    perioade,
    serii: coduri.map(c => ({
      nume: c === IND ? 'Toată industria' : ramuri.includes(c) ? `Ramura: ${nume(c)}` : nume(c),
      valori: perioade.map(p => D.serii[c].luni[String(+p.slice(0, 4))]?.[String(+p.slice(5))] ?? null),
      provizorii: [],
    })),
  }
}

/* ═══════════ Tab ═══════════ */
const baza = { credit: 'INS (TEMPO-Online), FOM105I', link: 'statistici.insse.ro', url: 'http://statistici.insse.ro:8077/tempo-online/', freq: 'lunar' }

export function salariatiTopic(accent: string): Topic {
  const chips = [`● Ultimele date: ${numeL(U)}`, '🔁 lunar', `📅 din ${numeL(START)}`]
  const sources: Source[] = [
    { key: 'sal-total', label: '🏭 Toată industria', ...baza, chips, analyses: [analizaEvolutie(), analizaRamuri(), analizaEconomie()] },
    {
      key: 'sal-domenii', label: '🔧 Pe domenii', ...baza, chips: [...chips.slice(0, 2), `🧩 ${dom.length} de domenii`],
      analyses: [analizaTopDomenii(), analizaCastiguri(), analizaTabel(), {
        name: '🔎 Explorează', type: 'table', unit: '', plain: '', labels: [], series: [{ name: '', data: [] }], labelCol: '', kpis: [],
        content: <EurostatExplorer set={setExplorator()} accent={accent} locale="ro-RO" />,
      }],
    },
  ]
  return {
    key: 'salariati', label: 'Salariați', icon: '👷', sources,
    intro: 'Câți oameni lucrează cu contract în industria României — lună de lună, pe ramuri și domenii.',
  }
}
