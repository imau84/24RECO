'use client'

import { useMemo, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

/* Explorator pentru o serie Eurostat: alegi un indicator și unul sau mai mulți ani,
   vezi graficul (ani suprapuși sau linie continuă) și un tabel sortabil și filtrabil.
   Numerele folosesc formatul 1,234.5 (virgulă la mii, punct la zecimale). */

export type EurostatSet = {
  key: string
  scurt: string
  titlu: string
  descriere: string
  cod: string
  freq: 'M' | 'Q'
  unitate: string
  zecimale: number
  agregare: 'suma' | 'medie'
  note: string[]
  url: string
  /** numele sursei în subsol (implicit „Eurostat”) */
  sursa?: string
  actualizat: string
  perioade: string[]
  serii: { nume: string; valori: (number | null)[]; provizorii: number[] }[]
}

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const LUNI_SCURT = ['Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug', 'Sep', 'Oct', 'Noi', 'Dec']
const PALETA = ['#12a5b8', '#e5544b', '#5b4be0', '#e0a020', '#22b07d', '#e0559c', '#3b82f6', '#7c5ce6', '#8a6d3b', '#5a6178', '#0b5f6a', '#c2410c']


/** „2026-03” → { an: 2026, poz: 3 }; „2026-Q1” → { an: 2026, poz: 1 } */
const parse = (p: string) => (p.includes('Q') ? { an: +p.slice(0, 4), poz: +p.slice(-1) } : { an: +p.slice(0, 4), poz: +p.slice(5, 7) })
const eticheta = (p: string, lung = false) => {
  const { an, poz } = parse(p)
  if (p.includes('Q')) return `${lung ? 'trimestrul ' : 'T'}${poz} ${an}`
  return `${lung ? LUNI[poz - 1] : LUNI_SCURT[poz - 1]} ${an}`
}

type Rand = { p: string; an: number; poz: number; et: string; vals: (number | null)[]; prov: boolean[]; yoy: number | null }
type SortCol = 'p' | 'yoy' | number

/** locale: 'en-US' → 1,234.5 (implicit, cerut pentru Eurostat); 'ro-RO' → 1.234,5 */
export default function EurostatExplorer({ set, accent = '#12a5b8', locale = 'en-US' }: { set: EurostatSet; accent?: string; locale?: string }) {
  const nf = (z: number) => new Intl.NumberFormat(locale, { minimumFractionDigits: z, maximumFractionDigits: z })
  const pctFmt = nf(1)
  const semn = (p: number) => `${p > 0 ? '+' : p < 0 ? '−' : ''}${pctFmt.format(Math.abs(p))}%`
  const f = nf(set.zecimale)
  const fmt = (v: number | null | undefined) => (v == null ? '—' : f.format(v))
  const perAn = set.freq === 'Q' ? 4 : 12
  const etPoz = set.freq === 'Q' ? ['T1', 'T2', 'T3', 'T4'] : LUNI_SCURT
  const ani = useMemo(() => Array.from(new Set(set.perioade.map(p => parse(p).an))), [set.perioade])

  const [ind, setInd] = useState(0)
  const [aniSel, setAniSel] = useState<number[]>(ani.slice(-3))
  const [mod, setMod] = useState<'suprapus' | 'continuu'>('suprapus')
  const [cauta, setCauta] = useState('')
  const [sort, setSort] = useState<{ col: SortCol; dir: 1 | -1 }>({ col: 'p', dir: -1 })

  const serie = set.serii[ind]
  const idx = useMemo(() => new Map(set.perioade.map((p, i) => [p, i])), [set.perioade])
  const val = (s: number, an: number, poz: number) => {
    const i = idx.get(set.freq === 'Q' ? `${an}-Q${poz}` : `${an}-${String(poz).padStart(2, '0')}`)
    return i == null ? null : set.serii[s].valori[i]
  }

  /* ── KPI-uri și „pe scurt” (pentru indicatorul ales) ── */
  const rezumat = useMemo(() => {
    const v = serie.valori
    let u = v.length - 1
    while (u >= 0 && v[u] == null) u--
    const pU = set.perioade[u], { an, poz } = parse(pU)
    const vU = v[u]!, vT = val(ind, an - 1, poz)
    const pYoY = vT ? (vU - vT) / vT * 100 : null
    // anul curent (până la ultima perioadă) vs. aceleași perioade din anul trecut
    const agg = (a: number) => {
      const x = Array.from({ length: poz }, (_, k) => val(ind, a, k + 1))
      if (x.some(y => y == null)) return null
      const s = (x as number[]).reduce((p, c) => p + c, 0)
      return set.agregare === 'suma' ? s : s / x.length
    }
    const aC = agg(an), aT = agg(an - 1)
    const pAn = aC != null && aT ? (aC - aT) / aT * 100 : null
    let iMax = 0
    v.forEach((x, i) => { if (x != null && x > (v[iMax] ?? -Infinity)) iMax = i })
    return { pU, vU, vT, pYoY, an, poz, aC, aT, pAn, iMax }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ind, set])

  const { pU, vU, vT, pYoY, an, poz, aC, pAn, iMax } = rezumat
  const perioadaAn = poz === perAn ? `tot anul ${an}` : poz === 1 ? eticheta(pU, true) : `${set.freq === 'Q' ? `primele ${poz} trimestre` : `primele ${poz} luni`} din ${an}`
  const cuvant = set.agregare === 'suma' ? 'Total' : 'Media'
  const pe_scurt = `În ${eticheta(pU, true)}: ${fmt(vU)} ${set.unitate.startsWith('indice') ? `(${set.unitate})` : set.unitate}` +
    (pYoY != null ? `, cu ${pctFmt.format(Math.abs(pYoY))}% ${set.key === 'preturi' ? (pYoY >= 0 ? 'mai scump' : 'mai ieftin') : pYoY >= 0 ? 'mai mult' : 'mai puțin'} decât în ${eticheta(`${set.perioade[0].includes('Q') ? `${an - 1}-Q${poz}` : `${an - 1}-${String(poz).padStart(2, '0')}`}`, true)}.` : '.') +
    (pAn != null && poz > 1 ? ` Pe ${perioadaAn}, ${set.agregare === 'suma' ? 'totalul' : 'media'} e ${pAn >= 0 ? 'în creștere' : 'în scădere'} cu ${pctFmt.format(Math.abs(pAn))}% față de aceeași perioadă a anului trecut.` : '')

  /* ── Grafic ── */
  const aniGrafic = [...aniSel].sort((a, b) => a - b)
  const culoareAn = (a: number) => (a === ani[ani.length - 1] ? accent : PALETA[(ani.indexOf(a) + 1) % PALETA.length])
  const dateGrafic: Record<string, string | number | null>[] = mod === 'suprapus'
    ? etPoz.map((e, k) => {
        const r: Record<string, string | number | null> = { x: e }
        aniGrafic.forEach(a => { r[String(a)] = val(ind, a, k + 1) })
        return r
      })
    : set.perioade.filter(p => aniSel.includes(parse(p).an)).map(p => ({ x: eticheta(p), v: serie.valori[idx.get(p)!] }))
  const toate = (mod === 'suprapus'
    ? dateGrafic.flatMap(r => aniGrafic.map(a => r[String(a)] as number | null))
    : dateGrafic.map(r => r.v as number | null)).filter((x): x is number => x != null)
  const yMin = toate.length ? Math.min(...toate) : 0, yMax = toate.length ? Math.max(...toate) : 1
  // gradații rotunde: indicii pornesc aproape de minim, cantitățile de la 0
  const jos = set.unitate.startsWith('indice') ? yMin : 0
  const pas = [1, 2, 2.5, 5].flatMap(m => [0.1, 1, 10, 100, 1e3, 1e4, 1e5, 1e6].map(p => m * p)).sort((x, y) => x - y)
    .find(x => (yMax - jos) / x <= 5) ?? 1e7
  const ticks: number[] = []
  for (let v = Math.floor(jos / pas) * pas; v <= Math.ceil(yMax / pas) * pas + 1e-9; v += pas) ticks.push(Math.round(v * 10) / 10)
  const dom: [number, number] = [ticks[0], ticks[ticks.length - 1]]
  const scurt = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 })
  const axa = (v: number) => (Math.abs(v) >= 1e6 ? `${scurt.format(v / 1e6)}M` : Math.abs(v) >= 1e3 && yMax >= 1e4 ? `${scurt.format(v / 1e3)}k` : scurt.format(v))

  /* ── Tabel ── */
  const randuri: Rand[] = useMemo(() => set.perioade.map((p, i) => {
    const { an: a, poz: z } = parse(p)
    const v = set.serii[ind].valori[i], t = val(ind, a - 1, z)
    return {
      p, an: a, poz: z, et: eticheta(p, true),
      vals: set.serii.map(s => s.valori[i]),
      prov: set.serii.map(s => s.provizorii.includes(i)),
      yoy: v != null && t ? (v - t) / t * 100 : null,
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [set, ind])
  const q = cauta.trim().toLowerCase()
  const vizibile = randuri
    .filter(r => aniSel.includes(r.an))
    .filter(r => !q || r.et.includes(q) || eticheta(r.p).toLowerCase().includes(q) || r.p.includes(q))
    .sort((a, b) => {
      const g = (r: Rand) => (sort.col === 'p' ? r.p : sort.col === 'yoy' ? r.yoy : r.vals[sort.col])
      const x = g(a), y = g(b)
      if (x == null) return 1
      if (y == null) return -1
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir
    })
  const sorteaza = (col: SortCol) => setSort(s => (s.col === col ? { col, dir: (s.dir * -1) as 1 | -1 } : { col, dir: -1 }))
  const sageata = (col: SortCol) => (sort.col === col ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ↕')
  const comuta = (a: number) => setAniSel(s => (s.includes(a) ? (s.length > 1 ? s.filter(x => x !== a) : s) : [...s, a]))
  const areProv = vizibile.some(r => r.prov.some(Boolean))

  return (
    <div className="ex">
      <style dangerouslySetInnerHTML={{ __html: `
        .ex{--acc:${accent}}
        .ex-desc{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;font-size:14px;line-height:1.55;color:var(--ink2);margin-bottom:14px}
        .ex-desc b{color:var(--ink)}
        .ex-ctl{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:12px;margin-bottom:14px}
        .ex-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
        .ex-lbl{font-size:12px;font-weight:700;color:var(--mute);min-width:74px}
        .ex select,.ex input[type=search]{font:inherit;font-size:14px;color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:9px;padding:8px 10px;min-width:0}
        .ex select{flex:1;max-width:460px;font-weight:600}
        .ex select:focus,.ex input:focus{outline:2px solid var(--acc);outline-offset:1px}
        .ex-yr{font:inherit;font-size:13px;font-weight:700;border:1px solid var(--line);background:#fff;color:var(--ink2);border-radius:100px;padding:5px 11px;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
        .ex-yr i{width:9px;height:9px;border-radius:50%;display:inline-block;background:var(--line)}
        .ex-yr.on{border-color:var(--ink);color:var(--ink)}
        .ex-q{font:inherit;font-size:12.5px;font-weight:600;color:var(--acc);background:none;border:none;cursor:pointer;padding:4px 6px;text-decoration:underline}
        .ex-tbl{overflow-x:auto;max-height:520px;overflow-y:auto}
        .ex table{width:100%;border-collapse:collapse;font-size:13.5px}
        .ex thead th{position:sticky;top:0;background:#fff;z-index:1;cursor:pointer;user-select:none}
        .ex thead th:hover{color:var(--ink)}
        .ex th.sel,.ex td.sel{background:#f2fafb}
        .ex td.up{color:var(--up)}.ex td.down{color:var(--down)}
        .ex-prov{color:var(--mute);font-weight:400;margin-left:2px}
        .ex-notes{margin:10px 0 0;padding-left:18px;font-size:12.5px;color:var(--mute);line-height:1.5}
      ` }} />

      <div className="ex-desc"><b>{set.titlu}.</b> {set.descriere}</div>

      <div className="ex-ctl">
        <div className="ex-row">
          <span className="ex-lbl">Indicator</span>
          <select value={ind} onChange={e => setInd(+e.target.value)} aria-label="Alege indicatorul">
            {set.serii.map((s, i) => <option key={s.nume} value={i}>{s.nume}</option>)}
          </select>
        </div>
        <div className="ex-row">
          <span className="ex-lbl">Ani</span>
          {ani.map(a => (
            <button key={a} className={'ex-yr' + (aniSel.includes(a) ? ' on' : '')} onClick={() => comuta(a)} aria-pressed={aniSel.includes(a)}>
              <i style={aniSel.includes(a) && mod === 'suprapus' ? { background: culoareAn(a) } : undefined} />{a}
            </button>
          ))}
          <button className="ex-q" onClick={() => setAniSel(ani.slice(-3))}>ultimii 3</button>
          <button className="ex-q" onClick={() => setAniSel(ani)}>toți</button>
        </div>
      </div>

      <div className="ma-kpis" style={{ marginTop: 0 }}>
        <div className="ma-kpi">
          <div className="l">Ultima valoare ({eticheta(pU, true)})</div>
          <div className="v">{fmt(vU)}</div>
          {pYoY != null && <div className={'c ' + (pYoY >= 0 ? 'up' : 'down')}>{pYoY >= 0 ? '▲' : '▼'} {semn(pYoY)} față de anul trecut</div>}
          <div className="h">{set.unitate}{vT != null ? ` · acum un an: ${fmt(vT)}` : ''}</div>
        </div>
        <div className="ma-kpi">
          <div className="l">{cuvant} {poz === perAn || poz === 1 ? 'în' : 'pe'} {perioadaAn}</div>
          <div className="v">{fmt(aC)}</div>
          {pAn != null && <div className={'c ' + (pAn >= 0 ? 'up' : 'down')}>{pAn >= 0 ? '▲' : '▼'} {semn(pAn)} față de aceeași perioadă din {an - 1}</div>}
          <div className="h">{set.agregare === 'suma' ? 'Adunat pe perioadele publicate.' : 'Media perioadelor publicate.'}</div>
        </div>
        <div className="ma-kpi">
          <div className="l">Cea mai mare valoare</div>
          <div className="v">{fmt(serie.valori[iMax])}</div>
          <div className="c">{eticheta(set.perioade[iMax], true)}</div>
          <div className="h">Din {eticheta(set.perioade[0], true)} încoace.</div>
        </div>
      </div>

      <div className="ma-plain">💡 {pe_scurt}</div>

      <div className="ma-card" style={{ marginBottom: 14 }}>
        <div className="ma-ch">
          <h3>{serie.nume} — {set.unitate}</h3>
          <div className="ma-seg">
            <button className={mod === 'suprapus' ? 'on' : ''} onClick={() => setMod('suprapus')}>📅 Ani suprapuși</button>
            <button className={mod === 'continuu' ? 'on' : ''} onClick={() => setMod('continuu')}>📈 Continuu</button>
          </div>
        </div>
        {mod === 'suprapus' && (
          <div className="ma-legend">
            {aniGrafic.map(a => <span key={a}><i style={{ background: culoareAn(a) }} />{a}</span>)}
          </div>
        )}
        <div className="ma-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dateGrafic}>
              <CartesianGrid vertical={false} stroke="#eef0f6" />
              <XAxis dataKey="x" tick={{ fontSize: 11, fill: '#9aa3b8' }} minTickGap={8} />
              <YAxis tick={{ fontSize: 11, fill: '#9aa3b8' }} tickFormatter={axa} domain={dom} ticks={ticks} width={56} />
              <Tooltip formatter={(v: number, k: string) => [fmt(v), mod === 'suprapus' ? k : serie.nume]} />
              {mod === 'suprapus'
                ? aniGrafic.map(a => (
                    <Line key={a} dataKey={String(a)} stroke={culoareAn(a)} strokeWidth={a === ani[ani.length - 1] ? 3 : 2} dot={set.freq === 'Q'} connectNulls={false} isAnimationActive={false} />
                  ))
                : <Line dataKey="v" stroke={accent} strokeWidth={2.5} dot={false} isAnimationActive={false} />}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="ma-card">
        <div className="ma-ch">
          <h3>Tabel — {vizibile.length} {set.freq === 'Q' ? 'trimestre' : 'luni'}</h3>
          <input type="search" placeholder={set.freq === 'Q' ? 'Caută: T2, 2025…' : 'Caută: mai, 2025…'} value={cauta} onChange={e => setCauta(e.target.value)} aria-label="Filtrează perioadele" />
        </div>
        <div className="ex-tbl">
          <table>
            <thead>
              <tr>
                <th onClick={() => sorteaza('p')}>Perioada{sageata('p')}</th>
                {set.serii.map((s, i) => (
                  <th key={s.nume} className={'n' + (i === ind ? ' sel' : '')} onClick={() => sorteaza(i)} title="Sortează">{s.nume}{sageata(i)}</th>
                ))}
                <th className="n" onClick={() => sorteaza('yoy')} title={`Variația „${serie.nume}” față de aceeași perioadă a anului trecut`}>Față de anul trecut{sageata('yoy')}</th>
              </tr>
            </thead>
            <tbody>
              {vizibile.map(r => (
                <tr key={r.p}>
                  <td>{r.et}</td>
                  {r.vals.map((v, i) => (
                    <td key={i} className={'n' + (i === ind ? ' sel' : '')}>{fmt(v)}{r.prov[i] && <span className="ex-prov">*</span>}</td>
                  ))}
                  <td className={'n ' + (r.yoy == null ? '' : r.yoy >= 0 ? 'up' : 'down')}>{r.yoy == null ? '—' : semn(r.yoy)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="ma-src">
          📌 Sursă: {set.sursa ?? 'Eurostat'} · <a href={set.url} target="_blank" rel="noopener noreferrer">{set.cod}</a> · Prelucrare: 24reco.com · verificat lunar (ultima schimbare a datelor: {set.actualizat})
          {areProv && <><br />* valoare provizorie sau estimată — Eurostat o poate revizui.</>}
          <ul className="ex-notes">{set.note.map(n => <li key={n}>{n}</li>)}</ul>
        </div>
      </div>
    </div>
  )
}
