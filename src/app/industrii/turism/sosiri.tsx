import type { Source, Topic } from '@/components/ModelA'
import SosiriExplorer, { type SosiriProps, type Agregat } from './SosiriExplorer'
import raw from '../../../../public/turism_data.json'

/* Tema „Sosiri” — turiști sosiți în structurile de cazare (INS TEMPO, matricele TUR104*).
   public/turism_data.json e actualizat lunar de scripts/fetch_turism.py (GitHub Actions).
   Aici, la build, datele se compactează: pentru județe și localități trimitem în pagină doar totalurile
   (anul curent până la ultima lună cu date, aceeași perioadă anul trecut, tot anul trecut),
   nu seriile lunare — altfel pagina ar căra ~500 KB. */

type YearMap = Record<string, (number | null)[]>
type TurismData = {
  CHART_DATA: Record<string, Record<string, YearMap>>
  COUNTY_DATA: Record<string, Record<string, Record<string, YearMap>>>
  CAT_DATA: Record<string, Record<string, Record<string, YearMap>>>
  LOC_DATA: Record<string, Record<string, Record<string, YearMap>>>
  STRUCTURI_DISPLAY: Record<string, string>
  CATEGORII_ORDER: string[]
  CATEGORII_COLORS?: Record<string, string>
  META?: { updated: string; lastMonth: string; source: string }
}
const D = raw as unknown as TurismData

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']

/* ── nume pe înțeles ── */
const JUDETE: Record<string, string> = {
  Arges: 'Argeș', Bacau: 'Bacău', 'Bistrita-Nasaud': 'Bistrița-Năsăud', Botosani: 'Botoșani', Braila: 'Brăila', Brasov: 'Brașov',
  Buzau: 'Buzău', Calarasi: 'Călărași', 'Caras-Severin': 'Caraș-Severin', Constanta: 'Constanța', Dambovita: 'Dâmbovița',
  Galati: 'Galați', Ialomita: 'Ialomița', Iasi: 'Iași', Maramures: 'Maramureș', Mehedinti: 'Mehedinți', 'Municipiul Bucuresti': 'București',
  Mures: 'Mureș', Neamt: 'Neamț', Salaj: 'Sălaj', Timis: 'Timiș', Valcea: 'Vâlcea',
}
const judet = (j: string) => JUDETE[j] ?? j
const STRUCTURI: Record<string, string> = {
  Total: 'Toate tipurile de cazare', 'Apartamente si camere de inchiriat': 'Apartamente și camere de închiriat', 'Casute  turistice': 'Căsuțe turistice',
  'Sate de vacanta': 'Sate de vacanță', 'Tabere de elevi si prescolari': 'Tabere de elevi și preșcolari',
  'Spatii de cazare de pe navele fluviale si maritime': 'Cazare pe nave (fluviale și maritime)',
}
const structura = (s: string) => STRUCTURI[s] ?? D.STRUCTURI_DISPLAY[s] ?? s
/** „1017 MUNICIPIUL ALBA IULIA” → { nume: „Alba Iulia”, tip: „municipiu” } (sursa nu are diacritice) */
const localitate = (s: string) => {
  const t = s.replace(/^\d+\s*/, '')
  const tip = t.startsWith('MUNICIPIUL ') ? 'municipiu' : t.startsWith('ORAS ') ? 'oraș' : 'comună'
  const nume = t.replace(/^(MUNICIPIUL|ORAS)\s+/, '').toLowerCase().replace(/(^|[\s-])[a-z]/g, m => m.toUpperCase())
  return { nume, tip }
}

/* ── ani și ultima lună cu date, per bloc (localitățile vin cu câteva luni în urma restului) ── */
const ani = (ym: YearMap) => Object.keys(ym).filter(y => /^\d{4}$/.test(y)).sort()
const ultimaLuna = (arr: (number | null)[] = []) => { for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return i; return -1 }
const suma = (arr: (number | null)[] = [], n = arr.length) => arr.slice(0, n).reduce<number>((a, b) => a + (b ?? 0), 0)
const serie = (ym: YearMap | undefined, an: string) => ym?.[an] ?? (ym as Record<string, (number | null)[]> | undefined)?.['y' + an.slice(2)] ?? []

type Per = { an: string; anPrev: string; luni: number }
function perioada(blocuri: YearMap[]): Per {
  const toti = Array.from(new Set(blocuri.flatMap(ani))).sort()
  const an = toti[toti.length - 1], anPrev = toti[toti.length - 2] ?? ''
  return { an, anPrev, luni: Math.max(...blocuri.map(b => ultimaLuna(serie(b, an)))) + 1 }
}
const textPer = (p: Per) => (p.luni === 12 ? `tot anul ${p.an}` : p.luni === 1 ? `ianuarie ${p.an}` : `ianuarie–${LUNI[p.luni - 1]} ${p.an}`)

/** totaluri compacte: [an curent până la luna p.luni, aceeași perioadă anul trecut, tot anul trecut] */
const agregat = (ym: YearMap, p: Per): Agregat => [suma(serie(ym, p.an), p.luni), suma(serie(ym, p.anPrev), p.luni), suma(serie(ym, p.anPrev))]

/* ── pregătirea datelor ── */
const perNat = perioada([D.CHART_DATA.Total.Total])
const perJud = perioada(Object.values(D.COUNTY_DATA.Total.Total))
const perCat = perioada(Object.values(D.CAT_DATA.Total ?? {}).map(c => c.Total).filter(Boolean))
const perLoc = perioada(Object.values(D.LOC_DATA.Total).flatMap(j => Object.values(j)))

const ordineStr = (keys: string[]) => ['Total', ...keys.filter(k => k !== 'Total').sort((a, b) => structura(a).localeCompare(structura(b), 'ro'))]

// localități: nume deduplicate o singură dată, apoi pe structuri doar indici + totaluri
const locNume: { nume: string; tip: string; judet: string }[] = []
const locIdx = new Map<string, number>()
const locPeStructura: Record<string, [number, ...Agregat][]> = {}
for (const [s, judete] of Object.entries(D.LOC_DATA)) {
  locPeStructura[s] = []
  for (const [j, locs] of Object.entries(judete)) for (const [n, ym] of Object.entries(locs)) {
    if (n === 'TOTAL') continue
    const a = agregat(ym, perLoc)
    if (!a[0] && !a[2]) continue
    const k = `${j}|${n}`
    if (!locIdx.has(k)) { locIdx.set(k, locNume.length); locNume.push({ ...localitate(n), judet: judet(j) }) }
    locPeStructura[s].push([locIdx.get(k)!, ...a])
  }
}

const props = {
  structuri: Object.fromEntries(Object.keys(D.STRUCTURI_DISPLAY).concat(Object.keys(D.LOC_DATA)).map(s => [s, structura(s)])),
  national: {
    per: { ...perNat, text: textPer(perNat) },
    structuri: ordineStr(Object.keys(D.CHART_DATA)),
    serii: Object.fromEntries(Object.entries(D.CHART_DATA).map(([s, t]) => [s, Object.fromEntries(Object.entries(t).map(([k, ym]) =>
      [k, { cur: serie(ym, perNat.an), prev: serie(ym, perNat.anPrev) }]))])),
  },
  judete: {
    per: { ...perJud, text: textPer(perJud) },
    structuri: ordineStr(Object.keys(D.COUNTY_DATA)),
    randuri: Object.fromEntries(Object.entries(D.COUNTY_DATA).map(([s, t]) => [s, Object.fromEntries(Object.entries(t).map(([k, jud]) =>
      [k, Object.entries(jud).map(([j, ym]) => [judet(j), ...agregat(ym, perJud)] as [string, ...Agregat])]))])),
  },
  categorii: {
    per: { ...perCat, text: textPer(perCat) },
    structuri: ordineStr(Object.keys(D.CAT_DATA)),
    ordine: D.CATEGORII_ORDER.filter(c => c !== 'Total'),
    culori: D.CATEGORII_COLORS ?? {},
    date: Object.fromEntries(Object.entries(D.CAT_DATA).map(([s, cats]) => [s, Object.fromEntries(Object.entries(cats).filter(([c]) => c !== 'Total')
      .map(([c, t]) => [c, Object.fromEntries(Object.entries(t).map(([k, ym]) => [k, { cur: serie(ym, perCat.an).slice(0, perCat.luni), agg: agregat(ym, perCat) }]))]))])),
  },
  localitati: { per: { ...perLoc, text: textPer(perLoc) }, structuri: ordineStr(Object.keys(D.LOC_DATA)), nume: locNume, randuri: locPeStructura },
  actualizat: D.META?.updated?.slice(0, 10) ?? '',
} satisfies Omit<SosiriProps, 'view' | 'accent'>

const SUB: { key: SosiriProps['view']; label: string; per: Per }[] = [
  { key: 'national', label: '🇷🇴 Total național', per: perNat },
  { key: 'judete', label: '📍 Județe', per: perJud },
  { key: 'categorii', label: '⭐ Categorii (stele/flori)', per: perCat },
  { key: 'localitati', label: '🏘️ Localități', per: perLoc },
]

export function sosiriTopic(accent: string): Topic {
  const sources: Source[] = SUB.map(s => ({
    key: s.key, label: s.label,
    credit: 'INS', link: 'statistici.insse.ro', url: 'http://statistici.insse.ro:8077/tempo-online/',
    freq: 'lunar',
    chips: [`● Ultimele date: ${LUNI[s.per.luni - 1]} ${s.per.an}`, '🔁 lunar', `📅 din ${s.per.anPrev || s.per.an}`],
    analyses: [],
    // fiecare subtab primește doar blocul lui de date (altfel totul ar fi serializat de 4 ori în pagină)
    content: <SosiriExplorer key={s.key} view={s.key} accent={accent} structuri={props.structuri} actualizat={props.actualizat} {...{ [s.key]: props[s.key] }} />,
  }))
  return { key: 'sosiri', label: 'Sosiri', icon: '🧳', sources, intro: 'Câți turiști au ajuns în hoteluri, pensiuni și alte locuri de cazare: în toată țara, pe județe, pe stele și pe localități.' }
}
