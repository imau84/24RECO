import type { Analysis, Topic } from '@/components/ModelA'
import carneData from '@/data/agricultura/carne_data.json'
import sacrificariData from '@/data/agricultura/sacrificari_data.json'
import { fmt0, fmt1, pct, semn, cap, diferenta, schimbare, mii, numeLuna, eticheta, parsePerioada } from './util'

/* Carne produsă în abatoare, greutate carcasă — Eurostat apro_mt_pwgtm, mii tone/lună.
   Greutatea medie a unui porc = tone de carne de porc ÷ porci sacrificați (setul „Sacrificări”).
   Toate textele se calculează din date, ca să rămână corecte la actualizare. */

type Carne = 'pasare' | 'porc'
const CARNE: Record<Carne, { nume: string; color: string }> = {
  pasare: { nume: 'Carne de pasăre', color: '#12a5b8' },
  porc: { nume: 'Carne de porc', color: '#e0559c' },
}
const ORDINE: Carne[] = ['pasare', 'porc']
const sageata = (p: number) => `${p > 0 ? '▲' : '▼'} ${semn(p)}`
const tone = (v: number) => `${v < 100 ? fmt1(v) : fmt0(v)} mii t` // compact, pentru KPI

/* ── Date ── */
const { meta } = carneData
const puncte = carneData.luni.map(l => ({ ...parsePerioada(l.perioada), porc: l.porc, pasare: l.pasare }))
type P = typeof puncte[number]
const n = puncte.length
const ultim = puncte[n - 1]
const anTrecut = (p: P) => puncte.find(q => q.an === p.an - 1 && q.luna === p.luna)
const ani = Array.from(new Set(puncte.map(p => p.an)))
const aniCompleti = ani.filter(a => puncte.filter(p => p.an === a).length === 12)
const totalAn = (c: Carne, a: number) => puncte.filter(p => p.an === a).reduce((t, p) => t + p[c], 0)

const notaSursa = 'Doar carnea din abatoare autorizate, fără sacrificările din gospodării. Greutatea în carcasă (animalul tăiat și curățat, cu oase) nu e totuna cu carnea care ajunge la vânzare. Ultimele luni sunt provizorii. 1 mie de tone = 1 milion de kilograme.'

/* 1 — Pasăre vs. porc, lunar */
function analizaComparatie(): Analysis {
  const t = anTrecut(ultim)!
  const pPas = pct(ultim.pasare, t.pasare), pPorc = pct(ultim.porc, t.porc)
  const raport = ultim.pasare / ultim.porc
  return {
    name: 'Pasăre vs. porc',
    type: 'line',
    unit: 'mii tone pe lună',
    plain: `În ${numeLuna(ultim)}, abatoarele din România au produs ${mii(ultim.pasare)} de tone de carne de pasăre și ${mii(ultim.porc)} de tone de carne de porc. Adică la fiecare kilogram de porc se produc cam ${fmt1(raport)} kilograme de carne de pasăre. Față de ${numeLuna(t)}, carnea de pasăre ${schimbare(ultim.pasare, t.pasare)}, iar cea de porc ${schimbare(ultim.porc, t.porc)}.`,
    labels: puncte.map(eticheta),
    labelsLong: puncte.map(p => cap(numeLuna(p))),
    series: ORDINE.map(c => ({ name: CARNE[c].nume, color: CARNE[c].color, data: puncte.map(p => p[c]) })),
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Pasăre (${numeLuna(ultim)})`, value: tone(ultim.pasare), chg: `${sageata(pPas)} față de ${numeLuna(t)}`, dir: pPas < 0 ? 'down' : 'up', hint: `≈ ${fmt0(ultim.pasare)} milioane de kilograme.` },
      { label: `Porc (${numeLuna(ultim)})`, value: tone(ultim.porc), chg: `${sageata(pPorc)} față de ${numeLuna(t)}`, dir: pPorc < 0 ? 'down' : 'up', hint: `≈ ${fmt0(ultim.porc)} milioane de kilograme.` },
      { label: 'Pasăre la 1 kg de porc', value: `${fmt1(raport)} kg`, chg: 'în ultima lună', hint: 'Câtă carne de pasăre se produce pentru fiecare kilogram de carne de porc.' },
    ],
    footnote: notaSursa,
  }
}

/* 2 — Total pe an */
function analizaTotalAn(): Analysis {
  const ult = aniCompleti[aniCompleti.length - 1], prim = aniCompleti[0]
  const tot = (c: Carne) => aniCompleti.map(a => totalAn(c, a))
  // câți ani la rând a crescut carnea de pasăre
  const pas = tot('pasare')
  let crestere = 0
  for (let i = pas.length - 1; i > 0 && pas[i] > pas[i - 1]; i--) crestere++
  const porc = tot('porc')
  const minPorc = aniCompleti[porc.indexOf(Math.min(...porc))]
  const pPas = pct(totalAn('pasare', ult), totalAn('pasare', ult - 1))
  const pPorc = pct(totalAn('porc', ult), totalAn('porc', ult - 1))
  return {
    name: 'Total pe an',
    type: 'bar',
    unit: 'mii tone pe an',
    plain: `${crestere >= 2 ? `Carnea de pasăre crește de ${crestere} ani la rând: ` : 'Carnea de pasăre: '}${mii(totalAn('pasare', ult))} de tone în ${ult}, ${diferenta(totalAn('pasare', ult), totalAn('pasare', prim))} decât în ${prim}. Carnea de porc ${minPorc !== ult ? `a coborât până la ${mii(totalAn('porc', minPorc))} de tone în ${minPorc}, apoi și-a revenit la ${mii(totalAn('porc', ult))} în ${ult}` : `a ajuns la ${mii(totalAn('porc', ult))} de tone în ${ult}, cel mai puțin din ${prim} încoace`}.`,
    labels: aniCompleti.map(String),
    series: ORDINE.map(c => ({ name: CARNE[c].nume, color: CARNE[c].color, data: tot(c).map(Math.round) })),
    labelCol: 'Anul',
    tableNewestFirst: true,
    kpis: [
      { label: `Pasăre în ${ult}`, value: tone(totalAn('pasare', ult)), chg: `${sageata(pPas)} față de ${ult - 1}`, dir: pPas < 0 ? 'down' : 'up', hint: `În medie ${mii(totalAn('pasare', ult) / 12)} de tone pe lună.` },
      { label: `Porc în ${ult}`, value: tone(totalAn('porc', ult)), chg: `${sageata(pPorc)} față de ${ult - 1}`, dir: pPorc < 0 ? 'down' : 'up', hint: `În medie ${mii(totalAn('porc', ult) / 12)} de tone pe lună.` },
      { label: `Pasăre ${ult} vs. ${prim}`, value: semn(pct(totalAn('pasare', ult), totalAn('pasare', prim))), dir: totalAn('pasare', ult) < totalAn('pasare', prim) ? 'down' : 'up',
        chg: `porc: ${semn(pct(totalAn('porc', ult), totalAn('porc', prim)))}`, hint: `Cum s-a schimbat producția anuală față de ${prim}.` },
    ],
    footnote: `Doar anii compleți; ${ultim.an} are deocamdată ${puncte.filter(p => p.an === ultim.an).length} luni. ${notaSursa}`,
  }
}

/* 3 — Greutatea medie a unui porc (carne de porc ÷ porci sacrificați) */
function analizaGreutatePorc(): Analysis {
  const capete = new Map(sacrificariData.luni.map(l => [l.perioada, l.porcine]))
  const kg = carneData.luni
    .filter(l => capete.get(l.perioada))
    .map(l => ({ ...parsePerioada(l.perioada), v: Math.round(l.porc / capete.get(l.perioada)! * 1000 * 10) / 10 }))
  const u = kg[kg.length - 1]
  const max = kg.reduce((a, b) => (b.v > a.v ? b : a)), min = kg.reduce((a, b) => (b.v < a.v ? b : a))
  const medieAn = (a: number) => { const v = kg.filter(k => k.an === a).map(k => k.v); return v.reduce((x, y) => x + y, 0) / v.length }
  const ult = aniCompleti[aniCompleti.length - 1], prim = aniCompleti[0]
  // greutatea per porc variază mult mai puțin decât tonajul total? (max/min)
  const tonaj = puncte.map(p => p.porc)
  const variazaMaiPutin = max.v / min.v < Math.max(...tonaj) / Math.min(...tonaj)
  return {
    name: 'Greutatea unui porc',
    type: 'line',
    unit: 'kg carcasă pe porc',
    plain: `Un porc sacrificat în abator dă, în medie, în jur de ${fmt0(medieAn(ult))} de kilograme de carcasă (animalul tăiat și curățat, cu oase). Greutatea variază puțin: între ${fmt0(min.v)} și ${fmt0(max.v)} kg din ${prim} încoace.${variazaMaiPutin ? ' Deci când se produce mai multă carne de porc, e în principal pentru că se sacrifică mai mulți porci, nu pentru că porcii sunt mai grei.' : ''}`,
    labels: kg.map(eticheta),
    labelsLong: kg.map(k => cap(numeLuna(k))),
    series: [{ name: 'Kg carcasă pe porc', color: CARNE.porc.color, data: kg.map(k => k.v) }],
    labelCol: 'Luna',
    tableNewestFirst: true,
    zoomY: true,
    kpis: [
      { label: `Ultima lună (${numeLuna(u)})`, value: `${fmt1(u.v)} kg`, chg: 'carcasă pe porc', hint: 'Tonele de carne de porc împărțite la numărul de porci sacrificați.' },
      { label: `Media anului ${ult}`, value: `${fmt1(medieAn(ult))} kg`, chg: `${fmt1(medieAn(prim))} kg în ${prim}` },
      { label: 'Cel mai greu / cel mai ușor', value: `${fmt0(max.v)} / ${fmt0(min.v)} kg`, chg: `${cap(numeLuna(max))} / ${numeLuna(min)}` },
    ],
    footnote: `Calcul 24reco.com: carne de porc (acest set) ÷ porci sacrificați (tema „Sacrificări în abatoare”), ambele din Eurostat. ${notaSursa}`,
  }
}

export function carneTopic(): Topic {
  return {
    key: 'carne', label: 'Carne produsă', icon: '🍗',
    sources: [{
      key: 'EUROSTAT', tag: 'oficial', label: 'Eurostat', link: 'ec.europa.eu/eurostat', url: meta.url, freq: 'lunar',
      chips: [`● Actualizat: ${numeLuna(ultim)}`, '🔁 lunar', `📅 date din ${ani[0]}`],
      analyses: [analizaComparatie(), analizaTotalAn(), analizaGreutatePorc()],
    }],
  }
}
