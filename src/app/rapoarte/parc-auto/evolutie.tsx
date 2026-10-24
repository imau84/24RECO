'use client'

import { useState } from 'react'
import {
  BarChart, Bar, Cell, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine,
} from 'recharts'
import { C, URL_SERII, de, fmt, fmtD, fmtP, n, numeMarca, pct, useJson, type Serii, type Vec } from './date'
import {
  ACCENT, AXIS, COMBUSTIBIL, Card, Comutator, Legenda, PALETA, Plain, VARSTA_6, Asteapta, useNume, useStare,
} from './comune'

/* Tab-ul „Evoluție” — seriile pe ani din public/parc-auto/serii.json (06_build_series.py). */

const perioada = (s: Serii) => `${s.ani[0]}–${s.ani[s.ani.length - 1]}`
const semn = (x: number) => (x > 0 ? '+' : x < 0 ? '−' : '')
const puncte = (x: number) => `${semn(x)}${fmtD(Math.abs(x))} puncte`
const crestere = (a: number, b: number) => (a ? (b / a - 1) * 100 : 0)

function useSerii() {
  const { judet } = useStare()
  const { data: s, error } = useJson<Serii>(URL_SERII)
  const nume = useNume(s)
  return { s, error, judet, ...nume }
}

/** bare stivuite 100% pe ani (vechime sau combustibil) */
function Stivuit({ s, total, serii }: { s: Serii; total: Vec[]; serii: { k: number; l: string; c: string }[] }) {
  const rows = s.ani.map((an, i) => ({ name: String(an), ...Object.fromEntries(serii.map(x => [String(x.k), pct(total[i][x.k], total[i][C.total])])) }))
  return <>
    <Legenda items={serii} />
    <div className="ma-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ left: 0, right: 4 }}>
          <CartesianGrid vertical={false} stroke="#eef0f6" />
          <XAxis dataKey="name" tick={AXIS} interval="preserveStartEnd" />
          <YAxis tick={AXIS} unit="%" width={44} domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} />
          <Tooltip formatter={(x, k) => [fmtP(Number(x)), serii.find(c => String(c.k) === k)?.l ?? '']} />
          {serii.map(x => <Bar key={x.k} dataKey={String(x.k)} stackId="a" fill={x.c} isAnimationActive={false} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  </>
}

/* ═════════════ Parc total ═════════════ */
function EvParc() {
  const { s, error, judet, nume, Loc } = useSerii()
  if (!s) return <Asteapta eroare={error} />
  const t = s.date[judet].total.map(v => n(v[C.total])), tr = s.date.RO.total.map(v => n(v[C.total]))
  const a0 = s.ani[0], aN = s.ani[s.ani.length - 1], ani = s.ani.length - 1
  const cr = crestere(t[0], t[ani]), crRO = crestere(tr[0], tr[ani])
  const anual = (Math.pow(t[ani] / t[0], 1 / ani) - 1) * 100
  const pePe = (t[ani] - t[0]) / ani
  const ro = judet !== 'RO'
  const placi = [
    { l: `Autoturisme în ${a0}`, v: fmt(t[0]), c: '#5a6178' },
    { l: `Autoturisme în ${aN}`, v: fmt(t[ani]), c: ACCENT },
    { l: `Creștere ${perioada(s)}`, v: `${semn(cr)}${fmtP(Math.abs(cr), 0)}`, c: '#22b07d', s: ro ? `în toată țara: ${semn(crRO)}${fmtP(Math.abs(crRO), 0)}` : `de ${fmtD(t[ani] / t[0])} ori mai multe` },
    { l: 'În medie pe an', v: `${semn(anual)}${fmtP(Math.abs(anual))}`, c: '#e0a020', s: `cam ${fmt(pePe)}${de(pePe)} mașini în plus pe an` },
  ]
  return <>
    <Plain>
      {Loc(judet)}, numărul de autoturisme a crescut de la {fmt(t[0])} în {a0} la {fmt(t[ani])} în {aN}: {semn(cr)}{fmtP(Math.abs(cr), 0)},
      adică de {fmtD(t[ani] / t[0])} ori{ro && <> (în toată țara: {semn(crRO)}{fmtP(Math.abs(crRO), 0)})</>}.
      {' '}În medie s-au adăugat în fiecare an cam {fmt(pePe)}{de(pePe)} mașini.
    </Plain>
    <div className="pa-tiles">
      {placi.map(x => (
        <div key={x.l} className="pa-tile" style={{ background: x.c }}>
          <div className="l">{x.l}</div><div className="v">{x.v}</div>{x.s && <div className="s">{x.s}</div>}
        </div>
      ))}
    </div>
    <Card titlu={`Autoturisme înmatriculate ${ro ? `în ${nume(judet)}` : 'în România'}, la 31 decembrie`} an={perioada(s)}
      nota="2012–2019: categoria „AUTOTURISM”; din 2020: M1, M1G, M1S, M1GS. Cele două definiții acoperă practic aceleași mașini.">
      <div className="ma-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={s.ani.map((an, i) => ({ name: String(an), v: t[i] }))} margin={{ left: 0, right: 4 }}>
            <CartesianGrid vertical={false} stroke="#eef0f6" />
            <XAxis dataKey="name" tick={AXIS} interval="preserveStartEnd" />
            <YAxis tick={AXIS} width={58} tickFormatter={x => (Number(x) >= 1e6 ? `${fmtD(Number(x) / 1e6)} mil.` : `${fmt(Number(x) / 1000)} mii`)} />
            <Tooltip formatter={x => [fmt(Number(x)), 'Autoturisme']} />
            <Bar dataKey="v" fill={ACCENT} radius={[6, 6, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="ma-tbl">
        <table>
          <thead><tr><th>An</th><th className="n">Autoturisme</th><th className="n">Față de anul anterior</th><th className="n">%</th></tr></thead>
          <tbody>
            {s.ani.map((an, i) => {
              const d = i ? t[i] - t[i - 1] : null
              return (
                <tr key={an}>
                  <td>{an}</td><td className="n">{fmt(t[i])}</td>
                  <td className="n">{d == null ? '—' : `${semn(d)}${fmt(Math.abs(d))}`}</td>
                  <td className="n">{d == null ? '—' : `${semn(d)}${fmtP(Math.abs(crestere(t[i - 1], t[i])))}`}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/* ═════════════ Vechime ═════════════ */
function EvVechime() {
  const { s, error, judet, nume, Loc } = useSerii()
  if (!s) return <Asteapta eroare={error} />
  const tot = s.date[judet].total
  const a0 = s.ani[0], aN = s.ani[s.ani.length - 1], v0 = tot[0], vN = tot[tot.length - 1]
  const p = (v: Vec, k: number) => pct(v[k], v[C.total])
  const sub5 = (v: Vec) => p(v, C.v_0_2) + p(v, C.v_3_5)
  const p20a = p(v0, C.v_peste_20), p20b = p(vN, C.v_peste_20)
  return <>
    <Plain>
      {Loc(judet)}, ponderea mașinilor de peste 20 de ani {p20b > p20a ? 'a crescut' : 'a scăzut'} de la {fmtP(p20a, 0)} în {a0} la {fmtP(p20b, 0)} în {aN}.
      {' '}Mașinile de cel mult 5 ani erau {fmtP(sub5(v0), 0)} din total în {a0} și sunt {fmtP(sub5(vN), 0)} în {aN}.
    </Plain>
    <Card titlu={`Vechimea autoturismelor ${judet === 'RO' ? 'din România' : `din ${nume(judet)}`} — % pe ani`} an={perioada(s)}
      nota="Intervalele 0–2 … peste 20 de ani sunt singurele publicate în toți anii (grupele 0–4 … peste 12 lipsesc în 2012).">
      <Stivuit s={s} total={tot} serii={VARSTA_6} />
      <div className="ma-tbl">
        <table>
          <thead><tr><th>An</th>{VARSTA_6.map(x => <th key={x.k} className="n">{x.l}</th>)}</tr></thead>
          <tbody>
            {s.ani.map((an, i) => (
              <tr key={an}><td>{an}</td>{VARSTA_6.map(x => <td key={x.k} className="n">{fmtP(p(tot[i], x.k))}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/* ═════════════ Combustibil ═════════════ */
function EvCombustibil() {
  const { s, error, judet, nume, Loc } = useSerii()
  if (!s) return <Asteapta eroare={error} />
  const tot = s.date[judet].total
  const a0 = s.ani[0], aN = s.ani[s.ani.length - 1], v0 = tot[0], vN = tot[tot.length - 1]
  const p = (v: Vec, k: number) => pct(v[k], v[C.total])
  const cuEl = s.ani.map((an, i) => ({ an, v: tot[i] })).filter(x => x.v[C.electric] != null)
  const e0 = cuEl[0]
  return <>
    <Plain>
      {Loc(judet)}, motorina a ajuns de la {fmtP(p(v0, C.motorina), 0)} din mașini în {a0} la {fmtP(p(vN, C.motorina), 0)} în {aN},
      iar benzina de la {fmtP(p(v0, C.benzina), 0)} la {fmtP(p(vN, C.benzina), 0)}.
      {e0 && <> Electricele și hibridele apar separat din {e0.an}: de atunci, electricele au crescut de la {fmt(e0.v[C.electric])} la {fmt(vN[C.electric])},
        iar hibridele de la {fmt(e0.v[C.hibrid])} la {fmt(vN[C.hibrid])}.</>}
    </Plain>
    <Card titlu={`Combustibil ${judet === 'RO' ? 'în România' : `în ${nume(judet)}`} — % pe ani`} an={perioada(s)}
      nota={<>Până în {e0?.an ?? aN} DGPCI publică doar benzină și motorină: electricele și hibridele sunt incluse atunci în „GPL / altele”.</>}>
      <Stivuit s={s} total={tot} serii={COMBUSTIBIL} />
      <div className="ma-tbl">
        <table>
          <thead><tr><th>An</th>{COMBUSTIBIL.map(x => <th key={x.k} className="n">{x.l}</th>)}</tr></thead>
          <tbody>
            {s.ani.map((an, i) => (
              <tr key={an}><td>{an}</td>{COMBUSTIBIL.map(x =>
                <td key={x.k} className="n">{tot[i][x.k] == null ? '—' : fmtP(p(tot[i], x.k))}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
    {cuEl.length > 0 && (
      <Card titlu={`Electrice și hibride ${judet === 'RO' ? 'în România' : `în ${nume(judet)}`} — număr de mașini`} an={perioada(s)}>
        <Legenda items={[{ l: 'Electrice', c: '#16a34a' }, { l: 'Hibride', c: '#12a5b8' }]} />
        <div className="ma-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cuEl.map(x => ({ name: String(x.an), e: n(x.v[C.electric]), h: n(x.v[C.hibrid]) }))} margin={{ left: 0, right: 4 }}>
              <CartesianGrid vertical={false} stroke="#eef0f6" />
              <XAxis dataKey="name" tick={AXIS} />
              <YAxis tick={AXIS} width={58} tickFormatter={x => fmt(Number(x))} />
              <Tooltip formatter={(x, k) => [fmt(Number(x)), k === 'e' ? 'Electrice' : 'Hibride']} />
              <Bar dataKey="e" fill="#16a34a" radius={[6, 6, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="h" fill="#12a5b8" radius={[6, 6, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    )}
  </>
}

/* ═════════════ Mărci ═════════════ */
function EvMarci() {
  const { s, error, judet, loc, Loc } = useSerii()
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  if (!s) return <Asteapta eroare={error} />
  const tot = s.date[judet].total.map(v => n(v[C.total]))
  const marci = Object.entries(s.date[judet].marci).sort((a, z) => z[1][z[1].length - 1] - a[1][a[1].length - 1])
  const cota = (m: number[]) => m.map((x, i) => pct(x, tot[i]))
  const top = marci.slice(0, 8)
  const a0 = s.ani[0], aN = s.ani[s.ani.length - 1], N = s.ani.length - 1
  const dif = marci.map(([m, v]) => ({ m, d: cota(v)[N] - cota(v)[0] })).sort((a, z) => z.d - a.d)
  const [m1, v1] = marci[0]
  const rows = s.ani.map((an, i) => ({ name: String(an), ...Object.fromEntries(top.map(([m, v]) => [m, pct(v[i], tot[i])])) }))

  return <>
    <Plain>
      {Loc(judet)}, {numeMarca(m1)} are acum {fmtP(cota(v1)[N], 0)} din mașini, față de {fmtP(cota(v1)[0], 0)} în {a0}.
      {' '}Cea mai mare creștere de cotă din {a0} până în {aN}: {numeMarca(dif[0].m)} ({puncte(dif[0].d)}).
      {' '}Cea mai mare scădere: {numeMarca(dif[dif.length - 1].m)} ({puncte(dif[dif.length - 1].d)}).
    </Plain>
    <Card titlu={`Cota mărcilor ${loc(judet)} — % din autoturisme`} an={perioada(s)} dreapta={<Comutator v={vedere} set={setVedere} />}
      nota="Mărcile care au fost în top 10 în cel puțin un an. Graficul arată primele 8 după numărul de mașini din ultimul an.">
      {vedere === 'grafic' ? <>
        <Legenda items={top.map(([m], i) => ({ l: numeMarca(m), c: PALETA[i % PALETA.length] }))} />
        <div className="ma-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ left: 0, right: 8 }}>
              <CartesianGrid vertical={false} stroke="#eef0f6" />
              <XAxis dataKey="name" tick={AXIS} interval="preserveStartEnd" />
              <YAxis tick={AXIS} unit="%" width={40} />
              <Tooltip formatter={(x, k) => [fmtP(Number(x)), numeMarca(String(k))]} itemSorter={i => -Number(i.value)} />
              {top.map(([m], i) => (
                <Line key={m} dataKey={m} stroke={PALETA[i % PALETA.length]} strokeWidth={2.5} dot={false} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </> : (
        <div className="ma-tbl">
          <table>
            <thead><tr><th>Marcă</th>{s.ani.map(an => <th key={an} className="n">{an}</th>)}<th className="n">Diferență</th></tr></thead>
            <tbody>
              {marci.map(([m, v]) => {
                const c = cota(v)
                return (
                  <tr key={m}>
                    <td>{numeMarca(m)}</td>{c.map((x, i) => <td key={i} className="n">{fmtP(x)}</td>)}
                    <td className="n">{puncte(c[N] - c[0])}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  </>
}

/* ═════════════ Județe ═════════════ */
type IndEv = { k: string; l: string; f: (t: Vec[]) => number; fmt: (x: number) => string; sus: string; jos: string; medie?: 'suma' }
const sem = (x: number, f: (y: number) => string) => `${semn(x)}${f(Math.abs(x))}`
const ultim = (t: Vec[]) => t[t.length - 1]
const p = (v: Vec, k: number) => pct(v[k], v[C.total])

function indicatori(s: Serii): IndEv[] {
  const per = perioada(s)
  return [
    { k: 'cr', l: `Creștere ${per} (%)`, f: t => crestere(n(t[0][C.total]), n(ultim(t)[C.total])), fmt: x => sem(x, y => fmtP(y)), sus: 'Cea mai mare creștere', jos: 'Cea mai mică' },
    { k: 'plus', l: `Mașini în plus ${per}`, f: t => n(ultim(t)[C.total]) - n(t[0][C.total]), fmt: x => sem(x, fmt), sus: 'Cele mai multe mașini în plus', jos: 'Cele mai puține', medie: 'suma' },
    { k: 'v20', l: `Pondere peste 20 de ani: variație ${per}`, f: t => p(ultim(t), C.v_peste_20) - p(t[0], C.v_peste_20), fmt: puncte, sus: 'Cea mai mare creștere a mașinilor foarte vechi', jos: 'Cea mai mare scădere' },
    { k: 'v5', l: `Pondere sub 5 ani (0–5): variație ${per}`, f: t => (p(ultim(t), C.v_0_2) + p(ultim(t), C.v_3_5)) - (p(t[0], C.v_0_2) + p(t[0], C.v_3_5)), fmt: puncte, sus: 'Cea mai mare creștere a mașinilor noi', jos: 'Cea mai mică (sau scădere)' },
    { k: 'mot', l: `Pondere motorină: variație ${per}`, f: t => p(ultim(t), C.motorina) - p(t[0], C.motorina), fmt: puncte, sus: 'Cea mai mare creștere a motorinei', jos: 'Cea mai mică' },
  ]
}

function EvJudete() {
  const { s, error, judet } = useSerii()
  const { setJudet } = useStare()
  const [indK, setIndK] = useState('cr')
  const [sort, setSort] = useState<{ k: string; desc: boolean }>({ k: 'cr', desc: true })
  if (!s) return <Asteapta eroare={error} />
  const ind = indicatori(s)
  const i = ind.find(x => x.k === indK) ?? ind[0]
  const judete = s.judete.filter(j => j.cod !== 'RO')
  const medie = i.medie === 'suma' ? i.f(s.date.RO.total) / judete.length : i.f(s.date.RO.total)
  const rows = judete.map(j => ({ cod: j.cod, name: j.nume, v: i.f(s.date[j.cod].total) })).sort((a, z) => z.v - a.v)
  const lista = (r: typeof rows) => r.map(x => `${x.name} (${i.fmt(x.v)})`).join(', ')
  const a0 = s.ani[0], aN = s.ani[s.ani.length - 1]

  const coloane = [
    { k: 't0', l: `Autoturisme ${a0}`, f: (t: Vec[]) => n(t[0][C.total]), fmt },
    { k: 'tN', l: `Autoturisme ${aN}`, f: (t: Vec[]) => n(ultim(t)[C.total]), fmt },
    { k: 'cr', l: 'Creștere', f: ind[0].f, fmt: ind[0].fmt },
    { k: 'p0', l: `% peste 20 ani ${a0}`, f: (t: Vec[]) => p(t[0], C.v_peste_20), fmt: (x: number) => fmtP(x) },
    { k: 'pN', l: `% peste 20 ani ${aN}`, f: (t: Vec[]) => p(ultim(t), C.v_peste_20), fmt: (x: number) => fmtP(x) },
    { k: 'm0', l: `% motorină ${a0}`, f: (t: Vec[]) => p(t[0], C.motorina), fmt: (x: number) => fmtP(x) },
    { k: 'mN', l: `% motorină ${aN}`, f: (t: Vec[]) => p(ultim(t), C.motorina), fmt: (x: number) => fmtP(x) },
  ]
  const col = coloane.find(c => c.k === sort.k)
  const tabel = judete.map(j => ({ j, t: s.date[j.cod].total })).sort((a, z) => {
    const d = col ? col.f(a.t) - col.f(z.t) : a.j.nume.localeCompare(z.j.nume, 'ro')
    return sort.desc ? -d : d
  })
  const sorteaza = (k: string) => setSort(x => ({ k, desc: x.k === k ? !x.desc : k !== 'nume' }))
  const sageata = (k: string) => (sort.k === k ? (sort.desc ? ' ▼' : ' ▲') : '')

  return <>
    <Plain>
      <b>{i.sus}:</b> {lista(rows.slice(0, 5))}. <b>{i.jos}:</b> {lista(rows.slice(-5).reverse())}.
      {' '}{i.medie === 'suma' ? <>Media pe județ: {i.fmt(medie)}.</> : <>Toată țara: {i.fmt(medie)}.</>}
    </Plain>
    <div className="pa-filtre">
      <label>Indicator
        <select value={i.k} onChange={e => setIndK(e.target.value)}>
          {ind.map(x => <option key={x.k} value={x.k}>{x.l}</option>)}
        </select>
      </label>
    </div>
    <Card titlu={`${i.l} — toate județele`} an={perioada(s)}
      nota={<>Linia verticală = {i.medie === 'suma' ? 'media pe județ' : 'valoarea pentru toată țara'}. Apasă pe un județ ca să-l alegi pentru toată pagina.</>}>
      <div style={{ height: rows.length * 21 + 40 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 20 }}>
            <CartesianGrid horizontal={false} stroke="#eef0f6" />
            <XAxis type="number" tick={AXIS} tickFormatter={x => fmtD(Number(x), 0)} />
            <YAxis type="category" dataKey="name" tick={AXIS} width={104} interval={0} />
            <Tooltip formatter={x => [i.fmt(Number(x)), i.l]} />
            <ReferenceLine x={medie} stroke="#1e2233" strokeDasharray="4 3"
              label={{ value: i.medie === 'suma' ? 'media' : 'România', position: 'top', fontSize: 11, fill: '#1e2233' }} />
            <Bar dataKey="v" isAnimationActive={false} radius={[0, 4, 4, 0]} cursor="pointer"
              onClick={d => { const c = (d as { payload?: { cod?: string } }).payload?.cod; if (c) setJudet(c) }}>
              {rows.map(r => <Cell key={r.cod} fill={r.cod === judet ? ACCENT : '#cfc7f5'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
    <Card titlu={`Județele în ${a0} și în ${aN}`} an={perioada(s)} nota="Apasă pe antetul unei coloane ca să sortezi.">
      <div className="ma-tbl pa-lung">
        <table className="pa-sort">
          <thead><tr>
            <th onClick={() => sorteaza('nume')}>Județ{sageata('nume')}</th>
            {coloane.map(c => <th key={c.k} className="n" onClick={() => sorteaza(c.k)}>{c.l}{sageata(c.k)}</th>)}
          </tr></thead>
          <tbody>
            {tabel.map(({ j, t }) => (
              <tr key={j.cod} className={j.cod === judet ? 'pa-ales' : ''}>
                <td>{j.nume}</td>{coloane.map(c => <td key={c.k} className="n">{c.fmt(c.f(t))}</td>)}
              </tr>
            ))}
            <tr className="pa-tot"><td>România</td>{coloane.map(c => <td key={c.k} className="n">{c.fmt(c.f(s.date.RO.total))}</td>)}</tr>
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/** sub-tab-urile tab-ului „Evoluție” (nume, ancoră URL, conținut) */
export const TABURI_EVOLUTIE = [
  { name: 'Parc total', hash: 'evolutie', content: <EvParc /> },
  { name: 'Vechime', hash: 'evolutie-vechime', content: <EvVechime /> },
  { name: 'Combustibil', hash: 'evolutie-combustibil', content: <EvCombustibil /> },
  { name: 'Mărci', hash: 'evolutie-marci', content: <EvMarci /> },
  { name: 'Județe', hash: 'evolutie-judete', content: <EvJudete /> },
]
