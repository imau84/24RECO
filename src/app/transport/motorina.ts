import type { Analysis, Source, Topic } from '@/components/ModelA'
import td from '../../../public/transport-data.json'
import { fmt0, fmt1, fmt2, pct, semn } from '../industrii/agricultura/util'

/* Prețul motorinei în UE — Weekly Oil Bulletin al Comisiei Europene (săptămânal, cu taxe, convertit în euro).
   `dieselData` din public/transport-data.json e actualizat de scripts/fetch_oil_bulletin.py (GitHub Actions, miercurea). */

type Sapt = { date: string } & Record<string, number | null | string>
const D = ((td as unknown as { dieselData: Sapt[] }).dieselData).slice().sort((a, b) => a.date.localeCompare(b.date))

const TARI: Record<string, string> = {
  AT: 'Austria', BE: 'Belgia', BG: 'Bulgaria', CY: 'Cipru', CZ: 'Cehia', DE: 'Germania', DK: 'Danemarca', EE: 'Estonia',
  ES: 'Spania', FI: 'Finlanda', FR: 'Franța', GR: 'Grecia', HR: 'Croația', HU: 'Ungaria', IE: 'Irlanda', IT: 'Italia',
  LT: 'Lituania', LU: 'Luxemburg', LV: 'Letonia', MT: 'Malta', NL: 'Țările de Jos', PL: 'Polonia', PT: 'Portugalia',
  RO: 'România', SE: 'Suedia', SI: 'Slovenia', SK: 'Slovacia',
}
const C_RO = '#12a5b8', C_UE = '#9aa3b8', C_UP = '#e5544b', C_DOWN = '#22b07d'

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const LUNI_SCURT = ['ian', 'feb', 'mar', 'apr', 'mai', 'iun', 'iul', 'aug', 'sep', 'oct', 'noi', 'dec']
const zi = (d: string) => { const [a, l, z] = d.split('-').map(Number); return `${z} ${LUNI[l - 1]} ${a}` }
const ziScurt = (d: string) => { const [a, l, z] = d.split('-').map(Number); return `${z} ${LUNI_SCURT[l - 1]} ${String(a).slice(2)}` }
const eur = (v: number) => `${fmt2(v)} €`
const r3 = (v: number) => Math.round(v * 1000) / 1000
const val = (s: Sapt, k: string) => (typeof s[k] === 'number' ? (s[k] as number) : null)
const sageata = (p: number) => (p > 0 ? '▲' : p < 0 ? '▼' : '=')
/** la motorină, scumpirea e „rea” → roșu */
const dirPret = (p: number) => (p > 0 ? 'down' as const : 'up' as const)

const NOTA = 'Prețuri medii la pompă, cu toate taxele (TVA, accize), raportate de fiecare țară Comisiei Europene și convertite în euro. Pentru România, prețul în lei se obține înmulțind cu cursul euro.'

const ultim = D[D.length - 1]
const ro = val(ultim, 'RO')!, ue = val(ultim, 'EU')!
/** aceeași săptămână cu un an în urmă (cea mai apropiată dată) */
const anTrecut = (() => {
  const t = new Date(ultim.date); t.setFullYear(t.getFullYear() - 1)
  return D.reduce((a, b) => (Math.abs(+new Date(b.date) - +t) < Math.abs(+new Date(a.date) - +t) ? b : a))
})()

/* ── România vs. UE ── */
function analizaUltimulAn(): Analysis {
  const s = D.slice(-53)
  const roA = val(anTrecut, 'RO')!, p = pct(ro, roA)
  const roV = s.map(x => val(x, 'RO')).filter((v): v is number => v != null)
  const max = Math.max(...roV), min = Math.min(...roV)
  const sub = ro < ue
  return {
    name: 'Ultimul an',
    type: 'line',
    unit: 'euro pe litru, săptămânal',
    plain: `Pe ${zi(ultim.date)}, un litru de motorină costa în România ${eur(ro)}, ${sub ? 'sub' : 'peste'} media UE (${eur(ue)}). ` +
      `Față de acum un an, motorina ${p > 0 ? 's-a scumpit' : 's-a ieftinit'} cu ${fmt1(Math.abs(p))}%. ` +
      `Pentru un camion care alimentează 1.000 de litri, diferența față de media UE e de ${fmt0(Math.abs(ue - ro) * 1000)} € la fiecare plin.`,
    labels: s.map(x => ziScurt(x.date)),
    labelsLong: s.map(x => `Săptămâna din ${zi(x.date)}`),
    series: [
      { name: 'România', color: C_RO, data: s.map(x => val(x, 'RO')) },
      { name: 'Media UE', color: C_UE, data: s.map(x => val(x, 'EU')) },
    ],
    labelCol: 'Săptămâna',
    tableNewestFirst: true,
    zoomY: true,
    valueSuffix: ' €',
    kpis: [
      { label: 'România, acum', value: eur(ro), chg: `${sageata(p)} ${semn(p)} față de acum un an`, dir: dirPret(p), hint: 'Prețul unui litru, cu taxe.' },
      { label: 'Media UE', value: eur(ue), chg: `România: ${semn(pct(ro, ue))} față de medie`, hint: sub ? 'La noi e mai ieftin decât media.' : 'La noi e mai scump decât media.' },
      { label: 'Ultimele 12 luni', value: `${fmt2(min)}–${fmt2(max)} €`, hint: 'Cel mai mic și cel mai mare preț din România.' },
    ],
    footnote: NOTA,
  }
}

function analizaPeAni(): Analysis {
  const ani = Array.from(new Set(D.map(x => x.date.slice(0, 4)))).filter(a => D.some(x => x.date.startsWith(a) && val(x, 'RO') != null))
  const medie = (a: string, k: string) => {
    const v = D.filter(x => x.date.startsWith(a)).map(x => val(x, k)).filter((x): x is number => x != null)
    return v.length ? r3(v.reduce((s, x) => s + x, 0) / v.length) : null
  }
  const roS = ani.map(a => medie(a, 'RO')), ueS = ani.map(a => medie(a, 'EU'))
  const sub = roS.filter((v, i) => v != null && ueS[i] != null && v < ueS[i]!).length
  const iMax = roS.indexOf(Math.max(...roS.map(v => v ?? 0)))
  const aCur = ani[ani.length - 1]
  return {
    name: 'Pe ani',
    type: 'bar',
    unit: 'euro pe litru, media anului',
    plain: `În ${sub} din ${ani.length} ani, motorina a fost mai ieftină în România decât media UE. ` +
      `Cel mai scump an a fost ${ani[iMax]} (media ${eur(roS[iMax]!)} pe litru). ${aCur} e an în curs — media se schimbă până la final.`,
    labels: ani,
    series: [
      { name: 'România', color: C_RO, data: roS },
      { name: 'Media UE', color: C_UE, data: ueS },
    ],
    labelCol: 'Anul',
    tableNewestFirst: true,
    valueSuffix: ' €',
    kpis: [
      { label: `Media ${aCur} (România)`, value: eur(roS[roS.length - 1]!), hint: 'An în curs.' },
      { label: 'Cel mai scump an', value: ani[iMax], chg: `${eur(roS[iMax]!)} / litru` },
      { label: 'Ani sub media UE', value: `${sub} din ${ani.length}` },
    ],
    footnote: 'Date pentru România din 2008. ' + NOTA,
  }
}

/* ── Toate țările ── */
const tariAcum = Object.keys(TARI).map(k => ({ k, nume: TARI[k], v: val(ultim, k), a: val(anTrecut, k) }))
  .filter((x): x is { k: string; nume: string; v: number; a: number | null } => x.v != null)
  .sort((a, b) => a.v - b.v)

function analizaClasament(): Analysis {
  const loc = tariAcum.findIndex(x => x.k === 'RO') + 1
  const [ieftin] = tariAcum, scump = tariAcum[tariAcum.length - 1]
  const vecini = ['BG', 'HU'].map(k => tariAcum.find(x => x.k === k)!).filter(Boolean)
  return {
    name: 'Clasament',
    type: 'bar',
    unit: `euro pe litru, ${zi(ultim.date)}`,
    plain: `România e pe locul ${loc} din ${tariAcum.length} de țări UE, de la cea mai ieftină motorină la cea mai scumpă. ` +
      `Cea mai ieftină e în ${ieftin.nume} (${eur(ieftin.v)}), cea mai scumpă în ${scump.nume} (${eur(scump.v)}). ` +
      `Vecinii: ${vecini.map(x => `${x.nume} ${eur(x.v)}`).join(', ')}.`,
    labels: tariAcum.map(x => x.k),
    labelsLong: tariAcum.map(x => x.nume),
    series: [{ name: 'Preț motorină', data: tariAcum.map(x => x.v), colors: tariAcum.map(x => (x.k === 'RO' ? C_RO : '#cfd5e2')) }],
    labelCol: 'Țara',
    valueSuffix: ' €',
    kpis: [
      { label: 'Locul României', value: `${loc} din ${tariAcum.length}`, hint: 'Locul 1 = cea mai ieftină motorină.' },
      { label: 'Cea mai ieftină', value: ieftin.nume, chg: eur(ieftin.v) },
      { label: 'Cea mai scumpă', value: scump.nume, chg: eur(scump.v) },
    ],
    footnote: 'În Malta prețul e fixat de stat. ' + NOTA,
  }
}

function analizaSchimbare(): Analysis {
  const r = tariAcum.filter(x => x.a != null).map(x => ({ ...x, p: pct(x.v, x.a!) })).sort((a, b) => b.p - a.p)
  const roR = r.find(x => x.k === 'RO')!
  const scump = r.filter(x => x.p > 0).length
  return {
    name: 'Schimbare într-un an',
    type: 'bar',
    unit: `% față de ${zi(anTrecut.date)}`,
    plain: `În ultimul an, motorina s-a scumpit în ${scump} din ${r.length} de țări. În România prețul ${roR.p > 0 ? 'a crescut' : 'a scăzut'} cu ${fmt1(Math.abs(roR.p))}% ` +
      `(de la ${eur(roR.a!)} la ${eur(roR.v)}). Cea mai mare scumpire: ${r[0].nume} (${semn(r[0].p)}).`,
    labels: r.map(x => x.k),
    labelsLong: r.map(x => x.nume),
    series: [{ name: 'Schimbare', data: r.map(x => Math.round(x.p * 10) / 10), colors: r.map(x => (x.k === 'RO' ? C_RO : x.p > 0 ? C_UP : C_DOWN)) }],
    labelCol: 'Țara',
    valueSuffix: '%',
    extraCols: [{ name: 'Acum un an', values: r.map(x => eur(x.a!)) }, { name: 'Acum', values: r.map(x => eur(x.v)) }],
    kpis: [
      { label: 'România', value: semn(roR.p), dir: dirPret(roR.p), chg: `${eur(roR.a!)} → ${eur(roR.v)}` },
      { label: 'Țări cu scumpiri', value: `${scump} din ${r.length}` },
      { label: 'Cea mai mare scumpire', value: r[0].nume, chg: semn(r[0].p), dir: 'down' },
    ],
    footnote: NOTA,
  }
}

/* ── Tab ── */
const baza = { credit: 'Comisia Europeană — Weekly Oil Bulletin', link: 'energy.ec.europa.eu', url: 'https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en', freq: 'săptămânal' }
const chips = [`● Ultimele date: ${zi(ultim.date)}`, '🔁 săptămânal', `📅 din ${D[0].date.slice(0, 4)}`]

export function motorinaTopic(): Topic {
  const sources: Source[] = [
    { key: 'ro', label: '📍 România vs. UE', ...baza, chips, analyses: [analizaUltimulAn(), analizaPeAni()] },
    { key: 'tari', label: '🌍 Toate țările', ...baza, chips, analyses: [analizaClasament(), analizaSchimbare()] },
  ]
  return { key: 'motorina', label: 'Prețul motorinei', icon: '⛽', sources }
}
