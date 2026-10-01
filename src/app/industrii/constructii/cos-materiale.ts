import type { Analysis, Kpi, Topic } from '@/components/ModelA'
import cosData from '@/data/constructii/cos_dedeman_data.json'
import { LUNI, fmt0, fmt1, fmt2, pct, semn, cap, numeLuna, eticheta, parsePerioada } from '../agricultura/util'

/* Coșul de materiale de construcții — indice propriu 24reco, din prețurile de raft dedeman.ro,
   colectate în ziua 1 a fiecărei luni (scripts/fetch_cos_dedeman.py).
   Indice de grupă = lanț lunar al mediei geometrice a raporturilor de preț (Jevons);
   indice general = media ponderată a grupelor. Prima observație = 100.
   Analizele se adaptează singure: cu o singură lună arată prețurile de bază, de la a doua
   lună apar automat indicele, scumpirile și evoluția pe grupe. */

type Pret = { pret: number; pret_unitar?: number; unitate?: string; unitate_pachet?: string; promo?: boolean; pret_vechi?: number }
type Obs = { luna: string; data: string; produse: Record<string, Pret>; erori?: string[] }
type Grupa = { key: string; nume: string; pondere: number }
type Produs = { cod: string; grupa: string; nume: string; url: string }
type CosData = { meta: { url: string; metoda: string }; grupe: Grupa[]; cos: Produs[]; observatii: Obs[] }

const GRUPA_COLOR: Record<string, string> = {
  ciment: '#5a6178', zidarie: '#e5544b', termo: '#3b82f6', otel: '#7c5ce6', adezivi: '#e0a020', gips: '#12a5b8',
}
const C_GEN = '#e0a020', C_FARA = '#9aa3b8', C_UP = '#e5544b', C_DOWN = '#22b07d' // aici scumpire = roșu
const MAX_IMPUTARE = 2 // luni în care un produs lipsă își păstrează ultimul preț

/* ── Date ── */
const { meta, grupe, cos, observatii } = cosData as unknown as CosData
const n = observatii.length
const luni = observatii.map(o => parsePerioada(o.luna))
const ultimaLuna = luni[n - 1]
const indexLuna = (p: { an: number; luna: number }) => p.an * 12 + p.luna
const urmatoarea = (() => { const i = indexLuna(ultimaLuna) + 1; return `1 ${LUNI[i % 12]} ${Math.floor(i / 12)}` })()
const dataObs = (o: Obs) => { const [a, l, z] = o.data.split('-').map(Number); return `${z} ${LUNI[l - 1]} ${a}` }
const ultima = observatii[n - 1]

/** prețul valid al unui produs în luna t: observat sau, dacă lipsește, ultimul preț din ultimele 2 luni */
const efectiv = (t: number, cod: string): Pret | null => {
  for (let k = t; k >= 0 && indexLuna(luni[t]) - indexLuna(luni[k]) <= MAX_IMPUTARE; k--) {
    const p = observatii[k].produse[cod]
    if (p) return p
  }
  return null
}

/** raportul de preț b/a pe aceeași bază: prețul pe unitate dacă ambele îl au în aceeași unitate, altfel prețul de raft */
const raport = (a: Pret, b: Pret, faraPromo: boolean) => {
  const reg = (p: Pret) => (faraPromo && p.promo && p.pret_vechi ? p.pret_vechi / p.pret : 1)
  const unitar = a.pret_unitar && b.pret_unitar && a.unitate === b.unitate
  const va = (unitar ? a.pret_unitar! : a.pret) * reg(a)
  const vb = (unitar ? b.pret_unitar! : b.pret) * reg(b)
  return vb / va
}

/** indicii lunari pe grupe (lanț Jevons), bază = prima lună = 100 */
function indiciGrupe(faraPromo: boolean): Record<string, number[]> {
  const out: Record<string, number[]> = {}
  for (const g of grupe) {
    const prod = cos.filter(p => p.grupa === g.key)
    const serie = [100]
    for (let t = 1; t < n; t++) {
      const r = prod.map(p => { const a = efectiv(t - 1, p.cod), b = efectiv(t, p.cod); return a && b ? raport(a, b, faraPromo) : null })
        .filter((x): x is number => x != null)
      const geo = r.length ? Math.exp(r.reduce((s, x) => s + Math.log(x), 0) / r.length) : 1
      serie.push(serie[t - 1] * geo)
    }
    out[g.key] = serie
  }
  return out
}
const general = (ig: Record<string, number[]>) => observatii.map((_, t) => {
  const w = grupe.reduce((s, g) => s + g.pondere, 0)
  return grupe.reduce((s, g) => s + g.pondere * ig[g.key][t], 0) / w
})

const ig = indiciGrupe(false), igFara = indiciGrupe(true)
const gen = general(ig), genFara = general(igFara)
const r1 = (v: number) => Math.round(v * 10) / 10
const labels = luni.map(eticheta)
const labelsLong = luni.map(p => cap(numeLuna(p)))
const sageata = (p: number, fata: string): Pick<Kpi, 'chg' | 'dir'> =>
  Math.abs(p) < 0.05 ? { chg: `= neschimbat față de ${fata}` } : { chg: `${p > 0 ? '▲' : '▼'} ${semn(p)} față de ${fata}`, dir: p > 0 ? 'down' : 'up' } // scumpirea e o veste proastă
const grupeVerb = (k: number, v: string) => (k === 0 ? `nicio grupă nu s-a ${v}` : k === 1 ? `o grupă s-a ${v}` : `${k} grupe s-au ${v}`)
const verb = (p: number) => (Math.abs(p) < 0.5 ? 'au rămas cam la fel' : p > 0 ? `s-au scumpit cu ${fmt1(p)}%` : `s-au ieftinit cu ${fmt1(-p)}%`)

/* ── Prețuri pe unitate, pentru afișare ── */
const UNIT: Record<string, string> = { m2: 'mp', m3: 'mc', 'bucată': 'buc.', 'rolă': 'rolă' }
const kgDinNume = (nume: string) => { const m = nume.match(/(\d+(?:[.,]\d+)?)\s*kg/i); return m ? Number(m[1].replace(',', '.')) : null }
const leiPeKg = (pr: Produs, p: Pret) => (p.unitate === 'kg' && p.pret_unitar ? p.pret_unitar : kgDinNume(pr.nume) ? p.pret / kgDinNume(pr.nume)! : null)
const textUnitar = (pr: Produs, p: Pret) => {
  if (p.pret_unitar && p.unitate) return `${fmt2(p.pret_unitar)} lei/${UNIT[p.unitate] ?? p.unitate}`
  const kg = leiPeKg(pr, p)
  if (kg) return `≈ ${fmt2(kg)} lei/kg`
  return p.unitate_pachet ? `lei/${UNIT[p.unitate_pachet] ?? p.unitate_pachet}` : '—'
}
const mediana = (v: number[]) => { const s = [...v].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2 }

const numeGrupa = (k: string) => grupe.find(g => g.key === k)!.nume
const promotii = cos.filter(p => ultima.produse[p.cod]?.promo)
const notaMetoda = `Indice propriu 24reco: prețul de raft al ${cos.length} de materiale de construcții de pe dedeman.ro, notat în ziua 1 a fiecărei luni (prima colectare: ${dataObs(observatii[0])} = 100). Folosim prețul pe unitate (lei/kg, lei/mp), ca să nu ne păcălească sacii mai mici. Indicele unei grupe e media geometrică a variațiilor de preț; indicele general e media ponderată a grupelor. Un produs lipsă își păstrează ultimul preț cel mult ${MAX_IMPUTARE} luni.`

/* 1 — Indice general (de la a doua lună) */
function analizaGeneral(): Analysis {
  const pLuna = pct(gen[n - 1], gen[n - 2])
  const pBaza = gen[n - 1] - 100
  const iAn = luni.findIndex(p => indexLuna(p) === indexLuna(ultimaLuna) - 12)
  const pAn = iAn >= 0 ? pct(gen[n - 1], gen[iAn]) : null
  return {
    name: 'Indicele coșului',
    type: 'line',
    unit: `indice, ${eticheta(luni[0])} = 100`,
    plain: `Cu 100 de lei cheltuiți pe materiale în ${numeLuna(luni[0])} cumperi acum aceleași lucruri cu aproximativ ${fmt1(gen[n - 1])} lei. Față de luna trecută, materialele ${verb(pLuna)}${pAn != null ? `, iar față de acum un an ${verb(pAn)}` : ''}. Linia gri arată prețurile fără reducerile de moment (promoții).`,
    labels, labelsLong,
    series: [
      { name: 'Cu promoții (preț plătit)', color: C_GEN, data: gen.map(r1) },
      { name: 'Fără promoții', color: C_FARA, data: genFara.map(r1) },
    ],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Indicele acum (${numeLuna(ultimaLuna)})`, value: fmt1(gen[n - 1]), ...sageata(pLuna, 'luna trecută'),
        hint: `100 lei de materiale din ${numeLuna(luni[0])} costă acum ≈ ${fmt1(gen[n - 1])} lei.` },
      pAn != null
        ? { label: 'Față de acum un an', value: semn(pAn), ...sageata(pAn, numeLuna(luni[iAn])) }
        : { label: `De la început (${numeLuna(luni[0])})`, value: semn(pBaza), ...sageata(pBaza, numeLuna(luni[0])) },
      { label: 'Fără promoții', value: fmt1(genFara[n - 1]), chg: `${semn(pct(genFara[n - 1], genFara[n - 2]))} față de luna trecută`,
        hint: 'Prețurile întregi, ca și cum n-ar exista reduceri.' },
    ],
    footnote: notaMetoda,
  }
}

/* 2 — Scumpiri pe grupe, luna aceasta (de la a doua lună) */
function analizaLuna(): Analysis {
  const v = grupe.map(g => pct(ig[g.key][n - 1], ig[g.key][n - 2]))
  const ord = grupe.map((g, i) => ({ g, v: v[i] })).sort((a, b) => b.v - a.v)
  const sus = ord[0], jos = ord[ord.length - 1]
  const scumpite = v.filter(x => x > 0.05).length, ieftinite = v.filter(x => x < -0.05).length
  return {
    name: 'Luna aceasta, pe grupe',
    type: 'bar',
    unit: `% față de ${numeLuna(luni[n - 2])}`,
    plain: `Între ${dataObs(observatii[n - 2])} și ${dataObs(ultima)}: ${grupeVerb(scumpite, 'scumpit')}, ${grupeVerb(ieftinite, 'ieftinit')}. ${sus.v > 0.05 ? `Cea mai mare scumpire: ${sus.g.nume.toLowerCase()} (${semn(sus.v)}).` : ''} ${jos.v < -0.05 ? `Cea mai mare ieftinire: ${jos.g.nume.toLowerCase()} (${semn(jos.v)}).` : ''} Roșu = mai scump, verde = mai ieftin.`,
    labels: grupe.map(g => g.nume),
    series: [{ name: 'Variație lunară', data: v.map(r1), colors: v.map(x => (x > 0 ? C_UP : C_DOWN)) }],
    labelCol: 'Grupa',
    valueSuffix: '%',
    kpis: [
      { label: 'Cea mai mare scumpire', value: sus.v > 0.05 ? sus.g.nume : '—', chg: sus.v > 0.05 ? semn(sus.v) : 'nicio grupă', dir: sus.v > 0.05 ? 'down' : undefined },
      { label: 'Cea mai mare ieftinire', value: jos.v < -0.05 ? jos.g.nume : '—', chg: jos.v < -0.05 ? semn(jos.v) : 'nicio grupă', dir: jos.v < -0.05 ? 'up' : undefined },
      { label: 'Grupe scumpite / ieftinite', value: `${scumpite} / ${ieftinite}`, chg: `din ${grupe.length} grupe` },
    ],
    footnote: notaMetoda,
  }
}

/* 3 — Evoluție pe grupe (de la a doua lună) */
function analizaEvolutieGrupe(): Analysis {
  const ord = grupe.map(g => ({ g, v: ig[g.key][n - 1] })).sort((a, b) => b.v - a.v)
  return {
    name: 'Evoluție pe grupe',
    type: 'line',
    unit: `indice, ${eticheta(luni[0])} = 100`,
    plain: `Fiecare linie e o grupă de materiale, toate pornind de la 100 în ${numeLuna(luni[0])}. De atunci, cel mai mult s-au scumpit ${ord[0].g.nume.toLowerCase()} (${fmt1(ord[0].v)}), iar cel mai puțin ${ord[ord.length - 1].g.nume.toLowerCase()} (${fmt1(ord[ord.length - 1].v)}). Peste 100 = mai scump decât la început.`,
    labels, labelsLong,
    series: grupe.map(g => ({ name: g.nume, color: GRUPA_COLOR[g.key], data: ig[g.key].map(r1) })),
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: 'Cel mai scumpit', value: ord[0].g.nume, chg: `indice ${fmt1(ord[0].v)}`, dir: ord[0].v > 100 ? 'down' : undefined },
      { label: 'Cel mai puțin scumpit', value: ord[ord.length - 1].g.nume, chg: `indice ${fmt1(ord[ord.length - 1].v)}` },
      { label: 'Diferența între grupe', value: `${fmt1(ord[0].v - ord[ord.length - 1].v)} puncte`, hint: 'Cât de diferit s-au mișcat prețurile între grupe.' },
    ],
    footnote: notaMetoda,
  }
}

/* 4 — Prețurile de azi (mereu) */
function analizaPreturi(): Analysis {
  const lista = grupe.flatMap(g => cos.filter(p => p.grupa === g.key)).filter(p => ultima.produse[p.cod])
  const cimentKg = lista.filter(p => p.grupa === 'ciment').map(p => leiPeKg(p, ultima.produse[p.cod])).filter((x): x is number => x != null)
  const kgC = cimentKg.length ? mediana(cimentKg) : null
  const prec = n > 1 ? observatii[n - 2] : null
  const varLuna = (p: Produs) => {
    const a = prec?.produse[p.cod], b = ultima.produse[p.cod]
    return a && b ? semn(pct(b.pret, a.pret)) : '—'
  }
  return {
    name: n > 1 ? 'Prețurile de azi' : `Prețurile de azi (${dataObs(ultima)})`,
    type: 'table',
    unit: `lei, preț de raft pe ${dataObs(ultima)}`,
    plain: `${n > 1 ? `Pe ${dataObs(ultima)}` : `Astăzi, ${dataObs(ultima)},`} am notat prețul de raft al ${lista.length} de materiale de construcții de bază.${kgC ? ` De exemplu, cimentul costă în jur de ${fmt2(kgC)} lei pe kilogram — adică ≈ ${fmt0(kgC * 40)} lei un sac de 40 kg.` : ''} ${n > 1 ? `Ultima coloană arată cât s-a schimbat prețul față de ${dataObs(prec!)}.` : `Acestea sunt prețurile de pornire. Pe ${urmatoarea} pagina se actualizează singură și arată cât s-au scumpit sau ieftinit materialele.`}`,
    labels: lista.map(p => p.nume),
    labelsLong: lista.map(p => (ultima.produse[p.cod].promo ? `${p.nume} 🏷️ promoție` : p.nume)),
    series: [{ name: 'Preț raft (lei)', data: lista.map(p => ultima.produse[p.cod].pret) }],
    labelCol: 'Produs',
    extraCols: [
      { name: 'Pe unitate', values: lista.map(p => textUnitar(p, ultima.produse[p.cod])) },
      { name: 'Grupa', values: lista.map(p => numeGrupa(p.grupa)) },
      ...(prec ? [{ name: 'Față de luna trecută', values: lista.map(varLuna) }] : []),
    ],
    kpis: [
      { label: 'Produse urmărite', value: String(lista.length), chg: `în ${grupe.length} grupe`, hint: 'Ciment, zidărie, termoizolație, armături, adezivi, gips-carton.' },
      { label: 'Data colectării', value: dataObs(ultima), chg: `următoarea: ${urmatoarea}`, hint: 'Prețurile se notează în ziua 1 a fiecărei luni.' },
      { label: 'Produse în promoție', value: String(promotii.length), chg: promotii.length ? promotii.map(p => numeGrupa(p.grupa)).join(', ') : 'niciunul',
        hint: 'Promoțiile sunt marcate cu 🏷️; indicele se calculează și fără ele.' },
    ],
    footnote: `Prețuri publice de pe dedeman.ro, la data colectării; pot diferi între magazine. ${notaMetoda}`,
  }
}

/* 5 — Ce conține coșul (mereu) */
function analizaComponenta(): Analysis {
  const nr = (k: string) => cos.filter(p => p.grupa === k).length
  const top = [...grupe].sort((a, b) => b.pondere - a.pondere)
  return {
    name: 'Ce conține coșul',
    type: 'pie',
    unit: 'pondere în indicele general',
    plain: `Coșul e împărțit în ${grupe.length} grupe de materiale folosite la orice casă: de la fundație (ciment, armături) la pereți, izolație și finisaje. Fiecare grupă are o pondere fixă, după cât cântărește de obicei în costul materialelor. Cele mai importante: ${top[0].nume.toLowerCase()} (${top[0].pondere}%) și ${top[1].nume.toLowerCase()} (${top[1].pondere}%).`,
    labels: grupe.map(g => g.nume),
    series: [{ name: 'Pondere', data: grupe.map(g => g.pondere) }],
    labelCol: 'Grupa',
    valueSuffix: '%',
    extraCols: [{ name: 'Produse', values: grupe.map(g => String(nr(g.key))) }],
    kpis: [
      { label: 'Grupe', value: String(grupe.length), chg: `${cos.length} de produse` },
      { label: 'Cea mai mare pondere', value: top[0].nume, chg: `${top[0].pondere}% din indice` },
      { label: 'Metoda', value: 'Medie geometrică', chg: 'ponderi fixe, publice', hint: 'Standardul folosit la indicii oficiali de preț.' },
    ],
    footnote: notaMetoda,
  }
}

/* 6 — Indicele pe grupe la pornire (doar în prima lună) */
function analizaBaza(): Analysis {
  return {
    name: 'Indice pe grupe',
    type: 'bar',
    unit: `indice, ${eticheta(luni[0])} = 100`,
    plain: `Toate grupele pornesc de la 100 pe ${dataObs(observatii[0])}. Pe ${urmatoarea} vezi aici primele scumpiri și ieftiniri: 105 ar însemna că materialele din grupă s-au scumpit cu 5%, 97 că s-au ieftinit cu 3%.`,
    labels: grupe.map(g => g.nume),
    series: [{ name: 'Indice', data: grupe.map(g => r1(ig[g.key][n - 1])), colors: grupe.map(g => GRUPA_COLOR[g.key]) }],
    labelCol: 'Grupa',
    kpis: [
      { label: 'Indice general', value: fmt1(gen[n - 1]), chg: 'luna de bază' },
      { label: 'Prima variație', value: cap(urmatoarea), chg: 'actualizare automată' },
      { label: 'Frecvență', value: 'Lunar', chg: 'ziua 1 a lunii' },
    ],
    footnote: notaMetoda,
  }
}

export function cosMaterialeTopic(): Topic {
  const analyses = n > 1
    ? [analizaGeneral(), analizaLuna(), analizaEvolutieGrupe(), analizaPreturi(), analizaComponenta()]
    : [analizaPreturi(), analizaComponenta(), analizaBaza()]
  return {
    key: 'cos-materiale', label: 'Prețuri materiale', icon: '🧱',
    sources: [{
      key: 'DEDEMAN', tag: 'indice 24reco', label: 'Coșul 24reco · Dedeman', link: 'dedeman.ro', url: meta.url, freq: 'lunar (ziua 1)',
      chips: [`● Actualizat: ${dataObs(ultima)}`, '🔁 lunar, pe 1', `🧱 ${cos.length} de produse`],
      analyses,
    }],
  }
}
