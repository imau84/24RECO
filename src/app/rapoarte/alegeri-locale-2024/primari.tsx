'use client'

import { useState, type ReactNode } from 'react'
import { fmt0, fmt1 } from '../../industrii/agricultura/util'
import {
  Bare, Cadru as CadruComun, Comutator, Competitor, culoareComp, culoarePartid, eticheta, fara, frumos, incarcator,
  IND, Kpis, procent, Tabel, type Col, type Comp, type Rand,
} from './comune'

/* Alegeri locale 2024 — primari (tab-ul de nivel 1 „Primar”). Datele vin din
   public/data/alegeri-locale-2024/primari.json, generat cu scripts/build-primari-2024.py
   din exportul AEP (PV final); alianțele → partide din data/alegeri-locale-2024/aliante.json. */

/* ═════════════ date ═════════════ */
/** [nume, indice competitor, voturi, % din c] */
type Cand = [string, number, number, number]
export type Uat = {
  j: string; u: string; s: number; t: 'UAT' | 'sector'
  a: number; b: number; c: number; d: number; pr: number
  k: Cand[]; w: 0 | null; eg: boolean; mv: number; mp: number; nc: number
}
type Fisier = { sursa: string; data_pv: string; partide: Record<string, string>; competitori: Comp[]; uat: Uat[] }

type Date = Fisier & {
  /** partidele în care se descompune fiecare competitor (alianțele → componentele lor) */
  partideDe: string[][]
  castigate: Uat[]
}

const useDate = incarcator<Fisier, Date>('/data/alegeri-locale-2024/primari.json', f => ({
  ...f,
  partideDe: f.competitori.map(c => (c.t === 'independent' ? [IND] : c.p.length ? c.p : [c.n])),
  castigate: f.uat.filter(u => u.w === 0),
}))

const etichetaPartid = (d: Date, p: string) => (p === IND || d.partide[p] ? p : frumos(p))
const marja = (u: Uat) => `${fmt1(u.mp)} pp (${fmt0(u.mv)})`

/* ═════════════ piese comune ═════════════ */
function Cadru({ d, err, children }: { d: Date | null; err: boolean; children: (d: Date) => ReactNode }) {
  return <CadruComun d={d} err={err} mesaj="Se încarcă rezultatele pentru primari…">{children}</CadruComun>
}

function Sursa({ nota }: { nota?: ReactNode }) {
  return (
    <div className="ma-src">
      📌 Sursă: Autoritatea Electorală Permanentă · <a href="https://prezenta.roaep.ro/locale09062024v2/romania/pv-final" target="_blank" rel="noopener noreferrer">prezenta.roaep.ro</a> (procese-verbale finale, alegeri pentru primar, 9 iunie 2024) · Prelucrare: 24reco.com
      <br />Primarul General al Municipiului București nu este inclus; sectoarele 1–6 apar ca localități separate.
      {' '}La Poșaga (Alba) și Chețani (Mureș) primii doi candidați au avut același număr de voturi: nu există câștigător (egalitate – alegeri repetate), iar cele două localități nu sunt numărate la partide.
      {nota && <><br />{nota}</>}
    </div>
  )
}


/** coloanele comune pentru tabelele de UAT-uri */
function coloaneUat(d: Date, cuJudet: boolean): Col<Uat>[] {
  const castig = (u: Uat) => (u.w === 0 ? u.k[0] : null)
  return [
    ...(cuJudet ? [{ l: 'Județ', v: (u: Uat) => frumos(u.j) }] : []),
    { l: 'Localitate', v: u => frumos(u.u) },
    { l: 'Primar', v: u => (castig(u) ? frumos(castig(u)![0]) : 'Egalitate – alegeri repetate') },
    { l: 'Competitor', v: u => (castig(u) ? eticheta(d.competitori[castig(u)![1]]) : '—'), r: u => (castig(u) ? <Competitor c={d.competitori[castig(u)![1]]} /> : '—') },
    { l: 'Voturi', v: u => castig(u)?.[2] ?? 0, r: u => fmt0(castig(u)?.[2] ?? 0), n: true },
    { l: '%', v: u => castig(u)?.[3] ?? 0, r: u => procent(castig(u)?.[3] ?? 0), n: true },
    { l: 'Marjă', v: u => (u.w === 0 ? u.mp : 0), r: u => (u.w === 0 ? marja(u) : '0'), n: true, nw: true },
    { l: 'Prezență', v: u => u.pr, r: u => procent(u.pr), n: true },
  ]
}

/** toți candidații unei localități, cu bare, și cifrele din procesul-verbal */
function DetaliuUat({ d, u }: { d: Date; u: Uat }) {
  return <>
    <div className="pr-cand">
      {u.k.map(k => {
        const c = d.competitori[k[1]]
        return (
          <div key={k[0] + k[1]} className="r">
            <b>{frumos(k[0])}</b><span className="n">{fmt0(k[2])} · {procent(k[3])}</span>
            <small><Competitor c={c} />{c.s !== c.n && c.t !== 'independent' ? ` — ${frumos(c.n)}` : ''}</small>
            <div className="bar"><i style={{ width: `${k[3]}%`, background: culoareComp(c) }} /></div>
          </div>
        )
      })}
    </div>
    <div className="pr-pv">
      <span>a) Înscriși: <b>{fmt0(u.a)}</b></span><span>b) Au votat: <b>{fmt0(u.b)}</b> ({procent(u.pr)})</span>
      <span>c) Voturi valabile: <b>{fmt0(u.c)}</b></span><span>d) Voturi nule: <b>{fmt0(u.d)}</b></span>
      {u.eg && <span><b>Egalitate pe primul loc – alegeri repetate</b></span>}
    </div>
  </>
}

/** numărul de primari pe competitor (alianțele separat) sau pe partid (alianțele descompuse) */
function numara(d: Date, uat: Uat[], mod: 'comp' | 'partid'): Rand[] {
  const m = new Map<string, Rand>()
  for (const u of uat) {
    if (u.w !== 0) continue
    const ci = u.k[0][1], c = d.competitori[ci]
    const chei = mod === 'comp' ? [String(ci)] : d.partideDe[ci]
    for (const k of chei) {
      const r = m.get(k) ?? (mod === 'comp'
        ? { name: eticheta(c), v: 0, c: culoareComp(c), k }
        : { name: etichetaPartid(d, k), v: 0, c: culoarePartid(k), k })
      r.v++
      m.set(k, r)
    }
  }
  return Array.from(m.values()).sort((a, b) => b.v - a.v || a.name.localeCompare(b.name, 'ro'))
}

/* ═════════════ Pe scurt ═════════════ */
export function PrimariPeScurt() {
  const { d, err } = useDate()
  const [mod, setMod] = useState<'comp' | 'partid'>('comp')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  return <Cadru d={d} err={err}>{d => {
    const t = d.uat.reduce((s, u) => ({ a: s.a + u.a, b: s.b + u.b, c: s.c + u.c, d: s.d + u.d }), { a: 0, b: 0, c: 0, d: 0 })
    const n = d.castigate.length
    const rows = numara(d, d.uat, mod)
    const total = rows.reduce((s, r) => s + r.v, 0)
    const [p1, p2] = numara(d, d.uat, 'comp')
    return <>
      <Kpis items={[
        { l: 'Primării alocate', v: fmt0(n), h: `din ${fmt0(d.uat.length)} (inclusiv cele 6 sectoare); 2 la egalitate` },
        { l: 'Prezență', v: procent(t.b / t.a * 100), h: `${fmt0(t.b)} de oameni au votat din ${fmt0(t.a)} înscriși` },
        { l: 'Voturi valabile', v: fmt0(t.c), h: `${fmt1(t.c / t.b * 100)}% din cei care au votat` },
        { l: 'Voturi nule', v: fmt0(t.d), h: `${fmt1(t.d / t.b * 100)}% din cei care au votat` },
      ]} />
      <div className="ma-plain">
        💡 Pe 9 iunie 2024 s-au ales primarii a {fmt0(d.uat.length)} de localități. {p1.name} a câștigat {fmt0(p1.v)} de primării
        ({fmt0(p1.v / n * 100)}% din total), iar {p2.name} {fmt0(p2.v)}. Primarul e cel care a luat cele mai multe voturi, într-un singur tur.
      </div>
      <div className="ma-card">
        <div className="ma-ch">
          <h3>Primari pe {mod === 'comp' ? 'competitor' : 'partid'}</h3>
          <div className="pr-ch2">
            <Comutator v={mod} set={setMod} optiuni={[['comp', 'Pe competitor'], ['partid', 'Pe partid']]} />
            <Comutator v={vedere} set={setVedere} optiuni={[['grafic', '📈 Grafic'], ['tabel', '⊞ Tabel']]} />
          </div>
        </div>
        {mod === 'comp'
          ? <p className="pr-nota">Exact cum au candidat: alianțele (de ex. PSD-PNL, ADU) apar separat de partidele care le formează.</p>
          : <p className="pr-nota"><b>Alianțele sunt împărțite pe partide:</b> un primar câștigat de alianța PSD-PNL contează și la PSD, și la PNL.
            De aceea totalul ({fmt0(total)}) depășește numărul de primării ({fmt0(n)}). Independenții sunt un grup separat.</p>}
        {vedere === 'grafic'
          ? <Bare rows={rows} />
          : <Tabel<Rand> rows={rows} cheie={r => r.k ?? r.name} pePagina={50} cols={[
            { l: mod === 'comp' ? 'Competitor' : 'Partid', v: r => r.name, r: r => <><i className="pr-dot" style={{ background: r.c }} />{r.name}</> },
            { l: 'Primari', v: r => r.v, r: r => fmt0(r.v), n: true },
            { l: '% din primării', v: r => r.v, r: r => procent(r.v / n * 100), n: true },
          ]} sortare={{ i: 1, desc: true }} />}
        <Sursa />
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Partide ═════════════ */
export function PrimariPartide() {
  const { d, err } = useDate()
  const [partid, setPartid] = useState('PNL')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  const [q, setQ] = useState('')
  return <Cadru d={d} err={err}>{d => {
    const partide = numara(d, d.uat, 'partid').filter(r => r.k !== IND)
    const optiuni = partide.map(r => ({ k: r.k!, l: `${r.name} (${fmt0(r.v)})` }))
    const p = optiuni.some(o => o.k === partid) ? partid : optiuni[0].k
    const nume = etichetaPartid(d, p)
    const are = (ci: number) => d.partideDe[ci].includes(p)
    const castigate = d.castigate.filter(u => are(u.k[0][1]))
    const singur = castigate.filter(u => d.partideDe[u.k[0][1]].length === 1)
    const prinAliante = new Map<number, number>()
    for (const u of castigate) if (d.partideDe[u.k[0][1]].length > 1) prinAliante.set(u.k[0][1], (prinAliante.get(u.k[0][1]) ?? 0) + 1)
    // voturi și scor unde a candidat (o alianță contează întreagă la fiecare partid din ea)
    let voturi = 0, scoruri = 0, candidaturi = 0
    for (const u of d.uat) for (const k of u.k) if (are(k[1])) { voturi += k[2]; scoruri += k[3]; candidaturi++ }
    const scorCastig = castigate.length ? castigate.reduce((s, u) => s + u.k[0][3], 0) / castigate.length : 0
    const peMarja = [...castigate].sort((a, b) => b.mp - a.mp)
    const peJudete = new Map<string, number>()
    for (const u of castigate) peJudete.set(u.j, (peJudete.get(u.j) ?? 0) + 1)
    const judete: Rand[] = Array.from(peJudete, ([j, v]) => ({ name: frumos(j), v, c: culoarePartid(p) })).sort((a, b) => b.v - a.v || a.name.localeCompare(b.name, 'ro'))
    const cauta = fara(q.trim())
    const tabel = cauta ? castigate.filter(u => fara(u.u).includes(cauta) || fara(u.j).includes(cauta) || fara(u.k[0][0]).includes(cauta)) : castigate
    const loc = (u: Uat) => `${frumos(u.u)} (${frumos(u.j)})`

    return <>
      <div className="pr-bara">
        <label>Partid
          <select value={p} onChange={e => setPartid(e.target.value)}>
            {optiuni.map(o => <option key={o.k} value={o.k}>{o.l}</option>)}
          </select>
        </label>
      </div>
      <Kpis items={[
        { l: 'Primării câștigate', v: fmt0(castigate.length), h: `${fmt0(singur.length)} singur · ${fmt0(castigate.length - singur.length)} prin alianțe` },
        { l: 'Voturi pentru primar', v: fmt0(voturi), h: `${fmt0(candidaturi)} de candidați${prinAliante.size || castigate.length !== singur.length ? ', inclusiv voturile alianțelor din care face parte' : ''}` },
        { l: 'Scor mediu unde a câștigat', v: procent(scorCastig), h: 'media procentelor primarilor aleși' },
        { l: 'Scor mediu unde a candidat', v: procent(candidaturi ? scoruri / candidaturi : 0), h: 'media procentelor tuturor candidaților' },
      ]} />
      <div className="ma-plain">
        💡 {d.partide[p] ? `${nume} (${frumos(d.partide[p])})` : nume} a câștigat {fmt0(castigate.length)} {castigate.length === 1 ? 'primărie' : 'de primării'}:
        {' '}{fmt0(singur.length)} cu candidați proprii{prinAliante.size > 0 && <> și {fmt0(castigate.length - singur.length)} prin alianțe
        ({Array.from(prinAliante, ([ci, v]) => `${fmt0(v)} prin ${frumos(d.competitori[ci].n)}`).join(', ')})</>}.
      </div>
      {prinAliante.size > 0 && (
        <div className="ma-card">
          <div className="ma-ch"><h3>{nume}: singur și prin alianțe</h3></div>
          <Tabel<{ c: Comp | null; v: number }> pePagina={50} cheie={r => r.c?.n ?? '_'}
            rows={[{ c: null, v: singur.length }, ...Array.from(prinAliante, ([ci, v]) => ({ c: d.competitori[ci], v }))]}
            sortare={{ i: 1, desc: true }}
            cols={[
              { l: 'Cum a candidat', v: r => (r.c ? frumos(r.c.n) : `Singur (${nume})`), r: r => (r.c ? <><Competitor c={r.c} /><br /><small>{frumos(r.c.n)}</small></> : <><i className="pr-dot" style={{ background: culoarePartid(p) }} />Singur ({nume})</>) },
              { l: 'Primării', v: r => r.v, r: r => fmt0(r.v), n: true },
            ]} />
        </div>
      )}
      <div className="ma-card pr-gap">
        <div className="ma-ch">
          <h3>Primarii {nume} pe județe</h3>
          <Comutator v={vedere} set={setVedere} optiuni={[['grafic', '📈 Grafic'], ['tabel', '⊞ Tabel']]} />
        </div>
        {judete.length === 0 ? <p className="pr-nota">Niciun primar.</p> : vedere === 'grafic' ? <Bare rows={judete} /> : (
          <Tabel<Rand> rows={judete} cheie={r => r.name} pePagina={50} sortare={{ i: 1, desc: true }} cols={[
            { l: 'Județ', v: r => r.name },
            { l: 'Primari', v: r => r.v, r: r => fmt0(r.v), n: true },
            { l: `% din primarii ${nume}`, v: r => r.v, r: r => procent(r.v / castigate.length * 100), n: true },
          ]} />
        )}
      </div>
      {castigate.length > 0 && (
        <div className="ma-card pr-gap">
          <div className="ma-ch"><h3>Cele mai mari și cele mai mici victorii</h3></div>
          <div className="pr-lista">
            <div><h4>Cea mai mare diferență față de locul 2</h4>
              <ol>{peMarja.slice(0, 5).map(u => <li key={u.s}>{loc(u)} — {frumos(u.k[0][0])}, {procent(u.k[0][3])}, marjă {marja(u)}</li>)}</ol></div>
            <div><h4>Cea mai mică diferență</h4>
              <ol>{peMarja.slice(-5).reverse().map(u => <li key={u.s}>{loc(u)} — {frumos(u.k[0][0])}, {procent(u.k[0][3])}, marjă {marja(u)}</li>)}</ol></div>
          </div>
          <p className="pr-mic ma-src">Marja = diferența dintre primul și al doilea candidat, în puncte procentuale din voturile valabile (și în voturi).</p>
        </div>
      )}
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Localitățile câștigate de {nume}</h3></div>
        <div className="pr-bara">
          <label>Caută localitate, județ sau primar
            <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="ex. Cluj, Popescu" />
          </label>
        </div>
        <Tabel<Uat> rows={tabel} cheie={u => String(u.s)} cols={coloaneUat(d, true).slice(0, 7)} sortare={{ i: 4, desc: true }} />
        <Sursa nota={`„Voturi” la partid include voturile alianțelor din care face parte ${nume}, numărate întreg.`} />
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Județe ═════════════ */
const PRINCIPALE = ['PSD', 'PNL', 'UDMR', 'USR', 'AUR', 'PMP', 'FD', IND]

export function PrimariJudete() {
  const { d, err } = useDate()
  const [judet, setJudet] = useState('')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  return <Cadru d={d} err={err}>{d => {
    const judete = Array.from(new Set(d.uat.map(u => u.j))).sort((a, b) => a.localeCompare(b, 'ro'))
    const j = judete.includes(judet) ? judet : judete[0]
    const uat = d.uat.filter(u => u.j === j)
    const rows = numara(d, uat, 'comp')
    const t = uat.reduce((s, u) => ({ a: s.a + u.a, b: s.b + u.b }), { a: 0, b: 0 })
    const egal = uat.filter(u => u.eg)
    type RJ = { j: string; n: number; pr: number; lider: Rand; pe: Record<string, number> }
    const toate: RJ[] = judete.map(jj => {
      const uu = d.uat.filter(u => u.j === jj)
      const pe = numara(d, uu, 'partid')
      const s = uu.reduce((x, u) => ({ a: x.a + u.a, b: x.b + u.b }), { a: 0, b: 0 })
      return { j: jj, n: uu.length, pr: s.b / s.a * 100, lider: pe[0], pe: Object.fromEntries(pe.map(r => [r.k!, r.v])) }
    })

    return <>
      <div className="pr-bara">
        <label>Județ
          <select value={j} onChange={e => setJudet(e.target.value)}>
            {judete.map(x => <option key={x} value={x}>{frumos(x)}</option>)}
          </select>
        </label>
      </div>
      <div className="ma-plain">
        💡 În {frumos(j)} s-au ales primarii a {fmt0(uat.length)} {uat.length === 1 ? 'localitate' : uat.length >= 20 ? 'de localități' : 'localități'}.
        {rows[0] && <> Cei mai mulți sunt de la {rows[0].name} ({fmt0(rows[0].v)}).</>} Prezența a fost de {procent(t.b / t.a * 100)}.
        {egal.length > 0 && <> La {egal.map(u => frumos(u.u)).join(', ')} a fost egalitate pe primul loc.</>}
      </div>
      <div className="ma-card">
        <div className="ma-ch">
          <h3>Primari pe competitor — {frumos(j)}</h3>
          <Comutator v={vedere} set={setVedere} optiuni={[['grafic', '📈 Grafic'], ['tabel', '⊞ Tabel']]} />
        </div>
        {vedere === 'grafic' ? <Bare rows={rows} /> : (
          <Tabel<Rand> rows={rows} cheie={r => r.k ?? r.name} pePagina={50} sortare={{ i: 1, desc: true }} cols={[
            { l: 'Competitor', v: r => r.name, r: r => <><i className="pr-dot" style={{ background: r.c }} />{r.name}</> },
            { l: 'Primari', v: r => r.v, r: r => fmt0(r.v), n: true },
          ]} />
        )}
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Localitățile din {frumos(j)}</h3></div>
        <Tabel<Uat> rows={uat} cheie={u => String(u.s)} cols={coloaneUat(d, false).filter(c => c.l !== 'Voturi')} sortare={{ i: 0, desc: false }}
          detaliu={u => <DetaliuUat d={d} u={u} />} />
        <p className="ma-src">Apasă pe o localitate ca să vezi toți candidații.</p>
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Toate județele</h3></div>
        <p className="pr-nota">Primari pe partid, cu alianțele împărțite pe partide (un primar PSD-PNL contează la ambele).</p>
        <Tabel<RJ> rows={toate} cheie={r => r.j} pePagina={50} sortare={{ i: 0, desc: false }} cols={[
          { l: 'Județ', v: r => frumos(r.j) },
          { l: 'Primării', v: r => r.n, r: r => fmt0(r.n), n: true },
          { l: 'Cei mai mulți', v: r => r.lider?.name ?? '', r: r => (r.lider ? <><i className="pr-dot" style={{ background: r.lider.c }} />{r.lider.name}</> : '—'), nw: true },
          ...PRINCIPALE.map((p): Col<RJ> => ({ l: p === IND ? 'Indep.' : p, v: r => r.pe[p] ?? 0, r: r => (r.pe[p] ? fmt0(r.pe[p]) : '–'), n: true })),
          { l: 'Prezență', v: r => r.pr, r: r => procent(r.pr), n: true },
        ]} />
        <Sursa />
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Localități ═════════════ */
export function PrimariLocalitati() {
  const { d, err } = useDate()
  const [q, setQ] = useState('')
  const [judet, setJudet] = useState('')
  const [filtru, setFiltru] = useState('')
  const [rol, setRol] = useState<'castigator' | 'candidat'>('castigator')
  return <Cadru d={d} err={err}>{d => {
    const judete = Array.from(new Set(d.uat.map(u => u.j))).sort((a, b) => a.localeCompare(b, 'ro'))
    const partide = numara(d, d.uat, 'partid')
    const comps = d.competitori.map((c, i) => ({ c, i })).filter(x => x.c.t !== 'independent')
      .sort((a, b) => eticheta(a.c).localeCompare(eticheta(b.c), 'ro'))
    const potriveste = (ci: number) => {
      if (!filtru) return true
      if (filtru.startsWith('p:')) return d.partideDe[ci].includes(filtru.slice(2))
      return ci === Number(filtru.slice(2))
    }
    const c = fara(q.trim())
    return <Lista d={d} rows={d.uat.filter(u => (!judet || u.j === judet) && (!c || fara(u.u).includes(c))
      && (!filtru || (rol === 'castigator' ? u.w === 0 && potriveste(u.k[0][1]) : u.k.some(k => potriveste(k[1])))))}>
      <div className="pr-bara">
        <label>Caută localitatea
          <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="ex. Florești, Sectorul 3" />
        </label>
        <label>Județ
          <select value={judet} onChange={e => setJudet(e.target.value)}>
            <option value="">Toate județele</option>
            {judete.map(x => <option key={x} value={x}>{frumos(x)}</option>)}
          </select>
        </label>
        <label>Partid / competitor
          <select value={filtru} onChange={e => setFiltru(e.target.value)}>
            <option value="">Toți</option>
            <optgroup label="Partide (inclusiv prin alianțe)">
              {partide.map(r => <option key={r.k} value={'p:' + r.k}>{r.name}</option>)}
            </optgroup>
            <optgroup label="Competitori (exact cum au candidat)">
              {comps.map(x => <option key={x.i} value={'c:' + x.i}>{eticheta(x.c)}</option>)}
            </optgroup>
          </select>
        </label>
        <label>Partidul / competitorul ales
          <select value={rol} onChange={e => setRol(e.target.value as 'castigator' | 'candidat')} disabled={!filtru}>
            <option value="castigator">a câștigat primăria</option>
            <option value="candidat">a avut candidat</option>
          </select>
        </label>
      </div>
    </Lista>
  }}</Cadru>
}

function Lista({ d, rows, children }: { d: Date; rows: Uat[]; children: ReactNode }) {
  return <>
    {children}
    <div className="ma-card">
      <div className="ma-ch"><h3>{fmt0(rows.length)} {rows.length === 1 ? 'localitate' : 'localități'}</h3></div>
      <Tabel<Uat> rows={rows} cheie={u => String(u.s)} cols={coloaneUat(d, true)} sortare={{ i: 1, desc: false }}
        detaliu={u => <DetaliuUat d={d} u={u} />} />
      <p className="ma-src">Apasă pe o localitate ca să vezi toți candidații, cu voturile lor și cifrele din procesul-verbal.</p>
      <Sursa />
    </div>
  </>
}
