import ModelA, { type Analysis, type Kpi } from '@/components/ModelA'
import agriculturaData from '@/data/agricultura/agricultura_data.json'
import { lapteTopic } from './lapte'
import { sacrificariTopic } from './sacrificari'

/* Pagina e Server Component: calculele de mai jos rulează la build,
   iar textul (KPI-uri, „pe scurt”) ajunge în HTML-ul văzut de Google. */

const ZONE = ['VEST', 'EST', 'SUD'] as const
type Zona = typeof ZONE[number]
type Cereala = 'grau' | 'porumb'

const ZONA_NUME: Record<Zona, string> = { VEST: 'Vest', EST: 'Est', SUD: 'Sud' }
const ZONA_COLOR: Record<Zona, string> = { VEST: '#3b82f6', EST: '#7c5ce6', SUD: '#e5544b' }
const CEREALA: Record<Cereala, { nume: string; color: string }> = {
  grau: { nume: 'Grâu', color: '#e0a020' },
  porumb: { nume: 'Porumb', color: '#22b07d' },
}

const LUNI: [RegExp, string][] = [
  [/ianuarie/g, 'ian'], [/februarie/g, 'feb'], [/martie/g, 'mar'], [/aprilie/g, 'apr'],
  [/iunie/g, 'iun'], [/iulie/g, 'iul'], [/august/g, 'aug'], [/septembrie/g, 'sep'],
  [/octombrie/g, 'oct'], [/noiembrie/g, 'noi'], [/decembrie/g, 'dec'],
]
const scurt = (label: string) => LUNI.reduce((s, [re, r]) => s.replace(re, r), label).replace(/\s*\d{4}$/, '')

const fmt = (n: number) => new Intl.NumberFormat('ro-RO').format(Math.round(n))
const fmt2 = (n: number) => new Intl.NumberFormat('ro-RO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
const pct = (a: number, b: number) => (a - b) / b * 100
const semn = (p: number) => `${p > 0 ? '+' : p < 0 ? '−' : ''}${new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(Math.abs(p))}%`
const sageata = (p: number): Pick<Kpi, 'chg' | 'dir'> =>
  Math.abs(p) < 0.05 ? { chg: '= neschimbat' } : { chg: `${p > 0 ? '▲' : '▼'} ${semn(p)} față de săpt. trecută`, dir: p > 0 ? 'up' : 'down' }
const perKg = (leiPeTona: number) => `≈ ${fmt2(leiPeTona / 1000)} lei pe kilogram`
const sumaVerb = (p: number) =>
  Math.abs(p) < 1 ? 'a rămas cam la fel' : p > 0 ? `s-a scumpit cu ${semn(p).slice(1)}` : `s-a ieftinit cu ${semn(p).slice(1)}`

/* ── Date ── */
const { meta, saptamani } = agriculturaData
const n = saptamani.length
const ultima = saptamani[n - 1]
const penultima = saptamani[n - 2]
const prima = saptamani[0]

const labels = saptamani.map(s => `S${s.nr}`)
const labelsLong = saptamani.map(s => `S${s.nr} · ${scurt(s.label)}`)
const medie = (s: typeof ultima, c: Cereala) => ZONE.reduce((a, z) => a + s[c][z], 0) / ZONE.length

// săptămâni lipsă din sursă (ex. S35)
const lipsa: number[] = []
for (let i = 1; i < n; i++) for (let w = saptamani[i - 1].nr + 1; w < saptamani[i].nr; w++) lipsa.push(w)
const notaLipsa = lipsa.length
  ? `Notă: BRM nu a publicat cotații pentru ${lipsa.map(w => 'S' + w).join(', ')}.`
  : undefined
const notaDepozit = 'Prețurile sunt „la depozit” (Ex Warehouse): nu includ transportul până la cumpărător. 1 tonă = 1.000 kg.'

/* 1 — Grâu vs. porumb (media celor 3 zone) */
function analizaComparatie(): Analysis {
  const g = medie(ultima, 'grau'), p = medie(ultima, 'porumb')
  const gPrev = medie(penultima, 'grau'), pPrev = medie(penultima, 'porumb')
  const gAn = pct(g, medie(prima, 'grau')), pAn = pct(p, medie(prima, 'porumb'))
  const dif = p - g
  const relatie = Math.abs(pct(p, g)) < 2
    ? `Porumbul e cam la același preț (${fmt(p)} lei/t)`
    : `Porumbul e ${dif > 0 ? 'mai scump' : 'mai ieftin'} cu ${fmt(Math.abs(dif))} lei pe tonă (${fmt(p)} lei/t)`
  return {
    name: 'Grâu vs. porumb',
    type: 'line',
    unit: 'lei/tonă, media țării',
    plain: `O tonă de grâu costă acum, în medie, ${fmt(g)} lei — adică aproximativ ${fmt2(g / 1000)} lei pe kilogram. ${relatie}. De la prima cotație din an (S${prima.nr}), grâul ${sumaVerb(gAn)}, iar porumbul ${sumaVerb(pAn)}.`,
    labels, labelsLong,
    series: (['grau', 'porumb'] as Cereala[]).map(c => ({
      name: CEREALA[c].nume, color: CEREALA[c].color,
      data: saptamani.map(s => Math.round(medie(s, c))),
    })),
    labelCol: 'Săptămâna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Grâu acum (S${ultima.nr})`, value: `${fmt(g)} lei/t`, ...sageata(pct(g, gPrev)), hint: perKg(g) },
      { label: `Porumb acum (S${ultima.nr})`, value: `${fmt(p)} lei/t`, ...sageata(pct(p, pPrev)), hint: perKg(p) },
      { label: `De la începutul anului (S${prima.nr})`, value: `Grâu ${semn(gAn)}`, chg: `Porumb ${semn(pAn)}`, hint: 'Cât s-a schimbat prețul față de prima cotație din 2026.' },
    ],
    footnote: [notaDepozit, notaLipsa].filter(Boolean).join(' '),
  }
}

/* 2 — Pe zone de livrare (ultima săptămână) */
function analizaZone(): Analysis {
  const extreme = (c: Cereala) => {
    const sort = [...ZONE].sort((a, b) => ultima[c][b] - ultima[c][a])
    return { max: sort[0], min: sort[sort.length - 1] }
  }
  const g = extreme('grau'), p = extreme('porumb')
  const gDif = ultima.grau[g.max] - ultima.grau[g.min]
  const pDif = ultima.porumb[p.max] - ultima.porumb[p.min]
  return {
    name: 'Pe zone de livrare',
    type: 'bar',
    unit: `lei/tonă, S${ultima.nr}`,
    plain: `Prețul diferă după zona în care e livrată marfa. În ultima săptămână, grâul a fost cel mai scump în ${ZONA_NUME[g.max]} (${fmt(ultima.grau[g.max])} lei/t) și cel mai ieftin în ${ZONA_NUME[g.min]} (${fmt(ultima.grau[g.min])} lei/t) — o diferență de ${fmt(gDif)} lei pe tonă. La porumb, cel mai scump a fost în ${ZONA_NUME[p.max]}, cel mai ieftin în ${ZONA_NUME[p.min]}.`,
    labels: ZONE.map(z => ZONA_NUME[z]),
    series: (['grau', 'porumb'] as Cereala[]).map(c => ({
      name: CEREALA[c].nume, color: CEREALA[c].color,
      data: ZONE.map(z => ultima[c][z]),
    })),
    labelCol: 'Zona',
    kpis: [
      { label: 'Grâul cel mai scump', value: ZONA_NUME[g.max], chg: `${fmt(ultima.grau[g.max])} lei/t`, hint: perKg(ultima.grau[g.max]) },
      { label: 'Porumbul cel mai scump', value: ZONA_NUME[p.max], chg: `${fmt(ultima.porumb[p.max])} lei/t`, hint: perKg(ultima.porumb[p.max]) },
      { label: 'Diferența între zone', value: `${fmt(gDif)} lei/t`, chg: `la grâu · ${fmt(pDif)} lei/t la porumb`, hint: 'Cât costă în plus o tonă în zona cea mai scumpă față de cea mai ieftină.' },
    ],
    footnote: `Cotații pentru ${scurt(ultima.label)}. ${notaDepozit}`,
  }
}

/* 3, 4 — Evoluția unei cereale pe cele 3 zone */
function analizaEvolutie(c: Cereala): Analysis {
  const nume = CEREALA[c].nume
  const toate = saptamani.flatMap(s => ZONE.map(z => ({ v: s[c][z], z, nr: s.nr })))
  const max = toate.reduce((a, b) => (b.v > a.v ? b : a))
  const min = toate.reduce((a, b) => (b.v < a.v ? b : a))
  const medieAn = toate.reduce((a, b) => a + b.v, 0) / toate.length
  const medieZona = ZONE.map(z => ({ z, v: saptamani.reduce((a, s) => a + s[c][z], 0) / n })).sort((a, b) => b.v - a.v)
  const scumpa = medieZona[0], ieftina = medieZona[medieZona.length - 1]
  return {
    name: `Evoluție ${nume.toLowerCase()}`,
    type: 'line',
    unit: 'lei/tonă, pe zone',
    plain: `În 2026, o tonă de ${nume.toLowerCase()} a costat între ${fmt(min.v)} și ${fmt(max.v)} lei, în funcție de săptămână și zonă. În medie, zona ${ZONA_NUME[scumpa.z]} a fost cea mai scumpă (${fmt(scumpa.v)} lei/t), iar zona ${ZONA_NUME[ieftina.z]} cea mai ieftină (${fmt(ieftina.v)} lei/t).`,
    labels, labelsLong,
    series: ZONE.map(z => ({ name: ZONA_NUME[z], color: ZONA_COLOR[z], data: saptamani.map(s => s[c][z]) })),
    labelCol: 'Săptămâna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: 'Cel mai mare preț', value: `${fmt(max.v)} lei/t`, chg: `${ZONA_NUME[max.z]} · S${max.nr}`, dir: 'up', hint: perKg(max.v) },
      { label: 'Cel mai mic preț', value: `${fmt(min.v)} lei/t`, chg: `${ZONA_NUME[min.z]} · S${min.nr}`, dir: 'down', hint: perKg(min.v) },
      { label: 'Media anului', value: `${fmt(medieAn)} lei/t`, chg: `din ${n} săptămâni × 3 zone`, hint: perKg(medieAn) },
    ],
    footnote: [notaDepozit, notaLipsa].filter(Boolean).join(' '),
  }
}

export default function AgriculturaPage() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Agricultură' }]}
      icon="🌾"
      title="Agricultură"
      sub="Prețuri și date din agricultura României, pe înțelesul tuturor"
      theme={{ accent: '#22b07d', accent2: '#5cc99a', tint: '#e6f6ef', tintBorder: '#c4ead9', tintInk: '#185c43' }}
      topics={[{
        key: 'cereale', label: 'Prețuri cereale', icon: '🌾',
        sources: [{
          key: 'BRM', tag: 'bursă', label: 'Bursa Română de Mărfuri', link: 'brm.ro/cotatii-cereale', url: meta.url, freq: 'săptămânal',
          chips: [`● Actualizat: ${scurt(meta.actualizat)}`, '🔁 săptămânal', `📅 ${n} săptămâni din 2026`],
          analyses: [analizaComparatie(), analizaZone(), analizaEvolutie('grau'), analizaEvolutie('porumb')],
        }],
      }, lapteTopic(), sacrificariTopic()]}
    />
  )
}
