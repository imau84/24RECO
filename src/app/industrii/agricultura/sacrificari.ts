import type { Analysis, Topic } from '@/components/ModelA'
import sacrificariData from '@/data/agricultura/sacrificari_data.json'
import { LUNI, fmt0, fmt1, pct, semn, cap, diferenta, numeLuna, eticheta, parsePerioada } from './util'

/* Sacrificări de animale în abatoare — Eurostat apro_mt_pheadm, mii capete/lună.
   Toate textele se calculează din date, ca să rămână corecte la actualizare. */

type Specie = 'porcine' | 'ovine' | 'bovine'
const SPECII: Record<Specie, { tab: string; animale: string; color: string; ce: string }> = {
  porcine: { tab: 'Porci', animale: 'porci', color: '#e0559c', ce: '' },
  ovine: { tab: 'Oi și miei', animale: 'oi și miei', color: '#3b82f6', ce: 'oi, berbeci și miei' },
  bovine: { tab: 'Bovine', animale: 'bovine', color: '#e0a020', ce: 'vaci, tauri și viței' },
}
const ORDINE: Specie[] = ['porcine', 'ovine', 'bovine']

// „308 mii”, dar „70 de mii” (regula lui „de” după numerale ≥ 20)
const mii = (v: number) => {
  if (v < 100) return `${fmt1(v)} mii`
  const r = Math.round(v) % 100
  return `${fmt0(v)} ${r === 0 || r >= 20 ? 'de ' : ''}mii`
}

/* ── Date ── */
const { meta } = sacrificariData
const puncte = sacrificariData.luni.map(l => ({ ...parsePerioada(l.perioada), porcine: l.porcine, ovine: l.ovine, bovine: l.bovine }))
type P = typeof puncte[number]
const n = puncte.length
const ultim = puncte[n - 1]
const anTrecut = (p: P) => puncte.find(q => q.an === p.an - 1 && q.luna === p.luna)
const ani = Array.from(new Set(puncte.map(p => p.an)))
const aniCompleti = ani.filter(a => puncte.filter(p => p.an === a).length === 12)
const totalAn = (s: Specie, a: number) => puncte.filter(p => p.an === a).reduce((t, p) => t + p[s], 0)
const medieLuna = (s: Specie) => LUNI.map((_, l) => { const v = puncte.filter(p => p.luna === l).map(p => p[s]); return v.reduce((a, b) => a + b, 0) / v.length })

const notaSursa = 'Doar animalele sacrificate în abatoare autorizate. Sacrificările din gospodării (mai ales porcul de Crăciun și mielul de Paște) nu intră aici, deci totalul real e mai mare. Ultimele luni sunt provizorii. „Mii de capete” = mii de animale.'

/* 1 — Pe specii, ultima lună */
function analizaPeSpecii(): Analysis {
  const total = ORDINE.reduce((t, s) => t + ultim[s], 0)
  const t = anTrecut(ultim)
  return {
    name: 'Pe specii',
    type: 'bar',
    unit: `mii de animale, ${numeLuna(ultim)}`,
    plain: `În ${numeLuna(ultim)}, abatoarele din România au sacrificat ${mii(ultim.porcine)} de porci, ${mii(ultim.ovine)} de oi și miei și ${mii(ultim.bovine)} de bovine. Porcii sunt de departe cei mai mulți: ${fmt0(ultim.porcine / total * 100)} din 100 de animale sacrificate.`,
    labels: ORDINE.map(s => SPECII[s].tab),
    series: [{ name: 'Mii de capete', data: ORDINE.map(s => ultim[s]), colors: ORDINE.map(s => SPECII[s].color) }],
    labelCol: 'Specia',
    share: true,
    kpis: ORDINE.map(s => {
      const p = t ? pct(ultim[s], t[s]) : 0
      return {
        label: SPECII[s].tab, value: mii(ultim[s]),
        chg: t ? `${p > 0 ? '▲' : '▼'} ${semn(p)} față de ${numeLuna(t)}` : undefined, dir: p < 0 ? 'down' : 'up',
        hint: SPECII[s].ce ? cap(SPECII[s].ce) + '.' : undefined,
      }
    }),
    footnote: notaSursa,
  }
}

/* 2–4 — Evoluția unei specii */
function analizaSpecie(s: Specie): Analysis {
  const { tab, animale, color } = SPECII[s]
  const t = anTrecut(ultim)!
  const pAn = pct(ultim[s], t[s])
  const ult = aniCompleti[aniCompleti.length - 1]
  const tUlt = totalAn(s, ult), tPrec = totalAn(s, ult - 1)
  const pTot = pct(tUlt, tPrec)
  const medii = medieLuna(s)
  const lMax = medii.indexOf(Math.max(...medii))
  const mediana = [...medii].sort((a, b) => a - b)[6]
  const max = puncte.reduce((a, b) => (b[s] > a[s] ? b : a))

  let sezon = `De obicei, cele mai multe ${animale} se sacrifică în ${LUNI[lMax]}.`
  let sezonHint = `Media lunii ${LUNI[lMax]}, pe ${ani.length} ani.`
  if (s === 'porcine' && lMax === 11) {
    sezon = 'Cei mai mulți porci se sacrifică în decembrie, înainte de Crăciun.'
    sezonHint = 'Înainte de Crăciun.'
  } else if (s === 'ovine' && (lMax === 2 || lMax === 3)) {
    sezon = `Paștele se vede clar în grafic: în luna de vârf se sacrifică, în medie, de ${fmt1(medii[lMax] / mediana)} ori mai multe oi și miei decât într-o lună obișnuită.`
    sezonHint = 'De Paște. Data Paștelui se schimbă, așa că vârful cade în martie sau aprilie.'
  }

  return {
    name: tab,
    type: 'line',
    unit: 'mii de animale pe lună',
    plain: `În ${numeLuna(ultim)} s-au sacrificat în abatoare ${mii(ultim[s])} de ${animale}, ${diferenta(ultim[s], t[s])} decât în ${numeLuna(t)}. În ${ult}, totalul a fost ${mii(tUlt)} de ${animale}, ${diferenta(tUlt, tPrec)} decât în ${ult - 1}. ${sezon}`,
    labels: puncte.map(eticheta),
    labelsLong: puncte.map(p => cap(numeLuna(p))),
    series: [{ name: `${tab} (mii capete)`, color, data: puncte.map(p => p[s]) }],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Ultima lună (${numeLuna(ultim)})`, value: mii(ultim[s]), dir: pAn < 0 ? 'down' : 'up',
        chg: `${pAn > 0 ? '▲' : '▼'} ${semn(pAn)} față de ${numeLuna(t)}`, hint: `Record lunar: ${mii(max[s])}, în ${numeLuna(max)}.` },
      { label: `Tot anul ${ult}`, value: mii(tUlt), dir: pTot < 0 ? 'down' : 'up',
        chg: `${pTot > 0 ? '▲' : '▼'} ${semn(pTot)} față de ${ult - 1}`, hint: `În medie ${mii(tUlt / 12)} pe lună.` },
      { label: 'Luna de vârf', value: cap(LUNI[lMax]), chg: `în medie ${mii(medii[lMax])}`, dir: 'up', hint: sezonHint },
    ],
    footnote: notaSursa,
  }
}

export function sacrificariTopic(): Topic {
  return {
    key: 'sacrificari', label: 'Sacrificări în abatoare', icon: '🥩',
    sources: [{
      key: 'EUROSTAT', tag: 'oficial', label: 'Eurostat', link: 'ec.europa.eu/eurostat', url: meta.url, freq: 'lunar',
      chips: [`● Actualizat: ${numeLuna(ultim)}`, '🔁 lunar', `📅 date din ${ani[0]}`],
      analyses: [analizaPeSpecii(), ...ORDINE.map(analizaSpecie)],
    }],
  }
}
