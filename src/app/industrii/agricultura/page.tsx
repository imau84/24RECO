'use client'

import { useState } from 'react'
import Link from 'next/link'
import agriculturaData from '@/data/agricultura/agricultura_data.json'

const C = {
  bg: '#f4f5f7', card: '#fff', border: '#e8eaed',
  navy: '#0f2044', blue: '#1a56db', blueLight: '#e8f0fe',
  green: '#0e7245', greenLight: '#d4edda',
  red: '#b91c1c', redLight: '#fee2e2',
  text: '#1a1d23', muted: '#6b7280', subtle: '#9ca3af',
}

const ZONE = ['VEST', 'EST', 'SUD'] as const
type Zona = typeof ZONE[number]

const ZONE_COLORS: Record<Zona, string> = { VEST: '#1a56db', EST: '#0e7245', SUD: '#c2410c' }
const ZONE_LIGHT: Record<Zona, string>  = { VEST: '#dbeafe', EST: '#dcfce7', SUD: '#fee2e2' }

const fmt = (v: number) => new Intl.NumberFormat('ro-RO').format(v)

type Saptamana = typeof agriculturaData.saptamani[0]

/* ── KPI Card ── */
function KPICard({ label, value, sub, color, delta }: {
  label: string; value: string; sub: string; color: string; delta?: number | null
}) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: '14px 18px', flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color, lineHeight: 1, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 11, color: C.subtle }}>{sub}</div>
      {delta != null && (
        <div style={{ fontSize: 11, fontWeight: 600, color: delta >= 0 ? C.green : C.red, marginTop: 3 }}>
          {delta >= 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}% față de S02
        </div>
      )}
    </div>
  )
}

/* ── Grafic SVG ── */
function LineChart({ dataKey }: { dataKey: 'grau' | 'porumb' }) {
  const [hover, setHover] = useState<number | null>(null)
  const saptamani = agriculturaData.saptamani
  const W = 860, H = 280, PL = 60, PR = 20, PT = 30, PB = 55
  const chartW = W - PL - PR, chartH = H - PT - PB
  const n = saptamani.length

  const allVals = saptamani.flatMap(s => ZONE.map(z => s[dataKey][z]).filter(Boolean)) as number[]
  const minV = Math.min(...allVals) - 30
  const maxV = Math.max(...allVals) + 30
  const range = maxV - minV

  const xOf = (i: number) => PL + (i / (n - 1)) * chartW
  const yOf = (v: number) => PT + chartH - ((v - minV) / range) * chartH

  const step = range > 200 ? 50 : 25
  const gridVals: number[] = []
  for (let v = Math.ceil(minV / step) * step; v <= maxV; v += step) gridVals.push(v)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}
      onMouseLeave={() => setHover(null)}>

      {gridVals.map(v => (
        <g key={v}>
          <line x1={PL} y1={yOf(v)} x2={W - PR} y2={yOf(v)} stroke={C.border} strokeWidth={0.5} strokeDasharray="3,3" />
          <text x={PL - 6} y={yOf(v) + 4} textAnchor="end" fontSize={9} fill={C.muted}>{v}</text>
        </g>
      ))}

      {hover !== null && (
        <line x1={xOf(hover)} y1={PT} x2={xOf(hover)} y2={PT + chartH} stroke="#ccc" strokeWidth={1} strokeDasharray="3,2" />
      )}

      {ZONE.map(zona => {
        const pts = saptamani.map((s, i) => ({ x: xOf(i), y: yOf(s[dataKey][zona]), v: s[dataKey][zona] }))
        const col = ZONE_COLORS[zona]
        return (
          <g key={zona}>
            <polyline points={pts.map(p => `${p.x},${p.y}`).join(' ')} stroke={col} strokeWidth={2.5} fill="none" strokeLinejoin="round" />
            {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r={3} fill={col} stroke="#fff" strokeWidth={1.5} />)}
          </g>
        )
      })}

      {saptamani.map((_, i) => (
        <rect key={i} x={xOf(i) - chartW / n / 2} y={PT} width={chartW / n} height={chartH}
          fill="transparent" onMouseEnter={() => setHover(i)} style={{ cursor: 'crosshair' }} />
      ))}

      {saptamani.map((s, i) => (
        <g key={i}>
          <text x={xOf(i)} y={H - 22} textAnchor="middle" fontSize={8} fill={hover === i ? C.navy : C.muted} fontWeight={hover === i ? 700 : 400}>S{s.nr}</text>
          <text x={xOf(i)} y={H - 10} textAnchor="middle" fontSize={7} fill={C.subtle}>{s.label.substring(0, 6)}</text>
        </g>
      ))}

      {ZONE.map((z, i) => (
        <g key={z}>
          <line x1={PL + i * 80} y1={14} x2={PL + i * 80 + 18} y2={14} stroke={ZONE_COLORS[z]} strokeWidth={2.5} />
          <text x={PL + i * 80 + 22} y={18} fontSize={9} fill={C.muted}>{z}</text>
        </g>
      ))}

      {hover !== null && (() => {
        const s = saptamani[hover]
        const x = xOf(hover)
        const tx = Math.min(Math.max(x - 80, 5), W - 170)
        const vals = ZONE.map(z => ({ z, v: s[dataKey][z] }))
        return (
          <g>
            <rect x={tx} y={5} width={165} height={18 + vals.length * 16} rx={5} fill={C.navy} opacity={0.95} />
            <text x={tx + 10} y={20} fontSize={10} fontWeight="700" fill="#fff">S{s.nr} — {s.label}</text>
            {vals.map(({ z, v }, i) => (
              <text key={z} x={tx + 10} y={35 + i * 16} fontSize={9} fill={ZONE_COLORS[z as Zona]}>
                {z}: {fmt(v)} lei/t
              </text>
            ))}
          </g>
        )
      })()}
    </svg>
  )
}

/* ── Tabel ── */
function DataTable({ dataKey }: { dataKey: 'grau' | 'porumb' }) {
  const saptamani = [...agriculturaData.saptamani].reverse()
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
        <thead>
          <tr style={{ background: C.navy }}>
            <th style={{ padding: '9px 12px', color: '#fff', fontWeight: 600, fontSize: 11, textAlign: 'left', minWidth: 140 }}>Săptămâna</th>
            {ZONE.map(z => (
              <th key={z} colSpan={2} style={{ padding: '9px 12px', color: ZONE_LIGHT[z], fontWeight: 600, fontSize: 11, textAlign: 'center', borderLeft: '2px solid rgba(255,255,255,0.1)' }}>{z}</th>
            ))}
          </tr>
          <tr style={{ background: '#0d1b36' }}>
            <th style={{ padding: '5px 12px', color: 'rgba(255,255,255,0.5)', fontSize: 10, textAlign: 'left' }}></th>
            {ZONE.flatMap(z => [
              <th key={z + '-p'} style={{ padding: '5px 10px', color: ZONE_LIGHT[z], fontSize: 10, textAlign: 'right', fontWeight: 400 }}>lei/t</th>,
              <th key={z + '-v'} style={{ padding: '5px 10px', color: 'rgba(255,255,255,0.4)', fontSize: 10, textAlign: 'right', fontWeight: 400 }}>var%</th>
            ])}
          </tr>
        </thead>
        <tbody>
          {saptamani.map((s, rowIdx) => {
            const prevS = agriculturaData.saptamani[agriculturaData.saptamani.length - 2 - rowIdx]
            const bg = rowIdx === 0 ? '#f0f7ff' : rowIdx % 2 === 0 ? '#fff' : '#fafafa'
            return (
              <tr key={s.nr} style={{ background: bg, borderBottom: `1px solid ${C.border}` }}>
                <td style={{ padding: '7px 12px', fontWeight: rowIdx === 0 ? 700 : 400, color: rowIdx === 0 ? C.navy : C.text, fontSize: 11 }}>
                  <div style={{ fontWeight: 600 }}>S{s.nr}/2026</div>
                  <div style={{ fontSize: 9, color: C.subtle }}>{s.label}</div>
                </td>
                {ZONE.flatMap(z => {
                  const v = s[dataKey][z]
                  const vPrev = prevS?.[dataKey]?.[z]
                  const varPct = v && vPrev ? ((v - vPrev) / vPrev * 100) : null
                  return [
                    <td key={z + '-p'} style={{ padding: '7px 10px', textAlign: 'right', fontFamily: 'monospace', fontWeight: rowIdx === 0 ? 700 : 400, color: ZONE_COLORS[z], borderLeft: `2px solid ${ZONE_LIGHT[z]}` }}>
                      {fmt(v)}
                    </td>,
                    <td key={z + '-v'} style={{ padding: '7px 10px', textAlign: 'right', fontSize: 10 }}>
                      {varPct !== null ? (
                        <span style={{ color: varPct > 0 ? C.green : varPct < 0 ? C.red : C.muted, fontWeight: Math.abs(varPct) > 5 ? 700 : 400 }}>
                          {varPct > 0 ? '+' : ''}{varPct.toFixed(1)}%
                        </span>
                      ) : '—'}
                    </td>
                  ]
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/* ── Pagina principală ── */
export default function AgriculturaPage() {
  const [produs, setProdus] = useState<'grau' | 'porumb'>('grau')
  const [view, setView] = useState<'grafic' | 'tabel'>('grafic')

  const saptamani = agriculturaData.saptamani
  const latest = saptamani[saptamani.length - 1]
  const first = saptamani[0]
  const { sursa, url, actualizat } = agriculturaData.meta

  const prodLabel = produs === 'grau' ? 'Grâu pt. Panificație' : 'Porumb'

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        body{font-family:'DM Sans',system-ui,sans-serif;background:#f4f5f7;color:#1a1d23;-webkit-font-smoothing:antialiased}
        .ag-nav{background:#0f2044;height:48px;display:flex;align-items:center;padding:0 24px;gap:16px;position:sticky;top:0;z-index:100}
        .ag-logo{font-size:14px;font-weight:700;color:#fff;text-decoration:none}
        .ag-navlinks{display:flex;gap:2px;flex:1}
        .ag-navlink{font-size:12px;color:rgba(255,255,255,.55);padding:5px 12px;border-radius:5px;text-decoration:none;white-space:nowrap}
        .ag-navlink:hover{color:#fff}
        .ag-navlink.active{color:#fff;border-bottom:2px solid #1a56db}
        .ag-header{background:#fff;border-bottom:1px solid #e8eaed;padding:0 24px}
        .ag-header-inner{max-width:1200px;margin:0 auto}
        .ag-breadcrumb{font-size:11px;color:#9ca3af;padding:10px 0 0;display:flex;gap:5px;align-items:center}
        .ag-breadcrumb a{color:#9ca3af;text-decoration:none}
        .ag-breadcrumb a:hover{color:#1a56db}
        .ag-title-row{display:flex;align-items:center;gap:14px;padding:10px 0 12px}
        .ag-subtabs{display:flex;border-top:1px solid #e8eaed}
        .ag-subtab{font-size:12px;padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;color:#6b7280;white-space:nowrap;background:none;border-left:none;border-right:none;border-top:none;font-family:'DM Sans',sans-serif}
        .ag-subtab.active{color:#1a56db;border-bottom-color:#1a56db;font-weight:600}
        .ag-main{max-width:1200px;margin:0 auto;padding:20px 24px}
        .ag-kpis{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}
        .ag-card{background:#fff;border:1px solid #e8eaed;border-radius:10px;overflow:hidden}
        .ag-tabbar{display:flex;border-bottom:1px solid #e8eaed;padding:0 16px;align-items:center}
        .ag-tab{background:none;border:none;border-bottom:2px solid transparent;cursor:pointer;padding:12px 16px;font-size:12px;font-family:'DM Sans',sans-serif;color:#6b7280;margin-bottom:-1px}
        .ag-tab.active{color:#1a56db;border-bottom-color:#1a56db;font-weight:600}
        .ag-selector{display:flex;background:#f0f0f0;border-radius:8px;padding:3px;gap:2px}
        .ag-sel-btn{background:none;border:none;border-radius:6px;padding:7px 16px;font-size:12px;font-family:'DM Sans',sans-serif;cursor:pointer;color:#6b7280}
        .ag-sel-btn.active{background:#fff;font-weight:600;color:#0f2044;box-shadow:0 1px 3px rgba(0,0,0,0.1)}
        .ag-footer{border-top:1px solid #e8eaed;background:#fff;padding:10px 24px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:20px;border-radius:8px}
        @media(max-width:768px){
          .ag-kpis{flex-direction:column}
          .ag-main{padding:16px}
          .ag-header{padding:0 16px}
          .ag-nav{padding:0 16px}
        }
      `}</style>

      {/* NAVBAR */}
      <nav className="ag-nav">
        <Link href="/" className="ag-logo">📊 24reco.com</Link>
        <div className="ag-navlinks">
          <Link href="/#industrii" className="ag-navlink active">Industrii</Link>
          <Link href="/#institutii" className="ag-navlink">Instituții publice</Link>
          <Link href="/#rapoarte" className="ag-navlink">Rapoarte</Link>
        </div>
        <Link href="/despre" style={{ fontSize: 11, color: 'rgba(255,255,255,.5)', padding: '4px 10px', border: '1px solid rgba(255,255,255,.15)', borderRadius: 5, textDecoration: 'none' }}>
          Despre · Contact
        </Link>
      </nav>

      {/* HEADER */}
      <div className="ag-header">
        <div className="ag-header-inner">
          <div className="ag-breadcrumb">
            <Link href="/">Acasă</Link><span>›</span>
            <Link href="/#industrii">Industrii</Link><span>›</span>
            <span style={{ color: C.text, fontWeight: 500 }}>Agricultură</span>
          </div>
          <div className="ag-title-row">
            <div style={{ width: 40, height: 40, background: '#f0fdf4', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22 }}>🌾</div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: C.navy }}>Agricultură</div>
              <div style={{ fontSize: 11, color: C.muted }}>brm.ro • Bursa Română de Mărfuri</div>
            </div>
            <a href={url} target="_blank" rel="noopener noreferrer"
              style={{ marginLeft: 'auto', fontSize: 11, color: C.blue, textDecoration: 'none', border: `1px solid ${C.blue}`, padding: '5px 12px', borderRadius: 6 }}>
              ↗ brm.ro
            </a>
          </div>
          <div className="ag-subtabs">
            <button className="ag-subtab active">Prețuri Cereale</button>
          </div>
        </div>
      </div>

      {/* MAIN */}
      <div className="ag-main">
        {/* Titlu + selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontSize: 18, fontWeight: 700, color: C.navy, marginBottom: 4 }}>Prețuri Cereale — Cotații BRM 2026</h1>
            <p style={{ fontSize: 12, color: C.muted }}>Cotații săptămânale pe zone de livrare (lei/tonă) • S02–S16 2026</p>
          </div>
          <div className="ag-selector">
            <button className={`ag-sel-btn${produs === 'grau' ? ' active' : ''}`} onClick={() => setProdus('grau')}>🌾 Grâu Panificație</button>
            <button className={`ag-sel-btn${produs === 'porumb' ? ' active' : ''}`} onClick={() => setProdus('porumb')}>🌽 Porumb</button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="ag-kpis">
          {ZONE.map(z => {
            const vLatest = latest[produs][z]
            const vFirst = first[produs][z]
            const delta = vFirst ? ((vLatest - vFirst) / vFirst * 100) : null
            return (
              <KPICard key={z}
                label={`S${latest.nr} — Zona ${z}`}
                value={`${fmt(vLatest)} lei/t`}
                sub={`${prodLabel} • Apr 2026`}
                color={ZONE_COLORS[z]}
                delta={delta}
              />
            )
          })}
          <KPICard
            label={`Medie națională S${latest.nr}`}
            value={`${fmt(Math.round(ZONE.reduce((s, z) => s + latest[produs][z], 0) / 3))} lei/t`}
            sub={`${prodLabel} • VEST+EST+SUD`}
            color={C.navy}
          />
        </div>

        {/* Card grafic/tabel */}
        <div className="ag-card">
          <div className="ag-tabbar">
            <button className={`ag-tab${view === 'grafic' ? ' active' : ''}`} onClick={() => setView('grafic')}>📈 Grafic evoluție</button>
            <button className={`ag-tab${view === 'tabel' ? ' active' : ''}`} onClick={() => setView('tabel')}>⊞ Tabel săptămânal</button>
            <div style={{ flex: 1 }} />
            <div style={{ display: 'flex', gap: 14, padding: '0 8px' }}>
              {ZONE.map(z => (
                <div key={z} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: C.muted }}>
                  <div style={{ width: 12, height: 3, background: ZONE_COLORS[z], borderRadius: 2 }} />
                  {z}
                </div>
              ))}
            </div>
          </div>

          <div style={{ padding: view === 'tabel' ? 0 : 24 }}>
            {view === 'grafic' && (
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.navy, marginBottom: 4 }}>
                  Evoluție {prodLabel} — S02–S16 2026 (lei/tonă)
                </div>
                <div style={{ fontSize: 11, color: C.muted, marginBottom: 16 }}>
                  Cotații BRM pe zone de livrare Ex Warehouse • Hover pe grafic pentru detalii
                </div>
                <LineChart dataKey={produs} />

                {/* Min/Max */}
                <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
                  {ZONE.map(z => {
                    const vals = saptamani.map(s => s[produs][z])
                    const min = Math.min(...vals), max = Math.max(...vals)
                    const minS = saptamani.find(s => s[produs][z] === min)
                    const maxS = saptamani.find(s => s[produs][z] === max)
                    return (
                      <div key={z} style={{ background: ZONE_LIGHT[z], border: `1px solid ${ZONE_COLORS[z]}33`, borderRadius: 8, padding: '10px 14px', flex: 1, minWidth: 160 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: ZONE_COLORS[z], marginBottom: 6 }}>Zona {z}</div>
                        <div style={{ display: 'flex', gap: 16, fontSize: 11 }}>
                          <div>
                            <div style={{ color: C.muted, fontSize: 10 }}>MIN</div>
                            <div style={{ fontWeight: 700, color: C.red }}>{fmt(min)} <span style={{ fontWeight: 400, color: C.muted }}>lei/t</span></div>
                            <div style={{ fontSize: 9, color: C.subtle }}>S{minS?.nr}</div>
                          </div>
                          <div>
                            <div style={{ color: C.muted, fontSize: 10 }}>MAX</div>
                            <div style={{ fontWeight: 700, color: C.green }}>{fmt(max)} <span style={{ fontWeight: 400, color: C.muted }}>lei/t</span></div>
                            <div style={{ fontSize: 9, color: C.subtle }}>S{maxS?.nr}</div>
                          </div>
                          <div>
                            <div style={{ color: C.muted, fontSize: 10 }}>VARIAȚIE</div>
                            <div style={{ fontWeight: 700, color: C.muted }}>{max - min} lei/t</div>
                            <div style={{ fontSize: 9, color: C.subtle }}>{((max - min) / min * 100).toFixed(1)}%</div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
            {view === 'tabel' && <DataTable dataKey={produs} />}
          </div>
        </div>

        {/* Footer */}
        <div className="ag-footer">
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
          <span style={{ fontSize: 11, color: C.muted }}>Sursă: {sursa}</span>
          <span style={{ color: C.border }}>•</span>
          <a href={url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: C.blue, textDecoration: 'none' }}>🔗 brm.ro/cotatii-cereale</a>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: C.subtle }}>Ultima actualizare: {actualizat} • Frecvență: săptămânal</span>
        </div>
      </div>
    </>
  )
}
