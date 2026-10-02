import fs from 'fs'
import path from 'path'
import type { Analysis, Source, Topic } from '@/components/ModelA'
import td from '../../../public/transport-data.json'
import { fmt0, fmt1, pct, semn } from '../industrii/agricultura/util'

/* Firme de transport rutier de marfă — autorizatiiauto.ro (ARR), lunar.
   public/transport-data.json + public/operatori-istoric.csv sunt actualizate de
   scripts/fetch_transportatori.py (GitHub Actions, pe 1 ale lunii). Textele se calculează din date. */

type Clasa = { nume: string; interval: string; operatori: number; camioane: number; pondere: number; color: string }
type Firma = { den: string; loc: string; veh: number }
type Evo = { luni: string[]; clase: { nume: string; operatori: Record<string, number>; camioane: Record<string, number> }[] }
const T = td as unknown as { lastUpdate: string; metrics: { totalOperatori: number; totalCamioane: number; flotaMedie: number; flotaMaxima: number }; clase: Clasa[]; operatoriMari: Firma[]; evolutie: Evo }

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const LUNI_SCURT = ['ian', 'feb', 'mar', 'apr', 'mai', 'iun', 'iul', 'aug', 'sep', 'oct', 'noi', 'dec']
/** „2026.09” → „septembrie 2026” */
const numeL = (k: string) => { const [a, l] = k.split('.').map(Number); return `${LUNI[l - 1]} ${a}` }
const etL = (k: string) => { const [a, l] = k.split('.').map(Number); return `${LUNI_SCURT[l - 1]} ${String(a).slice(2)}` }
const sageata = (p: number) => (p > 0 ? '▲' : p < 0 ? '▼' : '=')
const dir = (p: number) => (p > 0 ? 'up' as const : p < 0 ? 'down' as const : undefined)
const de = (v: number) => { const r = Math.round(v) % 100; return v >= 20 && (r === 0 || r >= 20) ? 'de ' : '' }
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

/* Numele claselor din JSON → limbaj simplu */
const CLASA: Record<string, string> = {
  'Operatori mici': 'Mici (1–9 camioane)', 'Operatori medii 1': 'Medii (10–39)',
  'Operatori medii 2': 'Mari (40–99)', 'Operatori mari': 'Foarte mari (100+)',
}
const numeClasa = (n: string) => CLASA[n] ?? n

const NOTA = 'Sursa: Autoritatea Rutieră Română, prin autorizatiiauto.ro — firmele cu licență de transport rutier de marfă și numărul de copii conforme (camioane) din licență. Datele sunt preluate pe 1 ale fiecărei luni și descriu luna anterioară.'

/* ── CSV-ul cu toate firmele (citit la build) ── */
type Rand = { den: string; cf: string; loc: string; veh: number; luna: string }
function citesteCsv(): Rand[] {
  const txt = fs.readFileSync(path.join(process.cwd(), 'public', 'operatori-istoric.csv'), 'utf-8').replace(/^﻿/, '')
  const out: Rand[] = []
  for (const linie of txt.split(/\r?\n/).slice(1)) {
    if (!linie.trim()) continue
    const c: string[] = []
    let cur = '', q = false
    for (let i = 0; i < linie.length; i++) {
      const ch = linie[i]
      if (q) { if (ch === '"' && linie[i + 1] === '"') { cur += '"'; i++ } else if (ch === '"') q = false; else cur += ch }
      else if (ch === '"') q = true
      else if (ch === ',') { c.push(cur); cur = '' }
      else cur += ch
    }
    c.push(cur)
    out.push({ den: c[0].trim(), cf: c[1].trim(), loc: c[2].trim(), veh: Number(c[3]) || 0, luna: c[4].trim() })
  }
  return out
}
const CSV = citesteCsv()
const luniCsv = Array.from(new Set(CSV.map(r => r.luna))).sort()
const ultimaCsv = luniCsv[luniCsv.length - 1]

/* Localitățile vin scrise în multe feluri („BUCURESTI, SECTOR 6”, „Cluj Napoca”, „MUN. ARAD”) */
const ORAS: Record<string, string> = {
  BUCURESTI: 'București', PITESTI: 'Pitești', IASI: 'Iași', TIMISOARA: 'Timișoara', CONSTANTA: 'Constanța',
  GALATI: 'Galați', BRASOV: 'Brașov', 'RAMNICU VALCEA': 'Râmnicu Vâlcea', PLOIESTI: 'Ploiești', RADAUTI: 'Rădăuți',
  'TARGU MURES': 'Târgu Mureș', 'CLUJ NAPOCA': 'Cluj-Napoca', TARGOVISTE: 'Târgoviște', BACAU: 'Bacău',
  BRAILA: 'Brăila', BUZAU: 'Buzău', 'SFANTU GHEORGHE': 'Sfântu Gheorghe', MILISAUTI: 'Milișăuți', SEBES: 'Sebeș',
  ZALAU: 'Zalău', TALMACIU: 'Tălmaciu', VISINA: 'Vișina', GAESTI: 'Găești', 'TARGU JIU': 'Târgu Jiu',
  'DROBETA TURNU SEVERIN': 'Drobeta-Turnu Severin', 'PIATRA NEAMT': 'Piatra-Neamț', FOCSANI: 'Focșani',
  BOTOSANI: 'Botoșani', CALARASI: 'Călărași', RESITA: 'Reșița', 'MIERCUREA CIUC': 'Miercurea Ciuc',
  'SATU MARE': 'Satu Mare', 'BAIA MARE': 'Baia Mare', 'ALBA IULIA': 'Alba Iulia', 'VALENII DE MUNTE': 'Vălenii de Munte',
}
function cheieLoc(s: string) {
  let k = s.toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[-.]/g, ' ').replace(/\s+/g, ' ').trim()
  k = k.replace(/^(MUN|MUNICIPIUL|ORAS|ORASUL|COM|COMUNA|SAT|LOC) /, '')
  if (k.startsWith('BUCURESTI')) k = 'BUCURESTI'
  return k
}
const afisLoc = (k: string) => ORAS[k] ?? k.toLowerCase().replace(/(^|\s)([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase()).replace(/ (De|Din|Lui|Pe) /g, m => m.toLowerCase())

/* ── Piața ── */
const ultima = T.evolutie.luni[T.evolutie.luni.length - 1]
const M = T.metrics

function analizaMarime(): Analysis {
  const [mici] = T.clase
  const mari = T.clase[T.clase.length - 1]
  const pCamMari = mari.camioane / M.totalCamioane * 100
  return {
    name: 'Firme pe mărime',
    type: 'pie',
    unit: `firme de transport, ${numeL(ultima)}`,
    plain: `Transportul de marfă e făcut mai ales de firme mici: ${fmt0(mici.pondere)}% din firme au sub 10 camioane. ` +
      `Doar ${fmt0(mari.operatori)} de firme au peste 100 de camioane (${fmt1(mari.pondere)}%), dar ele au ${fmt0(pCamMari)}% din toate camioanele.`,
    labels: T.clase.map(c => numeClasa(c.nume)),
    series: [{ name: 'Firme', data: T.clase.map(c => c.operatori) }],
    labelCol: 'Mărimea firmei',
    share: true,
    extraCols: [{ name: 'Camioane', values: T.clase.map(c => fmt0(c.camioane)) }],
    kpis: [
      { label: 'Firme de transport', value: fmt0(M.totalOperatori), hint: 'Firme cu licență de transport de marfă.' },
      { label: 'Camioane', value: fmt0(M.totalCamioane), hint: 'Copii conforme ale licenței — câte un camion fiecare.' },
      { label: 'Camioane per firmă', value: fmt1(M.flotaMedie), chg: `cea mai mare flotă: ${fmt0(M.flotaMaxima)}`, hint: 'Media pe firmă.' },
    ],
    footnote: NOTA,
  }
}

function analizaCamioane(): Analysis {
  const mari = T.clase[T.clase.length - 1], mici = T.clase[0]
  return {
    name: 'Camioane pe mărime',
    type: 'bar',
    unit: `camioane, ${numeL(ultima)}`,
    plain: `Cele ${fmt0(mici.operatori)} de firme mici au împreună ${fmt0(mici.camioane)} de camioane — mai puține decât cele doar ${fmt0(mari.operatori)} de firme foarte mari (${fmt0(mari.camioane)}). ` +
      `Fiecare grupă are între ${fmt0(Math.min(...T.clase.map(c => c.camioane)))} și ${fmt0(Math.max(...T.clase.map(c => c.camioane)))} de camioane: câteva zeci de firme mari cântăresc cât mii de firme mici.`,
    labels: T.clase.map(c => numeClasa(c.nume)),
    series: [{ name: 'Camioane', data: T.clase.map(c => c.camioane) }],
    labelCol: 'Mărimea firmei',
    share: true,
    extraCols: [{ name: 'Firme', values: T.clase.map(c => fmt0(c.operatori)) }, { name: 'Camioane per firmă', values: T.clase.map(c => fmt1(c.camioane / c.operatori)) }],
    kpis: [
      { label: 'Firme mici', value: fmt0(mici.camioane), chg: `${fmt0(mici.camioane / M.totalCamioane * 100)}% din camioane`, hint: `${fmt1(mici.camioane / mici.operatori)} camioane per firmă.` },
      { label: 'Firme foarte mari', value: fmt0(mari.camioane), chg: `${fmt0(mari.camioane / M.totalCamioane * 100)}% din camioane`, hint: `${fmt0(mari.camioane / mari.operatori)} de camioane per firmă.` },
      { label: 'Raport', value: `${fmt0(mici.operatori / mari.operatori)} la 1`, hint: 'De câte ori sunt mai multe firme mici decât foarte mari.' },
    ],
    footnote: NOTA,
  }
}

function analizaEvolutie(): Analysis {
  const L = T.evolutie.luni
  const sum = (k: 'operatori' | 'camioane') => L.map(l => T.evolutie.clase.reduce((s, c) => s + (c[k][l] ?? 0), 0))
  const op = sum('operatori'), cam = sum('camioane')
  const p = pct(op[op.length - 1], op[0]), pc = pct(cam[cam.length - 1], cam[0])
  return {
    name: 'Evoluție lunară',
    type: 'line',
    unit: 'firme de transport',
    plain: `Din ${numeL(L[0])} până în ${numeL(ultima)}, numărul firmelor de transport ${p < 0 ? 'a scăzut' : 'a crescut'} cu ${fmt1(Math.abs(p))}% (de la ${fmt0(op[0])} la ${fmt0(op[op.length - 1])}), ` +
      `iar camioanele ${pc < 0 ? 'au scăzut' : 'au crescut'} cu ${fmt1(Math.abs(pc))}%. ${p < 0 && pc > 0 ? 'Sunt mai puține firme, dar mai mari — piața se concentrează.' : ''}`,
    labels: L.map(etL),
    labelsLong: L.map(l => cap(numeL(l))),
    series: [{ name: 'Firme', color: '#12a5b8', data: op }],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    extraCols: [{ name: 'Camioane', values: cam.map(v => fmt0(v)) }],
    kpis: [
      { label: `Firme (${numeL(ultima)})`, value: fmt0(op[op.length - 1]), chg: `${sageata(p)} ${semn(p)} față de ${numeL(L[0])}`, dir: dir(p) },
      { label: 'Camioane', value: fmt0(cam[cam.length - 1]), chg: `${sageata(pc)} ${semn(pc)} față de ${numeL(L[0])}`, dir: dir(pc) },
      { label: 'Luni urmărite', value: String(L.length), hint: `Din ${numeL(L[0])}. Seria crește cu o lună la fiecare actualizare.` },
    ],
    footnote: NOTA,
  }
}

/* ── Firme ── */
function analizaTop(top = 15): Analysis {
  const f = T.operatoriMari
  const sel = f.slice(0, top)
  const tot = f.reduce((s, x) => s + x.veh, 0)
  return {
    name: `Top ${top} firme`,
    type: 'bar',
    unit: `camioane, ${numeL(ultima)}`,
    plain: `Cea mai mare firmă de transport, ${f[0].den}, are ${fmt0(f[0].veh)} ${de(f[0].veh)}camioane. ` +
      `Cele ${f.length} de firme cu peste 100 de camioane au împreună ${fmt0(tot)} — ${fmt0(tot / M.totalCamioane * 100)}% din toate camioanele din țară.`,
    labels: sel.map(x => x.den.replace(/\s+(S\.?R\.?L\.?|S\.?A\.?)$/i, '')),
    labelsLong: sel.map(x => `${x.den} (${afisLoc(cheieLoc(x.loc))})`),
    series: [{ name: 'Camioane', color: '#12a5b8', data: sel.map(x => x.veh) }],
    labelCol: 'Firma',
    extraCols: [{ name: 'Localitate', values: sel.map(x => afisLoc(cheieLoc(x.loc))) }],
    kpis: [
      { label: 'Cea mai mare flotă', value: fmt0(f[0].veh), chg: f[0].den },
      { label: 'Firme cu 100+ camioane', value: String(f.length), hint: `Din ${fmt0(M.totalOperatori)} de firme.` },
      { label: 'Camioanele lor', value: fmt0(tot), chg: `${fmt0(tot / M.totalCamioane * 100)}% din total` },
    ],
    footnote: NOTA,
  }
}

function analizaToateMari(): Analysis {
  const f = T.operatoriMari
  return {
    name: 'Toate firmele mari',
    type: 'table',
    unit: 'firme cu peste 100 de camioane',
    plain: `Lista completă a celor ${f.length} de firme de transport cu cel puțin 100 de camioane, în ${numeL(ultima)}.`,
    labels: f.map(x => x.den),
    series: [{ name: 'Camioane', data: f.map(x => x.veh) }],
    share: true,
    labelCol: 'Firma',
    extraCols: [{ name: 'Localitate', values: f.map(x => afisLoc(cheieLoc(x.loc))) }],
    kpis: [
      { label: 'Firme', value: String(f.length) },
      { label: 'Mediana flotei', value: fmt0(f[Math.floor(f.length / 2)].veh), hint: 'Jumătate au mai multe camioane, jumătate mai puține.' },
      { label: 'Cea mai mică din listă', value: fmt0(f[f.length - 1].veh), chg: f[f.length - 1].den },
    ],
    footnote: NOTA,
  }
}

function analizaIntrari(): Analysis | null {
  if (luniCsv.length < 2) return null
  const pe = (l: string) => new Set(CSV.filter(r => r.luna === l).map(r => r.cf))
  const seturi = luniCsv.map(pe)
  const L = luniCsv.slice(1)
  const noi = L.map((_, i) => Array.from(seturi[i + 1]).filter(x => !seturi[i].has(x)).length)
  const iesite = L.map((_, i) => Array.from(seturi[i]).filter(x => !seturi[i + 1].has(x)).length)
  const tn = noi.reduce((a, b) => a + b, 0), ti = iesite.reduce((a, b) => a + b, 0)
  return {
    name: 'Firme noi și ieșite',
    type: 'bar',
    unit: 'firme pe lună',
    plain: `În fiecare lună, unele firme primesc licență de transport, iar altele renunță sau o pierd. ` +
      `Din ${numeL(luniCsv[0])} până în ${numeL(ultimaCsv)} au apărut ${fmt0(tn)} ${de(tn)}firme noi și au ieșit ${fmt0(ti)} — ${tn >= ti ? 'piața a crescut' : 'piața s-a micșorat'} cu ${fmt0(Math.abs(tn - ti))}.`,
    labels: L.map(etL),
    labelsLong: L.map(l => cap(numeL(l))),
    series: [
      { name: 'Firme noi', color: '#22b07d', data: noi },
      { name: 'Firme ieșite', color: '#e5544b', data: iesite },
    ],
    labelCol: 'Luna',
    tableNewestFirst: true,
    kpis: [
      { label: 'Firme noi', value: fmt0(tn), chg: `în ${L.length} luni`, dir: 'up' },
      { label: 'Firme ieșite', value: fmt0(ti), chg: `în ${L.length} luni`, dir: 'down' },
      { label: 'Diferența', value: `${tn - ti > 0 ? '+' : ''}${fmt0(tn - ti)}`, dir: tn - ti >= 0 ? 'up' : 'down', hint: 'Câte firme are piața în plus (sau în minus).' },
    ],
    footnote: 'Comparăm lista firmelor de la o lună la alta, după codul fiscal. ' + NOTA,
  }
}

/* ── Localități ── */
const locAgg = (() => {
  const m = new Map<string, { firme: number; cam: number }>()
  CSV.filter(r => r.luna === ultimaCsv).forEach(r => {
    const k = cheieLoc(r.loc)
    const v = m.get(k) ?? { firme: 0, cam: 0 }
    v.firme++; v.cam += r.veh; m.set(k, v)
  })
  return Array.from(m.entries()).map(([k, v]) => ({ nume: afisLoc(k), ...v })).sort((a, b) => b.firme - a.firme)
})()

function analizaTopLoc(top = 15): Analysis {
  const sel = locAgg.slice(0, top)
  const [a, b, c] = locAgg
  const totF = locAgg.reduce((s, x) => s + x.firme, 0)
  const top10 = locAgg.slice(0, 10).reduce((s, x) => s + x.firme, 0) / totF * 100
  return {
    name: 'Top localități',
    type: 'bar',
    unit: `firme de transport, ${numeL(ultimaCsv)}`,
    plain: `Cele mai multe firme de transport au sediul în ${a.nume} (${fmt0(a.firme)}), ${b.nume} (${fmt0(b.firme)}) și ${c.nume} (${fmt0(c.firme)}). ` +
      `Firmele sunt foarte răspândite: primele 10 localități au doar ${fmt0(top10)}% din firme, restul sunt în alte ${fmt0(locAgg.length - 10)} de localități.`,
    labels: sel.map(x => x.nume),
    series: [{ name: 'Firme', data: sel.map(x => x.firme) }],
    labelCol: 'Localitate',
    extraCols: [{ name: 'Camioane', values: sel.map(x => fmt0(x.cam)) }],
    kpis: [
      { label: 'Primul loc', value: a.nume, chg: `${fmt0(a.firme)} firme · ${fmt0(a.cam)} camioane` },
      { label: 'Localități cu firme', value: fmt0(locAgg.length), hint: 'Orașe și comune unde își au sediul firmele de transport.' },
      { label: 'Primele 10 localități', value: `${fmt0(top10)}%`, hint: 'Din toate firmele de transport.' },
    ],
    footnote: 'Localitatea sediului social al firmei; camioanele pot opera din altă parte. ' + NOTA,
  }
}

function analizaTabelLoc(top = 50): Analysis {
  const sel = locAgg.slice(0, top)
  const bigCam = [...sel].sort((x, y) => y.cam / y.firme - x.cam / x.firme)[0]
  return {
    name: `Top ${top} localități`,
    type: 'table',
    unit: 'firme de transport',
    plain: `Cele ${top} de localități cu cele mai multe firme de transport. Coloana „camioane per firmă” arată unde sunt firmele mai mari — de exemplu în ${bigCam.nume}, cu ${fmt1(bigCam.cam / bigCam.firme)} camioane per firmă.`,
    labels: sel.map(x => x.nume),
    series: [{ name: 'Firme', data: sel.map(x => x.firme) }, { name: 'Camioane', data: sel.map(x => x.cam) }],
    labelCol: 'Localitate',
    extraCols: [{ name: 'Camioane per firmă', values: sel.map(x => fmt1(x.cam / x.firme)) }],
    kpis: [
      { label: `Firme în top ${top}`, value: fmt0(sel.reduce((s, x) => s + x.firme, 0)) },
      { label: `Camioane în top ${top}`, value: fmt0(sel.reduce((s, x) => s + x.cam, 0)) },
      { label: 'Cele mai mari firme', value: bigCam.nume, chg: `${fmt1(bigCam.cam / bigCam.firme)} camioane per firmă` },
    ],
    footnote: 'Localitatea sediului social al firmei. ' + NOTA,
  }
}

/* ── Tab ── */
const baza = { credit: 'Autoritatea Rutieră Română (autorizatiiauto.ro)', link: 'autorizatiiauto.ro', url: 'https://www.autorizatiiauto.ro/Marfa/ListaClase', freq: 'lunar' }
const chips = [`● Ultimele date: ${numeL(ultima)}`, '🔁 lunar', `🚛 ${fmt0(M.totalOperatori)} firme · ${fmt0(M.totalCamioane)} camioane`]

export function firmeTopic(): Topic {
  const sources: Source[] = [
    { key: 'piata', label: '📊 Piața', ...baza, chips, analyses: [analizaMarime(), analizaCamioane(), analizaEvolutie()] },
    { key: 'firme', label: '🏆 Firme', ...baza, chips, analyses: [analizaTop(), analizaToateMari(), analizaIntrari()].filter((a): a is Analysis => a != null) },
    { key: 'localitati', label: '📍 Localități', ...baza, chips, analyses: [analizaTopLoc(), analizaTabelLoc()] },
  ]
  return { key: 'firme', label: 'Firme de transport', icon: '🚛', sources }
}
