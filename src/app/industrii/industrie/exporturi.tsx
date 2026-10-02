import type { Analysis, Source, Topic } from '@/components/ModelA'
import EurostatExplorer, { type EurostatSet } from '@/components/EurostatExplorer'
import industrieData from '@/data/industrie/industrie_data.json'
import { LUNI, LUNI_SCURT, fmt0, fmt1, pct, semn, cap } from '../agricultura/util'

/* Exporturile României — INS TEMPO, lunar:
   EXP101I (pe grupe de produse CSCI, total / UE / non-UE) și EXP101J (pe județe și secțiuni NC).
   src/data/industrie/industrie_data.json e actualizat de scripts/fetch_industrie.py (GitHub Actions, pe 1 ale lunii).
   Valorile din sursă sunt în mii EUR; aici le afișăm în milioane / miliarde EUR. Textele se calculează din date. */

type Luni = Record<string, Record<string, number | null>>  // an → lună → valoare (mii EUR)
const D = industrieData as unknown as {
  RAW: Record<string, Record<'Total' | 'Intra-UE' | 'Extra-UE', Luni>>
  JD: Record<string, Record<string, Luni>>
  ultima_actualizare: string
}

const C_MAIN = '#3b82f6', C_PREV = '#9aa3b8', C_UE = '#5b4be0', C_NONUE = '#e0a020'

/* ── Nume pe înțeles ── */
const GRUPA: Record<string, string> = {
  'Produse alimentare si animale vii': 'Alimente și animale vii',
  'Bauturi si tutun': 'Băuturi și tutun',
  'Materiale crude  necomestibile  exclusiv combustibili': 'Materii prime (lemn, minereu, semințe…)',
  'Combustibili minerali  lubrifianti si materiale conexe': 'Combustibili și energie',
  'Uleiuri  grasimi si ceruri de origine vegetala si animala': 'Uleiuri și grăsimi',
  'Produse chimice si produse conexe  nespecificate in alta parte': 'Chimicale și medicamente',
  'Produse prelucrate clasificate in principal dupa materia prima': 'Metale, cauciuc, lemn, textile prelucrate',
  'Masini si echipamente de transport': 'Mașini, piese auto și echipamente',
  'Articole manufacturate diverse': 'Mobilă, haine, încălțăminte și altele',
  'Bunuri necuprinse in alta sectiune': 'Alte bunuri',
}
const SECTIUNE_NC: Record<string, string> = {
  I: 'Animale și produse animale', II: 'Produse vegetale (cereale…)', III: 'Uleiuri și grăsimi', IV: 'Alimente, băuturi, tutun',
  V: 'Produse minerale și combustibili', VI: 'Chimicale și medicamente', VII: 'Mase plastice și cauciuc', VIII: 'Piei și blănuri',
  IX: 'Lemn', X: 'Hârtie', XI: 'Textile și haine', XII: 'Încălțăminte', XIII: 'Piatră, ceramică, sticlă', XIV: 'Metale prețioase, bijuterii',
  XV: 'Metale și produse din metal', XVI: 'Mașini și echipamente electrice', XVII: 'Mașini și piese auto, vehicule', XVIII: 'Aparate optice și medicale',
  XIX: 'Arme și muniție', XX: 'Mobilă și alte produse', XXI: 'Obiecte de artă', XXII: 'Alte bunuri',
}
const numeNC = (s: string) => SECTIUNE_NC[s.split('.')[0]] ?? s
const JUDET: Record<string, string> = {
  Arges: 'Argeș', Bacau: 'Bacău', 'Bistrita-Nasaud': 'Bistrița-Năsăud', Botosani: 'Botoșani', Brasov: 'Brașov', Braila: 'Brăila',
  Buzau: 'Buzău', 'Caras-Severin': 'Caraș-Severin', Calarasi: 'Călărași', Constanta: 'Constanța', Dambovita: 'Dâmbovița',
  Galati: 'Galați', Ialomita: 'Ialomița', Iasi: 'Iași', Maramures: 'Maramureș', Mehedinti: 'Mehedinți', Mures: 'Mureș',
  Neamt: 'Neamț', Salaj: 'Sălaj', Timis: 'Timiș', Valcea: 'Vâlcea', 'Municipiul Bucuresti': 'București',
}
const numeJudet = (j: string) => JUDET[j] ?? j

/* ── Ajutoare ── */
type K = { an: number; luna: number } // luna: 1..12
const cheie = (k: K) => `${k.an}-${String(k.luna).padStart(2, '0')}`
const numeL = (k: K) => `${LUNI[k.luna - 1]} ${k.an}`
const etL = (k: K) => `${LUNI_SCURT[k.luna - 1]} ${String(k.an).slice(2)}`
const v = (l: Luni | undefined, k: K) => l?.[String(k.an)]?.[String(k.luna)] ?? null
const ultimaLuna = (l: Luni): K => {
  let b: K = { an: 0, luna: 0 }
  for (const [a, m] of Object.entries(l)) for (const [x, y] of Object.entries(m)) if (y != null && (+a > b.an || (+a === b.an && +x > b.luna))) b = { an: +a, luna: +x }
  return b
}
const inapoi = (k: K, n: number): K => { const t = k.an * 12 + k.luna - 1 - n; return { an: Math.floor(t / 12), luna: (t % 12) + 1 } }
/** suma pe ultimele n luni care se termină cu k (null dacă lipsește vreo lună) */
const suma = (l: Luni | undefined, k: K, n = 12) => {
  let s = 0
  for (let i = 0; i < n; i++) { const x = v(l, inapoi(k, i)); if (x == null) return null; s += x }
  return s
}
const mld = (x: number) => `${fmt1(x / 1e6)} mld €`   // din mii EUR
const mil = (x: number) => `${fmt0(x / 1e3)} mil. €`
const bani = (x: number) => (x >= 1e6 ? mld(x) : mil(x))
const sageata = (p: number) => (p > 0 ? '▲' : p < 0 ? '▼' : '=')
const dir = (p: number) => (p > 0 ? 'up' as const : 'down' as const)

const NOTA = 'Exporturi de bunuri (FOB), în euro. Nu includ serviciile (IT, transport, turism). Ultimele luni sunt provizorii și INS le poate revizui.'

/* ═══════════ Toate exporturile ═══════════ */
const T = D.RAW['Total']
const U = ultimaLuna(T.Total)
const U12 = suma(T.Total, U)!, P12 = suma(T.Total, inapoi(U, 12))!

function analizaEvolutie(): Analysis {
  const n = 36
  const ks = Array.from({ length: n }, (_, i) => inapoi(U, n - 1 - i))
  const vU = v(T.Total, U)!, vT = v(T.Total, inapoi(U, 12))!
  const p = pct(vU, vT), p12 = pct(U12, P12)
  const vals = ks.map(k => v(T.Total, k))
  const iMax = vals.indexOf(Math.max(...vals.map(x => x ?? 0)))
  return {
    name: 'Evoluție lunară',
    type: 'line',
    unit: 'milioane EUR pe lună',
    plain: `În ${numeL(U)}, România a exportat bunuri de ${bani(vU)}, cu ${fmt1(Math.abs(p))}% ${p >= 0 ? 'mai mult' : 'mai puțin'} decât în ${numeL(inapoi(U, 12))}. ` +
      `În ultimele 12 luni exporturile au însumat ${mld(U12)} (${semn(p12)} față de cele 12 luni dinainte). August și decembrie sunt mereu mai slabe — fabricile au concediu.`,
    labels: ks.map(etL), labelsLong: ks.map(k => cap(numeL(k))),
    series: [{ name: 'Exporturi', color: C_MAIN, data: vals.map(x => (x == null ? null : Math.round(x / 1000))) }],
    labelCol: 'Luna', tableNewestFirst: true,
    kpis: [
      { label: `Ultima lună (${numeL(U)})`, value: bani(vU), chg: `${sageata(p)} ${semn(p)} față de ${numeL(inapoi(U, 12))}`, dir: dir(p) },
      { label: 'Ultimele 12 luni', value: mld(U12), chg: `${sageata(p12)} ${semn(p12)} față de anul dinainte`, dir: dir(p12), hint: 'Suma pe un an întreg — fără efectul sezonului.' },
      { label: `Luna record (din ${ks[0].an})`, value: cap(numeL(ks[iMax])), chg: bani(vals[iMax]!), dir: 'up' },
    ],
    footnote: NOTA,
  }
}

function analizaAni(): Analysis {
  const ani = Object.keys(T.Total).map(Number).sort((a, b) => a - b)
  const tot = ani.map(a => Object.values(T.Total[String(a)]).reduce<number>((s, x) => s + (x ?? 0), 0))
  const complet = ani.filter(a => Object.values(T.Total[String(a)]).filter(x => x != null).length === 12)
  const aU = complet[complet.length - 1], aP = aU - 1
  const vU = tot[ani.indexOf(aU)], vP = tot[ani.indexOf(aP)], v0 = tot[0]
  const p = pct(vU, vP)
  return {
    name: 'Pe ani',
    type: 'bar',
    unit: 'miliarde EUR pe an',
    plain: `În ${aU}, România a exportat bunuri de ${mld(vU)} — cu ${fmt1(Math.abs(p))}% ${p >= 0 ? 'mai mult' : 'mai puțin'} decât în ${aP}. ` +
      `Față de ${ani[0]} (${mld(v0)}), exporturile ${vU / v0 >= 2 ? `s-au dublat` : `au crescut cu ${fmt0(pct(vU, v0))}%`}. ${U.luna < 12 ? `${U.an} are date doar pentru ${U.luna} luni.` : ''}`,
    labels: ani.map(a => (a === U.an && U.luna < 12 ? `${a}*` : String(a))),
    series: [{ name: 'Exporturi (mld €)', color: C_MAIN, data: tot.map(x => Math.round(x / 1e5) / 10) }],
    labelCol: 'Anul', tableNewestFirst: true,
    kpis: [
      { label: `Total ${aU}`, value: mld(vU), chg: `${sageata(p)} ${semn(p)} față de ${aP}`, dir: dir(p) },
      { label: `Total ${ani[0]}`, value: mld(v0), hint: `De atunci: ${semn(pct(vU, v0))}.` },
      { label: `${U.an} până acum`, value: mld(tot[tot.length - 1]), hint: `${U.luna} luni (până în ${LUNI[U.luna - 1]}).` },
    ],
    footnote: `* an incomplet. ${NOTA}`,
  }
}

function analizaAnCurent(): Analysis {
  const ani = [U.an - 1, U.an]
  const serie = (a: number) => LUNI.map((_, i) => { const x = v(T.Total, { an: a, luna: i + 1 }); return x == null ? null : Math.round(x / 1000) })
  const s0 = serie(ani[0]), s1 = serie(ani[1])
  const c1 = suma(T.Total, U, U.luna)!, c0 = suma(T.Total, inapoi(U, 12), U.luna)!
  const p = pct(c1, c0)
  const mai = s1.filter((x, i) => x != null && s0[i] != null && x > s0[i]!).length
  return {
    name: `${U.an} vs. ${U.an - 1}`,
    type: 'bar',
    unit: 'milioane EUR pe lună',
    plain: `În primele ${U.luna} luni din ${U.an}, exporturile au fost de ${mld(c1)}, cu ${fmt1(Math.abs(p))}% ${p >= 0 ? 'mai mult' : 'mai puțin'} decât în aceeași perioadă din ${U.an - 1}. ` +
      `${mai} din ${U.luna} luni au fost mai bune decât cu un an înainte.`,
    labels: LUNI_SCURT.map(cap), labelsLong: LUNI.map(cap),
    series: [{ name: String(ani[0]), color: C_PREV, data: s0 }, { name: String(ani[1]), color: C_MAIN, data: s1 }],
    labelCol: 'Luna',
    kpis: [
      { label: `${U.an} (${U.luna} luni)`, value: mld(c1), chg: `${sageata(p)} ${semn(p)}`, dir: dir(p) },
      { label: `${U.an - 1} (aceleași luni)`, value: mld(c0) },
      { label: `Luni mai bune în ${U.an}`, value: `${mai} din ${U.luna}` },
    ],
    footnote: NOTA,
  }
}

function analizaUE(): Analysis {
  const ue = suma(T['Intra-UE'], U)!, non = suma(T['Extra-UE'], U)!
  const pUE = ue / (ue + non) * 100
  const ueP = suma(T['Intra-UE'], inapoi(U, 12))!, nonP = suma(T['Extra-UE'], inapoi(U, 12))!
  return {
    name: 'UE și restul lumii',
    type: 'pie',
    unit: 'ultimele 12 luni',
    plain: `Cam ${Math.round(pUE / 10)} din 10 euro din exporturi vin din vânzări către alte țări din Uniunea Europeană (${fmt0(pUE)}%). ` +
      `Exporturile în UE ${ue >= ueP ? 'au crescut' : 'au scăzut'} cu ${fmt1(Math.abs(pct(ue, ueP)))}% într-un an, iar cele în afara UE ${non >= nonP ? 'au crescut' : 'au scăzut'} cu ${fmt1(Math.abs(pct(non, nonP)))}%.`,
    labels: ['În Uniunea Europeană', 'În afara UE'],
    series: [{ name: 'Exporturi (mil. €)', data: [Math.round(ue / 1000), Math.round(non / 1000)], colors: [C_UE, C_NONUE] }],
    labelCol: 'Destinație', share: true,
    kpis: [
      { label: 'Către UE', value: mld(ue), chg: `${sageata(pct(ue, ueP))} ${semn(pct(ue, ueP))} într-un an`, dir: dir(pct(ue, ueP)) },
      { label: 'În afara UE', value: mld(non), chg: `${sageata(pct(non, nonP))} ${semn(pct(non, nonP))} într-un an`, dir: dir(pct(non, nonP)) },
      { label: 'Ponderea UE', value: `${fmt0(pUE)}%` },
    ],
    footnote: `Ultimele 12 luni: ${numeL(inapoi(U, 11))} – ${numeL(U)}. ${NOTA}`,
  }
}

/* ═══════════ Pe produse ═══════════ */
const grupe = Object.keys(D.RAW).filter(g => g !== 'Total').map(g => {
  const r = D.RAW[g]
  const a = suma(r.Total, U) ?? 0, b = suma(r.Total, inapoi(U, 12)) ?? 0, ue = suma(r['Intra-UE'], U) ?? 0
  return { g, nume: GRUPA[g] ?? g, a, b, ue }
}).sort((x, y) => y.a - x.a)

function analizaProduse(): Analysis {
  const [p1, p2] = grupe
  return {
    name: 'Ce exportăm',
    type: 'bar',
    unit: 'miliarde EUR, ultimele 12 luni',
    plain: `Cea mai mare grupă: ${p1.nume.toLowerCase()} — ${fmt0(p1.a / U12 * 100)}% din toate exporturile (autoturisme, piese, cabluri, aparate electrice). ` +
      `Pe locul doi: ${p2.nume.toLowerCase()} (${fmt0(p2.a / U12 * 100)}%).`,
    labels: grupe.map(x => x.nume),
    series: [{ name: 'Exporturi (mld €)', color: C_MAIN, data: grupe.map(x => Math.round(x.a / 1e5) / 10) }],
    labelCol: 'Grupa de produse', share: true,
    kpis: [
      { label: 'Locul 1', value: p1.nume, chg: `${mld(p1.a)} · ${fmt0(p1.a / U12 * 100)}%` },
      { label: 'Locul 2', value: p2.nume, chg: `${mld(p2.a)} · ${fmt0(p2.a / U12 * 100)}%` },
      { label: 'Total 12 luni', value: mld(U12) },
    ],
    footnote: `Grupele CSCI (Clasificarea Standard de Comerț Internațional). Ultimele 12 luni: ${numeL(inapoi(U, 11))} – ${numeL(U)}. ${NOTA}`,
  }
}

function analizaTabelProduse(): Analysis {
  const d = grupe.map(x => pct(x.a, x.b))
  const iB = d.indexOf(Math.max(...d)), iW = d.indexOf(Math.min(...d))
  return {
    name: 'Toate grupele',
    type: 'table',
    unit: 'exporturi, ultimele 12 luni vs. cele 12 dinainte',
    plain: `Cea mai mare creștere într-un an: ${grupe[iB].nume.toLowerCase()} (${semn(d[iB])}). Cea mai mare scădere: ${grupe[iW].nume.toLowerCase()} (${semn(d[iW])}). ` +
      `Coloana „către UE” arată cât din fiecare grupă se vinde în Uniunea Europeană.`,
    labels: grupe.map(x => x.nume),
    series: [
      { name: 'Ultimele 12 luni (mil. €)', data: grupe.map(x => Math.round(x.a / 1000)) },
      { name: '12 luni înainte (mil. €)', data: grupe.map(x => Math.round(x.b / 1000)) },
    ],
    extraCols: [
      { name: 'Schimbare', values: d.map(p => `${sageata(p)} ${semn(p)}`) },
      { name: 'Pondere', values: grupe.map(x => `${fmt1(x.a / U12 * 100)}%`) },
      { name: 'Către UE', values: grupe.map(x => `${fmt0(x.a ? x.ue / x.a * 100 : 0)}%`) },
    ],
    labelCol: 'Grupa de produse',
    kpis: [
      { label: 'Grupe în creștere', value: `${d.filter(p => p > 0).length} din ${d.length}` },
      { label: 'Cea mai mare creștere', value: grupe[iB].nume, chg: semn(d[iB]), dir: 'up' },
      { label: 'Cea mai mare scădere', value: grupe[iW].nume, chg: semn(d[iW]), dir: 'down' },
    ],
    footnote: `Ultimele 12 luni: ${numeL(inapoi(U, 11))} – ${numeL(U)}. ${NOTA}`,
  }
}

/* ═══════════ Pe județe ═══════════ */
const UJ = ultimaLuna(D.JD['TOTAL']['Total'])
const TJ = suma(D.JD['TOTAL']['Total'], UJ)!
const judete = Object.keys(D.JD).filter(j => j !== 'TOTAL' && j !== 'Nespecificat').map(j => {
  const s = D.JD[j]
  const a = suma(s['Total'], UJ) ?? 0, b = suma(s['Total'], inapoi(UJ, 12))
  const sec = Object.keys(s).filter(x => x !== 'Total').map(x => ({ x, val: suma(s[x], UJ) ?? 0 })).sort((p, q) => q.val - p.val)[0]
  return { j, nume: numeJudet(j), a, b, princ: numeNC(sec.x), pPrinc: a ? sec.val / a * 100 : 0 }
}).sort((x, y) => y.a - x.a)
const perJ = `${numeL(inapoi(UJ, 11))} – ${numeL(UJ)}`

function analizaTopJudete(top = 12): Analysis {
  const sel = judete.slice(0, top)
  const top5 = judete.slice(0, 5).reduce((s, x) => s + x.a, 0) / TJ * 100
  const [a, b] = judete
  return {
    name: 'Top județe',
    type: 'bar',
    unit: 'miliarde EUR, ultimele 12 luni',
    plain: `${a.nume} exportă cel mai mult (${mld(a.a)} în ultimele 12 luni), urmat de ${b.nume} (${mld(b.a)}). ` +
      `Primele 5 județe fac ${fmt0(top5)}% din exporturile țării. Contează sediul firmei: multe companii mari au sediul în București, chiar dacă fabricile lor sunt în alte județe.`,
    labels: sel.map(x => x.nume),
    series: [{ name: 'Exporturi (mld €)', data: sel.map(x => Math.round(x.a / 1e5) / 10) }],
    labelCol: 'Județ',
    extraCols: [{ name: 'Ce exportă cel mai mult', values: sel.map(x => `${x.princ} (${fmt0(x.pPrinc)}%)`) }],
    kpis: [
      { label: 'Primul loc', value: a.nume, chg: mld(a.a) },
      { label: 'Primele 5 județe', value: `${fmt0(top5)}%`, hint: 'Din exporturile întregii țări.' },
      { label: 'Ce exportă liderul', value: a.princ, chg: `${fmt0(a.pPrinc)}% din exporturile lui` },
    ],
    footnote: `Ultimele 12 luni: ${perJ}. Județul firmei exportatoare (sediul), nu neapărat locul fabricii. Sursa: INS, EXP101J. ${NOTA}`,
  }
}

function analizaTabelJudete(): Analysis {
  const d = judete.map(x => (x.b ? pct(x.a, x.b) : null))
  const cu = judete.map((x, i) => ({ n: x.nume, p: d[i] })).filter((x): x is { n: string; p: number } => x.p != null)
  const best = cu.reduce((p, q) => (q.p > p.p ? q : p)), worst = cu.reduce((p, q) => (q.p < p.p ? q : p))
  return {
    name: 'Toate județele',
    type: 'table',
    unit: 'exporturi, ultimele 12 luni',
    plain: `Exporturile au crescut în ${cu.filter(x => x.p > 0).length} din ${cu.length} de județe față de anul dinainte. ` +
      `Cea mai mare creștere: ${best.n} (${semn(best.p)}); cea mai mare scădere: ${worst.n} (${semn(worst.p)}). Coloana din dreapta arată produsul principal al fiecărui județ.`,
    labels: judete.map(x => x.nume),
    series: [
      { name: 'Ultimele 12 luni (mil. €)', data: judete.map(x => Math.round(x.a / 1000)) },
      { name: '12 luni înainte (mil. €)', data: judete.map(x => (x.b == null ? null : Math.round(x.b / 1000))) },
    ],
    extraCols: [
      { name: 'Schimbare', values: d.map(p => (p == null ? '—' : `${sageata(p)} ${semn(p)}`)) },
      { name: 'Pondere', values: judete.map(x => `${fmt1(x.a / TJ * 100)}%`) },
      { name: 'Produs principal', values: judete.map(x => `${x.princ} (${fmt0(x.pPrinc)}%)`) },
    ],
    labelCol: 'Județ',
    kpis: [
      { label: 'Județe în creștere', value: `${cu.filter(x => x.p > 0).length} din ${cu.length}` },
      { label: 'Cea mai mare creștere', value: best.n, chg: semn(best.p), dir: 'up' },
      { label: 'Cea mai mare scădere', value: worst.n, chg: semn(worst.p), dir: 'down' },
    ],
    footnote: `Ultimele 12 luni: ${perJ}. Sursa: INS, EXP101J. ${NOTA}`,
  }
}

/* ═══════════ Exploratoare (alegi indicatorul și anii) ═══════════ */
function setExplorator(key: string, titlu: string, descriere: string, cod: string, serii: { nume: string; luni: Luni }[]): EurostatSet {
  const toate = serii.flatMap(s => Object.entries(s.luni).flatMap(([a, m]) => Object.keys(m).map(l => cheie({ an: +a, luna: +l }))))
  const perioade = Array.from(new Set(toate)).sort()
  return {
    key, scurt: titlu, titlu, descriere, cod, freq: 'M', unitate: 'milioane EUR', zecimale: 1, agregare: 'suma',
    note: [NOTA], url: 'http://statistici.insse.ro:8077/tempo-online/', sursa: 'INS (TEMPO-Online)', actualizat: D.ultima_actualizare,
    perioade,
    serii: serii.map(s => ({
      nume: s.nume,
      valori: perioade.map(p => { const x = s.luni[String(+p.slice(0, 4))]?.[String(+p.slice(5))]; return x == null ? null : Math.round(x / 100) / 10 }),
      provizorii: [],
    })),
  }
}

const explProduse = setExplorator('produse', 'Exporturi pe grupe de produse',
  'Alege o grupă de produse (sau totalul, către UE / în afara UE) și anii pe care vrei să-i compari.', 'EXP101I', [
    { nume: 'Toate exporturile', luni: T.Total },
    { nume: 'Toate exporturile — către UE', luni: T['Intra-UE'] },
    { nume: 'Toate exporturile — în afara UE', luni: T['Extra-UE'] },
    ...grupe.map(x => ({ nume: x.nume, luni: D.RAW[x.g].Total })),
  ])
const explJudete = setExplorator('judete', 'Exporturi pe județe',
  'Alege un județ și anii pe care vrei să-i compari.', 'EXP101J', [
    { nume: 'Toată țara', luni: D.JD['TOTAL']['Total'] },
    ...[...judete].sort((a, b) => a.nume.localeCompare(b.nume, 'ro')).map(x => ({ nume: x.nume, luni: D.JD[x.j]['Total'] })),
  ])

/* ═══════════ Tab ═══════════ */
const baza = { credit: 'INS (TEMPO-Online)', link: 'statistici.insse.ro', url: 'http://statistici.insse.ro:8077/tempo-online/', freq: 'lunar' }

/** un tab de analiză care afișează exploratorul în locul graficului standard */
const explorator = (set: EurostatSet, accent: string): Analysis => ({
  name: '🔎 Explorează', type: 'table', unit: '', plain: '', labels: [], series: [{ name: '', data: [] }], labelCol: '', kpis: [],
  content: <EurostatExplorer set={set} accent={accent} locale="ro-RO" />,
})

export function exporturiTopic(accent: string): Topic {
  const chipsTara = [`● Ultimele date: ${numeL(U)}`, '🔁 lunar', `📅 din ${Object.keys(T.Total).sort()[0]}`]
  const chipsJ = [`● Ultimele date: ${numeL(UJ)}`, '🔁 lunar', `📍 ${judete.length} de județe`]
  const sources: Source[] = [
    { key: 'total', label: '🗺️ Toată țara', ...baza, chips: chipsTara, analyses: [analizaEvolutie(), analizaAni(), analizaAnCurent(), analizaUE()] },
    { key: 'produse', label: '📦 Pe produse', ...baza, chips: chipsTara, analyses: [analizaProduse(), analizaTabelProduse(), explorator(explProduse, accent)] },
    { key: 'judete', label: '📍 Exporturi pe județe', ...baza, chips: chipsJ, analyses: [analizaTopJudete(), analizaTabelJudete(), explorator(explJudete, accent)] },
  ]
  return {
    key: 'exporturi', label: 'Exporturi', icon: '🚢', sources,
    intro: 'Ce vinde România în străinătate — pe produse și pe județe.',
  }
}
