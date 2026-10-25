'use client'

import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { fmt0, fmt1 } from '../../industrii/agricultura/util'

/* Piese comune pentru tab-urile „Primar” (primari.tsx) și „Consiliu local” (consiliu-local.tsx):
   nume frumoase, culorile pe partide, CSS-ul, tabelul sortabil cu paginare, graficul cu bare. */

export const IND = 'Independenți'
export type Comp = { n: string; s: string; p: string[]; t: 'partid' | 'alianta' | 'alianta_locala' | 'minoritate' | 'independent'; nota?: string }

/** încarcă un JSON din public/ o singură dată (promisiune păstrată la nivel de modul) */
export function incarcator<F, D>(url: string, pregateste: (f: F) => D) {
  let cerere: Promise<D> | null = null
  const incarca = () => {
    if (!cerere) {
      cerere = fetch(url).then(r => {
        if (!r.ok) throw new Error(String(r.status))
        return r.json()
      }).then(pregateste)
      cerere.catch(() => { cerere = null })
    }
    return cerere
  }
  return function useDate() {
    const [st, setSt] = useState<{ d: D | null; err: boolean }>({ d: null, err: false })
    useEffect(() => {
      let viu = true
      incarca().then(d => viu && setSt({ d, err: false }), () => viu && setSt({ d: null, err: true }))
      return () => { viu = false }
    }, [])
    return st
  }
}

/** CSS-ul comun + mesajul de încărcare */
export function Cadru<D>({ d, err, mesaj, children }: { d: D | null; err: boolean; mesaj: string; children: (d: D) => ReactNode }) {
  return <>
    <style dangerouslySetInnerHTML={{ __html: CSS }} />
    {d ? children(d) : <div className="ma-card pr-gap pr-wait">{err ? 'Datele nu s-au putut încărca. Reîncarcă pagina.' : mesaj}</div>}
  </>
}

/* ═════════════ nume și culori ═════════════ */
const MAJUSCULE = new Set(['PSD', 'PNL', 'USR', 'PMP', 'UDMR', 'AUR', 'S.O.S.', 'FD', 'PRO', 'PUSL', 'ARI', 'SENS', 'UIPS', 'II', 'III', 'IV', 'DEMOS', 'QANON'])
/** „PARTIDUL NAȚIONAL LIBERAL” → „Partidul Național Liberal”; „MUNICIPIUL TIMIȘOARA” → „Municipiul Timișoara” */
const MICI = new Set(['DE', 'DIN', 'PE', 'LA', 'PENTRU', 'ȘI', 'CU', 'AL', 'A', 'ÎN', 'SUB'])
export const frumos = (s: string) => s.split(/(\s+|-|\+|,|\(|"|\.)/).map((w, i) =>
  (MAJUSCULE.has(w) || !/[A-ZĂÂÎȘȚÁÉÍÓÖŐÚÜŰ]/.test(w) ? w
    : i > 0 && MICI.has(w) ? w.toLowerCase() : w.charAt(0) + w.slice(1).toLowerCase())).join('')
/** semnele diacritice combinate (U+0300–U+036F), după descompunerea NFD */
const DIACRITICE = new RegExp('[' + String.fromCharCode(0x300) + '-' + String.fromCharCode(0x36f) + ']', 'g')
export const fara = (s: string) => s.normalize('NFD').replace(DIACRITICE, '').toUpperCase()

/** aceleași culori ca la Consiliul județean (public/alegeri_data.json → PARTY_COLORS) */
export const CULORI: Record<string, string> = {
  PSD: '#e84a4a', PNL: '#4a8fe8', AUR: '#e88a4a', UDMR: '#4ae8d8', USR: '#4ae870', 'S.O.S. RO': '#e8c84a',
  PUSL: '#4aa0e8', FD: '#8ae84a', PMP: '#3d5a99', [IND]: '#7a8099', 'PRO ROMÂNIA': '#b5568a', PER: '#2e9e5b',
  REPER: '#5bc0de', AMT: '#2aa198', FDGR: '#c9a227', PNCR: '#8c6d46', POT: '#e05fa0', PV: '#5cb85c',
}
const CULORI_COMP: Record<string, string> = {
  'ALIANȚA DREAPTA UNITĂ USR - PMP - FORȚA DREPTEI': '#8a4ae8',
  'ALIANȚA ELECTORALĂ PSD PNL': '#e84aa0',
  'ALIANȚA TIMIȘOARA UNITĂ USR - PMP - FORȚA DREPTEI - UDMR': '#a04ae8',
  'ALIANȚA UNIȚI PENTRU BRAȘOV': '#e86a4a',
  'ALIANȚA DREAPTA UNITĂ USR - PMP': '#4a60e8',
}
const REZERVA = ['#9b8ae0', '#e0a020', '#12a5b8', '#e0559c', '#7cb342', '#a1887f', '#5c6bc0', '#26a69a', '#ef8354', '#8d6e63']
const dinNume = (s: string) => REZERVA[s.split('').reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7) % REZERVA.length]

export const culoarePartid = (p: string) => CULORI[p] ?? dinNume(p)
export const culoareComp = (c: Comp) =>
  CULORI_COMP[c.n] ?? (c.t === 'independent' ? CULORI[IND] : c.p.length === 1 ? culoarePartid(c.p[0]) : dinNume(c.n))
/** eticheta scurtă: abrevierea (PSD, ADU (USR-PMP-FD)) sau numele, cu litere mici */
export const eticheta = (c: Comp) => (c.s === c.n ? frumos(c.n) : c.s)

export const procent = (x: number) => `${fmt1(x)}%`

/* ═════════════ piese comune ═════════════ */
export const CSS = `
  .pr-k4{grid-template-columns:repeat(4,1fr)}
  .pr-k5{grid-template-columns:repeat(5,1fr)}
  .pr-k3{grid-template-columns:repeat(3,1fr)}
  .pr-bara{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin:4px 0 14px}
  .pr-bara label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:var(--mute);min-width:0;flex:1 1 200px;max-width:320px}
  .pr-bara select,.pr-bara input{font:inherit;font-size:14px;font-weight:600;color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:9px;padding:8px 10px;width:100%;min-width:0}
  .pr-gap{margin-top:16px}
  .pr-ch2{display:flex;gap:8px;flex-wrap:wrap}
  .pr-nota{font-size:12.5px;color:var(--ink2);background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:9px 12px;margin:0 0 12px;line-height:1.45}
  .pr-wait{color:var(--ink2);font-size:14px}
  .pr-tbl table{font-size:13px}
  .pr-tbl th{cursor:pointer;user-select:none}
  .pr-tbl th.on{color:var(--brand)}
  .pr-tbl td{vertical-align:top}
  .pr-tbl td.nw{white-space:nowrap}
  .pr-tbl tr.pr-clic{cursor:pointer}
  .pr-tbl tr.pr-clic:hover td{background:#fafbfe}
  .pr-tbl tr.pr-on td{background:var(--soft);font-weight:700}
  .pr-det td{background:#fcfcfe}
  .pr-pag{display:flex;justify-content:center;align-items:center;gap:12px;margin-top:12px;font-size:13px;color:var(--ink2);flex-wrap:wrap}
  .pr-pag button,.pr-btn{font:inherit;font-size:13px;font-weight:700;color:var(--ink2);background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 12px;cursor:pointer}
  .pr-pag button:disabled{opacity:.45;cursor:default}
  .pr-dot{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:7px;vertical-align:0}
  .pr-cand{display:grid;gap:8px;padding:6px 0}
  .pr-cand .r{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;font-size:13px}
  .pr-cand .r small{grid-column:1/-1;color:var(--ink2);font-size:12px}
  .pr-cand .bar{grid-column:1/-1;height:8px;background:var(--soft);border-radius:4px;overflow:hidden}
  .pr-cand .bar i{display:block;height:100%;border-radius:4px}
  .pr-pv{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--ink2);margin-top:6px}
  .pr-lista{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .pr-lista ol{padding-left:20px;display:grid;gap:6px;font-size:13.5px;line-height:1.4}
  .pr-lista h4{font-size:13px;font-weight:700;margin-bottom:8px}
  @media(max-width:1000px){.pr-k5{grid-template-columns:repeat(3,1fr)}}
  @media(max-width:820px){.pr-k4,.pr-k5,.pr-k3{grid-template-columns:1fr 1fr}.pr-lista{grid-template-columns:1fr}}
  @media(max-width:520px){.pr-k4,.pr-k5,.pr-k3{grid-template-columns:1fr}.pr-bara label{max-width:none;flex:1 1 100%}}
`

export function Kpis({ items, cls = 'pr-k4' }: { items: { l: string; v: string; h?: string }[]; cls?: string }) {
  return (
    <div className={'ma-kpis ' + cls}>
      {items.map(k => <div key={k.l} className="ma-kpi"><div className="l">{k.l}</div><div className="v">{k.v}</div>{k.h && <div className="h">{k.h}</div>}</div>)}
    </div>
  )
}

export function Comutator<T extends string>({ v, set, optiuni }: { v: T; set: (x: T) => void; optiuni: [T, string][] }) {
  return (
    <div className="ma-seg">
      {optiuni.map(([k, l]) => <button key={k} className={v === k ? 'on' : ''} onClick={() => set(k)}>{l}</button>)}
    </div>
  )
}

export type Rand = { name: string; v: number; c: string; k?: string }
export function Bare({ rows, eticheta: et = 'Primari' }: { rows: Rand[]; eticheta?: string }) {
  return (
    <div style={{ height: rows.length * 26 + 36 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 28 }}>
          <CartesianGrid horizontal={false} stroke="#eef0f6" />
          <XAxis type="number" tick={{ fontSize: 11, fill: '#9aa3b8' }} tickFormatter={x => fmt0(Number(x))} allowDecimals={false} />
          <YAxis type="category" dataKey="name" width={128} interval={0} tick={{ fontSize: 11, fill: '#5a6178' }}
            tickFormatter={(s: string) => (s.length > 21 ? s.slice(0, 20) + '…' : s)} />
          <Tooltip formatter={x => [fmt0(Number(x)), et]} />
          <Bar dataKey="v" radius={[0, 6, 6, 0]} isAnimationActive={false} label={{ position: 'right', fontSize: 11, fill: '#5a6178', formatter: (x: number) => fmt0(x) }}>
            {rows.map(r => <Cell key={r.name} fill={r.c} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/* ── tabel sortabil, cu paginare și rând de detaliu opțional ── */
export type Col<T> = { l: string; v: (r: T) => number | string; r?: (r: T) => ReactNode; n?: boolean; nw?: boolean }

export function Tabel<T>({ cols, rows, cheie, sortare = { i: 0, desc: true }, pePagina = 25, detaliu }: {
  cols: Col<T>[]; rows: T[]; cheie: (r: T) => string; sortare?: { i: number; desc: boolean }; pePagina?: number
  detaliu?: (r: T) => ReactNode
}) {
  const [sort, setSort] = useState(sortare)
  const [pg, setPg] = useState(0)
  const [deschis, setDeschis] = useState<string | null>(null)
  useEffect(() => { setPg(0); setDeschis(null) }, [rows])
  const sortate = useMemo(() => {
    const f = cols[sort.i].v
    return [...rows].sort((a, b) => {
      const x = f(a), y = f(b)
      const d = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'ro')
      return sort.desc ? -d : d
    })
  }, [rows, sort, cols])
  const pagini = Math.max(1, Math.ceil(sortate.length / pePagina))
  const p = Math.min(pg, pagini - 1)
  const clic = (i: number) => setSort(s => (s.i === i ? { i, desc: !s.desc } : { i, desc: !!cols[i].n }))

  return <>
    <div className="ma-tbl pr-tbl">
      <table>
        <thead><tr>
          {cols.map((c, i) => (
            <th key={c.l} className={(c.n ? 'n' : '') + (sort.i === i ? ' on' : '')} onClick={() => clic(i)}>
              {c.l}{sort.i === i ? (sort.desc ? ' ▼' : ' ▲') : ''}
            </th>
          ))}
        </tr></thead>
        <tbody>
          {sortate.length === 0 && <tr><td colSpan={cols.length} style={{ color: 'var(--mute)', textAlign: 'center' }}>Niciun rezultat.</td></tr>}
          {sortate.slice(p * pePagina, (p + 1) * pePagina).flatMap(r => {
            const k = cheie(r), on = deschis === k
            return [
              <tr key={k} className={detaliu ? 'pr-clic' + (on ? ' pr-on' : '') : ''} onClick={detaliu ? () => setDeschis(on ? null : k) : undefined}>
                {cols.map(c => <td key={c.l} className={(c.n ? 'n' : '') + (c.nw ? ' nw' : '')}>{c.r ? c.r(r) : c.v(r)}</td>)}
              </tr>,
              ...(on && detaliu ? [<tr key={k + '-d'} className="pr-det"><td colSpan={cols.length}>{detaliu(r)}</td></tr>] : []),
            ]
          })}
        </tbody>
      </table>
    </div>
    {pagini > 1 && (
      <div className="pr-pag">
        <button disabled={p === 0} onClick={() => setPg(p - 1)}>‹ Înapoi</button>
        <span>Pagina {p + 1} din {pagini} · {fmt0(sortate.length)} rânduri</span>
        <button disabled={p >= pagini - 1} onClick={() => setPg(p + 1)}>Înainte ›</button>
      </div>
    )}
  </>
}

export const Competitor = ({ c }: { c: Comp }) => <><i className="pr-dot" style={{ background: culoareComp(c) }} />{eticheta(c)}</>
