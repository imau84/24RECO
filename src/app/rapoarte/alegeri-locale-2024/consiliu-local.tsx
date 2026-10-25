'use client'

import { useState, type ReactNode } from 'react'
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { fmt0, fmt1 } from '../../industrii/agricultura/util'
import {
  Bare, Cadru as CadruComun, Comutator, Competitor, culoareComp, culoarePartid, eticheta, fara, frumos, incarcator,
  IND, Kpis, procent, Tabel, type Col, type Comp, type Rand,
} from './comune'

/* Alegeri locale 2024 — consilii locale (tab-ul de nivel 1 „Consiliu local”). Datele vin din
   public/data/alegeri-locale-2024/consiliu-local.json, generat cu scripts/build-consiliu-local-2024.py
   din CSV-urile AEP (PV final); alianțele → partide din data/alegeri-locale-2024/aliante.json.
   Mandatele unei liste de alianță nu se pot împărți pe partide (PV-ul nu spune de la ce partid e
   fiecare consilier), așa că în modul „pe partid” ele apar întregi la fiecare partid din alianță. */

/* ═════════════ date ═════════════ */
/** [competitor, voturi, % din c, mandate faza 1, faza 2, minorități (g8+g9), total] */
type K = [number, number, number, number, number, number, number]
type Uat = {
  j: string; u: string; s: number; t: 'UAT' | 'sector'
  a: number; b: number; c: number; d: number; pr: number
  /** mărimea consiliului */
  m: number
  k: K[]
  /** primul competitor (cele mai multe mandate) are majoritate absolută; lp = câte mandate îi lipsesc */
  maj: boolean; lp: number; eg: boolean
  /** [primar, competitor, mandatele competitorului primarului, are majoritate] — lipsește la egalitate */
  p?: [string, number, number, boolean]
}
type Fisier = { sursa: string; partide: Record<string, string>; competitori: Comp[]; uat: Uat[] }
type Date = Fisier & {
  partideDe: string[][]
  t: { a: number; b: number; c: number; d: number; m: number; f1: number; f2: number; g8: number }
}

const useDate = incarcator<Fisier, Date>('/data/alegeri-locale-2024/consiliu-local.json', f => {
  const t = { a: 0, b: 0, c: 0, d: 0, m: 0, f1: 0, f2: 0, g8: 0 }
  for (const u of f.uat) {
    t.a += u.a; t.b += u.b; t.c += u.c; t.d += u.d; t.m += u.m
    for (const k of u.k) { t.f1 += k[3]; t.f2 += k[4]; t.g8 += k[5] }
  }
  return { ...f, t, partideDe: f.competitori.map(c => (c.t === 'independent' ? [IND] : c.p.length ? c.p : [c.n])) }
})

const etichetaPartid = (d: Date, p: string) => (p === IND || d.partide[p] ? p : frumos(p))
/** numele afișat: abrevierea sau numele (independenții = numele persoanei) */
const numeComp = (d: Date, ci: number) => eticheta(d.competitori[ci])
const lider = (u: Uat) => u.k[0]
const loc = (u: Uat) => `${frumos(u.u)} (${frumos(u.j)})`
/** „de” după numerale de la 20 în sus („27 de locuri”, dar „13 locuri”) */
const de = (n: number) => (n % 100 >= 20 || (n > 0 && n % 100 === 0) ? 'de ' : '')
const consilii = (n: number) => (n === 1 ? 'consiliu' : de(n) + 'consilii')

function Cadru({ d, err, children }: { d: Date | null; err: boolean; children: (d: Date) => ReactNode }) {
  return <CadruComun d={d} err={err} mesaj="Se încarcă rezultatele pentru consiliile locale…">{children}</CadruComun>
}

const NOTA_ALIANTE = 'Mandatele obținute de o listă de alianță (de ex. PSD-PNL, ADU) apar întregi la fiecare partid din alianță, pentru că procesul-verbal nu spune din ce partid face parte fiecare consilier ales pe listă.'

function Sursa({ nota }: { nota?: ReactNode }) {
  return (
    <div className="ma-src">
      📌 Sursă: Autoritatea Electorală Permanentă · <a href="https://prezenta.roaep.ro/locale09062024v2/romania/pv-final" target="_blank" rel="noopener noreferrer">prezenta.roaep.ro</a> (procese-verbale finale, alegeri pentru consiliul local, 9 iunie 2024) · Prelucrare: 24reco.com
      <br />Consiliul General al Municipiului București nu este inclus; consiliile celor 6 sectoare apar ca localități separate. {NOTA_ALIANTE}
      {nota && <><br />{nota}</>}
    </div>
  )
}

/* ═════════════ calcule ═════════════ */
type RandM = Rand & { proprii: number; ali: number; voturi: number; f1: number; f2: number; g8: number }

/** mandate pe competitor (exact cum au candidat) sau pe partid (proprii + prin alianțe, separat) */
function mandate(d: Date, uat: Uat[], mod: 'comp' | 'partid'): RandM[] {
  const m = new Map<string, RandM>()
  for (const u of uat) {
    for (const x of u.k) {
      const ci = x[0], pd = d.partideDe[ci]
      const chei = mod === 'comp' ? [String(ci)] : pd
      for (const k of chei) {
        let r = m.get(k)
        if (!r) {
          r = mod === 'comp'
            ? { name: numeComp(d, ci), v: 0, c: culoareComp(d.competitori[ci]), k, proprii: 0, ali: 0, voturi: 0, f1: 0, f2: 0, g8: 0 }
            : { name: etichetaPartid(d, k), v: 0, c: culoarePartid(k), k, proprii: 0, ali: 0, voturi: 0, f1: 0, f2: 0, g8: 0 }
          m.set(k, r)
        }
        r.v += x[6]; r.voturi += x[1]; r.f1 += x[3]; r.f2 += x[4]; r.g8 += x[5]
        if (mod === 'partid' && pd.length > 1) r.ali += x[6]
        else r.proprii += x[6]
      }
    }
  }
  return Array.from(m.values()).filter(r => r.v > 0 || r.voturi > 0)
    .sort((a, b) => b.v - a.v || b.voturi - a.voturi || a.name.localeCompare(b.name, 'ro'))
}

/** câte consilii are fiecare partid / competitor cu majoritate absolută */
function majoritati(d: Date, uat: Uat[], mod: 'comp' | 'partid') {
  const m = new Map<string, number>()
  for (const u of uat) if (u.maj) for (const k of mod === 'comp' ? [String(lider(u)[0])] : d.partideDe[lider(u)[0]]) m.set(k, (m.get(k) ?? 0) + 1)
  return m
}

/* ═════════════ grafic stivuit: mandate proprii + prin alianțe ═════════════ */
function BareStivuite({ rows }: { rows: RandM[] }) {
  return (
    <div style={{ height: rows.length * 26 + 36 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 40 }}>
          <CartesianGrid horizontal={false} stroke="#eef0f6" />
          <XAxis type="number" tick={{ fontSize: 11, fill: '#9aa3b8' }} tickFormatter={x => fmt0(Number(x))} allowDecimals={false} />
          <YAxis type="category" dataKey="name" width={128} interval={0} tick={{ fontSize: 11, fill: '#5a6178' }}
            tickFormatter={(s: string) => (s.length > 21 ? s.slice(0, 20) + '…' : s)} />
          <Tooltip formatter={(x, n) => [fmt0(Number(x)), n === 'proprii' ? 'Mandate proprii' : 'Prin alianțe (comune)']} />
          <Bar dataKey="proprii" stackId="m" isAnimationActive={false}>
            {rows.map(r => <Cell key={r.name} fill={r.c} />)}
          </Bar>
          <Bar dataKey="ali" stackId="m" radius={[0, 6, 6, 0]} isAnimationActive={false}
            label={{ position: 'right', fontSize: 11, fill: '#5a6178', formatter: (x: number) => fmt0(x) }}>
            {rows.map(r => <Cell key={r.name} fill={r.c} fillOpacity={0.4} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

const Legenda = () => (
  <p className="pr-nota">
    <i className="pr-dot" style={{ background: '#5a6178' }} />mandate proprii (liste ale partidului)
    {'  '}<i className="pr-dot" style={{ background: '#5a6178', opacity: 0.4, marginLeft: 12 }} />mandate prin alianțe (comune cu celelalte partide din alianță)
  </p>
)

/* ═════════════ hemiciclu: un punct pe loc în consiliu ═════════════ */
function Hemiciclu({ d, u }: { d: Date; u: Uat }) {
  const n = u.m
  const randuri = n <= 11 ? 2 : n <= 19 ? 3 : n <= 27 ? 4 : 5
  const r0 = 0.42
  const raze = Array.from({ length: randuri }, (_, i) => r0 + (1 - r0) * i / (randuri - 1))
  const sr = raze.reduce((s, r) => s + r, 0)
  const pe = raze.map(r => Math.max(1, Math.round(n * r / sr)))
  pe[randuri - 1] += n - pe.reduce((s, x) => s + x, 0)
  const locuri: { x: number; y: number; a: number; r: number }[] = []
  raze.forEach((r, i) => {
    for (let j = 0; j < pe[i]; j++) {
      const a = pe[i] === 1 ? Math.PI / 2 : Math.PI * (1 - j / (pe[i] - 1))
      locuri.push({ x: r * Math.cos(a), y: -r * Math.sin(a), a, r })
    }
  })
  locuri.sort((p, q) => q.a - p.a || p.r - q.r)
  const culori = u.k.flatMap(x => Array<string>(x[6]).fill(culoareComp(d.competitori[x[0]])))
  const rLoc = Math.min((1 - r0) / (randuri - 1) * 0.42, Math.PI * r0 / Math.max(1, pe[0] - 1) * 0.42)
  return (
    <svg viewBox="-1.08 -1.08 2.16 1.16" className="cl-hemi" role="img" aria-label={`Componența consiliului: ${n} locuri`}>
      {locuri.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={rLoc} fill={culori[i] ?? '#dfe3ee'} />)}
      <text x="0" y="-0.12" textAnchor="middle" fontSize="0.2" fontWeight="800" fill="#2a3045">{n}</text>
      <text x="0" y="0.02" textAnchor="middle" fontSize="0.09" fill="#5a6178">locuri · majoritate {Math.floor(n / 2) + 1}</text>
    </svg>
  )
}

const CSS_CL = `
  .cl-hemi{width:100%;max-width:340px;display:block;margin:4px auto 8px}
  .cl-det{display:grid;grid-template-columns:minmax(0,340px) minmax(0,1fr);gap:16px;align-items:start}
  .cl-fz{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}
  .cl-fz div{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:12.5px;line-height:1.45;color:var(--ink2)}
  .cl-fz b{display:block;font-size:20px;color:var(--ink);margin-bottom:2px}
  .cl-tag{display:inline-block;font-size:11.5px;font-weight:700;border-radius:6px;padding:1px 7px;white-space:nowrap}
  .cl-da{background:#e3f6ea;color:#1d7a44}.cl-nu{background:#f3f4f8;color:#6a7187}
  @media(max-width:820px){.cl-det{grid-template-columns:1fr}.cl-fz{grid-template-columns:1fr}}
`
const Stil = () => <style dangerouslySetInnerHTML={{ __html: CSS_CL }} />
const DaNu = ({ da, t }: { da: boolean; t?: [string, string] }) => <span className={'cl-tag ' + (da ? 'cl-da' : 'cl-nu')}>{da ? t?.[0] ?? 'da' : t?.[1] ?? 'nu'}</span>

/** componența consiliului, toți competitorii și primarul */
function DetaliuUat({ d, u }: { d: Date; u: Uat }) {
  const l = lider(u)
  return <>
    <div className="cl-det">
      <div>
        <Hemiciclu d={d} u={u} />
        <p className="pr-nota" style={{ margin: 0 }}>
          {u.maj
            ? <><b>{numeComp(d, l[0])}</b> are majoritate absolută: {fmt0(l[6])} din {fmt0(u.m)} {de(u.m)}locuri.</>
            : <>Niciun competitor nu are majoritate. Primul, <b>{numeComp(d, l[0])}</b>, are {fmt0(l[6])} din {fmt0(u.m)} {de(u.m)}locuri — îi lipsesc {fmt0(u.lp)}.</>}
          {u.p
            ? <><br />Primar: <b>{frumos(u.p[0])}</b> ({numeComp(d, u.p[1])}) — {u.p[3] ? 'are majoritate în consiliu' : `nu are majoritate în consiliu (${fmt0(u.p[2])} ${u.p[2] === 1 ? 'mandat' : de(u.p[2]) + 'mandate'})`}.</>
            : <><br />Primar: egalitate la primul loc – alegeri repetate.</>}
        </p>
      </div>
      <div className="ma-tbl pr-tbl">
        <table>
          <thead><tr><th>Competitor</th><th className="n">Voturi</th><th className="n">%</th><th className="n">Faza 1</th><th className="n">Faza 2</th><th className="n">Minor.</th><th className="n">Mandate</th></tr></thead>
          <tbody>
            {u.k.map(x => (
              <tr key={x[0]}>
                <td><Competitor c={d.competitori[x[0]]} /></td>
                <td className="n">{fmt0(x[1])}</td><td className="n">{procent(x[2])}</td>
                <td className="n">{x[3] || '–'}</td><td className="n">{x[4] || '–'}</td><td className="n">{x[5] || '–'}</td>
                <td className="n"><b>{x[6] || '–'}</b></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
    <div className="pr-pv">
      <span>a) Înscriși: <b>{fmt0(u.a)}</b></span><span>b) Au votat: <b>{fmt0(u.b)}</b> ({procent(u.pr)})</span>
      <span>c) Voturi valabile: <b>{fmt0(u.c)}</b></span><span>d) Voturi nule: <b>{fmt0(u.d)}</b></span>
    </div>
  </>
}

/** coloanele comune pentru tabelele de UAT-uri */
function coloaneUat(d: Date, cuJudet: boolean): Col<Uat>[] {
  return [
    ...(cuJudet ? [{ l: 'Județ', v: (u: Uat) => frumos(u.j) }] : []),
    { l: 'Localitate', v: u => frumos(u.u) },
    { l: 'Locuri', v: u => u.m, n: true },
    { l: 'Primul în consiliu', v: u => numeComp(d, lider(u)[0]), r: u => <><Competitor c={d.competitori[lider(u)[0]]} /> · {lider(u)[6]}</> },
    { l: 'Majoritate', v: u => (u.maj ? 1 : 0), r: u => <DaNu da={u.maj} t={['da', `nu (−${u.lp})`]} />, n: true },
    { l: 'Primar', v: u => (u.p ? numeComp(d, u.p[1]) : ''), r: u => (u.p ? <><Competitor c={d.competitori[u.p[1]]} /> · {u.p[2]}</> : 'egalitate') },
    { l: 'Prezență', v: u => u.pr, r: u => procent(u.pr), n: true },
  ]
}

/* ═════════════ Pe scurt ═════════════ */
const MAX_GRAFIC = 20

export function ConsiliuPeScurt() {
  const { d, err } = useDate()
  const [mod, setMod] = useState<'comp' | 'partid'>('comp')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  return <Cadru d={d} err={err}>{d => {
    const { t } = d
    const rows = mandate(d, d.uat, mod)
    const [p1, p2] = mandate(d, d.uat, 'comp')
    const maj = d.uat.filter(u => u.maj).length
    return <>
      <Stil />
      <Kpis cls="pr-k5" items={[
        { l: 'Mandate de consilier', v: fmt0(t.m), h: 'câți consilieri locali s-au ales' },
        { l: 'Consilii locale', v: fmt0(d.uat.length), h: 'inclusiv cele 6 sectoare' },
        { l: 'Voturi valabile', v: fmt0(t.c), h: `${fmt1(t.c / t.b * 100)}% din cei care au votat` },
        { l: 'Prezență', v: procent(t.b / t.a * 100), h: `${fmt0(t.b)} din ${fmt0(t.a)} înscriși` },
        { l: 'Voturi nule', v: fmt0(t.d), h: `${fmt1(t.d / t.b * 100)}% din cei care au votat` },
      ]} />
      <div className="ma-plain">
        💡 S-au ales {fmt0(t.m)} de consilieri locali în {fmt0(d.uat.length)} de localități. {p1.name} are cei mai mulți ({fmt0(p1.v)}, adică {fmt0(p1.v / t.m * 100)}%),
        urmat de {p2.name} ({fmt0(p2.v)}). În {fmt0(maj)} {consilii(maj)} un singur competitor are peste jumătate din locuri; în celelalte {fmt0(d.uat.length - maj)} e nevoie de o coaliție.
      </div>
      <div className="ma-card">
        <div className="ma-ch">
          <h3>Mandate pe {mod === 'comp' ? 'competitor' : 'partid'}</h3>
          <div className="pr-ch2">
            <Comutator v={mod} set={setMod} optiuni={[['comp', 'Pe competitor'], ['partid', 'Pe partid']]} />
            <Comutator v={vedere} set={setVedere} optiuni={[['grafic', '📈 Grafic'], ['tabel', '⊞ Tabel']]} />
          </div>
        </div>
        {mod === 'comp'
          ? <p className="pr-nota">Exact cum au candidat: alianțele (de ex. PSD-PNL, ADU) apar separat de partidele care le formează. Independenții sunt numărați împreună în modul „Pe partid”.</p>
          : <p className="pr-nota"><b>Atenție:</b> {NOTA_ALIANTE} De aceea totalul pe partide depășește {fmt0(t.m)}.</p>}
        {vedere === 'grafic'
          ? <>
            {mod === 'partid' ? <><Legenda /><BareStivuite rows={rows.slice(0, MAX_GRAFIC)} /></> : <Bare rows={rows.slice(0, MAX_GRAFIC)} eticheta="Mandate" />}
            {rows.length > MAX_GRAFIC && <p className="ma-src">Graficul arată primii {MAX_GRAFIC}; toți {fmt0(rows.length)} sunt în tabel.</p>}
          </>
          : <Tabel<RandM> rows={rows} cheie={r => r.k ?? r.name} pePagina={25} sortare={{ i: mod === 'comp' ? 1 : 3, desc: true }} cols={[
            { l: mod === 'comp' ? 'Competitor' : 'Partid', v: r => r.name, r: r => <><i className="pr-dot" style={{ background: r.c }} />{r.name}</> },
            ...(mod === 'comp'
              ? [{ l: 'Mandate', v: (r: RandM) => r.v, r: (r: RandM) => fmt0(r.v), n: true }]
              : [
                { l: 'Proprii', v: (r: RandM) => r.proprii, r: (r: RandM) => fmt0(r.proprii), n: true },
                { l: 'Prin alianțe', v: (r: RandM) => r.ali, r: (r: RandM) => (r.ali ? fmt0(r.ali) : '–'), n: true },
                { l: 'Total', v: (r: RandM) => r.v, r: (r: RandM) => <b>{fmt0(r.v)}</b>, n: true },
              ]),
            { l: '% mandate', v: r => r.v, r: r => procent(r.v / t.m * 100), n: true },
            { l: '% voturi', v: r => r.voturi, r: r => procent(r.voturi / t.c * 100), n: true },
          ]} />}
        <Sursa />
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Cum se împart mandatele</h3></div>
        <div className="cl-fz">
          <div><b>{fmt0(t.f1)}</b>Faza 1 — mandate date direct: voturile fiecărei liste se împart la coeficientul electoral (voturile valabile ale listelor care au trecut pragul, împărțite la numărul de locuri).</div>
          <div><b>{fmt0(t.f2)}</b>Faza 2 — locurile rămase neocupate după faza 1 se dau pe resturile de voturi, listelor care au trecut pragul (cele mai mari resturi primesc câte un loc).</div>
          <div><b>{fmt0(t.g8)}</b>Minorități — un loc dat organizației unei minorități naționale care n-a trecut pragul, dar a luat cele mai multe voturi dintre organizațiile minorităților din localitate.</div>
        </div>
        {mod === 'comp' && (
          <div className="pr-gap">
            <Tabel<RandM> rows={rows.filter(r => r.v > 0)} cheie={r => r.k ?? r.name} pePagina={10} sortare={{ i: 4, desc: true }} cols={[
              { l: 'Competitor', v: r => r.name, r: r => <><i className="pr-dot" style={{ background: r.c }} />{r.name}</> },
              { l: 'Faza 1', v: r => r.f1, r: r => fmt0(r.f1), n: true },
              { l: 'Faza 2', v: r => r.f2, r: r => fmt0(r.f2), n: true },
              { l: 'Minorități', v: r => r.g8, r: r => (r.g8 ? fmt0(r.g8) : '–'), n: true },
              { l: 'Total', v: r => r.v, r: r => <b>{fmt0(r.v)}</b>, n: true },
            ]} />
          </div>
        )}
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Partide ═════════════ */
export function ConsiliuPartide() {
  const { d, err } = useDate()
  const [partid, setPartid] = useState('PNL')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  const [q, setQ] = useState('')
  return <Cadru d={d} err={err}>{d => {
    const partide = mandate(d, d.uat, 'partid').filter(r => r.k !== IND && r.v > 0)
    const p = partide.some(o => o.k === partid) ? partid : partide[0].k!
    const r = partide.find(o => o.k === p)!
    const nume = etichetaPartid(d, p)
    const are = (ci: number) => d.partideDe[ci].includes(p)
    // alianțele partidului, cu mandatele fiecăreia
    const aliante = new Map<number, number>()
    let cuConsilier = 0, cuMaj = 0, primul = 0
    type RU = { u: Uat; x: K }
    const uat: RU[] = []
    for (const u of d.uat) {
      const ale = u.k.filter(x => are(x[0]))
      for (const x of ale) if (d.partideDe[x[0]].length > 1) aliante.set(x[0], (aliante.get(x[0]) ?? 0) + x[6])
      if (ale.some(x => x[6] > 0)) cuConsilier++
      if (are(lider(u)[0])) { primul++; if (u.maj) cuMaj++ }
      for (const x of ale) uat.push({ u, x })
    }
    const ef = r.v / d.t.m * 100, ev = r.voturi / d.t.c * 100
    const peJ = new Map<string, RandM>()
    const majJ = new Map<string, number>()
    for (const { u, x } of uat) {
      const o = peJ.get(u.j) ?? { name: frumos(u.j), v: 0, c: culoarePartid(p), k: u.j, proprii: 0, ali: 0, voturi: 0, f1: 0, f2: 0, g8: 0 }
      o.v += x[6]; o.voturi += x[1]
      if (d.partideDe[x[0]].length > 1) o.ali += x[6]; else o.proprii += x[6]
      if (u.maj && lider(u)[0] === x[0]) majJ.set(u.j, (majJ.get(u.j) ?? 0) + 1)
      peJ.set(u.j, o)
    }
    const judete = Array.from(peJ.values()).filter(o => o.v > 0).sort((a, b) => b.v - a.v || a.name.localeCompare(b.name, 'ro'))
    const cauta = fara(q.trim())
    const tabel = cauta ? uat.filter(({ u }) => fara(u.u).includes(cauta) || fara(u.j).includes(cauta)) : uat

    return <>
      <Stil />
      <div className="pr-bara">
        <label>Partid
          <select value={p} onChange={e => setPartid(e.target.value)}>
            {partide.map(o => <option key={o.k} value={o.k}>{o.name} ({fmt0(o.v)})</option>)}
          </select>
        </label>
      </div>
      <Kpis items={[
        { l: 'Mandate de consilier', v: fmt0(r.v), h: `${fmt0(r.proprii)} proprii · ${fmt0(r.ali)} prin alianțe` },
        { l: 'Consilii cu cel puțin un consilier', v: fmt0(cuConsilier), h: `din ${fmt0(d.uat.length)}` },
        { l: 'Consilii cu majoritate', v: fmt0(cuMaj), h: 'peste jumătate din locuri (singur sau prin alianță)' },
        { l: 'Primul în consiliu', v: fmt0(primul), h: 'cele mai multe locuri (cu sau fără majoritate)' },
      ]} />
      <div className="ma-plain">
        💡 {d.partide[p] ? `${nume} (${frumos(d.partide[p])})` : nume} are {fmt0(r.v)} {r.v === 1 ? 'consilier local' : de(r.v) + 'consilieri locali'}, adică {procent(ef)} din toate mandatele,
        cu {procent(ev)} din voturi. {ef > ev
          ? 'A luat proporțional mai multe locuri decât voturi, pentru că voturile partidelor care n-au trecut pragul se redistribuie.'
          : 'A luat proporțional mai puține locuri decât voturi.'}
      </div>
      <div className="ma-card">
        <div className="ma-ch"><h3>{nume}: proprii și prin alianțe</h3></div>
        <p className="pr-nota">{NOTA_ALIANTE}</p>
        <Tabel<{ c: Comp | null; v: number }> pePagina={50} cheie={x => x.c?.n ?? '_'} sortare={{ i: 1, desc: true }}
          rows={[{ c: null, v: r.proprii }, ...Array.from(aliante, ([ci, v]) => ({ c: d.competitori[ci], v }))]}
          cols={[
            { l: 'Cum a candidat', v: x => (x.c ? frumos(x.c.n) : `Liste proprii (${nume})`), r: x => (x.c ? <><Competitor c={x.c} /><br /><small>{frumos(x.c.n)}</small></> : <><i className="pr-dot" style={{ background: culoarePartid(p) }} />Liste proprii ({nume})</>) },
            { l: 'Mandate', v: x => x.v, r: x => fmt0(x.v), n: true },
          ]} />
        <div className="cl-fz">
          <div><b>{procent(ef)}</b>din mandatele de consilier din țară</div>
          <div><b>{procent(ev)}</b>din voturile valabile (inclusiv voturile alianțelor, întregi)</div>
          <div><b>{fmt1(ev ? ef / ev : 0)}×</b>eficiență: % mandate împărțit la % voturi (peste 1 = mai multe locuri decât voturi)</div>
        </div>
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch">
          <h3>Mandatele {nume} pe județe</h3>
          <Comutator v={vedere} set={setVedere} optiuni={[['grafic', '📈 Grafic'], ['tabel', '⊞ Tabel']]} />
        </div>
        {vedere === 'grafic' ? <>{r.ali > 0 && <Legenda />}<BareStivuite rows={judete} /></> : (
          <Tabel<RandM> rows={judete} cheie={o => o.k!} pePagina={50} sortare={{ i: 3, desc: true }} cols={[
            { l: 'Județ', v: o => o.name },
            { l: 'Proprii', v: o => o.proprii, r: o => fmt0(o.proprii), n: true },
            { l: 'Prin alianțe', v: o => o.ali, r: o => (o.ali ? fmt0(o.ali) : '–'), n: true },
            { l: 'Total', v: o => o.v, r: o => <b>{fmt0(o.v)}</b>, n: true },
            { l: 'Consilii cu majoritate', v: o => majJ.get(o.k!) ?? 0, r: o => (majJ.get(o.k!) ? fmt0(majJ.get(o.k!)!) : '–'), n: true },
          ]} />
        )}
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Localitățile în care {nume} a avut listă</h3></div>
        <div className="pr-bara">
          <label>Caută localitate sau județ
            <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="ex. Cluj, Florești" />
          </label>
        </div>
        <Tabel<RU> rows={tabel} cheie={({ u, x }) => u.s + '-' + x[0]} sortare={{ i: 4, desc: true }}
          detaliu={({ u }) => <DetaliuUat d={d} u={u} />} cols={[
            { l: 'Județ', v: ({ u }) => frumos(u.j) },
            { l: 'Localitate', v: ({ u }) => frumos(u.u) },
            ...(aliante.size ? [{ l: 'Listă', v: ({ x }: RU) => numeComp(d, x[0]), r: ({ x }: RU) => <Competitor c={d.competitori[x[0]]} /> }] : []),
            { l: 'Voturi', v: ({ x }) => x[1], r: ({ x }) => fmt0(x[1]), n: true },
            { l: '%', v: ({ x }) => x[2], r: ({ x }) => procent(x[2]), n: true },
            { l: 'Mandate', v: ({ x }) => x[6], r: ({ x }) => <b>{x[6] || '–'}</b>, n: true },
            { l: 'Locuri', v: ({ u }) => u.m, n: true },
            { l: 'Majoritate', v: ({ u, x }) => (u.maj && lider(u)[0] === x[0] ? 1 : 0), r: ({ u, x }) => <DaNu da={u.maj && lider(u)[0] === x[0]} />, n: true },
          ]} />
        <p className="ma-src">Apasă pe o localitate ca să vezi componența consiliului.</p>
        <Sursa nota={`„Voturi” și „mandate” la partid includ, întregi, voturile și mandatele alianțelor din care face parte ${nume}.`} />
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Județe ═════════════ */
const PRINCIPALE = ['PSD', 'PNL', 'UDMR', 'AUR', 'USR', 'PMP', 'FD', IND]

export function ConsiliuJudete() {
  const { d, err } = useDate()
  const [judet, setJudet] = useState('')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  return <Cadru d={d} err={err}>{d => {
    const judete = Array.from(new Set(d.uat.map(u => u.j))).sort((a, b) => a.localeCompare(b, 'ro'))
    const j = judete.includes(judet) ? judet : judete[0]
    const uat = d.uat.filter(u => u.j === j)
    const rows = mandate(d, uat, 'comp')
    const total = uat.reduce((s, u) => s + u.m, 0)
    const majP = majoritati(d, uat, 'partid')
    const nMaj = uat.filter(u => u.maj).length
    const majRows = Array.from(majP, ([k, v]) => ({ k, v })).sort((a, b) => b.v - a.v)
    type RJ = { j: string; n: number; m: number; maj: number; lider: RandM; pe: Record<string, number> }
    const toate: RJ[] = judete.map(jj => {
      const uu = d.uat.filter(u => u.j === jj)
      const pe = mandate(d, uu, 'partid')
      return { j: jj, n: uu.length, m: uu.reduce((s, u) => s + u.m, 0), maj: uu.filter(u => u.maj).length, lider: pe[0], pe: Object.fromEntries(pe.map(r => [r.k!, r.v])) }
    })

    return <>
      <Stil />
      <div className="pr-bara">
        <label>Județ
          <select value={j} onChange={e => setJudet(e.target.value)}>
            {judete.map(x => <option key={x} value={x}>{frumos(x)}</option>)}
          </select>
        </label>
      </div>
      <div className="ma-plain">
        💡 În {frumos(j)} s-au ales {fmt0(total)} {de(total)}consilieri în {fmt0(uat.length)} {uat.length === 1 ? 'consiliu local' : de(uat.length) + 'consilii locale'}.
        {rows[0] && <> Cei mai mulți sunt de la {rows[0].name} ({fmt0(rows[0].v)}).</>} În {fmt0(nMaj)} {consilii(nMaj)} un singur competitor are majoritatea.
      </div>
      <div className="ma-card">
        <div className="ma-ch">
          <h3>Mandate pe competitor — {frumos(j)}</h3>
          <Comutator v={vedere} set={setVedere} optiuni={[['grafic', '📈 Grafic'], ['tabel', '⊞ Tabel']]} />
        </div>
        {vedere === 'grafic' ? <>
          <Bare rows={rows.filter(r => r.v > 0).slice(0, MAX_GRAFIC)} eticheta="Mandate" />
          {rows.filter(r => r.v > 0).length > MAX_GRAFIC && <p className="ma-src">Graficul arată primii {MAX_GRAFIC}; restul sunt în tabel.</p>}
        </> : (
          <Tabel<RandM> rows={rows} cheie={r => r.k ?? r.name} pePagina={25} sortare={{ i: 1, desc: true }} cols={[
            { l: 'Competitor', v: r => r.name, r: r => <><i className="pr-dot" style={{ background: r.c }} />{r.name}</> },
            { l: 'Mandate', v: r => r.v, r: r => fmt0(r.v), n: true },
            { l: '% mandate', v: r => r.v, r: r => procent(r.v / total * 100), n: true },
            { l: 'Voturi', v: r => r.voturi, r: r => fmt0(r.voturi), n: true },
          ]} />
        )}
        <div className="pr-gap">
          <h4 style={{ fontSize: 13, marginBottom: 8 }}>Consilii cu majoritate absolută, pe partid (alianțele contează la fiecare partid)</h4>
          {majRows.length === 0 ? <p className="pr-nota">Niciun consiliu cu majoritate.</p> : (
            <Tabel<{ k: string; v: number }> rows={majRows} cheie={r => r.k} pePagina={10} sortare={{ i: 1, desc: true }} cols={[
              { l: 'Partid', v: r => etichetaPartid(d, r.k), r: r => <><i className="pr-dot" style={{ background: culoarePartid(r.k) }} />{etichetaPartid(d, r.k)}</> },
              { l: 'Consilii cu majoritate', v: r => r.v, r: r => fmt0(r.v), n: true },
              { l: '% din consilii', v: r => r.v, r: r => procent(r.v / uat.length * 100), n: true },
            ]} />
          )}
        </div>
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Localitățile din {frumos(j)}</h3></div>
        <Tabel<Uat> rows={uat} cheie={u => String(u.s)} cols={coloaneUat(d, false)} sortare={{ i: 0, desc: false }}
          detaliu={u => <DetaliuUat d={d} u={u} />} />
        <p className="ma-src">Apasă pe o localitate ca să vezi componența consiliului.</p>
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Toate județele</h3></div>
        <p className="pr-nota">Mandate pe partid; mandatele alianțelor apar la fiecare partid din alianță.</p>
        <Tabel<RJ> rows={toate} cheie={r => r.j} pePagina={50} sortare={{ i: 0, desc: false }} cols={[
          { l: 'Județ', v: r => frumos(r.j) },
          { l: 'Mandate', v: r => r.m, r: r => fmt0(r.m), n: true },
          { l: 'Primul partid', v: r => r.lider?.name ?? '', r: r => (r.lider ? <><i className="pr-dot" style={{ background: r.lider.c }} />{r.lider.name}</> : '—'), nw: true },
          ...PRINCIPALE.map((p): Col<RJ> => ({ l: p === IND ? 'Indep.' : p, v: r => r.pe[p] ?? 0, r: r => (r.pe[p] ? fmt0(r.pe[p]) : '–'), n: true })),
          { l: 'Cu majoritate', v: r => r.maj, r: r => `${fmt0(r.maj)} / ${fmt0(r.n)}`, n: true, nw: true },
        ]} />
        <Sursa />
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Localități ═════════════ */
export function ConsiliuLocalitati() {
  const { d, err } = useDate()
  const [q, setQ] = useState('')
  const [judet, setJudet] = useState('')
  const [filtru, setFiltru] = useState('')
  const [maj, setMaj] = useState('')
  return <Cadru d={d} err={err}>{d => {
    const judete = Array.from(new Set(d.uat.map(u => u.j))).sort((a, b) => a.localeCompare(b, 'ro'))
    const partide = mandate(d, d.uat, 'partid').filter(r => r.v > 0)
    const comps = mandate(d, d.uat, 'comp').filter(r => r.v > 0 && d.competitori[Number(r.k)].t !== 'independent')
      .sort((a, b) => a.name.localeCompare(b.name, 'ro'))
    const potriveste = (ci: number) => (filtru.startsWith('p:') ? d.partideDe[ci].includes(filtru.slice(2)) : ci === Number(filtru.slice(2)))
    const c = fara(q.trim())
    const rows = d.uat.filter(u => (!judet || u.j === judet) && (!c || fara(u.u).includes(c))
      && (!filtru || u.k.some(x => x[6] > 0 && potriveste(x[0])))
      && (!maj || (maj === 'da' ? u.maj && (!filtru || potriveste(lider(u)[0])) : maj === 'nu' ? !u.maj
        : maj === 'pda' ? !!u.p?.[3] : !!u.p && !u.p[3])))
    return <>
      <Stil />
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
        <label>Are consilieri
          <select value={filtru} onChange={e => setFiltru(e.target.value)}>
            <option value="">Oricine</option>
            <optgroup label="Partide (inclusiv prin alianțe)">
              {partide.map(r => <option key={r.k} value={'p:' + r.k}>{r.name}</option>)}
            </optgroup>
            <optgroup label="Competitori (exact cum au candidat)">
              {comps.map(r => <option key={r.k} value={'c:' + r.k}>{r.name}</option>)}
            </optgroup>
          </select>
        </label>
        <label>Majoritate
          <select value={maj} onChange={e => setMaj(e.target.value)}>
            <option value="">Toate</option>
            <option value="da">{filtru ? 'competitorul ales are majoritate' : 'cineva are majoritate'}</option>
            <option value="nu">nimeni n-are majoritate</option>
            <option value="pda">primarul are majoritate</option>
            <option value="pnu">primarul n-are majoritate</option>
          </select>
        </label>
      </div>
      <div className="ma-card">
        <div className="ma-ch"><h3>{fmt0(rows.length)} {rows.length === 1 ? 'localitate' : 'localități'}</h3></div>
        <Tabel<Uat> rows={rows} cheie={u => String(u.s)} cols={coloaneUat(d, true)} sortare={{ i: 1, desc: false }}
          detaliu={u => <DetaliuUat d={d} u={u} />} />
        <p className="ma-src">Apasă pe o localitate ca să vezi componența consiliului, voturile și mandatele pe faze și primarul.</p>
        <Sursa />
      </div>
    </>
  }}</Cadru>
}

/* ═════════════ Primar vs consiliu ═════════════ */
export function ConsiliuPrimar() {
  const { d, err } = useDate()
  const [mod, setMod] = useState<'comp' | 'partid'>('comp')
  return <Cadru d={d} err={err}>{d => {
    const cuPrimar = d.uat.filter(u => u.p)
    const cuMaj = cuPrimar.filter(u => u.p![3])
    const primulFaraMaj = cuPrimar.filter(u => !u.p![3] && lider(u)[0] === u.p![1])
    const altul = cuPrimar.filter(u => lider(u)[0] !== u.p![1])
    const fragmentate = d.uat.filter(u => !u.maj)
    type RP = { k: string; name: string; c: string; n: number; maj: number; primul: number }
    const peP = new Map<string, RP>()
    for (const u of cuPrimar) {
      const ci = u.p![1]
      for (const k of mod === 'comp' ? [String(ci)] : d.partideDe[ci]) {
        const r = peP.get(k) ?? { k, name: mod === 'comp' ? numeComp(d, ci) : etichetaPartid(d, k), c: mod === 'comp' ? culoareComp(d.competitori[ci]) : culoarePartid(k), n: 0, maj: 0, primul: 0 }
        r.n++
        if (u.p![3]) r.maj++
        if (lider(u)[0] === ci) r.primul++
        peP.set(k, r)
      }
    }
    // primarii independenți: fiecare e alt competitor → îi grupăm
    const randuriP = Array.from(peP.values()).reduce<RP[]>((acc, r) => {
      if (mod === 'comp' && d.competitori[Number(r.k)].t === 'independent') {
        const g = acc.find(x => x.k === IND) ?? (acc.push({ k: IND, name: IND, c: culoarePartid(IND), n: 0, maj: 0, primul: 0 }), acc[acc.length - 1])
        g.n += r.n; g.maj += r.maj; g.primul += r.primul
      } else acc.push(r)
      return acc
    }, []).sort((a, b) => b.n - a.n)
    type RJ = { j: string; n: number; maj: number }
    const peJ = new Map<string, RJ>()
    for (const u of cuPrimar) {
      const r = peJ.get(u.j) ?? { j: u.j, n: 0, maj: 0 }
      r.n++
      if (u.p![3]) r.maj++
      peJ.set(u.j, r)
    }
    const colPrimar: Col<Uat>[] = [
      { l: 'Județ', v: u => frumos(u.j) },
      { l: 'Localitate', v: u => frumos(u.u) },
      { l: 'Primar', v: u => numeComp(d, u.p![1]), r: u => <><Competitor c={d.competitori[u.p![1]]} /><br /><small>{frumos(u.p![0])} · {u.p![2]} {u.p![2] === 1 ? 'loc' : de(u.p![2]) + 'locuri'}</small></> },
      { l: 'Primul în consiliu', v: u => numeComp(d, lider(u)[0]), r: u => <><Competitor c={d.competitori[lider(u)[0]]} /> · {lider(u)[6]}</> },
      { l: 'Locuri', v: u => u.m, n: true },
      { l: 'Majoritate', v: u => (u.maj ? 1 : 0), r: u => <DaNu da={u.maj} t={['da', `nu (−${u.lp})`]} />, n: true },
    ]

    return <>
      <Stil />
      <Kpis items={[
        { l: 'Primar cu majoritate proprie', v: fmt0(cuMaj.length), h: `${procent(cuMaj.length / cuPrimar.length * 100)} din ${fmt0(cuPrimar.length)} de primării cu primar ales` },
        { l: 'Primul în consiliu, fără majoritate', v: fmt0(primulFaraMaj.length), h: 'lista primarului e prima, dar sub jumătate din locuri' },
        { l: 'Consiliul e condus de altcineva', v: fmt0(altul.length), h: 'alt competitor are cele mai multe locuri' },
        { l: 'Consilii fragmentate', v: fmt0(fragmentate.length), h: 'nimeni nu are peste jumătate din locuri' },
      ]} />
      <div className="ma-plain">
        💡 Primarul are nevoie de consiliul local ca să treacă bugetul și hotărârile. În {fmt0(cuMaj.length)} de localități lista primarului are singură majoritatea;
        în rest trebuie să negocieze. Primarii independenți și cei ai unei alianțe care n-a candidat la consiliu au 0 locuri proprii.
      </div>
      <div className="ma-card">
        <div className="ma-ch">
          <h3>Primari cu majoritate în consiliu, pe {mod === 'comp' ? 'competitor' : 'partid'}</h3>
          <Comutator v={mod} set={setMod} optiuni={[['comp', 'Pe competitor'], ['partid', 'Pe partid']]} />
        </div>
        {mod === 'partid' && <p className="pr-nota">Un primar al alianței PSD-PNL contează și la PSD, și la PNL.</p>}
        <Tabel<RP> rows={randuriP} cheie={r => r.k} pePagina={15} sortare={{ i: 1, desc: true }} cols={[
          { l: mod === 'comp' ? 'Competitor' : 'Partid', v: r => r.name, r: r => <><i className="pr-dot" style={{ background: r.c }} />{r.name}</> },
          { l: 'Primari', v: r => r.n, r: r => fmt0(r.n), n: true },
          { l: 'Cu majoritate', v: r => r.maj, r: r => fmt0(r.maj), n: true },
          { l: '%', v: r => r.maj / r.n, r: r => procent(r.maj / r.n * 100), n: true },
          { l: 'Primii în consiliu', v: r => r.primul, r: r => fmt0(r.primul), n: true },
        ]} />
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Pe județe</h3></div>
        <Tabel<RJ> rows={Array.from(peJ.values())} cheie={r => r.j} pePagina={50} sortare={{ i: 3, desc: true }} cols={[
          { l: 'Județ', v: r => frumos(r.j) },
          { l: 'Primari', v: r => r.n, r: r => fmt0(r.n), n: true },
          { l: 'Cu majoritate', v: r => r.maj, r: r => fmt0(r.maj), n: true },
          { l: '%', v: r => r.maj / r.n, r: r => procent(r.maj / r.n * 100), n: true },
        ]} />
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Primarul e de la un competitor, primul loc în consiliu e al altuia ({fmt0(altul.length)})</h3></div>
        <p className="pr-nota">Competitori diferiți exact cum au candidat: de exemplu, un primar PSD cu un consiliu în care alianța PSD-PNL are cele mai multe locuri apare și el aici.</p>
        <Tabel<Uat> rows={altul} cheie={u => String(u.s)} cols={colPrimar} sortare={{ i: 0, desc: false }} detaliu={u => <DetaliuUat d={d} u={u} />} />
      </div>
      <div className="ma-card pr-gap">
        <div className="ma-ch"><h3>Consilii fragmentate — nimeni nu are majoritate ({fmt0(fragmentate.length)})</h3></div>
        <Tabel<Uat> rows={fragmentate} cheie={u => String(u.s)} sortare={{ i: 0, desc: false }} detaliu={u => <DetaliuUat d={d} u={u} />}
          cols={coloaneUat(d, true).filter(c => c.l !== 'Majoritate').concat({ l: 'Îi lipsesc', v: u => u.lp, n: true })} />
        <p className="ma-src">„Îi lipsesc” = câte locuri mai trebuie primului competitor ca să aibă majoritatea.</p>
        <Sursa nota="Primarul: din rezultatele alegerilor pentru primar (tab-ul „Primar”). La Poșaga și Chețani nu există primar ales (egalitate)." />
      </div>
    </>
  }}</Cadru>
}
