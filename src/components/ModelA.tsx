'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

/* ── Tipuri ── */
export type Kpi = {
  label: string
  value: string
  chg?: string
  dir?: 'up' | 'down'
  /** explicație în limbaj simplu, sub cifră */
  hint?: string
}

export type Series = { name: string; data: number[]; color?: string }

export type Analysis = {
  name: string
  type: 'bar' | 'line' | 'pie'
  unit: string
  /** rândul „pe scurt” — limbaj simplu */
  plain: string
  labels: string[]
  /** etichete complete pentru tooltip și tabel (ex. „S38 · 17-23 sep”) */
  labelsLong?: string[]
  series: Series[]
  /** antetul primei coloane din tabel */
  labelCol: string
  kpis: Kpi[]
  /** coloană „Pondere” în tabel (doar pentru o singură serie) */
  share?: boolean
  /** tabelul afișează rândurile de la ultimul la primul (serii de timp) */
  tableNewestFirst?: boolean
  /** axa Y pornește de la minimul datelor, nu de la 0 (doar la grafic linie) */
  zoomY?: boolean
  footnote?: string
}

export type Source = {
  key: string
  tag: string
  label: string
  link: string
  url?: string
  freq: string
  analyses: Analysis[]
}

export type Theme = {
  accent: string   // culoarea categoriei (ex. #22b07d)
  accent2: string  // capătul gradientului din bara de sus
  tint: string     // fundalul rândului „pe scurt”
  tintBorder: string
  tintInk: string
}

export type Crumb = { label: string; href?: string }

export type ModelAProps = {
  crumbs: Crumb[]
  icon: string
  title: string
  sub: string
  chips: string[]
  theme: Theme
  sources: Source[]
}

const PALETTE = ['#5b4be0', '#e5544b', '#22b07d', '#e0a020', '#3b82f6', '#12a5b8', '#e0559c', '#7c5ce6']
const fmt = (n: number) => new Intl.NumberFormat('ro-RO').format(n)
const AXIS = { fontSize: 11, fill: '#9aa3b8' }

export default function ModelA({ crumbs, icon, title, sub, chips, theme, sources }: ModelAProps) {
  const [srcKey, setSrcKey] = useState(sources[0].key)
  const [anIdx, setAnIdx] = useState(0)
  const [view, setView] = useState<'grafic' | 'tabel'>('grafic')

  const source = sources.find(s => s.key === srcKey) || sources[0]
  const an = source.analyses[Math.min(anIdx, source.analyses.length - 1)]
  const multi = an.series.length > 1
  const colorOf = (s: Series, i: number) => s.color || (multi ? PALETTE[i % PALETTE.length] : theme.accent)

  // rânduri pentru Recharts: { name, full, s0, s1, ... }
  const rows = an.labels.map((l, i) => {
    const r: Record<string, string | number> = { name: l, full: an.labelsLong?.[i] ?? l }
    an.series.forEach((s, j) => { r['s' + j] = s.data[i] })
    return r
  })
  const total = an.series[0].data.reduce((a, b) => a + b, 0)
  const tableRows = an.labels.map((_, i) => i)
  if (an.tableNewestFirst) tableRows.reverse()

  const tooltip = (
    <Tooltip
      formatter={(v: number, key: string) => [fmt(v), an.series[Number(String(key).slice(1))]?.name ?? '']}
      labelFormatter={(_: unknown, p: { payload?: { full?: string } }[]) => p?.[0]?.payload?.full ?? ''}
    />
  )
  // zoomY: axa pornește aproape de minim, cu gradații rotunde (ex. 850, 900, 950…)
  let yTicks: number[] | undefined
  if (an.zoomY) {
    const all = an.series.flatMap(s => s.data)
    const span = Math.max(...all) - Math.min(...all)
    const step = [10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000].find(s => span / s <= 6) ?? 10000
    const lo = Math.floor(Math.min(...all) / step) * step, hi = Math.ceil(Math.max(...all) / step) * step
    yTicks = []
    for (let v = lo; v <= hi; v += step) yTicks.push(v)
  }
  const yDomain: [number, number | 'auto'] = yTicks ? [yTicks[0], yTicks[yTicks.length - 1]] : [0, 'auto']

  return (
    <main className="ma">
      {/* dangerouslySetInnerHTML: altfel React escapează ghilimelele diferit pe server vs. client → eroare de hidratare */}
      <style dangerouslySetInnerHTML={{ __html: `
        .ma{--ink:#1e2233;--ink2:#5a6178;--mute:#9aa3b8;--line:#e8ebf1;--soft:#f6f7fb;--up:#1a9d6e;--down:#e5544b;
          --brand:${theme.accent};max-width:1080px;margin:0 auto;padding:0 22px 48px;color:var(--ink);
          font-family:-apple-system,'Segoe UI',Roboto,sans-serif}
        body{background:#f6f7fb}
        .ma *{box-sizing:border-box}
        .ma-hero{background:linear-gradient(120deg,${theme.accent},${theme.accent2});color:#fff;border-radius:0 0 20px 20px;padding:22px 24px;margin:0 -22px 20px}
        .ma-crumb{font-size:12.5px;opacity:.9}
        .ma-crumb a{color:#fff;text-decoration:none}
        .ma-crumb a:hover{text-decoration:underline}
        .ma-row{display:flex;align-items:center;gap:14px;margin-top:8px}
        .ma-ic{font-size:34px}
        .ma-hero h1{font-size:26px;font-weight:800;font-family:inherit;letter-spacing:-.01em}
        .ma-sub{font-size:14px;opacity:.95}
        .ma-chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
        .ma-chip{font-size:12px;font-weight:600;background:rgba(255,255,255,.18);padding:5px 11px;border-radius:100px}
        .ma-l1{display:flex;gap:8px;flex-wrap:wrap}
        .ma-l1 button{font:inherit;font-size:14px;font-weight:700;color:var(--ink2);background:#fff;border:1px solid var(--line);border-radius:100px;padding:9px 16px;cursor:pointer;display:inline-flex;gap:8px;align-items:center}
        .ma-l1 .tag{font-size:10.5px;font-weight:700;color:#fff;background:var(--mute);border-radius:5px;padding:1px 6px}
        .ma-l1 button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
        .ma-l1 button.on .tag{background:var(--brand)}
        .ma-l2{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px;border-bottom:1px solid var(--line)}
        .ma-l2 button{font:inherit;font-size:13px;font-weight:600;color:var(--ink2);background:none;border:none;padding:9px 12px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
        .ma-l2 button.on{color:var(--brand);border-color:var(--brand)}
        .ma-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}
        .ma-kpi{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
        .ma-kpi .l{font-size:12px;color:var(--mute);font-weight:600}
        .ma-kpi .v{font-size:22px;font-weight:800;margin-top:4px}
        .ma-kpi .c{font-size:12px;font-weight:700;margin-top:2px;color:var(--ink2)}
        .ma-kpi .c.up{color:var(--up)}.ma-kpi .c.down{color:var(--down)}
        .ma-kpi .h{font-size:12px;color:var(--ink2);margin-top:6px;line-height:1.4}
        .ma-plain{background:${theme.tint};border:1px solid ${theme.tintBorder};border-radius:14px;padding:13px 16px;font-size:14px;line-height:1.5;color:${theme.tintInk};margin-bottom:16px}
        .ma-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px}
        .ma-ch{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px}
        .ma-ch h3{font-size:15px;font-weight:700;font-family:inherit;letter-spacing:0}
        .ma-seg{display:inline-flex;background:var(--soft);border:1px solid var(--line);border-radius:9px;padding:3px}
        .ma-seg button{font:inherit;font-size:12.5px;font-weight:700;color:var(--ink2);background:none;border:none;padding:6px 12px;border-radius:7px;cursor:pointer}
        .ma-seg button.on{background:#fff;color:var(--brand)}
        .ma-legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;font-weight:600;color:var(--ink2);margin-bottom:8px}
        .ma-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
        .ma-chart{height:300px}
        .ma-tbl{overflow-x:auto}
        .ma table{width:100%;border-collapse:collapse;font-size:13.5px}
        .ma th{text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
        .ma td{padding:9px 10px;border-bottom:1px solid var(--line)}
        .ma td.n,.ma th.n{text-align:right}
        .ma td.n{font-weight:700;font-variant-numeric:tabular-nums}
        .ma-src{font-size:12.5px;color:var(--mute);margin-top:14px;line-height:1.5}
        .ma-src a{color:var(--ink2)}
        @media(max-width:820px){.ma-kpis{grid-template-columns:1fr 1fr}}
        @media(max-width:520px){.ma{padding:0 16px 40px}.ma-hero{margin:0 -16px 18px}.ma-kpis{grid-template-columns:1fr}.ma-chart{height:260px}}
      ` }} />

      <div className="ma-hero">
        <div className="ma-crumb">
          {crumbs.map((c, i) => (
            <span key={c.label}>
              {i > 0 && ' › '}
              {c.href ? <Link href={c.href}>{c.label}</Link> : c.label}
            </span>
          ))}
        </div>
        <div className="ma-row">
          <div className="ma-ic">{icon}</div>
          <div>
            <h1>{title}</h1>
            <div className="ma-sub">{sub}</div>
          </div>
        </div>
        <div className="ma-chips">
          {chips.map(c => <span key={c} className="ma-chip">{c}</span>)}
        </div>
      </div>

      <div className="ma-l1">
        {sources.map(s => (
          <button key={s.key} className={s.key === srcKey ? 'on' : ''} onClick={() => { setSrcKey(s.key); setAnIdx(0) }}>
            {s.label} <span className="tag">{s.tag}</span>
          </button>
        ))}
      </div>

      <div className="ma-l2">
        {source.analyses.map((a, i) => (
          <button key={a.name} className={a === an ? 'on' : ''} onClick={() => setAnIdx(i)}>{a.name}</button>
        ))}
      </div>

      <div className="ma-kpis">
        {an.kpis.map(k => (
          <div key={k.label} className="ma-kpi">
            <div className="l">{k.label}</div>
            <div className="v">{k.value}</div>
            {k.chg && <div className={'c ' + (k.dir || '')}>{k.chg}</div>}
            {k.hint && <div className="h">{k.hint}</div>}
          </div>
        ))}
      </div>

      <div className="ma-plain">💡 {an.plain}</div>

      <div className="ma-card">
        <div className="ma-ch">
          <h3>{an.name} — {an.unit}</h3>
          <div className="ma-seg">
            <button className={view === 'grafic' ? 'on' : ''} onClick={() => setView('grafic')}>📈 Grafic</button>
            <button className={view === 'tabel' ? 'on' : ''} onClick={() => setView('tabel')}>⊞ Tabel</button>
          </div>
        </div>

        {view === 'grafic' ? (
          <>
            {multi && (
              <div className="ma-legend">
                {an.series.map((s, i) => <span key={s.name}><i style={{ background: colorOf(s, i) }} />{s.name}</span>)}
              </div>
            )}
            <div className="ma-chart">
              <ResponsiveContainer width="100%" height="100%">
                {an.type === 'pie' ? (
                  <PieChart>
                    <Pie data={rows} dataKey="s0" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={2}>
                      {rows.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                    </Pie>
                    {tooltip}
                  </PieChart>
                ) : an.type === 'line' ? (
                  <LineChart data={rows}>
                    <CartesianGrid vertical={false} stroke="#eef0f6" />
                    <XAxis dataKey="name" tick={AXIS} minTickGap={8} />
                    <YAxis tick={AXIS} tickFormatter={fmt} domain={yDomain} ticks={yTicks} width={52} />
                    {tooltip}
                    {an.series.map((s, i) => (
                      <Line key={s.name} dataKey={'s' + i} stroke={colorOf(s, i)} strokeWidth={2.5} dot={false} connectNulls />
                    ))}
                  </LineChart>
                ) : (
                  <BarChart data={rows}>
                    <CartesianGrid vertical={false} stroke="#eef0f6" />
                    <XAxis dataKey="name" tick={AXIS} />
                    <YAxis tick={AXIS} tickFormatter={fmt} width={52} />
                    {tooltip}
                    {an.series.map((s, i) => (
                      <Bar key={s.name} dataKey={'s' + i} fill={colorOf(s, i)} radius={[6, 6, 0, 0]} isAnimationActive={false}>
                        {!multi && rows.map((_, j) => <Cell key={j} fill={PALETTE[j % PALETTE.length]} />)}
                      </Bar>
                    ))}
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <div className="ma-tbl">
            <table>
              <thead>
                <tr>
                  <th>{an.labelCol}</th>
                  {an.series.map(s => <th key={s.name} className="n">{s.name}</th>)}
                  {an.share && <th className="n">Pondere</th>}
                </tr>
              </thead>
              <tbody>
                {tableRows.map(i => (
                  <tr key={i}>
                    <td>{an.labelsLong?.[i] ?? an.labels[i]}</td>
                    {an.series.map(s => <td key={s.name} className="n">{fmt(s.data[i])}</td>)}
                    {an.share && <td className="n">{total ? (an.series[0].data[i] / total * 100).toFixed(1) : 0}%</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="ma-src">
          📌 Sursă: {source.label} · {source.url
            ? <a href={source.url} target="_blank" rel="noopener noreferrer">{source.link}</a>
            : source.link} · Prelucrare: 24reco.com · Actualizat {source.freq}
          {an.footnote && <><br />{an.footnote}</>}
        </div>
      </div>
    </main>
  )
}
