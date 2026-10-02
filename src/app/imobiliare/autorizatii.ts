import type { Analysis, Source, Topic } from '@/components/ModelA'
import locData from '@/data/imobiliare/autorizatii_localitati.json'
import { fmt0, fmt1, pct, semn, schimbare } from '../industrii/agricultura/util'

/* Autorizații de construire pentru clădiri — INS TEMPO, matricea LOC108B (anual, pe județe și localități).
   JSON-ul e generat local de scripts/build_autorizatii_localitati.py (INS actualizează o dată pe an, în aprilie).
   Toate textele se calculează din date, ca să rămână corecte la actualizare. */

type Serii = { nr: number[]; mp: number[]; locuinte_nr: number[]; locuinte_mp: number[] }
type Loc = { j: string; s: number; n: string; nr: number[]; mp: number; loc: number }
const D = locData as unknown as {
  meta: { actualizat_ins: string | null; ani: number[]; ani_localitati: number[] }
  national: Serii & { birouri_nr: number[]; birouri_mp: number[]; altele_nr: number[]; altele_mp: number[] }
  judete: Record<string, Serii>
  localitati: Loc[]
}

const C_TOT = '#e0a020', C_LOC = '#3b82f6'
const { ani } = D.meta
const N = ani.length, U = N - 1
const an = ani[U], anPrec = ani[U - 1]
const NAT = D.national

const NOTA = 'O autorizație de construire poate fi pentru o casă sau pentru un bloc întreg, de aceea contează și suprafața. Suprafața utilă = metrii pătrați care se pot folosi efectiv (fără ziduri). Numărul arată ce s-a aprobat, nu ce s-a terminat de construit.'
const NOTA_LOC = 'Numele localităților sunt scrise fără diacritice, ca în baza de date INS. Localitățile fără nicio autorizație nu apar în date.'

/* ── Ajutoare ── */
const sageata = (p: number) => (p > 0 ? '▲' : p < 0 ? '▼' : '=')
const dir = (p: number) => (p > 0 ? 'up' as const : 'down' as const)
const de = (v: number) => { const r = Math.round(v) % 100; return v >= 20 && (r === 0 || r >= 20) ? 'de ' : '' }
/** „1,4 milioane m²” / „850 de mii m²” */
const mpText = (v: number) => (v >= 1e6 ? `${fmt1(v / 1e6)} milioane m²` : `${fmt0(v / 1000)} ${de(v / 1000)}mii m²`)
const iMax = (a: number[]) => a.indexOf(Math.max(...a))

const JUDET: Record<string, string> = {
  'Arges': 'Argeș', 'Bacau': 'Bacău', 'Bistrita-Nasaud': 'Bistrița-Năsăud', 'Botosani': 'Botoșani', 'Braila': 'Brăila',
  'Brasov': 'Brașov', 'Buzau': 'Buzău', 'Calarasi': 'Călărași', 'Caras-Severin': 'Caraș-Severin', 'Constanta': 'Constanța',
  'Dambovita': 'Dâmbovița', 'Galati': 'Galați', 'Ialomita': 'Ialomița', 'Iasi': 'Iași', 'Maramures': 'Maramureș',
  'Mehedinti': 'Mehedinți', 'Municipiul Bucuresti': 'București', 'Mures': 'Mureș', 'Neamt': 'Neamț', 'Salaj': 'Sălaj',
  'Timis': 'Timiș', 'Valcea': 'Vâlcea',
}
const numeJudet = (j: string) => JUDET[j] ?? j

/** „MUNICIPIUL CLUJ-NAPOCA” → „Cluj-Napoca”, tip „municipiu” */
function numeLoc(n: string): { nume: string; tip: string } {
  let tip = 'comună', r = n
  if (r.startsWith('MUNICIPIUL ')) { tip = 'municipiu'; r = r.slice(11) } else if (r.startsWith('ORAS ')) { tip = 'oraș'; r = r.slice(5) }
  if (r === 'BUCURESTI') return { nume: 'București', tip: 'municipiu' }
  const nume = r.toLowerCase().replace(/(^|[\s-])([a-zăâîșț])/g, (_, a: string, b: string) => a + b.toUpperCase())
  return { nume, tip }
}

/* ── Toată țara ── */
function analizaEvolutie(): Analysis {
  const v = NAT.nr[U], vp = NAT.nr[U - 1], p = pct(v, vp)
  const im = iMax(NAT.nr)
  const loc = NAT.locuinte_nr[U]
  return {
    name: 'Evoluție',
    type: 'line',
    unit: 'autorizații pe an',
    plain: `În ${an} s-au eliberat ${fmt0(v)} ${de(v)}autorizații de construire pentru clădiri, dintre care ${fmt0(loc)} pentru locuințe (${fmt0(loc / v * 100)}%). ` +
      `Față de ${anPrec}, numărul ${schimbare(v, vp)}. Recordul a fost în ${ani[im]}, chiar înainte de criză, cu ${fmt0(NAT.nr[im])} — în ${an} s-a autorizat ${fmt0(Math.abs(pct(v, NAT.nr[im])))}% mai puțin.`,
    labels: ani.map(String),
    series: [
      { name: 'Toate clădirile', color: C_TOT, data: NAT.nr },
      { name: 'Locuințe', color: C_LOC, data: NAT.locuinte_nr },
    ],
    labelCol: 'Anul',
    tableNewestFirst: true,
    kpis: [
      { label: `Autorizații în ${an}`, value: fmt0(v), chg: `${sageata(p)} ${semn(p)} față de ${anPrec}`, dir: dir(p),
        hint: 'Câte clădiri noi au primit voie să fie construite.' },
      { label: 'Pentru locuințe', value: fmt0(loc), chg: `${fmt0(loc / v * 100)}% din total`,
        hint: 'Case și blocuri de locuințe.' },
      { label: 'Anul record', value: String(ani[im]), chg: `${fmt0(NAT.nr[im])} autorizații`, dir: 'up',
        hint: 'Boom-ul imobiliar dinainte de criza din 2009.' },
    ],
    footnote: NOTA,
  }
}

function analizaSuprafata(): Analysis {
  const v = NAT.mp[U], vp = NAT.mp[U - 1], p = pct(v, vp)
  const im = iMax(NAT.mp)
  const mpLoc = NAT.locuinte_mp[U]
  return {
    name: 'Suprafață',
    type: 'bar',
    unit: 'mii m² utili autorizați pe an',
    plain: `În ${an} s-au autorizat clădiri cu ${mpText(v)} utili — cam cât ${fmt0(v / 60)} de apartamente de 60 m². ` +
      `Suprafața ${schimbare(v, vp)} față de ${anPrec}. Vârful a fost în ${ani[im]} (${mpText(NAT.mp[im])}).`,
    labels: ani.map(String),
    series: [{ name: 'Suprafață utilă (mii m²)', color: C_TOT, data: NAT.mp.map(x => Math.round(x / 1000)) }],
    labelCol: 'Anul',
    tableNewestFirst: true,
    kpis: [
      { label: `Suprafață ${an}`, value: mpText(v), chg: `${sageata(p)} ${semn(p)} față de ${anPrec}`, dir: dir(p) },
      { label: 'Din care locuințe', value: mpText(mpLoc), chg: `${fmt0(mpLoc / v * 100)}% din suprafață` },
      { label: `Vârf (${ani[im]})`, value: mpText(NAT.mp[im]), hint: `În ${an}: ${fmt0(v / NAT.mp[im] * 100)}% din nivelul de atunci.` },
    ],
    footnote: NOTA,
  }
}

function analizaTipuri(): Analysis {
  const g = [
    { nume: 'Locuințe', explic: 'case și blocuri', nr: NAT.locuinte_nr[U], mp: NAT.locuinte_mp[U] },
    { nume: 'Hoteluri, magazine și altele', explic: 'hoteluri, spații comerciale, hale, clădiri pentru colectivități etc.', nr: NAT.altele_nr[U], mp: NAT.altele_mp[U] },
    { nume: 'Clădiri de birouri', explic: 'clădiri administrative', nr: NAT.birouri_nr[U], mp: NAT.birouri_mp[U] },
  ]
  const tot = g.reduce((s, x) => s + x.nr, 0), totMp = g.reduce((s, x) => s + x.mp, 0)
  const [l, a, b] = g
  return {
    name: 'Ce se construiește',
    type: 'pie',
    unit: `autorizații, ${an}`,
    plain: `Cam ${Math.round(l.nr / tot * 10)} din 10 autorizații sunt pentru locuințe. ` +
      `Hotelurile, magazinele și celelalte clădiri sunt mai puține (${fmt0(a.nr / tot * 100)}%), dar sunt mai mari: au ${fmt0(a.mp / totMp * 100)}% din suprafață.`,
    labels: g.map(x => x.nume),
    labelsLong: g.map(x => `${x.nume} — ${x.explic}`),
    series: [{ name: 'Autorizații', data: g.map(x => x.nr) }],
    labelCol: 'Tip de clădire',
    share: true,
    extraCols: [{ name: 'Suprafață utilă', values: g.map(x => mpText(x.mp)) }],
    kpis: [
      { label: 'Locuințe', value: fmt0(l.nr), chg: `${fmt1(l.nr / tot * 100)}% din autorizații` },
      { label: 'Hoteluri, magazine, altele', value: fmt0(a.nr), chg: `${fmt1(a.mp / totMp * 100)}% din suprafață` },
      { label: 'Clădiri de birouri', value: fmt0(b.nr), chg: mpText(b.mp) },
    ],
    footnote: 'Din 2009, INS împarte „alte clădiri” în hoteluri, comerț și altele; aici le adunăm, ca seria să fie comparabilă cu anii dinainte. ' + NOTA,
  }
}

function analizaMarime(): Analysis {
  const med = NAT.locuinte_nr.map((n, i) => (n ? Math.round(NAT.locuinte_mp[i] / n) : null))
  const v = med[U]!, v0 = med[0]!
  const im = iMax(med.map(x => x ?? 0))
  return {
    name: 'Mărimea medie',
    type: 'line',
    unit: 'm² utili pe autorizație de locuință',
    plain: `În ${an}, o autorizație pentru locuințe a însemnat în medie ${fmt0(v)} m² utili, față de ${fmt0(v0)} m² în ${ani[0]}. ` +
      `Media crește când se autorizează mai multe blocuri (o singură autorizație pentru zeci de apartamente) și scade când domină casele.`,
    labels: ani.map(String),
    series: [{ name: 'm² pe autorizație', color: C_LOC, data: med }],
    labelCol: 'Anul',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Media în ${an}`, value: `${fmt0(v)} m²`, chg: `${sageata(pct(v, med[U - 1]!))} ${semn(pct(v, med[U - 1]!))} față de ${anPrec}`, dir: dir(pct(v, med[U - 1]!)) },
      { label: `Media în ${ani[0]}`, value: `${fmt0(v0)} m²`, hint: 'Atunci se autorizau mai ales case.' },
      { label: 'Cea mai mare medie', value: `${fmt0(med[im]!)} m²`, chg: `în ${ani[im]}`, dir: 'up' },
    ],
    footnote: NOTA,
  }
}

/* ── Pe județe ── */
const judRows = Object.entries(D.judete).map(([j, s]) => ({ j, nume: numeJudet(j), ...s })).sort((a, b) => b.nr[U] - a.nr[U])

function analizaTopJudete(top = 12): Analysis {
  const tot = judRows.reduce((s, r) => s + r.nr[U], 0)
  const sel = judRows.slice(0, top)
  const [a, b, c] = judRows
  const top3 = (a.nr[U] + b.nr[U] + c.nr[U]) / tot * 100
  return {
    name: 'Top județe',
    type: 'bar',
    unit: `autorizații, ${an}`,
    plain: `${a.nume} conduce, cu ${fmt0(a.nr[U])} ${de(a.nr[U])}autorizații în ${an}, urmat de ${b.nume} (${fmt0(b.nr[U])}) și ${c.nume} (${fmt0(c.nr[U])}). ` +
      `Aceste trei județe adună ${fmt0(top3)}% din autorizațiile din țară.`,
    labels: sel.map(r => r.nume),
    series: [{ name: 'Autorizații', data: sel.map(r => r.nr[U]) }],
    labelCol: 'Județ',
    kpis: [
      { label: 'Primul loc', value: a.nume, chg: `${fmt0(a.nr[U])} autorizații`, dir: 'up' },
      { label: 'Primele 3 județe', value: `${fmt0(top3)}%`, hint: 'Din toate autorizațiile din țară.' },
      { label: 'Ultimul loc', value: judRows[judRows.length - 1].nume, chg: `${fmt0(judRows[judRows.length - 1].nr[U])} autorizații` },
    ],
    footnote: `Graficul arată primele ${top} județe; restul sunt în tabul „Toate județele”. ` + NOTA,
  }
}

function analizaTabelJudete(): Analysis {
  const delta = judRows.map(r => (r.nr[U - 1] ? pct(r.nr[U], r.nr[U - 1]) : null))
  const cu = judRows.map((r, i) => ({ n: r.nume, p: delta[i] })).filter((x): x is { n: string; p: number } => x.p != null)
  const crescut = cu.filter(x => x.p > 0).length
  const best = cu.reduce((a, b) => (b.p > a.p ? b : a)), worst = cu.reduce((a, b) => (b.p < a.p ? b : a))
  return {
    name: 'Toate județele',
    type: 'table',
    unit: 'autorizații de construire',
    plain: `Față de ${anPrec}, numărul de autorizații a crescut în ${crescut} din ${cu.length} ${de(cu.length)}județe. ` +
      `Cea mai mare creștere: ${best.n} (${semn(best.p)}); cea mai mare scădere: ${worst.n} (${semn(worst.p)}).`,
    labels: judRows.map(r => r.nume),
    series: [
      { name: String(an), data: judRows.map(r => r.nr[U]) },
      { name: String(anPrec), data: judRows.map(r => r.nr[U - 1]) },
    ],
    extraCols: [
      { name: `Față de ${anPrec}`, values: delta.map(p => (p == null ? '—' : `${sageata(p)} ${semn(p)}`)) },
      { name: `Suprafață ${an}`, values: judRows.map(r => mpText(r.mp[U])) },
      { name: 'Locuințe', values: judRows.map(r => `${fmt0(r.nr[U] ? r.locuinte_nr[U] / r.nr[U] * 100 : 0)}%`) },
    ],
    labelCol: 'Județ',
    kpis: [
      { label: 'Județe în creștere', value: `${crescut} din ${cu.length}`, hint: `Comparat cu ${anPrec}.` },
      { label: 'Cea mai mare creștere', value: best.n, chg: `▲ ${semn(best.p)}`, dir: 'up' },
      { label: 'Cea mai mare scădere', value: worst.n, chg: `▼ ${semn(worst.p)}`, dir: 'down' },
    ],
    footnote: 'Coloana „Locuințe” arată ce parte din autorizații sunt pentru case și blocuri. ' + NOTA,
  }
}

/* ── Pe localități ── */
const L = D.localitati.map(l => ({ ...l, ...numeLoc(l.n), jud: numeJudet(l.j) }))
const UL = D.meta.ani_localitati.length - 1
const locSort = [...L].sort((a, b) => b.nr[UL] - a.nr[UL])

function analizaTopLoc(top = 12): Analysis {
  const sel = locSort.slice(0, top)
  const comune = sel.filter(l => l.tip === 'comună').length
  const [a] = sel
  return {
    name: 'Top localități',
    type: 'bar',
    unit: `autorizații, ${an}`,
    plain: `${a.nume} (${a.jud}) are cele mai multe autorizații în ${an}: ${fmt0(a.nr[UL])}. ` +
      `${comune} din primele ${top} localități sunt comune, de obicei lângă orașe mari — acolo se construiesc cele mai multe case noi.`,
    labels: sel.map(l => l.nume),
    labelsLong: sel.map(l => `${l.nume} (${l.tip}, ${l.jud})`),
    series: [{ name: 'Autorizații', data: sel.map(l => l.nr[UL]) }],
    labelCol: 'Localitate',
    extraCols: [{ name: 'Județ', values: sel.map(l => l.jud) }],
    kpis: [
      { label: 'Primul loc', value: a.nume, chg: `${fmt0(a.nr[UL])} autorizații · ${a.jud}`, dir: 'up' },
      { label: `Comune în top ${top}`, value: `${comune} din ${top}`, hint: 'Oamenii își construiesc case la marginea orașelor.' },
      { label: 'Localități cu autorizații', value: fmt0(L.filter(l => l.nr[UL] > 0).length), hint: `Din ${fmt0(L.length)} localități cu date în ultimii ${UL + 1} ani.` },
    ],
    footnote: NOTA_LOC + ' ' + NOTA,
  }
}

function analizaTabelLoc(top = 100): Analysis {
  const sel = locSort.slice(0, top)
  const ani5 = D.meta.ani_localitati.slice(-5)
  return {
    name: `Top ${top} localități`,
    type: 'table',
    unit: 'autorizații de construire',
    plain: `Cele ${top} de localități cu cele mai multe autorizații în ${an}. Pentru fiecare vezi și anul ${anPrec} și media ultimilor 5 ani (${ani5[0]}–${ani5[4]}), ca să deosebești un an excepțional de o tendință.`,
    labels: sel.map(l => l.nume),
    series: [
      { name: String(an), data: sel.map(l => l.nr[UL]) },
      { name: String(anPrec), data: sel.map(l => l.nr[UL - 1]) },
      { name: `Media ${ani5[0]}–${ani5[4]}`, data: sel.map(l => Math.round(l.nr.slice(-5).reduce((s, x) => s + x, 0) / 5)) },
    ],
    extraCols: [
      { name: 'Județ', values: sel.map(l => l.jud) },
      { name: 'Tip', values: sel.map(l => l.tip) },
      { name: `Suprafață ${an}`, values: sel.map(l => `${fmt0(l.mp)} m²`) },
    ],
    labelCol: 'Localitate',
    kpis: [
      { label: `Total top ${top}`, value: fmt0(sel.reduce((s, l) => s + l.nr[UL], 0)),
        chg: `${fmt0(sel.reduce((s, l) => s + l.nr[UL], 0) / NAT.nr[U] * 100)}% din țară`, hint: `Din ${fmt0(NAT.nr[U])} autorizații în toată țara.` },
      { label: 'Comune în top', value: String(sel.filter(l => l.tip === 'comună').length), hint: `Din ${top} localități.` },
      { label: 'Municipii în top', value: String(sel.filter(l => l.tip === 'municipiu').length) },
    ],
    footnote: NOTA_LOC + ' ' + NOTA,
  }
}

function analizaCrestere(top = 25, minim = 100, minimVechi = 50): Analysis {
  const al = D.meta.ani_localitati
  const r = L.map(l => {
    const vechi = l.nr.slice(0, 5).reduce((s, x) => s + x, 0), nou = l.nr.slice(5).reduce((s, x) => s + x, 0)
    return { ...l, vechi, nou, p: vechi ? pct(nou, vechi) : null }
  }).filter(l => l.nou >= minim && l.vechi >= minimVechi && l.p != null).sort((a, b) => b.p! - a.p!).slice(0, top)
  const p1 = `${al[0]}–${al[4]}`, p2 = `${al[5]}–${al[9]}`
  const [a] = r
  return {
    name: 'Unde se construiește tot mai mult',
    type: 'table',
    unit: `autorizații, ${p2} față de ${p1}`,
    plain: `Localitățile în care s-a autorizat mult mai mult în ultimii 5 ani (${p2}) decât în cei 5 dinainte (${p1}). ` +
      `Pe primul loc, ${a.nume} (${a.jud}): de la ${fmt0(a.vechi)} la ${fmt0(a.nou)} autorizații. Am păstrat doar localitățile cu cel puțin ${minim} de autorizații în ultimii 5 ani și ${minimVechi} în cei dinainte, ca să nu apară creșteri „de la zero”.`,
    labels: r.map(l => l.nume),
    series: [
      { name: p1, data: r.map(l => l.vechi) },
      { name: p2, data: r.map(l => l.nou) },
    ],
    extraCols: [
      { name: 'Creștere', values: r.map(l => (l.nou / l.vechi >= 2 ? `de ${fmt1(l.nou / l.vechi)} ori` : `▲ ${semn(l.p!)}`)) },
      { name: 'Județ', values: r.map(l => l.jud) },
      { name: 'Tip', values: r.map(l => l.tip) },
    ],
    labelCol: 'Localitate',
    kpis: [
      { label: 'Cea mai mare creștere', value: a.nume, chg: `de ${fmt1(a.nou / a.vechi)} ori · ${a.jud}`, dir: 'up' },
      { label: `Autorizații ${p2}`, value: fmt0(a.nou), hint: `Față de ${fmt0(a.vechi)} în ${p1}.` },
      { label: 'Județul cel mai des', value: (() => {
          const f: Record<string, number> = {}
          r.forEach(l => { f[l.jud] = (f[l.jud] ?? 0) + 1 })
          return Object.entries(f).sort((x, y) => y[1] - x[1])[0][0]
        })(), hint: `Apare cel mai des în această listă de ${top}.` },
    ],
    footnote: NOTA_LOC,
  }
}

/* ── Tab ── */
const chips = (extra: string[] = []) => [`● Ultimele date: anul ${an}`, '🔁 anual', `📅 din ${ani[0]}`, ...extra]
const baza = { credit: 'INS (TEMPO-Online, LOC108B)', link: 'statistici.insse.ro', url: 'http://statistici.insse.ro:8077/tempo-online/', freq: 'anual' }

export function autorizatiiTopic(): Topic {
  const sources: Source[] = [
    { key: 'tara', label: '🗺️ Toată țara', ...baza, chips: chips(), analyses: [analizaEvolutie(), analizaSuprafata(), analizaTipuri(), analizaMarime()] },
    { key: 'judete', label: '📍 Pe județe', ...baza, chips: chips(), analyses: [analizaTopJudete(), analizaTabelJudete()] },
    { key: 'localitati', label: '🏘️ Pe localități', ...baza, chips: chips([`🏘️ ${fmt0(L.length)} localități`]), analyses: [analizaTopLoc(), analizaTabelLoc(), analizaCrestere()] },
  ]
  return { key: 'autorizatii', label: 'Autorizații de construire', icon: '📝', sources }
}
