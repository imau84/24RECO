import type { Analysis, Source, Topic } from '@/components/ModelA'
import imobData from '../../../public/imobiliare_data.json'
import { LUNI, LUNI_SCURT, fmt0, fmt1, pct, semn, cap, schimbare, type Punct } from '../industrii/agricultura/util'

/* Tranzacții imobiliare — statisticile lunare ANCPI (imobile vândute).
   public/imobiliare_data.json e actualizat de scripts/update_imobiliare.py (GitHub Actions, săptămânal);
   fiecare commit declanșează un build nou, deci textele de mai jos se recalculează automat. */

type Cat = 'extrav_agr' | 'extrav_neagr' | 'intrav_constr' | 'intrav_fara' | 'unitati_indiv'
type Rand = Record<Cat | 'total', number> & { uat?: string }
type Luni = Record<string, Record<string, Rand>>

const DATA = imobData as unknown as { RAW: Luni; RES: Luni; SECT: Luni }

const C_2025 = '#9aa3b8', C_2026 = '#3b82f6'

/** categoriile ANCPI, traduse pentru nespecialiști */
const CATEGORII: { k: Cat; nume: string; explic: string }[] = [
  { k: 'unitati_indiv', nume: 'Apartamente', explic: 'unități individuale din blocuri (apartamente, birouri, spații)' },
  { k: 'intrav_constr', nume: 'Case și clădiri', explic: 'terenuri în localitate, cu construcții pe ele — de obicei case' },
  { k: 'intrav_fara', nume: 'Terenuri de construit', explic: 'terenuri în localitate, fără construcții' },
  { k: 'extrav_agr', nume: 'Teren agricol', explic: 'terenuri agricole din afara localităților' },
  { k: 'extrav_neagr', nume: 'Alte terenuri', explic: 'terenuri din afara localităților care nu sunt agricole (pădure, curți-construcții etc.)' },
]

/** cheile din JSON (MAJUSCULE, uneori fără diacritice) → nume afișat */
const JUDET: Record<string, string> = {
  'ALBA': 'Alba', 'ARAD': 'Arad', 'ARGEȘ': 'Argeș', 'BACAU': 'Bacău', 'BIHOR': 'Bihor',
  'BISTRIȚA NĂSĂUD': 'Bistrița-Năsăud', 'BOTOȘANI': 'Botoșani', 'BRAȘOV': 'Brașov', 'BRĂILA': 'Brăila',
  'BUCUREȘTI': 'București', 'BUZĂU': 'Buzău', 'CARAȘ SEVERIN': 'Caraș-Severin', 'CLUJ': 'Cluj',
  'CONSTANȚA': 'Constanța', 'COVASNA': 'Covasna', 'CĂLĂRAȘI': 'Călărași', 'DAMBOVIȚA': 'Dâmbovița',
  'DOLJ': 'Dolj', 'GALAȚI': 'Galați', 'GIURGIU': 'Giurgiu', 'GORJ': 'Gorj', 'HARGHITA': 'Harghita',
  'HUNEDOARA': 'Hunedoara', 'IALOMIȚA': 'Ialomița', 'IASI': 'Iași', 'ILFOV': 'Ilfov',
  'MARAMUREȘ': 'Maramureș', 'MEHEDINȚI': 'Mehedinți', 'MUREȘ': 'Mureș', 'NEAMȚ': 'Neamț', 'OLT': 'Olt',
  'PRAHOVA': 'Prahova', 'SATU MARE': 'Satu Mare', 'SIBIU': 'Sibiu', 'SUCEAVA': 'Suceava', 'SĂLAJ': 'Sălaj',
  'TELEORMAN': 'Teleorman', 'TIMIȘ': 'Timiș', 'TULCEA': 'Tulcea', 'VASLUI': 'Vaslui', 'VRANCEA': 'Vrancea',
  'VÂLCEA': 'Vâlcea',
}
const numeJudet = (k: string) => JUDET[k] ?? cap(k.toLowerCase())

const NOTA = 'ANCPI numără imobilele vândute (contracte de vânzare înscrise în cartea funciară), nu prețuri. „Apartamente” = unități individuale (pot include și birouri sau spații comerciale din clădiri). Site-ul ANCPI este indisponibil din august 2026, după incidentul informatic; lunile noi vor fi adăugate automat când statisticile vor fi publicate din nou.'

/* ── Ajutoare ── */
const parseCheie = (k: string): Punct => { const [a, l] = k.split('_').map(Number); return { an: a, luna: l - 1 } }
const numeL = (k: string) => { const p = parseCheie(k); return `${LUNI[p.luna]} ${p.an}` }
const etL = (k: string) => { const p = parseCheie(k); return `${LUNI_SCURT[p.luna]} ${String(p.an).slice(2)}` }
const cheieAnTrecut = (k: string) => { const p = parseCheie(k); return `${p.an - 1}_${String(p.luna + 1).padStart(2, '0')}` }
const sumaLuna = (luna: Record<string, Rand>, c: Cat | 'total' = 'total') =>
  Object.values(luna).reduce((s, r) => s + r[c], 0)
const sageata = (p: number) => (p > 0 ? '▲' : p < 0 ? '▼' : '=')
/** „20 de imobile”, dar „15 imobile” / „1.615 imobile” (regula lui „de” după numerale) */
const de = (v: number) => { const r = Math.round(v) % 100; return v >= 20 && (r === 0 || r >= 20) ? 'de ' : '' }
const dir = (p: number) => (p > 0 ? 'up' as const : 'down' as const)
/** „de 2,4 ori” / „1 din 5” — o pondere spusă pe înțeles */
const dinZece = (p: number) => {
  const r = Math.round(p / 10)
  return r >= 1 ? `cam ${r} din 10` : 'sub 1 din 10'
}

/** cumul de la începutul anului, comparat cu aceleași luni din anul precedent */
function cumulAn(d: Luni, chei: string[], ultima: string, k?: string) {
  const an = parseCheie(ultima).an
  const acum = chei.filter(c => c.startsWith(`${an}_`))
  const inainte = acum.map(cheieAnTrecut).filter(c => d[c])
  if (inainte.length !== acum.length) return null
  const val = (cs: string[]) => cs.reduce((s, c) => s + (k ? (d[c][k]?.total ?? 0) : sumaLuna(d[c])), 0)
  return { an, luni: acum.length, acum: val(acum), inainte: val(inainte) }
}

/* ── Analize comune (folosite pentru țară, orașe, sectoare) ── */
type Ctx = {
  d: Luni
  chei: string[]
  ultima: string
  /** cum se numește o unitate: „județ”, „oraș”, „sector” */
  unit: { sg: string; pl: string; plArt: string }
  nume: (k: string, r: Rand) => string
}

function ctx(d: Luni, unit: Ctx['unit'], nume: Ctx['nume']): Ctx {
  const chei = Object.keys(d).sort()
  return { d, chei, ultima: chei[chei.length - 1], unit, nume }
}

function analizaEvolutie(c: Ctx, cine: string): Analysis {
  const { d, chei, ultima } = c
  const tot = chei.map(k => sumaLuna(d[k]))
  const v = tot[tot.length - 1]
  const kt = cheieAnTrecut(ultima)
  const vt = d[kt] ? sumaLuna(d[kt]) : null
  const pAn = vt ? pct(v, vt) : null
  const iMax = tot.indexOf(Math.max(...tot)), iMin = tot.indexOf(Math.min(...tot))
  const cum = cumulAn(d, chei, ultima)
  const pCum = cum ? pct(cum.acum, cum.inainte) : null
  return {
    name: 'Evoluție lunară',
    type: 'line',
    unit: 'imobile vândute pe lună',
    plain: `În ${numeL(ultima)} s-au vândut ${fmt0(v)} ${de(v)}imobile ${cine}${vt != null ? ` — numărul ${schimbare(v, vt)} față de ${numeL(kt)}` : ''}. ` +
      `Cele mai multe vânzări au fost în ${numeL(chei[iMax])} (${fmt0(tot[iMax])}), cele mai puține în ${numeL(chei[iMin])} (${fmt0(tot[iMin])}) — ianuarie e mereu o lună slabă, după sărbători.`,
    labels: chei.map(etL), labelsLong: chei.map(k => cap(numeL(k))),
    series: [{ name: 'Imobile vândute', color: C_2026, data: tot }],
    labelCol: 'Luna',
    tableNewestFirst: true,
    kpis: [
      { label: `Ultima lună (${numeL(ultima)})`, value: fmt0(v),
        ...(pAn != null ? { chg: `${sageata(pAn)} ${semn(pAn)} față de ${numeL(kt)}`, dir: dir(pAn) } : {}),
        hint: 'Comparăm cu aceeași lună de anul trecut, ca să scoatem efectul sezonului.' },
      cum && pCum != null
        ? { label: `Total ${cum.an} (${cum.luni} luni)`, value: fmt0(cum.acum),
            chg: `${sageata(pCum)} ${semn(pCum)} față de aceleași luni din ${cum.an - 1}`, dir: dir(pCum),
            hint: `În ${cum.an - 1}, în aceleași luni: ${fmt0(cum.inainte)}.` }
        : { label: `Total pe ${chei.length} luni`, value: fmt0(tot.reduce((a, b) => a + b, 0)), hint: 'Toate lunile disponibile.' },
      { label: 'Luna record', value: cap(numeL(chei[iMax])), chg: `${fmt0(tot[iMax])} imobile`, dir: 'up',
        hint: `Cea mai slabă: ${numeL(chei[iMin])}, cu ${fmt0(tot[iMin])}.` },
    ],
    footnote: NOTA,
  }
}

function analizaAni(c: Ctx): Analysis | null {
  const { d, chei, ultima } = c
  const an = parseCheie(ultima).an
  const ani = [an - 1, an]
  const luni = LUNI_SCURT.map((_, i) => String(i + 1).padStart(2, '0'))
  const serie = (a: number) => luni.map(l => (d[`${a}_${l}`] ? sumaLuna(d[`${a}_${l}`]) : null))
  const [s0, s1] = ani.map(serie)
  if (s0.every(v => v == null)) return null
  const cum = cumulAn(d, chei, ultima)
  const pCum = cum ? pct(cum.acum, cum.inainte) : null
  const comune = luni.map((_, i) => (s0[i] != null && s1[i] != null ? i : -1)).filter(i => i >= 0)
  const mai = comune.filter(i => s1[i]! > s0[i]!).length
  return {
    name: `${an} vs. ${an - 1}`,
    type: 'bar',
    unit: 'imobile vândute pe lună',
    plain: `Barele gri sunt ${an - 1}, cele albastre ${an}. ` +
      (pCum != null && cum
        ? `În primele ${cum.luni} luni din ${an} s-au vândut ${fmt0(cum.acum)} ${de(cum.acum)}imobile, ${pCum < 0 ? 'cu ' + fmt1(Math.abs(pCum)) + '% mai puține' : 'cu ' + fmt1(pCum) + '% mai multe'} decât în aceeași perioadă din ${an - 1}. `
        : '') +
      `${mai} din ${comune.length} luni comparabile ${mai === 1 ? 'a fost mai bună' : 'au fost mai bune'} în ${an}.`,
    labels: LUNI_SCURT.map(cap), labelsLong: LUNI.map(cap),
    series: [
      { name: String(an - 1), color: C_2025, data: s0 },
      { name: String(an), color: C_2026, data: s1 },
    ],
    labelCol: 'Luna',
    kpis: [
      ...(cum && pCum != null ? [
        { label: `${an} (${cum.luni} luni)`, value: fmt0(cum.acum), chg: `${sageata(pCum)} ${semn(pCum)}`, dir: dir(pCum),
          hint: `Comparat cu aceleași ${cum.luni} luni din ${an - 1}.` },
        { label: `${an - 1} (aceleași luni)`, value: fmt0(cum.inainte), hint: `Anul ${an - 1} întreg: ${fmt0(s0.reduce<number>((a, b) => a + (b ?? 0), 0))}.` },
      ] : []),
      { label: `Luni mai bune în ${an}`, value: `${mai} din ${comune.length}`, hint: 'Lunile în care s-a vândut mai mult decât cu un an înainte.' },
    ],
    footnote: NOTA,
  }
}

function analizaTop(c: Ctx, top = 12): Analysis {
  const { d, ultima, unit, nume } = c
  const luna = d[ultima]
  const total = sumaLuna(luna)
  const rows = Object.entries(luna).sort((a, b) => b[1].total - a[1].total)
  const sel = rows.slice(0, top)
  const [k1, r1] = rows[0]
  const p1 = r1.total / total * 100
  const top3 = rows.slice(0, 3).reduce((s, [, r]) => s + r.total, 0) / total * 100
  return {
    name: `Top ${unit.pl}`,
    type: 'bar',
    unit: `imobile vândute, ${numeL(ultima)}`,
    plain: `${nume(k1, r1)} e pe primul loc, cu ${fmt0(r1.total)} ${de(r1.total)}imobile vândute în ${numeL(ultima)} — ${fmt1(p1)}% din total. ` +
      `Primele 3 ${unit.pl} adună ${dinZece(top3)} vânzări.`,
    labels: sel.map(([k, r]) => nume(k, r)),
    series: [{ name: 'Imobile vândute', data: sel.map(([, r]) => r.total) }],
    labelCol: cap(unit.sg),
    kpis: [
      { label: `Total ${numeL(ultima)}`, value: fmt0(total), hint: `Suma tuturor celor ${rows.length} ${de(rows.length)}${unit.pl}.` },
      { label: `Primul loc`, value: nume(k1, r1), chg: `${fmt0(r1.total)} imobile`, dir: 'up' },
      { label: 'Primele 3', value: `${fmt0(top3)}%`, hint: 'Cât din toate vânzările se fac în primele trei.' },
    ],
    footnote: rows.length > top ? `Graficul arată primele ${top} ${unit.pl}. Restul sunt în tabul „Toate ${unit.plArt}”.` : undefined,
  }
}

function analizaTabel(c: Ctx): Analysis {
  const { d, chei, ultima, unit, nume } = c
  const kt = cheieAnTrecut(ultima)
  const rows = Object.entries(d[ultima]).sort((a, b) => b[1].total - a[1].total)
  const cum = cumulAn(d, chei, ultima)
  const delta = rows.map(([k, r]) => {
    const t = d[kt]?.[k]?.total
    return t ? pct(r.total, t) : null
  })
  const cuDate = rows.map((r, i) => ({ n: c.nume(r[0], r[1]), p: delta[i] })).filter(x => x.p != null) as { n: string; p: number }[]
  const crescut = cuDate.filter(x => x.p > 0).length
  const best = cuDate.reduce((a, b) => (b.p > a.p ? b : a), cuDate[0])
  const worst = cuDate.reduce((a, b) => (b.p < a.p ? b : a), cuDate[0])
  const cumK = cum ? rows.map(([k]) => cumulAn(d, chei, ultima, k)) : null
  return {
    name: `Toate ${unit.plArt}`,
    type: 'table',
    unit: `imobile vândute`,
    plain: cuDate.length
      ? `Față de ${numeL(kt)}, vânzările au crescut în ${crescut} din ${cuDate.length} ${de(cuDate.length)}${unit.pl}. Cea mai mare creștere: ${best.n} (${semn(best.p)}); cea mai mare scădere: ${worst.n} (${semn(worst.p)}).`
      : `Câte imobile s-au vândut în ${numeL(ultima)}, în fiecare ${unit.sg}.`,
    labels: rows.map(([k, r]) => nume(k, r)),
    series: [
      { name: cap(numeL(ultima)), data: rows.map(([, r]) => r.total) },
      ...(d[kt] ? [{ name: cap(numeL(kt)), data: rows.map(([k]) => d[kt][k]?.total ?? null) }] : []),
      ...(cumK && cum ? [{ name: `Total ${cum.an} (${cum.luni} luni)`, data: cumK.map(x => x?.acum ?? null) }] : []),
    ],
    extraCols: [
      ...(d[kt] ? [{ name: 'Față de anul trecut', values: delta.map(p => (p == null ? '—' : `${sageata(p)} ${semn(p)}`)) }] : []),
      { name: 'Apartamente', values: rows.map(([, r]) => `${fmt0(r.total ? r.unitati_indiv / r.total * 100 : 0)}%`) },
    ],
    labelCol: cap(unit.sg),
    kpis: [
      { label: `${cap(unit.pl)} în creștere`, value: `${crescut} din ${cuDate.length}`, hint: `Comparat cu ${numeL(kt)}.` },
      ...(best ? [{ label: 'Cea mai mare creștere', value: best.n, chg: `▲ ${semn(best.p)}`, dir: 'up' as const }] : []),
      ...(worst ? [{ label: 'Cea mai mare scădere', value: worst.n, chg: `▼ ${semn(worst.p)}`, dir: 'down' as const }] : []),
    ],
    footnote: 'Coloana „Apartamente” arată ce parte din vânzări sunt apartamente (unități individuale). ' + NOTA,
  }
}

function analizaCe(c: Ctx, unde: string): Analysis {
  const { d, ultima } = c
  const luna = d[ultima]
  const total = sumaLuna(luna)
  const cats = CATEGORII.map(x => ({ ...x, v: sumaLuna(luna, x.k) })).filter(x => x.v > 0)
  const ord = [...cats].sort((a, b) => b.v - a.v)
  const [a, b] = ord
  const kt = cheieAnTrecut(ultima)
  const apT = d[kt] ? sumaLuna(d[kt], 'unitati_indiv') : null
  const ap = sumaLuna(luna, 'unitati_indiv')
  const pAp = apT ? pct(ap, apT) : null
  return {
    name: 'Ce se vinde',
    type: 'pie',
    unit: `imobile vândute, ${numeL(ultima)}`,
    plain: `${unde} cel mai des se vând ${a.nume.toLowerCase()} (${fmt1(a.v / total * 100)}%), urmate de ${b.nume.toLowerCase()} (${fmt1(b.v / total * 100)}%). ` +
      `${cap(a.nume)} = ${a.explic}.`,
    labels: cats.map(x => x.nume),
    labelsLong: cats.map(x => `${x.nume} — ${x.explic}`),
    series: [{ name: 'Imobile vândute', data: cats.map(x => x.v) }],
    labelCol: 'Ce s-a vândut',
    share: true,
    kpis: [
      { label: 'Cel mai vândut', value: a.nume, chg: `${fmt0(a.v)} · ${fmt1(a.v / total * 100)}%`, dir: 'up', hint: cap(a.explic) + '.' },
      { label: 'Apartamente', value: fmt0(ap),
        ...(pAp != null ? { chg: `${sageata(pAp)} ${semn(pAp)} față de ${numeL(kt)}`, dir: dir(pAp) } : {}),
        hint: `${fmt1(ap / total * 100)}% din toate vânzările.` },
      { label: 'Terenuri (toate tipurile)', value: fmt0(total - ap),
        hint: 'Case cu teren, terenuri de construit și terenuri agricole la un loc.' },
    ],
    footnote: NOTA,
  }
}

/* ── Tab-ul ANCPI: Toată țara / Orașe mari / București → analize ── */
const sursa = (key: string, label: string, c: Ctx, analyses: (Analysis | null)[], extraChip?: string): Source => ({
  key, label, credit: 'ANCPI', link: 'ancpi.ro', url: 'https://www.ancpi.ro', freq: 'lunar',
  chips: [`● Ultimele date: ${numeL(c.ultima)}`, '🔁 lunar', `📅 din ${numeL(c.chei[0])}`, ...(extraChip ? [extraChip] : [])],
  analyses: analyses.filter((a): a is Analysis => a != null),
})

export function ancpiTopic(): Topic {
  const tara = ctx(DATA.RAW, { sg: 'județ', pl: 'județe', plArt: 'județele' }, k => numeJudet(k))
  const orase = ctx(DATA.RES, { sg: 'oraș', pl: 'orașe', plArt: 'orașele' }, (k, r) => r.uat || numeJudet(k))
  const buc = ctx(DATA.SECT, { sg: 'sector', pl: 'sectoare', plArt: 'sectoarele' }, k => k.replace('București ', ''))
  return {
    key: 'ancpi', label: 'ANCPI', icon: '🔑',
    sources: [
      sursa('tara', '🗺️ Toată țara', tara, [analizaEvolutie(tara, 'în România'), analizaAni(tara), analizaCe(tara, 'În România,'), analizaTop(tara), analizaTabel(tara)]),
      sursa('orase', '🏙️ Orașe mari', orase, [analizaEvolutie(orase, 'în orașele reședință de județ'), analizaCe(orase, 'În orașele mari,'), analizaTop(orase), analizaTabel(orase)]),
      sursa('bucuresti', '🏛️ București pe sectoare', buc, [analizaTop(buc), analizaEvolutie(buc, 'în București'), analizaCe(buc, 'În București,')], '⚠ nu se mai actualizează automat'),
    ],
  }
}
