'use client'

import { useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

type Analysis = {
  name: string
  type: 'bar' | 'line' | 'pie'
  unit: string
  plain: string
  labels: string[]
  data: number[]
  cols: string[]
  kpis: { label: string; value: string; chg?: string; dir?: 'up' | 'down' }[]
}
type Source = { key: string; tag: string; label: string; link: string; analyses: Analysis[] }

const SOURCES: Source[] = [
  {
    key: 'DRPCIV', tag: 'oficial', label: 'DRPCIV', link: 'dgpci.mai.gov.ro',
    analyses: [
      {
        name: 'Top mărci', type: 'bar', unit: 'mașini noi',
        plain: 'Dacia conduce detașat — aproape de 2 ori mai multe mașini noi decât Toyota.',
        labels: ['Dacia', 'Toyota', 'Skoda', 'VW', 'BYD', 'BMW', 'Mercedes', 'Renault'],
        data: [2142, 1240, 845, 708, 653, 428, 409, 385],
        cols: ['Marcă', 'Înmatriculări'],
        kpis: [
          { label: 'Total mașini noi', value: '9.552', chg: '▼ −37% vs 2025', dir: 'down' },
          { label: 'Lider', value: 'Dacia', chg: '2.142 buc.', dir: 'up' },
          { label: 'Nou vs. rulat', value: '27%', chg: 'din piață noi' },
        ],
      },
      {
        name: 'Pe combustibil', type: 'pie', unit: 'mașini noi',
        plain: 'Hibridul domină — aproape 6 din 10 mașini noi sunt hibride. Motorina aproape a dispărut.',
        labels: ['Hibrid', 'Benzină', 'Benzină+GPL', 'Electric', 'Motorină'],
        data: [5525, 1591, 1245, 671, 515],
        cols: ['Combustibil', 'Mașini'],
        kpis: [
          { label: 'Hibrid', value: '57,8%', chg: '▲ preferat', dir: 'up' },
          { label: 'Electric', value: '7,0%', chg: '671 buc.' },
          { label: 'Motorină', value: '5,4%', chg: '▼ în declin', dir: 'down' },
        ],
      },
      {
        name: 'Evoluție 12 luni', type: 'line', unit: 'mașini/lună',
        plain: 'Decembrie a fost vârful (peste 21.000), apoi piața a scăzut. Vara aduce o revenire parțială.',
        labels: ['Sep', 'Oct', 'Noi', 'Dec', 'Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug'],
        data: [12449, 12827, 13877, 21308, 7922, 8958, 10374, 10202, 11245, 16114, 11723, 9948],
        cols: ['Luna', 'Total'],
        kpis: [
          { label: 'Vârf', value: 'Dec 2025', chg: '21.308 buc.', dir: 'up' },
          { label: 'Minim', value: 'Ian 2026', chg: '7.922 buc.', dir: 'down' },
          { label: 'August', value: '9.948', chg: '▼ sub media anului', dir: 'down' },
        ],
      },
      {
        name: 'Nou vs. rulat', type: 'bar', unit: 'mașini',
        plain: '3 din 4 mașini sunt second-hand. Piața de rulate e de aproape 3 ori mai mare decât cea de mașini noi.',
        labels: ['Mașini noi', 'Mașini rulate'],
        data: [9552, 25923],
        cols: ['Tip', 'Număr'],
        kpis: [
          { label: 'Rulate', value: '25.923', chg: '73% din piață' },
          { label: 'Noi', value: '9.552', chg: '27% din piață' },
          { label: 'Total', value: '35.475', chg: 'august 2026' },
        ],
      },
    ],
  },
  {
    key: 'ACAROM', tag: 'asociație', label: 'ACAROM', link: 'acarom.ro',
    analyses: [
      {
        name: 'Producție națională', type: 'bar', unit: 'mii vehicule',
        plain: 'Producția a atins vârful în 2023 (514 mii), apoi a scăzut. 2026 sunt date parțiale.',
        labels: ['2021', '2022', '2023', '2024', '2025', '2026*'],
        data: [438, 509, 514, 480, 452, 210],
        cols: ['An', 'Producție (mii)'],
        kpis: [
          { label: 'Vârf', value: '2023', chg: '514 mii', dir: 'up' },
          { label: '2025', value: '452 mii', chg: '▼ în scădere', dir: 'down' },
          { label: '2026*', value: '210 mii', chg: 'parțial' },
        ],
      },
    ],
  },
]

const PALETTE = ['#5b4be0', '#e5544b', '#22b07d', '#e0a020', '#3b82f6', '#12a5b8', '#e0559c', '#7c5ce6']
const fmt = (n: number) => new Intl.NumberFormat('ro-RO').format(n)

export default function ModelADemo() {
  const [srcKey, setSrcKey] = useState(SOURCES[0].key)
  const [anIdx, setAnIdx] = useState(0)
  const [view, setView] = useState<'grafic' | 'tabel'>('grafic')

  const source = SOURCES.find(s => s.key === srcKey) || SOURCES[0]
  const an = source.analyses[Math.min(anIdx, source.analyses.length - 1)]
  const rows = an.labels.map((l, i) => ({ name: l, value: an.data[i] }))
  const total = an.data.reduce((a, b) => a + b, 0)

  return (
    <main className="wrap">
      <style>{`
        :root{--ink:#1e2233;--ink2:#5a6178;--mute:#9aa3b8;--line:#e8ebf1;--brand:#5b4be0;--soft:#f6f7fb;--green:#1a9d6e;--red:#e5544b}
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:var(--soft);color:var(--ink)}
        .wrap{max-width:1080px;margin:0 auto;padding:0 22px 48px}
        .phero{background:linear-gradient(120deg,#e5544b,#e0728a);color:#fff;border-radius:0 0 20px 20px;padding:22px 24px;margin:0 -22px 20px}
        .crumb{font-size:12.5px;opacity:.9}
        .ph-row{display:flex;align-items:center;gap:14px;margin-top:8px}
        .ph-ic{font-size:34px}
        .phero h1{font-size:26px;font-weight:800}
        .phero .sub{font-size:14px;opacity:.95}
        .chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
        .chip{font-size:12px;font-weight:600;background:rgba(255,255,255,.18);padding:5px 11px;border-radius:100px}
        .l1{display:flex;gap:8px;flex-wrap:wrap}
        .l1 button{font:inherit;font-size:14px;font-weight:700;color:var(--ink2);background:#fff;border:1px solid var(--line);border-radius:100px;padding:9px 16px;cursor:pointer;display:inline-flex;gap:8px;align-items:center}
        .l1 button .tag{font-size:10.5px;font-weight:700;color:#fff;background:var(--mute);border-radius:5px;padding:1px 6px}
        .l1 button.on{background:var(--ink);color:#fff;border-color:var(--ink)}
        .l1 button.on .tag{background:var(--brand)}
        .l2{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px;border-bottom:1px solid var(--line)}
        .l2 button{font:inherit;font-size:13px;font-weight:600;color:var(--ink2);background:none;border:none;padding:9px 12px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
        .l2 button.on{color:var(--brand);border-color:var(--brand)}
        .kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}
        .kpi{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px}
        .kpi .l{font-size:12px;color:var(--mute);font-weight:600}
        .kpi .v{font-size:22px;font-weight:800;margin-top:4px}
        .kpi .c{font-size:12px;font-weight:700;margin-top:2px}
        .up{color:var(--green)}.down{color:var(--red)}
        .plain{background:#efedfc;border:1px solid #ddd8f7;border-radius:14px;padding:13px 16px;font-size:14px;color:#3a3170;margin-bottom:16px}
        .card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px}
        .ch{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px}
        .ch h3{font-size:15px;font-weight:700}
        .seg{display:inline-flex;background:var(--soft);border:1px solid var(--line);border-radius:9px;padding:3px}
        .seg button{font:inherit;font-size:12.5px;font-weight:700;color:var(--ink2);background:none;border:none;padding:6px 12px;border-radius:7px;cursor:pointer}
        .seg button.on{background:#fff;color:var(--brand)}
        .chartbox{height:300px}
        table{width:100%;border-collapse:collapse;font-size:13.5px}
        th{text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);padding:9px 10px;border-bottom:1px solid var(--line)}
        td{padding:9px 10px;border-bottom:1px solid var(--line)}
        td.n{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}
        .src{font-size:12.5px;color:var(--mute);margin-top:14px}
        @media(max-width:820px){.kpis{grid-template-columns:1fr 1fr}}
      `}</style>

      <div className="phero">
        <div className="crumb">Acasă › Industrii › Comerț · MODEL A (demo)</div>
        <div className="ph-row">
          <div className="ph-ic">🚗</div>
          <div>
            <h1>Înmatriculări auto</h1>
            <div className="sub">Câte mașini se înmatriculează în România, lunar</div>
          </div>
        </div>
        <div className="chips">
          <span className="chip">● Actualizat: august 2026</span>
          <span className="chip">🔁 lunar</span>
          <span className="chip">📊 grafic + tabel</span>
        </div>
      </div>

      <div className="l1">
        {SOURCES.map(s => (
          <button key={s.key} className={s.key === srcKey ? 'on' : ''} onClick={() => { setSrcKey(s.key); setAnIdx(0) }}>
            {s.label} <span className="tag">{s.tag}</span>
          </button>
        ))}
      </div>

      <div className="l2">
        {source.analyses.map((a, i) => (
          <button key={a.name} className={i === anIdx ? 'on' : ''} onClick={() => setAnIdx(i)}>{a.name}</button>
        ))}
      </div>

      <div className="kpis">
        {an.kpis.map(k => (
          <div key={k.label} className="kpi">
            <div className="l">{k.label}</div>
            <div className="v">{k.value}</div>
            <div className={'c ' + (k.dir || '')}>{k.chg || ''}</div>
          </div>
        ))}
      </div>

      <div className="plain">💡 {an.plain}</div>

      <div className="card">
        <div className="ch">
          <h3>{an.name} — {an.unit}</h3>
          <div className="seg">
            <button className={view === 'grafic' ? 'on' : ''} onClick={() => setView('grafic')}>📈 Grafic</button>
            <button className={view === 'tabel' ? 'on' : ''} onClick={() => setView('tabel')}>⊞ Tabel</button>
          </div>
        </div>

        {view === 'grafic' ? (
          <div className="chartbox">
            <ResponsiveContainer width="100%" height="100%">
              {an.type === 'pie' ? (
                <PieChart>
                  <Pie data={rows} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={2}>
                    {rows.map((r, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt(v)} />
                </PieChart>
              ) : an.type === 'line' ? (
                <LineChart data={rows}>
                  <CartesianGrid vertical={false} stroke="#eef0f6" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9aa3b8' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#9aa3b8' }} tickFormatter={fmt} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Line dataKey="value" stroke="#5b4be0" strokeWidth={2.5} dot={false} />
                </LineChart>
              ) : (
                <BarChart data={rows}>
                  <CartesianGrid vertical={false} stroke="#eef0f6" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9aa3b8' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#9aa3b8' }} tickFormatter={fmt} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {rows.map((r, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                  </Bar>
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        ) : (
          <table>
            <thead>
              <tr><th>{an.cols[0]}</th><th style={{ textAlign: 'right' }}>{an.cols[1]}</th><th style={{ textAlign: 'right' }}>Pondere</th></tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td className="n">{fmt(r.value)}</td>
                  <td className="n">{total ? (r.value / total * 100).toFixed(1) : 0}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="src">📌 Sursă: {source.label} · {source.link} · Prelucrare: 24reco.com · Actualizat lunar</div>
      </div>
    </main>
  )
}
