'use client'

import { useState, type ReactNode } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'

/* Sosiri de turiști (INS) în stil Model A — cele 4 subtab-uri de pe vechea pagină Turism:
   Total național, Județe, Categorii (stele/flori), Localități. Fiecare: filtre, KPI-uri, „pe scurt”,
   grafic sau tabel sortabil și filtrabil. Datele vin deja compactate de la server (sosiri.tsx). */

/** [anul curent până la ultima lună cu date, aceeași perioadă anul trecut, tot anul trecut] */
export type Agregat = [number, number, number]
type Per = { an: string; anPrev: string; luni: number; text: string }
type Serie = (number | null)[]
type Turisti = 'Total' | 'Romani' | 'Straini'

export type SosiriProps = {
  view: 'national' | 'judete' | 'categorii' | 'localitati'
  accent: string
  structuri: Record<string, string>
  actualizat: string
  national?: { per: Per; structuri: string[]; serii: Record<string, Record<string, { cur: Serie; prev: Serie }>> }
  judete?: { per: Per; structuri: string[]; randuri: Record<string, Record<string, [string, ...Agregat][]>> }
  categorii?: { per: Per; structuri: string[]; ordine: string[]; culori: Record<string, string>; date: Record<string, Record<string, Record<string, { cur: Serie; agg: Agregat }>>> }
  localitati?: { per: Per; structuri: string[]; nume: { nume: string; tip: string; judet: string }[]; randuri: Record<string, [number, ...Agregat][]> }
}

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const LUNI_SCURT = ['Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug', 'Sep', 'Oct', 'Noi', 'Dec']
const TURISTI: [Turisti, string][] = [['Total', 'Toți'], ['Romani', 'Români'], ['Straini', 'Străini']]
const TXT_TURISTI: Record<Turisti, string> = { Total: 'turiști', Romani: 'turiști români', Straini: 'turiști străini' }
const PALETA = ['#1a56db', '#5b4be0', '#12a5b8', '#e0a020', '#e5544b', '#7c5ce6', '#22b07d', '#5cc99a', '#a3d9b1', '#c2410c', '#9aa3b8', '#3b82f6']
const C_PREV = '#c3c9d6'

const nf = new Intl.NumberFormat('ro-RO')
const f0 = (n: number | null | undefined) => (n == null ? '—' : nf.format(Math.round(n)))
const p1 = (n: number) => new Intl.NumberFormat('ro-RO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(n) + '%'
const semn = (n: number | null) => (n == null ? '—' : `${n > 0 ? '+' : n < 0 ? '−' : ''}${p1(Math.abs(n))}`)
const evol = (a: number, b: number) => (b > 0 ? (a - b) / b * 100 : null)
const scurt = (v: number) => (v >= 1e6 ? `${new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(v / 1e6)} mil.` : v >= 1e3 ? `${nf.format(Math.round(v / 1e3))} mii` : nf.format(v))
const fara = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
const oameni = (n: number) => `${f0(n)}${Math.round(n) % 100 >= 1 && Math.round(n) % 100 <= 19 ? '' : ' de'}`

type K = { l: string; v: string; c?: string; dir?: 'up' | 'down'; h?: string }
const kpiEvol = (e: number | null, fata: string): Partial<K> => (e == null ? {} : { c: `${e >= 0 ? '▲' : '▼'} ${semn(e)} față de ${fata}`, dir: e >= 0 ? 'up' : 'down' })

/* ── tabel generic: sortare din antet + căutare ── */
type Col<R> = { k: string; t: string; v: (r: R) => string | number | null; f?: (r: R) => ReactNode; num?: boolean; cls?: (r: R) => string }
function Tabel<R>({ rows, cols, cauta, sortInit, max = 300, gol = 'Nimic găsit.' }: { rows: R[]; cols: Col<R>[]; cauta?: (r: R) => string; sortInit: { k: string; dir: 1 | -1 }; max?: number; gol?: string }) {
  const [q, setQ] = useState('')
  const [sort, setSort] = useState(sortInit)
  const col = cols.find(c => c.k === sort.k) ?? cols[0]
  const qq = fara(q.trim())
  const vis = rows.filter(r => !qq || !cauta || fara(cauta(r)).includes(qq))
    .sort((a, b) => {
      const x = col.v(a), y = col.v(b)
      if (x == null) return 1
      if (y == null) return -1
      return (typeof x === 'string' ? x.localeCompare(y as string, 'ro') : x - (y as number)) * sort.dir
    })
  const sorteaza = (k: string, num?: boolean) => setSort(s => (s.k === k ? { k, dir: (s.dir * -1) as 1 | -1 } : { k, dir: num ? -1 : 1 }))
  return (
    <>
      {cauta && (
        <div className="so-tq">
          <span className="so-lbl">{f0(vis.length)} rânduri · clic pe antet pentru sortare</span>
          <input type="search" placeholder="Caută…" value={q} onChange={e => setQ(e.target.value)} aria-label="Filtrează tabelul" />
        </div>
      )}
      <div className="so-tbl">
        <table>
          <thead>
            <tr>{cols.map(c => (
              <th key={c.k} className={c.num ? 'n' : ''} onClick={() => sorteaza(c.k, c.num)} title="Sortează">
                {c.t}{sort.k === c.k ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ↕'}
              </th>
            ))}</tr>
          </thead>
          <tbody>
            {vis.slice(0, max).map((r, i) => (
              <tr key={i}>{cols.map(c => <td key={c.k} className={(c.num ? 'n ' : '') + (c.cls?.(r) ?? '')}>{c.f ? c.f(r) : c.v(r)}</td>)}</tr>
            ))}
            {!vis.length && <tr><td colSpan={cols.length} className="so-gol">{gol}</td></tr>}
          </tbody>
        </table>
      </div>
      {vis.length > max && <div className="so-lbl" style={{ marginTop: 8 }}>Se văd primele {max} din {f0(vis.length)} rânduri — caută sau alege un județ ca să restrângi lista.</div>}
    </>
  )
}

export default function SosiriExplorer(p: SosiriProps) {
  const { view, accent, structuri } = p
  const numeS = (s: string) => structuri[s] ?? s
  const init = view === 'categorii' ? 'Hoteluri' : 'Total'
  const [str, setStr] = useState(init)
  const [tur, setTur] = useState<Turisti>('Total')
  const [jud, setJud] = useState('__ALL__')
  const [vz, setVz] = useState<'grafic' | 'tabel'>(view === 'localitati' ? 'tabel' : 'grafic')
  const AX = { fontSize: 11, fill: '#9aa3b8' }
  const clsEvol = (e: number | null) => (e == null ? '' : e >= 0 ? 'up' : 'down')

  let per: Per, listaStr: string[]
  let kpis: K[] = [], pe_scurt = '', titlu = '', grafic: ReactNode = null, tabel: ReactNode = null, nota = ''
  const areTuristi = view !== 'localitati'

  /* ═════ Total național ═════ */
  if (view === 'national') {
    const d = p.national!
    per = d.per; listaStr = d.structuri
    const s = d.serii[str]?.[tur] ?? { cur: [], prev: [] }
    const li = per.luni - 1
    const vU = s.cur[li] ?? 0, vT = s.prev[li] ?? 0
    const ytd = s.cur.slice(0, per.luni).reduce<number>((a, b) => a + (b ?? 0), 0)
    const ytdP = s.prev.slice(0, per.luni).reduce<number>((a, b) => a + (b ?? 0), 0)
    const eU = evol(vU, vT), eA = evol(ytd, ytdP)
    const str_ = d.serii[str]
    const strainiYtd = str_?.Straini ? str_.Straini.cur.slice(0, per.luni).reduce<number>((a, b) => a + (b ?? 0), 0) : null
    const totYtd = str_?.Total ? str_.Total.cur.slice(0, per.luni).reduce<number>((a, b) => a + (b ?? 0), 0) : 0
    const vPrec = li > 0 ? s.cur[li - 1] ?? null : null
    kpis = [
      { l: `Sosiri în ${LUNI[li]} ${per.an}`, v: f0(vU), ...kpiEvol(eU, `${LUNI[li]} ${per.anPrev}`), h: `${numeS(str)} · ${TXT_TURISTI[tur]}` },
      { l: `Total pe ${per.text}`, v: f0(ytd), ...kpiEvol(eA, `aceeași perioadă din ${per.anPrev}`), h: `${per.anPrev}, aceeași perioadă: ${f0(ytdP)}` },
      tur === 'Total' && strainiYtd != null && totYtd
        ? { l: 'Cât din ei sunt străini', v: p1(strainiYtd / totYtd * 100), h: `${f0(strainiYtd)} turiști străini pe ${per.text}.` }
        : { l: 'Față de luna precedentă', v: vPrec ? semn(evol(vU, vPrec)) : '—', h: vPrec ? `${LUNI[li - 1]}: ${f0(vPrec)}` : '' },
    ]
    pe_scurt = `În ${LUNI[li]} ${per.an} au ajuns în ${str === 'Total' ? 'locurile de cazare' : numeS(str).toLowerCase()} ${oameni(vU)} ${TXT_TURISTI[tur]}` +
      (eU != null ? `, cu ${p1(Math.abs(eU))} ${eU >= 0 ? 'mai mulți' : 'mai puțini'} decât în ${LUNI[li]} ${per.anPrev}.` : '.') +
      (eA != null ? ` De la începutul anului: ${f0(ytd)} (${semn(eA)} față de ${per.anPrev}).` : '') +
      (() => {
        const v = s.prev.map(x => x ?? 0), iMax = v.indexOf(Math.max(...v)), iMin = v.indexOf(Math.min(...v.filter(x => x > 0)))
        return v[iMin] > 0 && iMax !== iMin
          ? ` În ${per.anPrev}, luna cea mai aglomerată a fost ${LUNI[iMax]}, cu de ${new Intl.NumberFormat('ro-RO', { maximumFractionDigits: 1 }).format(v[iMax] / v[iMin])} ori mai mulți turiști decât ${LUNI[iMin]}.`
          : ''
      })()
    titlu = `Sosiri pe luni — ${numeS(str)}, ${TXT_TURISTI[tur]}`
    const rows = LUNI_SCURT.map((l, i) => ({ l, full: LUNI[i], i, prev: s.prev[i] ?? null, cur: s.cur[i] ?? null }))
    grafic = (
      <>
        <div className="ma-legend"><span><i style={{ background: C_PREV }} />{per.anPrev}</span><span><i style={{ background: accent }} />{per.an}</span></div>
        <div className="ma-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows}>
              <CartesianGrid vertical={false} stroke="#eef0f6" />
              <XAxis dataKey="l" tick={AX} />
              <YAxis tick={AX} tickFormatter={scurt} width={60} />
              <Tooltip formatter={(v: number, k: string) => [f0(v), k === 'cur' ? per.an : per.anPrev]} labelFormatter={(_: unknown, x: { payload?: { full?: string } }[]) => x?.[0]?.payload?.full ?? ''} />
              <Bar dataKey="prev" fill={C_PREV} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="cur" fill={accent} radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </>
    )
    type R = typeof rows[number]
    tabel = <Tabel<R> rows={rows} sortInit={{ k: 'luna', dir: 1 }} cols={[
      { k: 'luna', t: 'Luna', v: r => r.i, f: r => r.full },
      { k: 'prev', t: per.anPrev, v: r => r.prev, f: r => f0(r.prev), num: true },
      { k: 'cur', t: per.an, v: r => r.cur, f: r => f0(r.cur), num: true },
      { k: 'ev', t: 'Evoluție', v: r => (r.cur != null && r.prev ? evol(r.cur, r.prev) : null), f: r => semn(r.cur != null && r.prev ? evol(r.cur, r.prev) : null), num: true, cls: r => clsEvol(r.cur != null && r.prev ? evol(r.cur, r.prev) : null) },
    ]} />

  /* ═════ Județe ═════ */
  } else if (view === 'judete') {
    const d = p.judete!
    per = d.per; listaStr = d.structuri
    const rows = (d.randuri[str]?.[tur] ?? []).map(([j, cur, prev, tot]) => ({ j, cur, prev, tot, ev: evol(cur, prev) })).sort((a, b) => b.cur - a.cur)
    const total = rows.reduce((a, r) => a + r.cur, 0) || 1
    const top = rows[0], top5 = rows.slice(0, 5).reduce((a, r) => a + r.cur, 0) / total * 100
    const cresc = rows.filter(r => r.ev != null && r.ev > 0).length
    if (top) {
      kpis = [
        { l: `Pe primul loc: ${top.j}`, v: f0(top.cur), c: `${p1(top.cur / total * 100)} din total`, h: `${TXT_TURISTI[tur][0].toUpperCase() + TXT_TURISTI[tur].slice(1)}, ${per.text}.` },
        { l: 'Primele 5 județe adunate', v: p1(top5), h: rows.slice(0, 5).map(r => r.j).join(', ') },
        { l: `Județe în creștere față de ${per.anPrev}`, v: `${cresc} din ${rows.length}`, h: 'Comparat cu aceeași perioadă a anului trecut.' },
      ]
      pe_scurt = `Pe ${per.text}, cei mai mulți ${TXT_TURISTI[tur]} au mers în ${top.j} (${f0(top.cur)}), apoi în ${rows[1]?.j} și ${rows[2]?.j}. ` +
        `Primele 5 județe adună ${p1(top5)} din toate sosirile.`
    }
    titlu = `Primele 15 județe — ${per.text}`
    const t15 = rows.slice(0, 15)
    grafic = (
      <div style={{ height: Math.max(280, t15.length * 28) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={t15} layout="vertical" margin={{ left: 8, right: 24 }}>
            <CartesianGrid horizontal={false} stroke="#eef0f6" />
            <XAxis type="number" tick={AX} tickFormatter={scurt} />
            <YAxis type="category" dataKey="j" width={120} tick={{ fontSize: 12, fill: '#1e2233' }} interval={0} />
            <Tooltip formatter={(v: number) => [f0(v), 'sosiri']} />
            <Bar dataKey="cur" fill={accent} radius={[0, 6, 6, 0]} barSize={18} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
    type R = typeof rows[number]
    tabel = <Tabel<R> rows={rows} cauta={r => r.j} sortInit={{ k: 'cur', dir: -1 }} cols={[
      { k: 'j', t: 'Județul', v: r => r.j },
      { k: 'cur', t: per.text, v: r => r.cur, f: r => f0(r.cur), num: true },
      { k: 'prev', t: `aceeași perioadă ${per.anPrev}`, v: r => r.prev, f: r => f0(r.prev), num: true },
      { k: 'ev', t: 'Evoluție', v: r => r.ev, f: r => semn(r.ev), num: true, cls: r => clsEvol(r.ev) },
      { k: 'pond', t: 'Pondere', v: r => r.cur / total * 100, f: r => p1(r.cur / total * 100), num: true },
      { k: 'tot', t: `tot anul ${per.anPrev}`, v: r => r.tot, f: r => f0(r.tot), num: true },
    ]} />

  /* ═════ Categorii ═════ */
  } else if (view === 'categorii') {
    const d = p.categorii!
    per = d.per; listaStr = d.structuri.filter(s => s !== 'Total' || d.date.Total)
    const root = d.date[str] ?? {}
    const cats = [...d.ordine.filter(c => root[c]), ...Object.keys(root).filter(c => !d.ordine.includes(c))]
    const culoare = (c: string, i: number) => d.culori[c] ?? PALETA[i % PALETA.length]
    const rows = cats.map((c, i) => { const [cur, prev] = root[c][tur]?.agg ?? [0, 0, 0]; return { c, i, cur, prev, ev: evol(cur, prev) } })
    const total = rows.reduce((a, r) => a + r.cur, 0) || 1
    const sorted = [...rows].sort((a, b) => b.cur - a.cur)
    const top = sorted[0]
    const lux = rows.filter(r => /^[45] (stele|flori)/.test(r.c)).reduce((a, r) => a + r.cur, 0) / total * 100
    if (top) {
      kpis = [
        { l: `Sosiri — ${numeS(str)}`, v: f0(total), ...kpiEvol(evol(total, rows.reduce((a, r) => a + r.prev, 0)), `aceeași perioadă din ${per.anPrev}`), h: per.text },
        { l: `Cele mai multe: ${top.c}`, v: p1(top.cur / total * 100), h: `${f0(top.cur)} ${TXT_TURISTI[tur]}.` },
        { l: '4 și 5 stele (sau flori)', v: p1(lux), h: 'Cât din sosiri sunt în locurile cele mai bine clasificate.' },
      ]
      pe_scurt = `Pe ${per.text}, la ${numeS(str).toLowerCase()} cei mai mulți ${TXT_TURISTI[tur]} au stat la ${top.c} (${p1(top.cur / total * 100)}). ` +
        `Locurile de 4 și 5 stele sau flori au primit ${p1(lux)} din turiști.`
    }
    titlu = `Sosiri pe luni și categorii — ${numeS(str)}, ${per.an}`
    const lunar = LUNI_SCURT.slice(0, per.luni).map((l, m) => {
      const r: Record<string, string | number | null> = { l, full: `${LUNI[m]} ${per.an}` }
      cats.forEach(c => { r[c] = root[c][tur]?.cur[m] ?? null })
      return r
    })
    grafic = (
      <>
        <div className="ma-legend">{cats.map((c, i) => <span key={c}><i style={{ background: culoare(c, i) }} />{c}</span>)}</div>
        <div className="ma-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={lunar}>
              <CartesianGrid vertical={false} stroke="#eef0f6" />
              <XAxis dataKey="l" tick={AX} />
              <YAxis tick={AX} tickFormatter={scurt} width={60} />
              <Tooltip formatter={(v: number, k: string) => [f0(v), k]} labelFormatter={(_: unknown, x: { payload?: { full?: string } }[]) => x?.[0]?.payload?.full ?? ''} />
              {cats.map((c, i) => <Bar key={c} dataKey={c} stackId="c" fill={culoare(c, i)} isAnimationActive={false} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </>
    )
    type R = typeof rows[number]
    tabel = <Tabel<R> rows={rows} cauta={r => r.c} sortInit={{ k: 'ord', dir: 1 }} cols={[
      { k: 'ord', t: 'Categoria', v: r => r.i, f: r => <><i className="so-dot" style={{ background: culoare(r.c, r.i) }} />{r.c}</> },
      { k: 'cur', t: per.text, v: r => r.cur, f: r => f0(r.cur), num: true },
      { k: 'prev', t: `aceeași perioadă ${per.anPrev}`, v: r => r.prev, f: r => f0(r.prev), num: true },
      { k: 'ev', t: 'Evoluție', v: r => r.ev, f: r => semn(r.ev), num: true, cls: r => clsEvol(r.ev) },
      { k: 'pond', t: 'Pondere', v: r => r.cur / total * 100, f: r => p1(r.cur / total * 100), num: true },
    ]} />
    nota = '„Neclasificate pe stele” = locuri de cazare fără clasificare (ex. tabere, unele apartamente). Pensiunile agroturistice se clasifică în flori.'

  /* ═════ Localități ═════ */
  } else {
    const d = p.localitati!
    per = d.per; listaStr = d.structuri
    const toate = (d.randuri[str] ?? []).map(([i, cur, prev, tot]) => ({ ...d.nume[i], cur, prev, tot, ev: evol(cur, prev) }))
    const judete = Array.from(new Set(toate.map(r => r.judet))).sort((a, b) => a.localeCompare(b, 'ro'))
    const rows = (jud === '__ALL__' ? toate : toate.filter(r => r.judet === jud)).sort((a, b) => b.cur - a.cur)
    const total = rows.reduce((a, r) => a + r.cur, 0) || 1
    const top = rows[0], top10 = rows.slice(0, 10).reduce((a, r) => a + r.cur, 0) / total * 100
    const unde = jud === '__ALL__' ? 'în toată țara' : `în județul ${jud}`
    if (top) {
      kpis = [
        { l: `Pe primul loc: ${top.nume}`, v: f0(top.cur), c: `${p1(top.cur / total * 100)} din sosiri ${unde}`, h: `${top.tip}, județul ${top.judet}` },
        { l: 'Primele 10 localități adunate', v: p1(top10), h: rows.slice(1, 4).map(r => r.nume).join(', ') + '…' },
        { l: 'Localități cu turiști', v: f0(rows.filter(r => r.cur > 0).length), h: `${numeS(str)}, ${per.text}.` },
      ]
      pe_scurt = `Pe ${per.text}, ${unde}, cei mai mulți turiști au ajuns în ${top.nume} (${f0(top.cur)}), apoi în ${rows[1]?.nume ?? '—'} și ${rows[2]?.nume ?? '—'}. ` +
        `Primele 10 localități adună ${p1(top10)} din sosiri.`
    }
    titlu = `Sosiri pe localități — ${numeS(str)}, ${per.text}`
    const t15 = rows.slice(0, 15)
    grafic = (
      <div style={{ height: Math.max(280, t15.length * 28) }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={t15} layout="vertical" margin={{ left: 8, right: 24 }}>
            <CartesianGrid horizontal={false} stroke="#eef0f6" />
            <XAxis type="number" tick={AX} tickFormatter={scurt} />
            <YAxis type="category" dataKey="nume" width={140} tick={{ fontSize: 12, fill: '#1e2233' }} interval={0} />
            <Tooltip formatter={(v: number) => [f0(v), 'sosiri']} />
            <Bar dataKey="cur" fill={accent} radius={[0, 6, 6, 0]} barSize={18} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
    type R = typeof rows[number]
    tabel = <Tabel<R> key={str + jud} rows={rows} cauta={r => `${r.nume} ${r.judet} ${r.tip}`} sortInit={{ k: 'cur', dir: -1 }} cols={[
      { k: 'nume', t: 'Localitatea', v: r => r.nume },
      { k: 'tip', t: 'Tip', v: r => r.tip, cls: () => 'mute' },
      { k: 'judet', t: 'Județul', v: r => r.judet, cls: () => 'mute' },
      { k: 'cur', t: per.text, v: r => r.cur, f: r => f0(r.cur), num: true },
      { k: 'prev', t: `aceeași perioadă ${per.anPrev}`, v: r => r.prev, f: r => f0(r.prev), num: true },
      { k: 'ev', t: 'Evoluție', v: r => r.ev, f: r => semn(r.ev), num: true, cls: r => clsEvol(r.ev) },
      { k: 'tot', t: `tot anul ${per.anPrev}`, v: r => r.tot, f: r => f0(r.tot), num: true },
    ]} />
    nota = `Datele pe localități apar la INS cu câteva luni întârziere față de restul (aici: până în ${LUNI[per.luni - 1]} ${per.an}). Numele localităților sunt scrise ca în sursă, fără diacritice.`
    return render(true, judete)
  }
  return render(false, [])

  function render(loc: boolean, judete: string[]) {
    return (
      <div className="so">
        <style dangerouslySetInnerHTML={{ __html: `
          .so{--acc:${accent}}
          .so-ctl{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 16px;display:flex;gap:18px;flex-wrap:wrap;align-items:center}
          .so-g{display:flex;gap:10px;align-items:center;min-width:0}
          .so-lbl{font-size:12px;font-weight:700;color:var(--mute)}
          .so select,.so input[type=search]{font:inherit;font-size:14px;color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:9px;padding:8px 10px;min-width:0;max-width:100%}
          .so select{font-weight:600}
          .so select:focus,.so input:focus{outline:2px solid var(--acc);outline-offset:1px}
          .so-tq{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
          .so-tbl{overflow-x:auto;max-height:600px;overflow-y:auto}
          .so thead th{position:sticky;top:0;background:#fff;z-index:1;cursor:pointer;user-select:none}
          .so thead th:hover{color:var(--ink)}
          .so td.up{color:var(--up)}.so td.down{color:var(--down)}
          .so td.mute{color:var(--ink2)}
          .so-gol{text-align:center;color:var(--mute)}
          .so-dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:7px;vertical-align:-1px}
        ` }} />

        <div className="so-ctl">
          {loc && (
            <div className="so-g">
              <span className="so-lbl">Județul</span>
              <select value={jud} onChange={e => setJud(e.target.value)} aria-label="Alege județul">
                <option value="__ALL__">Toate județele</option>
                {judete.map(j => <option key={j} value={j}>{j}</option>)}
              </select>
            </div>
          )}
          <div className="so-g">
            <span className="so-lbl">Cazare</span>
            <select value={listaStr.includes(str) ? str : listaStr[0]} onChange={e => setStr(e.target.value)} aria-label="Alege tipul de cazare">
              {listaStr.map(s => <option key={s} value={s}>{numeS(s)}</option>)}
            </select>
          </div>
          {areTuristi && (
            <div className="so-g">
              <span className="so-lbl">Turiști</span>
              <div className="ma-seg">
                {TURISTI.map(([k, l]) => <button key={k} className={tur === k ? 'on' : ''} onClick={() => setTur(k)}>{l}</button>)}
              </div>
            </div>
          )}
        </div>

        <div className="ma-kpis">
          {kpis.map(k => (
            <div key={k.l} className="ma-kpi">
              <div className="l">{k.l}</div>
              <div className="v">{k.v}</div>
              {k.c && <div className={'c ' + (k.dir || '')}>{k.c}</div>}
              {k.h && <div className="h">{k.h}</div>}
            </div>
          ))}
        </div>

        {pe_scurt && <div className="ma-plain">💡 {pe_scurt}</div>}

        <div className="ma-card">
          <div className="ma-ch">
            <h3>{titlu}</h3>
            <div className="ma-seg">
              <button className={vz === 'grafic' ? 'on' : ''} onClick={() => setVz('grafic')}>📈 Grafic</button>
              <button className={vz === 'tabel' ? 'on' : ''} onClick={() => setVz('tabel')}>⊞ Tabel</button>
            </div>
          </div>
          {vz === 'grafic' ? grafic : tabel}
          <div className="ma-src">
            📌 Sursă: INS, TEMPO-Online (sosiri în structurile de primire turistică) · <a href="http://statistici.insse.ro:8077/tempo-online/" target="_blank" rel="noopener noreferrer">statistici.insse.ro</a> · Prelucrare: 24reco.com · actualizat lunar{p.actualizat ? ` (ultima verificare: ${p.actualizat})` : ''}
            <br />„Sosiri” = câți turiști s-au cazat (o persoană care stă 3 nopți e numărată o dată). Sunt numărate doar locurile de cazare care raportează la INS.
            {nota && <><br />{nota}</>}
          </div>
        </div>
      </div>
    )
  }
}
