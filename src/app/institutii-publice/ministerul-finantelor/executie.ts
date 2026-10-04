import type { Analysis, Source, Topic } from '@/components/ModelA'
import eb from '../../../../public/executie-bugetara_data.json'
import { LUNI, LUNI_SCURT, cap, fmt0, fmt1, semn } from '../../industrii/agricultura/util'

/* Execuția bugetului general consolidat — fișierul „Sinteza” publicat lunar de Ministerul Finanțelor.
   public/executie-bugetara_data.json e actualizat de scripts/fetch_executie_bugetara.py (GitHub Actions, săptămânal).
   Valorile lunare (ex. „aug26”) sunt fluxuri pe lună; „cum26”/„cum25” = de la 1 ianuarie până la ultima lună. */

type Rand = { label: string; bold?: boolean; indent?: number; cat: 'venituri' | 'cheltuieli' | 'deficit'; cum26: number; cum25: number; var: number | null } & Record<string, unknown>
const D = eb as unknown as { pib2026: number; months: string[]; lastUpdated: string; rows: Rand[] }

const C_VEN = '#3b82f6', C_CH = '#e5544b', C_VEN_V = '#a9c8fb', C_CH_V = '#f4b1ac', C_UP = '#22b07d', C_DOWN = '#e5544b'
const LUNI_EB = ['ian', 'feb', 'mar', 'apr', 'mai', 'iun', 'iul', 'aug', 'sep', 'oct', 'noi', 'dec']
const idxLuna = (m: string) => (m === 'nov' ? 10 : LUNI_EB.indexOf(m))
const AN = 2026
const luni = D.months
const ultima = luni[luni.length - 1]
const perioada = `ianuarie–${LUNI[idxLuna(ultima)]} ${AN}`
const mld = (v: number) => `${fmt1(v / 1000)} mld. lei`
const num = (r: Rand, k: string) => (typeof r[k] === 'number' ? (r[k] as number) : null)
const rand = (l: string) => D.rows.find(r => r.label === l || (l === 'EXCEDENT / DEFICIT' && r.label.includes('EXCEDENT')))!

const ven = rand('VENITURI TOTALE'), ch = rand('CHELTUIELI TOTALE'), def = rand('EXCEDENT / DEFICIT')
const defPib = def.cum26 / D.pib2026 * 100

const SURSA = {
  credit: 'Ministerul Finanțelor', link: 'mfinante.gov.ro',
  url: 'https://mfinante.gov.ro/ro/domenii/buget/executia-bugetara', freq: 'lunar',
  chips: [`● Ultimele date: ${LUNI[idxLuna(ultima)]} ${AN}`, '🔁 lunar', `📅 comparat cu ${AN - 1}`],
}
const NOTA = 'Bugetul general consolidat = bugetul de stat + bugetele locale + asigurările sociale (pensii, sănătate, șomaj) + fondurile europene. Valori în lei curenți.'

/* ── Sinteză ── */
function luna(): Analysis {
  return {
    name: 'Venituri și cheltuieli pe luni',
    type: 'bar',
    unit: 'milioane lei, pe lună',
    plain: `În ${perioada}, statul a încasat ${mld(ven.cum26)} și a cheltuit ${mld(ch.cum26)}. ` +
      `Diferența, ${mld(Math.abs(def.cum26))}, e ${def.cum26 < 0 ? 'deficitul — bani împrumutați' : 'excedentul'}. ` +
      `Față de aceleași luni din ${AN - 1}, veniturile au crescut cu ${fmt1(ven.var ?? 0)}%, iar cheltuielile cu ${fmt1(ch.var ?? 0)}%.`,
    labels: luni.map(m => cap(LUNI_SCURT[idxLuna(m)])),
    labelsLong: luni.map(m => `${cap(LUNI[idxLuna(m)])}`),
    series: [
      { name: `Venituri ${AN}`, color: C_VEN, data: luni.map(m => num(ven, `${m}26`)) },
      { name: `Cheltuieli ${AN}`, color: C_CH, data: luni.map(m => num(ch, `${m}26`)) },
      { name: `Venituri ${AN - 1}`, color: C_VEN_V, data: luni.map(m => num(ven, `${m}25`)) },
      { name: `Cheltuieli ${AN - 1}`, color: C_CH_V, data: luni.map(m => num(ch, `${m}25`)) },
    ],
    labelCol: 'Luna',
    kpis: [
      { label: `Venituri (${perioada})`, value: mld(ven.cum26), chg: `${semn(ven.var ?? 0)} față de ${AN - 1}`, dir: 'up', hint: 'Impozite, TVA, contribuții, fonduri UE.' },
      { label: `Cheltuieli (${perioada})`, value: mld(ch.cum26), chg: `${semn(ch.var ?? 0)} față de ${AN - 1}`, dir: (ch.var ?? 0) > (ven.var ?? 0) ? 'down' : 'up', hint: 'Salarii, pensii și ajutoare, investiții, dobânzi.' },
      { label: 'Deficit', value: mld(Math.abs(def.cum26)), chg: `${fmt1(Math.abs(defPib))}% din PIB`, dir: Math.abs(def.cum26) < Math.abs(def.cum25) ? 'up' : 'down',
        hint: `Anul trecut, în aceleași luni: ${mld(Math.abs(def.cum25))}.` },
    ],
    footnote: NOTA,
  }
}

function deficitLunar(): Analysis {
  const v = luni.map(m => num(def, `${m}26`))
  const nrDef = v.filter(x => x != null && x < 0).length
  return {
    name: 'Deficitul pe luni',
    type: 'bar',
    unit: 'milioane lei, pe lună (minus = deficit)',
    plain: `În ${nrDef} din ${luni.length} luni din ${AN}, statul a cheltuit mai mult decât a încasat. ` +
      `Bara roșie = lună cu deficit (s-au împrumutat bani), bara verde = lună cu excedent.`,
    labels: luni.map(m => cap(LUNI_SCURT[idxLuna(m)])),
    labelsLong: luni.map(m => `${cap(LUNI[idxLuna(m)])} ${AN}`),
    series: [{ name: `Sold ${AN}`, data: v, colors: v.map(x => ((x ?? 0) < 0 ? C_DOWN : C_UP)) }],
    labelCol: 'Luna',
    kpis: [
      { label: 'Cel mai mare deficit lunar', value: mld(Math.abs(Math.min(...v.map(x => x ?? 0)))), hint: cap(LUNI[idxLuna(luni[v.indexOf(Math.min(...v.map(x => x ?? 0)))])]) },
      { label: `Deficit în ${LUNI[idxLuna(ultima)]}`, value: mld(Math.abs(v[v.length - 1] ?? 0)), hint: `${AN - 1}: ${mld(Math.abs(num(def, `${ultima}25`) ?? 0))}` },
      { label: 'Deficit cumulat', value: `${fmt1(Math.abs(defPib))}% din PIB`, hint: 'Ținta UE pentru deficit e sub 3% din PIB pe tot anul.' },
    ],
    footnote: NOTA,
  }
}

function deficitCumulat(): Analysis {
  const cum = (an: '26' | '25') => { let s = 0; return luni.map(m => { const x = num(def, `${m}${an}`); s += x ?? 0; return x == null ? null : Math.round(s) }) }
  return {
    name: 'Deficitul adunat de la 1 ianuarie',
    type: 'line',
    unit: 'milioane lei, cumulat',
    plain: `De la începutul anului, deficitul a ajuns la ${mld(Math.abs(def.cum26))}, ${Math.abs(def.cum26) < Math.abs(def.cum25) ? 'mai mic' : 'mai mare'} decât în ${AN - 1} (${mld(Math.abs(def.cum25))}). ` +
      `Linia care coboară mai repede înseamnă că statul se împrumută mai mult.`,
    labels: luni.map(m => cap(LUNI_SCURT[idxLuna(m)])),
    labelsLong: luni.map(m => `Ianuarie–${LUNI[idxLuna(m)]}`),
    series: [{ name: String(AN), color: C_CH, data: cum('26') }, { name: String(AN - 1), color: '#9aa3b8', data: cum('25') }],
    labelCol: 'Perioada',
    kpis: [
      { label: `Deficit ${perioada}`, value: mld(Math.abs(def.cum26)), chg: `${fmt1(Math.abs(defPib))}% din PIB` },
      { label: `Aceeași perioadă din ${AN - 1}`, value: mld(Math.abs(def.cum25)) },
      { label: 'Diferență', value: mld(Math.abs(def.cum26 - def.cum25)), chg: Math.abs(def.cum26) < Math.abs(def.cum25) ? 'deficit mai mic' : 'deficit mai mare', dir: Math.abs(def.cum26) < Math.abs(def.cum25) ? 'up' : 'down' },
    ],
    footnote: NOTA,
  }
}

/* ── Structura veniturilor / cheltuielilor (cumulat) ── */
const CAT_VEN = ['TVA', 'Contribuții de asigurări', 'Impozitul pe salarii și venit', 'Impozitul pe profit', 'Accize', 'Venituri nefiscale',
  'Sume primite UE (prefinanțări)', 'Impozite și taxe pe proprietate', 'Alte sume UE (incl. 2014–2020)', 'Taxe utilizare bunuri', 'Alte impozite pe venit/profit',
  'Alte impozite bunuri și servicii', 'Taxe vamale', 'Alte impozite și taxe fiscale', 'Venituri din capital']
const CAT_CH = ['Asistență socială', 'Cheltuieli de personal', 'Bunuri și servicii', 'Dobânzi', 'Cheltuieli de capital', 'Proiecte fonduri externe nerambursabile',
  'Alte transferuri', 'Proiecte PNRR nerambursabil', 'Proiecte PNRR împrumut', 'Alte cheltuieli', 'Subvenții', 'Proiecte FEN 2014–2020',
  'Transferuri între unități adm. pub.', 'Programe finanțare rambursabilă']

function structura(cat: 'venituri' | 'cheltuieli'): Analysis {
  const tot = cat === 'venituri' ? ven : ch
  // categorii care nu se suprapun (rândurile din raport sunt imbricate: ex. TVA ⊂ taxe pe bunuri ⊂ venituri fiscale)
  const r = (cat === 'venituri' ? CAT_VEN : CAT_CH).map(rand).filter(x => x.cum26 > 0).sort((a, b) => b.cum26 - a.cum26)
  const top = r[0]
  return {
    name: cat === 'venituri' ? 'De unde vin banii' : 'Pe ce se cheltuie',
    type: 'bar',
    unit: `milioane lei, ${perioada}`,
    plain: cat === 'venituri'
      ? `Cea mai mare sursă de bani a statului sunt ${top.label.toLowerCase()}: ${mld(top.cum26)}, adică ${fmt0(top.cum26 / tot.cum26 * 100)}% din toate veniturile. ` +
        `Coloana deschisă arată aceleași luni din ${AN - 1}.`
      : `Cei mai mulți bani merg pe ${top.label.toLowerCase()}: ${mld(top.cum26)}, adică ${fmt0(top.cum26 / tot.cum26 * 100)}% din cheltuieli. ` +
        `Asistența socială include pensiile și alocațiile.`,
    labels: r.map(x => x.label),
    series: [
      { name: String(AN), color: cat === 'venituri' ? C_VEN : C_CH, data: r.map(x => Math.round(x.cum26)) },
      { name: String(AN - 1), color: cat === 'venituri' ? C_VEN_V : C_CH_V, data: r.map(x => Math.round(x.cum25)) },
    ],
    labelCol: cat === 'venituri' ? 'Venit' : 'Cheltuială',
    extraCols: [{ name: `Față de ${AN - 1}`, values: r.map(x => (x.var == null ? '—' : semn(x.var))) }],
    kpis: [
      { label: `Total ${cat}`, value: mld(tot.cum26), chg: `${semn(tot.var ?? 0)} față de ${AN - 1}` },
      { label: `Cea mai mare: ${top.label}`, value: mld(top.cum26), hint: `${fmt0(top.cum26 / tot.cum26 * 100)}% din total` },
      ...(cat === 'venituri'
        ? [{ label: 'TVA', value: mld(rand('TVA').cum26), chg: `${semn(rand('TVA').var ?? 0)} față de ${AN - 1}`, dir: 'up' as const }]
        : [{ label: 'Dobânzi la datoria publică', value: mld(rand('Dobânzi').cum26), chg: `${semn(rand('Dobânzi').var ?? 0)} față de ${AN - 1}`, dir: 'down' as const }]),
    ],
    footnote: NOTA,
  }
}

/* ── Tabelul complet ── */
function tabel(): Analysis {
  return {
    name: 'Toți indicatorii',
    type: 'table',
    unit: 'milioane lei',
    plain: `Toate rândurile din raportul Ministerului Finanțelor, lună de lună, plus totalul ${perioada} și comparația cu ${AN - 1}. Rândurile cu „·” sunt detalieri ale rândului de deasupra.`,
    labels: D.rows.map(r => `${'· '.repeat(Math.max(0, (r.indent ?? 0) - 1))}${r.label}`),
    series: [
      ...luni.map(m => ({ name: `${cap(LUNI_SCURT[idxLuna(m)])} ${AN}`, data: D.rows.map(r => { const x = num(r, `${m}26`); return x == null ? null : Math.round(x) }) })),
      { name: `Total ${AN}`, data: D.rows.map(r => Math.round(r.cum26)) },
      { name: `Total ${AN - 1}`, data: D.rows.map(r => Math.round(r.cum25)) },
    ],
    labelCol: 'Indicator',
    extraCols: [{ name: 'Variație', values: D.rows.map(r => (r.var == null ? '—' : semn(r.var))) }],
    kpis: [
      { label: 'Venituri', value: mld(ven.cum26) },
      { label: 'Cheltuieli', value: mld(ch.cum26) },
      { label: 'Deficit', value: mld(Math.abs(def.cum26)), chg: `${fmt1(Math.abs(defPib))}% din PIB` },
    ],
    footnote: NOTA,
  }
}

export function executieTopic(): Topic {
  const sources: Source[] = [
    { key: 'sinteza', label: '📊 Pe scurt', ...SURSA, analyses: [luna(), deficitLunar(), deficitCumulat()] },
    { key: 'venituri', label: '💰 Venituri', ...SURSA, analyses: [structura('venituri')] },
    { key: 'cheltuieli', label: '🧾 Cheltuieli', ...SURSA, analyses: [structura('cheltuieli')] },
    { key: 'tabel', label: '⊞ Tabel complet', ...SURSA, analyses: [tabel()] },
  ]
  return {
    key: 'executie', label: 'Execuție Bugetară', icon: '💰', sources,
    intro: `Câți bani a încasat statul și câți a cheltuit în ${AN}, lună de lună, comparat cu ${AN - 1}. Date actualizate ${D.lastUpdated.split('-').reverse().join('.')}.`,
  }
}
