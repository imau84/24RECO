import type { Analysis, Topic } from '@/components/ModelA'
import lapteData from '@/data/agricultura/lapte_data.json'
import { LUNI, LUNI_SCURT, fmt0, fmt1, fmt2, pct, semn, cap, numeLuna, parsePerioada } from './util'

/* Lapte crud de vacă colectat de procesatori — Eurostat apro_mk_colm (date INS), mii tone/lună.
   Toate textele se calculează din date, ca să rămână corecte la actualizare. */

const ANI_CULORI = ['#9aa3b8', '#3b82f6', '#e0a020', '#22b07d'] // ultimul an = verde (accent)

// 1 l lapte ≈ 1,03 kg → mii tone / 1,03 = milioane de litri
const litri = (miiTone: number) => {
  const mil = miiTone / 1.03
  return mil >= 1000 ? `≈ ${fmt1(mil / 1000)} miliarde de litri` : `≈ ${fmt0(mil)} milioane de litri`
}

/* ── Date ── */
const { meta } = lapteData
const puncte = lapteData.luni.map(l => ({ ...parsePerioada(l.perioada), v: l.valoare }))
const n = puncte.length
const ultim = puncte[n - 1]
const gaseste = (an: number, luna: number) => puncte.find(p => p.an === an && p.luna === luna)
const anulTrecut = (i: number) => gaseste(puncte[i].an - 1, puncte[i].luna)

const ani = Array.from(new Set(puncte.map(p => p.an)))
const aniCompleti = ani.filter(a => puncte.filter(p => p.an === a).length === 12)
const totalAn = (a: number, panaLaLuna = 11) => puncte.filter(p => p.an === a && p.luna <= panaLaLuna).reduce((s, p) => s + p.v, 0)

// variația față de aceeași lună din anul anterior
const yoy = puncte.map((p, i) => { const t = anulTrecut(i); return t ? pct(p.v, t.v) : null })

// media fiecărei luni calendaristice → sezonul laptelui
const medieLuna = LUNI.map((_, l) => { const v = puncte.filter(p => p.luna === l).map(p => p.v); return v.reduce((a, b) => a + b, 0) / v.length })
const lunaMax = medieLuna.indexOf(Math.max(...medieLuna))
const lunaMin = medieLuna.indexOf(Math.min(...medieLuna))

const notaSursa = 'Include doar laptele predat fabricilor de lactate. Laptele consumat în gospodărie sau vândut direct de fermieri nu intră aici, deci producția reală e mai mare. Date raportate de INS către Eurostat, provizorii la sursă. 1 mie de tone ≈ 1 milion de litri.'

/* 1 — Evoluție lunară */
function analizaEvolutie(): Analysis {
  const prec = puncte[n - 2]
  const tAn = anulTrecut(n - 1)!
  const pAn = pct(ultim.v, tAn.v)
  const max = puncte.reduce((a, b) => (b.v > a.v ? b : a))
  const min = puncte.reduce((a, b) => (b.v < a.v ? b : a))
  const pLuna = pct(ultim.v, prec.v)
  return {
    name: 'Evoluție lunară',
    type: 'line',
    unit: 'mii tone pe lună',
    plain: `În ${numeLuna(ultim)}, fabricile de lactate au colectat de la fermieri ${fmt0(ultim.v)} de mii de tone de lapte de vacă (în jur de ${litri(ultim.v).slice(2)}). E cu ${fmt1(Math.abs(pAn))}% ${pAn < 0 ? 'mai puțin' : 'mai mult'} decât în ${numeLuna(tAn)}. Laptele are sezon: cel mai mult se strânge în ${LUNI[lunaMax]}, cel mai puțin în ${LUNI[lunaMin]}.`,
    labels: puncte.map(p => `${LUNI_SCURT[p.luna]} ${String(p.an).slice(2)}`),
    labelsLong: puncte.map(p => cap(numeLuna(p))),
    series: [{ name: 'Lapte colectat (mii tone)', data: puncte.map(p => p.v) }],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Ultima lună (${numeLuna(ultim)})`, value: `${fmt2(ultim.v)} mii t`,
        chg: `${pLuna > 0 ? '▲' : '▼'} ${semn(pLuna)} față de ${LUNI[prec.luna]}`, dir: pLuna > 0 ? 'up' : 'down', hint: litri(ultim.v) },
      { label: `Față de ${numeLuna(tAn)}`, value: semn(pAn), dir: pAn < 0 ? 'down' : 'up',
        chg: pAn < 0 ? '▼ mai puțin lapte decât acum un an' : '▲ mai mult lapte decât acum un an',
        hint: 'Comparăm cu aceeași lună din anul trecut, pentru că laptele are sezon.' },
      { label: 'Record lunar', value: `${fmt2(max.v)} mii t`, chg: cap(numeLuna(max)), dir: 'up',
        hint: `Cel mai slab: ${fmt2(min.v)} mii t, în ${numeLuna(min)}.` },
    ],
    footnote: notaSursa,
  }
}

/* 2 — Comparație pe ani (aceeași lună, ani diferiți) */
function analizaPeAni(): Analysis {
  const aniAfisati = ani.slice(-4)
  const anCurent = aniAfisati[aniAfisati.length - 1]
  const luniCurente = puncte.filter(p => p.an === anCurent).length
  const precedenti = aniAfisati.slice(0, -1)
  const subToti = puncte.filter(p => p.an === anCurent)
    .every(p => precedenti.every(a => (gaseste(a, p.luna)?.v ?? Infinity) > p.v))
  const tCur = totalAn(anCurent, luniCurente - 1), tPrec = totalAn(anCurent - 1, luniCurente - 1)
  const pPer = pct(tCur, tPrec)
  const perioada = `ian–${LUNI_SCURT[luniCurente - 1]}`
  return {
    name: 'Comparație pe ani',
    type: 'line',
    unit: 'mii tone, lună de lună',
    plain: `Fiecare linie e un an. Toți anii au aceeași formă: urcă primăvara, au vârful în ${LUNI[lunaMax]} și coboară spre iarnă. ${subToti
      ? `Anul ${anCurent} (linia verde) e, în fiecare lună de până acum, sub ${precedenti[0]}–${precedenti[precedenti.length - 1]}.`
      : `Anul ${anCurent} e linia verde.`} În ${perioada} ${anCurent} s-au colectat cu ${fmt1(Math.abs(pPer))}% ${pPer < 0 ? 'mai puțin' : 'mai mult'} lapte decât în aceeași perioadă din ${anCurent - 1}.`,
    labels: LUNI_SCURT.map(cap),
    labelsLong: LUNI.map(cap),
    series: aniAfisati.map((a, i) => ({
      name: String(a), color: ANI_CULORI[i + ANI_CULORI.length - aniAfisati.length],
      data: LUNI.map((_, l) => gaseste(a, l)?.v ?? null),
    })),
    labelCol: 'Luna',
    zoomY: true,
    kpis: [
      { label: 'Luna cu cel mai mult lapte', value: cap(LUNI[lunaMax]), chg: `în medie ${fmt0(medieLuna[lunaMax])} mii t`, dir: 'up', hint: 'Primăvara vacile trec pe iarbă proaspătă și dau, de obicei, mai mult lapte.' },
      { label: 'Luna cu cel mai puțin lapte', value: cap(LUNI[lunaMin]), chg: `în medie ${fmt0(medieLuna[lunaMin])} mii t`, dir: 'down', hint: `Media pe ${ani.length} ani (${ani[0]}–${anCurent}).` },
      { label: `${cap(perioada)} ${anCurent} vs. ${anCurent - 1}`, value: semn(pPer), dir: pPer < 0 ? 'down' : 'up',
        chg: `${fmt0(tCur)} față de ${fmt0(tPrec)} mii t`, hint: 'Aceleași luni, comparate de la un an la altul.' },
    ],
    footnote: notaSursa,
  }
}

/* 3 — Total pe an (doar ani compleți) */
function analizaTotalAn(): Analysis {
  const totaluri = aniCompleti.map(a => ({ a, t: totalAn(a) }))
  const rec = totaluri.reduce((x, y) => (y.t > x.t ? y : x))
  const [pen, ult] = totaluri.slice(-2)
  const pUlt = pct(ult.t, pen.t)
  return {
    name: 'Total pe an',
    type: 'bar',
    unit: 'mii tone pe an',
    plain: `Într-un an întreg, fabricile strâng cam ${fmt1(Math.min(...totaluri.map(x => x.t)) / 1000)}–${fmt1(rec.t / 1000)} milioane de tone de lapte de vacă. Anul record a fost ${rec.a}, cu ${fmt0(rec.t)} mii de tone. În ${ult.a} s-a colectat cu ${fmt1(Math.abs(pUlt))}% ${pUlt < 0 ? 'mai puțin' : 'mai mult'} decât în ${pen.a}.`,
    labels: totaluri.map(x => String(x.a)),
    series: [{ name: 'Total (mii tone)', color: '#22b07d', data: totaluri.map(x => Math.round(x.t)) }],
    labelCol: 'Anul',
    tableNewestFirst: true,
    kpis: [
      { label: 'Anul record', value: String(rec.a), chg: `${fmt0(rec.t)} mii t`, dir: 'up', hint: litri(rec.t) },
      { label: `Anul ${ult.a}`, value: `${fmt0(ult.t)} mii t`, chg: `${pUlt > 0 ? '▲' : '▼'} ${semn(pUlt)} față de ${pen.a}`, dir: pUlt < 0 ? 'down' : 'up', hint: litri(ult.t) },
      { label: 'Media anuală', value: `${fmt0(totaluri.reduce((s, x) => s + x.t, 0) / totaluri.length)} mii t`,
        chg: `${aniCompleti[0]}–${aniCompleti[aniCompleti.length - 1]}`, hint: `Doar anii compleți; ${ultim.an} are deocamdată ${puncte.filter(p => p.an === ultim.an).length} luni.` },
    ],
    footnote: notaSursa,
  }
}

/* 4 — Variație anuală, ultimele 24 de luni */
function analizaVariatie(): Analysis {
  const idx = puncte.map((_, i) => i).slice(-24)
  let laRand = 0
  for (let i = n - 1; i >= 0 && yoy[i] != null && yoy[i]! < 0; i--) laRand++
  const minI = idx.reduce((a, b) => (yoy[b]! < yoy[a]! ? b : a))
  const ultY = yoy[n - 1]!
  return {
    name: 'Variație anuală',
    type: 'bar',
    unit: '% față de aceeași lună a anului trecut',
    plain: `Fiecare bară arată cu cât s-a schimbat cantitatea față de aceeași lună de acum un an. Verde = mai mult lapte, roșu = mai puțin. ${laRand >= 2
      ? `De ${laRand} luni la rând, fabricile primesc mai puțin lapte decât cu un an în urmă.`
      : `În ${numeLuna(ultim)} variația a fost ${semn(ultY)}.`}`,
    labels: idx.map(i => `${LUNI_SCURT[puncte[i].luna]} ${String(puncte[i].an).slice(2)}`),
    labelsLong: idx.map(i => cap(numeLuna(puncte[i]))),
    series: [{
      name: 'Variație anuală',
      data: idx.map(i => Math.round(yoy[i]! * 10) / 10),
      colors: idx.map(i => (yoy[i]! >= 0 ? '#22b07d' : '#e5544b')),
    }],
    labelCol: 'Luna',
    valueSuffix: '%',
    tableNewestFirst: true,
    kpis: [
      { label: `Ultima lună (${numeLuna(ultim)})`, value: semn(ultY), dir: ultY < 0 ? 'down' : 'up', chg: ultY < 0 ? '▼ scădere' : '▲ creștere', hint: 'Față de aceeași lună din anul trecut.' },
      { label: 'Luni la rând în scădere', value: String(laRand), dir: laRand ? 'down' : undefined,
        chg: laRand ? `din ${numeLuna(puncte[n - laRand])}` : 'nicio scădere acum', hint: 'Câte luni consecutive a fost mai puțin lapte decât cu un an înainte.' },
      { label: 'Cea mai mare scădere (24 luni)', value: semn(yoy[minI]!), dir: 'down', chg: cap(numeLuna(puncte[minI])) },
    ],
    footnote: notaSursa,
  }
}

export function lapteTopic(): Topic {
  return {
    key: 'lapte', label: 'Lapte de vacă', icon: '🥛',
    sources: [{
      key: 'EUROSTAT', tag: 'oficial', label: 'Eurostat', link: 'ec.europa.eu/eurostat', url: meta.url, freq: 'lunar',
      chips: [`● Actualizat: ${numeLuna(ultim)}`, '🔁 lunar', `📅 date din ${ani[0]}`],
      analyses: [analizaEvolutie(), analizaPeAni(), analizaTotalAn(), analizaVariatie()],
    }],
  }
}
