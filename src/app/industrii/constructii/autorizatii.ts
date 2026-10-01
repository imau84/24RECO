import type { Analysis, Topic } from '@/components/ModelA'
import autorizatiiData from '@/data/constructii/autorizatii_data.json'
import { LUNI, LUNI_SCURT, fmt0, fmt1, pct, semn, cap, numeLuna, eticheta, parsePerioada, type Punct } from '../agricultura/util'

/* Autorizații de construire pentru clădiri — Eurostat sts_cobp_m (date INS),
   indice al suprafeței utile autorizate, 2021 = 100, serie brută (neajustată sezonier).
   Toate textele se calculează din date, ca să rămână corecte la actualizare. */

const C_RO = '#e0a020', C_TREND = '#5a6178', C_REZ = '#3b82f6', C_NEREZ = '#7c5ce6', C_UE = '#12a5b8'
const C_UP = '#22b07d', C_DOWN = '#e5544b'

type Rand = Punct & { total: number; rez: number | null; nerez: number | null; ue: number | null }

/* ── Date ── */
const { meta } = autorizatiiData
const puncte: Rand[] = autorizatiiData.luni.map(l => ({
  ...parsePerioada(l.perioada),
  total: l.total as number, rez: l.rezidentiale, nerez: l.nerezidentiale, ue: l.ue27,
}))
const n = puncte.length
const ultim = puncte[n - 1]
const ani = Array.from(new Set(puncte.map(p => p.an)))
const gaseste = (an: number, luna: number) => puncte.find(p => p.an === an && p.luna === luna)
const anulTrecut = (i: number) => gaseste(puncte[i].an - 1, puncte[i].luna)

const labels = puncte.map(eticheta)
const labelsLong = puncte.map(p => cap(numeLuna(p)))
const r1 = (v: number) => Math.round(v * 10) / 10

/** media ultimelor 12 luni (null dacă lipsește vreo lună) — netezește sezonul */
const medie12 = (k: 'total' | 'rez' | 'nerez' | 'ue') => puncte.map((_, i) => {
  if (i < 11) return null
  const v = puncte.slice(i - 11, i + 1).map(p => p[k])
  return v.every(x => x != null) ? r1((v as number[]).reduce((a, b) => a + b, 0) / 12) : null
})

const yoy = puncte.map((p, i) => { const t = anulTrecut(i); return t ? pct(p.total, t.total) : null })

/** „cu 21% sub nivelul din 2021” — traducerea indicelui în limbaj simplu */
const fata2021 = (v: number) => {
  const p = v - 100
  if (Math.abs(p) < 1) return 'cam cât într-o lună obișnuită din 2021'
  return `cu ${fmt0(Math.abs(p))}% ${p < 0 ? 'mai puțin' : 'mai mult'} decât într-o lună obișnuită din 2021`
}

const notaIndice = 'Indice 2021 = 100: 100 înseamnă suprafața medie autorizată pe lună în 2021. Măsoară metrii pătrați utili ai clădirilor noi care au primit autorizație, nu numărul de autorizații. Serie brută (cu sezonalitate). Date raportate de INS către Eurostat; ultimele luni pot fi revizuite.'

/* 1 — Evoluție lunară */
function analizaEvolutie(): Analysis {
  const t = anulTrecut(n - 1)!
  const pAn = pct(ultim.total, t.total)
  const m12 = medie12('total')
  const ult12 = m12[n - 1]!, prec12 = m12[n - 13]
  const p12 = prec12 != null ? pct(ult12, prec12) : null
  const max = puncte.reduce((a, b) => (b.total > a.total ? b : a))
  const min = puncte.reduce((a, b) => (b.total < a.total ? b : a))
  return {
    name: 'Evoluție lunară',
    type: 'line',
    unit: 'indice, 2021 = 100',
    plain: `Cifra arată câți metri pătrați de clădiri noi au primit autorizație de construire, comparat cu 2021 (2021 = 100). În ${numeLuna(ultim)} indicele a fost ${fmt1(ultim.total)} — adică s-a autorizat ${fata2021(ultim.total)}. Față de ${numeLuna(t)}, suprafața autorizată ${pAn < 0 ? 'a scăzut' : 'a crescut'} cu ${fmt1(Math.abs(pAn))}%. Linia gri e media ultimelor 12 luni și arată tendința, fără „zgomotul” de la o lună la alta.`,
    labels, labelsLong,
    series: [
      { name: 'România, lunar', color: C_RO, data: puncte.map(p => p.total) },
      { name: 'Tendință (media 12 luni)', color: C_TREND, data: m12 },
    ],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Ultima lună (${numeLuna(ultim)})`, value: fmt1(ultim.total),
        chg: `${pAn > 0 ? '▲' : '▼'} ${semn(pAn)} față de ${numeLuna(t)}`, dir: pAn > 0 ? 'up' : 'down',
        hint: `S-a autorizat ${fata2021(ultim.total)}.` },
      { label: 'Ultimele 12 luni', value: fmt1(ult12),
        ...(p12 != null ? { chg: `${p12 > 0 ? '▲' : '▼'} ${semn(p12)} față de cele 12 luni dinainte`, dir: p12 > 0 ? 'up' as const : 'down' as const } : {}),
        hint: 'Media pe un an întreg — cel mai bun semn al direcției reale.' },
      { label: `Maxim ${ani[0]}–${ultim.an}`, value: fmt1(max.total), chg: cap(numeLuna(max)), dir: 'up',
        hint: `Minimul: ${fmt1(min.total)}, în ${numeLuna(min)}.` },
    ],
    footnote: notaIndice,
  }
}

/* 2 — Locuințe vs. alte clădiri */
function analizaTipuri(): Analysis {
  const rez12 = medie12('rez'), nerez12 = medie12('nerez')
  const i = n - 1
  const t = anulTrecut(i)!
  const pRez = ultim.rez != null && t.rez != null ? pct(ultim.rez, t.rez) : null
  const pNerez = ultim.nerez != null && t.nerez != null ? pct(ultim.nerez, t.nerez) : null
  const r = rez12[i]!, nr = nerez12[i]!
  const sus = nr > r ? 'clădirile nerezidențiale (birouri, magazine, hale, depozite)' : 'locuințele'
  return {
    name: 'Locuințe vs. alte clădiri',
    type: 'line',
    unit: 'indice 2021 = 100, media ultimelor 12 luni',
    plain: `Comparăm locuințele (case și blocuri) cu restul clădirilor (birouri, magazine, hale, depozite, școli, spitale). Fiecare linie e media ultimelor 12 luni, ca să se vadă tendința. Acum, ${sus} stau mai bine față de 2021: locuințe ${fmt1(r)}, alte clădiri ${fmt1(nr)}. Locuințe: s-a autorizat ${fata2021(r)}.`,
    labels: labels.slice(11), labelsLong: labelsLong.slice(11),
    series: [
      { name: 'Locuințe', color: C_REZ, data: rez12.slice(11) },
      { name: 'Alte clădiri', color: C_NEREZ, data: nerez12.slice(11) },
    ],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Locuințe (${numeLuna(ultim)})`, value: ultim.rez != null ? fmt1(ultim.rez) : '—',
        ...(pRez != null ? { chg: `${pRez > 0 ? '▲' : '▼'} ${semn(pRez)} față de acum un an`, dir: pRez > 0 ? 'up' as const : 'down' as const } : {}),
        hint: 'Case și blocuri de locuințe.' },
      { label: `Alte clădiri (${numeLuna(ultim)})`, value: ultim.nerez != null ? fmt1(ultim.nerez) : '—',
        ...(pNerez != null ? { chg: `${pNerez > 0 ? '▲' : '▼'} ${semn(pNerez)} față de acum un an`, dir: pNerez > 0 ? 'up' as const : 'down' as const } : {}),
        hint: 'Birouri, magazine, hale, depozite, hoteluri, școli, spitale.' },
      { label: 'Tendință 12 luni', value: `${fmt1(r)} vs. ${fmt1(nr)}`, chg: 'locuințe vs. alte clădiri',
        hint: 'Media ultimelor 12 luni, 2021 = 100 pentru fiecare.' },
    ],
    footnote: notaIndice,
  }
}

/* 3 — România vs. Uniunea Europeană */
function analizaUE(): Analysis {
  const ro12 = medie12('total'), ue12 = medie12('ue')
  let j = n - 1
  while (j > 0 && ue12[j] == null) j--
  const ro = ro12[j]!, ue = ue12[j]!
  const dif = ro - ue
  const ultUe = [...puncte].reverse().find(p => p.ue != null)!
  return {
    name: 'România vs. UE',
    type: 'line',
    unit: 'indice 2021 = 100, media ultimelor 12 luni',
    plain: `Ambele linii pornesc de la același nivel (2021 = 100), așa că putem compara direcția. În ultimele 12 luni până în ${numeLuna(puncte[j])}, România a fost la ${fmt1(ro)}, iar media Uniunii Europene la ${fmt1(ue)} — ${Math.abs(dif) < 2 ? 'aproape la fel' : dif > 0 ? 'România s-a descurcat mai bine decât media UE' : 'România a autorizat mai puțin decât media UE, raportat la 2021'}.`,
    labels: labels.slice(11), labelsLong: labelsLong.slice(11),
    series: [
      { name: 'România', color: C_RO, data: ro12.slice(11) },
      { name: 'UE 27', color: C_UE, data: ue12.slice(11) },
    ],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: 'România (12 luni)', value: fmt1(ro), chg: `până în ${numeLuna(puncte[j])}`, hint: `S-a autorizat ${fata2021(ro)}.` },
      { label: 'UE 27 (12 luni)', value: fmt1(ue), chg: `până în ${numeLuna(puncte[j])}`, hint: `Ultima lună publicată pentru UE: ${numeLuna(ultUe)}.` },
      { label: 'Diferența', value: `${dif > 0 ? '+' : dif < 0 ? '−' : ''}${fmt1(Math.abs(dif))} puncte`, dir: dif < 0 ? 'down' : 'up',
        chg: dif < 0 ? '▼ România sub media UE' : '▲ România peste media UE', hint: 'Diferența dintre cei doi indici (2021 = 100).' },
    ],
    footnote: `${notaIndice} Datele UE apar de obicei cu 1–2 luni mai târziu decât cele ale României.`,
  }
}

/* 4 — Variație anuală, ultimele 24 de luni */
function analizaVariatie(): Analysis {
  const idx = puncte.map((_, i) => i).slice(-24)
  const crestere = idx.filter(i => yoy[i]! >= 0).length
  const ultY = yoy[n - 1]!
  const maxI = idx.reduce((a, b) => (yoy[b]! > yoy[a]! ? b : a))
  const minI = idx.reduce((a, b) => (yoy[b]! < yoy[a]! ? b : a))
  return {
    name: 'Variație anuală',
    type: 'bar',
    unit: '% față de aceeași lună a anului trecut',
    plain: `Fiecare bară arată cu cât s-a schimbat suprafața autorizată față de aceeași lună de acum un an. Verde = s-a autorizat mai mult, roșu = mai puțin. În ultimele 24 de luni au fost ${crestere} luni de creștere și ${idx.length - crestere} de scădere. Autorizațiile variază mult de la o lună la alta, așa că o singură bară nu spune totul.`,
    labels: idx.map(i => labels[i]),
    labelsLong: idx.map(i => labelsLong[i]),
    series: [{ name: 'Variație anuală', data: idx.map(i => r1(yoy[i]!)), colors: idx.map(i => (yoy[i]! >= 0 ? C_UP : C_DOWN)) }],
    labelCol: 'Luna',
    valueSuffix: '%',
    tableNewestFirst: true,
    kpis: [
      { label: `Ultima lună (${numeLuna(ultim)})`, value: semn(ultY), dir: ultY < 0 ? 'down' : 'up',
        chg: ultY < 0 ? '▼ mai puțin decât acum un an' : '▲ mai mult decât acum un an', hint: 'Comparăm cu aceeași lună din anul trecut, pentru că autorizațiile au sezon.' },
      { label: 'Cea mai mare creștere (24 luni)', value: semn(yoy[maxI]!), dir: 'up', chg: cap(numeLuna(puncte[maxI])) },
      { label: 'Cea mai mare scădere (24 luni)', value: semn(yoy[minI]!), dir: 'down', chg: cap(numeLuna(puncte[minI])) },
    ],
    footnote: notaIndice,
  }
}

/* 5 — Sezonalitate: media fiecărei luni calendaristice */
function analizaSezon(): Analysis {
  const medii = LUNI.map((_, l) => { const v = puncte.filter(p => p.luna === l).map(p => p.total); return r1(v.reduce((a, b) => a + b, 0) / v.length) })
  const lMax = medii.indexOf(Math.max(...medii)), lMin = medii.indexOf(Math.min(...medii))
  return {
    name: 'Sezonalitate',
    type: 'bar',
    unit: `indice mediu pe lună, ${ani[0]}–${ultim.an}`,
    plain: `Autorizațiile au sezon. În medie, cele mai multe se dau în ${LUNI[lMax]}, iar cele mai puține în ${LUNI[lMin]}, când lucrările sunt planificate mai rar. De aceea comparăm mereu o lună cu aceeași lună din anul trecut, nu cu luna dinainte.`,
    labels: LUNI_SCURT.map(cap),
    labelsLong: LUNI.map(cap),
    series: [{ name: 'Media lunii', data: medii, colors: medii.map((_, l) => (l === lMax ? C_UP : l === lMin ? C_DOWN : C_RO)) }],
    labelCol: 'Luna',
    kpis: [
      { label: 'Luna cea mai activă', value: cap(LUNI[lMax]), chg: `în medie ${fmt1(medii[lMax])}`, dir: 'up' },
      { label: 'Luna cea mai slabă', value: cap(LUNI[lMin]), chg: `în medie ${fmt1(medii[lMin])}`, dir: 'down' },
      { label: 'Diferența', value: `${fmt0(pct(medii[lMax], medii[lMin]))}%`, chg: `${LUNI[lMax]} față de ${LUNI[lMin]}`,
        hint: `Media pe ${ani.length} ani (${ani[0]}–${ultim.an}).` },
    ],
    footnote: notaIndice,
  }
}

/* 6 — Media pe an */
function analizaPeAni(): Analysis {
  const anCurent = ultim.an
  const luniCurente = puncte.filter(p => p.an === anCurent).length
  const medieAn = (a: number, panaLa = 11) => { const v = puncte.filter(p => p.an === a && p.luna <= panaLa).map(p => p.total); return v.reduce((x, y) => x + y, 0) / v.length }
  const ma = ani.map(a => ({ a, v: r1(medieAn(a)), complet: puncte.filter(p => p.an === a).length === 12 }))
  const compl = ma.filter(x => x.complet)
  const rec = compl.reduce((x, y) => (y.v > x.v ? y : x))
  const [pen, ult] = compl.slice(-2)
  const pUlt = pct(ult.v, pen.v)
  const per = `ian–${LUNI_SCURT[luniCurente - 1]}`
  const cur = medieAn(anCurent, luniCurente - 1), prev = medieAn(anCurent - 1, luniCurente - 1)
  const pCur = pct(cur, prev)
  return {
    name: 'Media pe an',
    type: 'bar',
    unit: 'indice mediu, 2021 = 100',
    plain: `Media pe un an întreg elimină sezonul. Cel mai bun an a fost ${rec.a} (${fmt1(rec.v)}). În ${ult.a} s-a autorizat în medie cu ${fmt1(Math.abs(pUlt))}% ${pUlt < 0 ? 'mai puțin' : 'mai mult'} decât în ${pen.a}. În ${per} ${anCurent}, suprafața autorizată e cu ${fmt1(Math.abs(pCur))}% ${pCur < 0 ? 'mai mică' : 'mai mare'} decât în aceeași perioadă din ${anCurent - 1}.`,
    labels: ma.map(x => (x.complet ? String(x.a) : `${x.a}*`)),
    labelsLong: ma.map(x => (x.complet ? String(x.a) : `${x.a} (${per}, parțial)`)),
    series: [{ name: 'Media anului', color: C_RO, data: ma.map(x => x.v) }],
    labelCol: 'Anul',
    tableNewestFirst: true,
    kpis: [
      { label: 'Cel mai bun an', value: String(rec.a), chg: `media ${fmt1(rec.v)}`, dir: 'up' },
      { label: `Anul ${ult.a}`, value: fmt1(ult.v), chg: `${pUlt > 0 ? '▲' : '▼'} ${semn(pUlt)} față de ${pen.a}`, dir: pUlt < 0 ? 'down' : 'up' },
      { label: `${cap(per)} ${anCurent}`, value: semn(pCur), dir: pCur < 0 ? 'down' : 'up',
        chg: `față de ${per} ${anCurent - 1}`, hint: `* ${anCurent} are deocamdată ${luniCurente} luni.` },
    ],
    footnote: notaIndice,
  }
}

export function autorizatiiTopic(): Topic {
  return {
    key: 'autorizatii', label: 'Autorizații de construire', icon: '📝',
    sources: [{
      key: 'EUROSTAT', tag: 'oficial', label: 'Eurostat · INS', link: 'ec.europa.eu/eurostat', url: meta.url, freq: 'lunar',
      chips: [`● Actualizat: ${numeLuna(ultim)}`, '🔁 lunar', `📅 date din ${ani[0]}`],
      analyses: [analizaEvolutie(), analizaTipuri(), analizaUE(), analizaVariatie(), analizaSezon(), analizaPeAni()],
    }],
  }
}
