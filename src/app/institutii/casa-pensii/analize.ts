import type { Analysis, Source } from '@/components/ModelA'
import cnpp from '../../../../public/cnpp_asigurati.json'
import { LUNI, LUNI_SCURT, cap, fmt0, fmt1, fmt2, semn, pct } from '../../industrii/agricultura/util'

/* Casa Națională de Pensii Publice — indicatori Pilon I: asigurați (salariați) pe tranșe de venit și pe județe.
   public/cnpp_asigurati.json e actualizat de scripts/fetch_cnpp_asigurati.py (GitHub Actions, lunar). */

type Salariu = { grupa: string; transa: string; numar: number; venit_mediu: number; timp_partial: number; fara_contract: number; somaj: number; contract_individual: number }
type Judet = { cod: string; judet: string; angajatori: number; fond_salarii: number; asigurati: number; salariu_mediu: number }
type Perioada = { year: number; month: number; period: string; total_asigurati: number | null; salarii: Salariu[]; judete: Judet[] }
const P = (cnpp as unknown as { updated_at: string; periods: Perioada[] }).periods.filter(p => p.salarii.length && p.judete.length)

const ultim = P[P.length - 1]
const anTrecut = P.find(p => p.year === ultim.year - 1 && p.month === ultim.month)
const luna = (p: Perioada) => `${LUNI[p.month - 1]} ${p.year}`
const lunaScurt = (p: Perioada) => `${LUNI_SCURT[p.month - 1]} ${String(p.year).slice(2)}`
const C = '#0ea5b7', C_LOW = '#e5544b', C_MID = '#e0a020'

const JUDETE: Record<string, string> = {
  ALBA: 'Alba', ARAD: 'Arad', ARGES: 'Argeș', BACAU: 'Bacău', BIHOR: 'Bihor', 'BISTRITA-NASAUD': 'Bistrița-Năsăud', BOTOSANI: 'Botoșani',
  BRASOV: 'Brașov', BRAILA: 'Brăila', BUZAU: 'Buzău', 'CARAS-SEVERIN': 'Caraș-Severin', CLUJ: 'Cluj', CONSTANTA: 'Constanța', COVASNA: 'Covasna',
  DAMBOVITA: 'Dâmbovița', DOLJ: 'Dolj', GALATI: 'Galați', GORJ: 'Gorj', HARGHITA: 'Harghita', HUNEDOARA: 'Hunedoara', IALOMITA: 'Ialomița',
  IASI: 'Iași', MARAMURES: 'Maramureș', MEHEDINTI: 'Mehedinți', MURES: 'Mureș', NEAMT: 'Neamț', OLT: 'Olt', PRAHOVA: 'Prahova',
  'SATU MARE': 'Satu Mare', SALAJ: 'Sălaj', SIBIU: 'Sibiu', SUCEAVA: 'Suceava', TELEORMAN: 'Teleorman', TIMIS: 'Timiș', TULCEA: 'Tulcea',
  VASLUI: 'Vaslui', VALCEA: 'Vâlcea', VRANCEA: 'Vrancea', BUCURESTI: 'București', ILFOV: 'Ilfov', CALARASI: 'Călărași', GIURGIU: 'Giurgiu',
}
const numeJudet = (j: string) => JUDETE[j.trim().toUpperCase()] ?? cap(j.toLowerCase())
const lei = (v: number) => `${fmt0(v)} lei`
const mii = (v: number) => (v >= 1e6 ? `${fmt2(v / 1e6)} mil.` : `${fmt0(v / 1000)} mii`)

const SURSA_CNPP = {
  credit: 'Casa Națională de Pensii Publice', link: 'cnpp.ro', url: 'https://www.cnpp.ro/ro/indicatori-statistici-pilon-i', freq: 'lunar',
  chips: [`● Ultimele date: ${luna(ultim)}`, '🔁 lunar', `📅 din ${luna(P[0])}`],
}
const NOTA = 'Asigurați = persoane pentru care angajatorii au declarat contribuții la pensie (declarația D112). Venit brut lunar, în lei.'

/* ── Salarii pe tranșe ── */
const S = ultim.salarii
const totalNI = ultim.total_asigurati ?? S.reduce((s, r) => s + r.numar, 0)
const subMinim = S.find(r => r.grupa === '1')!
const laMinim = S.find(r => r.grupa === '2')!
const peste10k = S.filter(r => r.venit_mediu > 10000).reduce((s, r) => s + r.numar, 0)
const median = (() => { let s = 0; for (const r of S) { s += r.numar; if (s >= totalNI / 2) return r } return S[S.length - 1] })()

function transe(): Analysis {
  return {
    name: 'Câți câștigă cât',
    type: 'bar',
    unit: `număr de salariați cu normă întreagă, ${luna(ultim)}`,
    plain: `Jumătate dintre salariații cu normă întreagă câștigă sub ${median.transa.split('-').pop()} lei brut pe lună (tranșa ${median.transa}). ` +
      `${fmt1(subMinim.numar / totalNI * 100)}% sunt declarați cu mai puțin decât salariul minim — de obicei cei care au lucrat doar o parte din lună — ` +
      `și ${fmt1(peste10k / totalNI * 100)}% câștigă peste 10.000 de lei brut.`,
    labels: S.map(r => r.transa),
    labelsLong: S.map(r => (r.transa.match(/^\d/) ? `${r.transa} lei brut` : r.transa)),
    series: [{ name: 'Salariați', data: S.map(r => r.numar), colors: S.map(r => (r.grupa === '1' || r.grupa.startsWith('0') ? C_LOW : r.venit_mediu <= 5000 ? C_MID : C)) }],
    labelCol: 'Tranșa de venit (lei)',
    share: true,
    extraCols: [{ name: 'Venit mediu', values: S.map(r => lei(r.venit_mediu)) }, { name: 'Cu normă parțială', values: S.map(r => fmt0(r.timp_partial)) }],
    kpis: [
      { label: 'Salariați cu normă întreagă', value: mii(totalNI),
        chg: anTrecut?.total_asigurati ? `${semn(pct(totalNI, anTrecut.total_asigurati))} față de ${luna(anTrecut)}` : undefined, dir: anTrecut?.total_asigurati && totalNI < anTrecut.total_asigurati ? 'down' : 'up' },
      { label: `Sub salariul minim (${subMinim.transa} lei)`, value: `${fmt1(subMinim.numar / totalNI * 100)}%`, hint: `${mii(subMinim.numar)} de persoane; ${mii(laMinim.numar)} sunt exact la minim.` },
      { label: 'Peste 10.000 lei brut', value: `${fmt1(peste10k / totalNI * 100)}%`, hint: `${mii(peste10k)}${peste10k >= 1e6 ? '' : ' de'} persoane` },
    ],
    footnote: `Tranșele cu o singură valoare (ex. 4.050) sunt pragurile salariului minim. Roșu = sub minim, galben = până la 5.000 lei. ${NOTA}`,
  }
}

function evolutieAsigurati(): Analysis {
  const v = P.map(p => p.total_asigurati)
  return {
    name: 'Câți salariați sunt',
    type: 'line',
    unit: 'salariați cu normă întreagă, pe lună',
    zoomY: true,
    plain: `În ${luna(ultim)} erau ${mii(totalNI)}${totalNI >= 1e6 ? '' : ' de'} salariați cu normă întreagă declarați la Casa de Pensii. ` +
      `Scăderile bruște (ex. ianuarie) vin din declarații depuse târziu de angajatori, care se completează în lunile următoare.`,
    labels: P.map(lunaScurt),
    labelsLong: P.map(luna),
    series: [{ name: 'Salariați cu normă întreagă', color: C, data: v }],
    labelCol: 'Luna',
    tableNewestFirst: true,
    kpis: [
      { label: luna(ultim), value: mii(totalNI) },
      { label: 'Cel mai mare număr', value: mii(Math.max(...v.map(x => x ?? 0))), hint: luna(P[v.indexOf(Math.max(...v.map(x => x ?? 0)))]) },
      { label: 'Cel mai mic număr', value: mii(Math.min(...v.map(x => x ?? Infinity))), hint: luna(P[v.indexOf(Math.min(...v.map(x => x ?? Infinity)))]) },
    ],
    footnote: NOTA,
  }
}

/* ── Județe ── */
const J = ultim.judete.slice().sort((a, b) => b.salariu_mediu - a.salariu_mediu)
const totJ = J.reduce((s, j) => ({ fond: s.fond + j.fond_salarii, asig: s.asig + j.asigurati, ang: s.ang + j.angajatori }), { fond: 0, asig: 0, ang: 0 })
const medNat = totJ.fond / totJ.asig

function salariuJudete(): Analysis {
  const sus = J[0], jos = J[J.length - 1]
  return {
    name: 'Salariul mediu pe județe',
    type: 'bar',
    unit: `lei brut pe lună, ${luna(ultim)}`,
    plain: `Cel mai mare salariu mediu e în ${numeJudet(sus.judet)} (${lei(sus.salariu_mediu)}), cel mai mic în ${numeJudet(jos.judet)} (${lei(jos.salariu_mediu)}) — ` +
      `de ${fmt1(sus.salariu_mediu / jos.salariu_mediu)} ori mai puțin. Media pe țară e ${lei(medNat)}. Doar ${J.filter(j => j.salariu_mediu > medNat).length} județe sunt peste medie.`,
    labels: J.map(j => numeJudet(j.judet)),
    series: [{ name: 'Salariu mediu brut', data: J.map(j => j.salariu_mediu), colors: J.map(j => (j.salariu_mediu >= medNat ? C : '#9aa3b8')) }],
    labelCol: 'Județ',
    extraCols: [{ name: 'Salariați', values: J.map(j => fmt0(j.asigurati)) }, { name: 'Angajatori', values: J.map(j => fmt0(j.angajatori)) }],
    kpis: [
      { label: 'Media pe țară', value: lei(medNat), hint: 'Fondul total de salarii împărțit la numărul de salariați.' },
      { label: `Cel mai mare: ${numeJudet(sus.judet)}`, value: lei(sus.salariu_mediu) },
      { label: `Cel mai mic: ${numeJudet(jos.judet)}`, value: lei(jos.salariu_mediu) },
    ],
    footnote: `Albastru = peste media pe țară. ${NOTA}`,
  }
}

function salariatiJudete(): Analysis {
  const s = ultim.judete.slice().sort((a, b) => b.asigurati - a.asigurati)
  const buc = s.find(j => j.judet.toUpperCase().startsWith('BUCUR'))!
  return {
    name: 'Câți salariați are fiecare județ',
    type: 'bar',
    unit: `salariați, ${luna(ultim)}`,
    plain: `București are ${mii(buc.asigurati)}${buc.asigurati >= 1e6 ? '' : ' de'} salariați — ${fmt0(buc.asigurati / totJ.asig * 100)}% din toți salariații din țară — și ${fmt0(buc.angajatori / totJ.ang * 100)}% din angajatori.`,
    labels: s.map(j => numeJudet(j.judet)),
    series: [{ name: 'Salariați', color: C, data: s.map(j => j.asigurati) }],
    labelCol: 'Județ',
    share: true,
    extraCols: [{ name: 'Angajatori', values: s.map(j => fmt0(j.angajatori)) }, { name: 'Salariu mediu', values: s.map(j => lei(j.salariu_mediu)) }],
    kpis: [
      { label: 'Salariați (toate județele)', value: mii(totJ.asig) },
      { label: 'Angajatori', value: mii(totJ.ang) },
      { label: 'Salariați pe angajator', value: fmt1(totJ.asig / totJ.ang), hint: 'Media; majoritatea firmelor au sub 10 angajați.' },
    ],
    footnote: NOTA,
  }
}

function judeteInTimp(): Analysis {
  const ultimele = P.slice(-12)
  const ord = J.map(j => j.cod)
  const val = (p: Perioada, cod: string) => p.judete.find(j => j.cod === cod)?.salariu_mediu ?? null
  const medii = ultimele.map(p => { const f = p.judete.reduce((s, j) => s + j.fond_salarii, 0), a = p.judete.reduce((s, j) => s + j.asigurati, 0); return Math.round(f / a) })
  const prim = ultimele[0]
  return {
    name: 'Salariul pe județe, lună de lună',
    type: 'table',
    unit: 'lei brut pe lună',
    plain: `Salariul mediu din fiecare județ în ultimele ${ultimele.length} luni. Media pe țară a ${pct(medii[medii.length - 1], medii[0]) >= 0 ? 'crescut' : 'scăzut'} de la ${lei(medii[0])} în ${luna(prim)} la ${lei(medii[medii.length - 1])} în ${luna(ultim)}.`,
    labels: ['Toată țara', ...J.map(j => numeJudet(j.judet))],
    series: ultimele.map((p, i) => ({ name: cap(lunaScurt(p)), data: [medii[i], ...ord.map(c => val(p, c))] })),
    labelCol: 'Județ',
    kpis: [
      { label: `Media pe țară, ${luna(ultim)}`, value: lei(medii[medii.length - 1]), chg: `${semn(pct(medii[medii.length - 1], medii[0]))} față de ${luna(prim)}`, dir: 'up' },
      { label: 'Cea mai mare creștere', value: (() => { const c = ord.map(k => [k, pct(val(ultim, k) ?? 0, val(prim, k) ?? 1)] as const).sort((a, b) => b[1] - a[1])[0]; return `${numeJudet(J.find(j => j.cod === c[0])!.judet)} ${semn(c[1])}` })() },
      { label: 'Perioada', value: `${ultimele.length} luni`, hint: `${luna(prim)} – ${luna(ultim)}` },
    ],
    footnote: NOTA,
  }
}

export const SURSE_CNPP: Source[] = [
  { key: 'salarii', label: '💰 Salarii pe tranșe', ...SURSA_CNPP, analyses: [transe(), evolutieAsigurati()] },
  { key: 'judete', label: '🗺️ Județe', ...SURSA_CNPP, analyses: [salariuJudete(), salariatiJudete(), judeteInTimp()] },
]
