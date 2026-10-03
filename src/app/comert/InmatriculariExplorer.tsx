'use client'

import { useMemo, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts'

/* Înmatriculări autoturisme (DRPCIV) în stil Model A: alegi perioada (o lună sau tot anul) și tipul (noi / rulate),
   apoi analiza (evoluție, mărci, județe, combustibil, proprietari). Fiecare are KPI-uri, „pe scurt”, grafic și
   tabel sortabil și filtrabil. Datele vin din public/comert_data.json (scripts/fetch_comert.py, lunar). */

type Pair = [string, number]
type DimByMotiv = { nou: Pair[]; uzat: Pair[] }
export type Luna = { label: string; total: number; nou: number; uzat: number; marca: DimByMotiv; judet: DimByMotiv; combustibil: DimByMotiv; detinator: DimByMotiv }
export type ComertData = { meta: { source: string; category: string; updated: string }; months: Record<string, Luna> }

type Motiv = 'toate' | 'nou' | 'uzat'
type Dim = 'marca' | 'judet' | 'combustibil' | 'detinator'
type Tab = 'evolutie' | Dim

const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
const LUNI_SCURT = ['Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug', 'Sep', 'Oct', 'Noi', 'Dec']
const TABURI: { key: Tab; label: string }[] = [
  { key: 'evolutie', label: 'Evoluție lunară' }, { key: 'marca', label: 'Mărci' }, { key: 'judet', label: 'Județe' },
  { key: 'combustibil', label: 'Combustibil' }, { key: 'detinator', label: 'Proprietari' },
]
const COL: Record<Dim, string> = { marca: 'Marca', judet: 'Județul', combustibil: 'Combustibil', detinator: 'Proprietar' }
const C_NOU = '#e0a020', C_UZAT = '#5a6178'

/* ── Nume pe înțeles (sursa le dă cu majuscule și fără diacritice) ── */
const JUDETE: Record<string, string> = {
  BUCURESTI: 'București', ARGES: 'Argeș', BACAU: 'Bacău', BIHOR: 'Bihor', 'BISTRITA-NASAUD': 'Bistrița-Năsăud', BOTOSANI: 'Botoșani',
  BRAILA: 'Brăila', BRASOV: 'Brașov', BUZAU: 'Buzău', CALARASI: 'Călărași', 'CARAS-SEVERIN': 'Caraș-Severin', CONSTANTA: 'Constanța',
  DAMBOVITA: 'Dâmbovița', GALATI: 'Galați', IALOMITA: 'Ialomița', IASI: 'Iași', MARAMURES: 'Maramureș', MEHEDINTI: 'Mehedinți',
  MURES: 'Mureș', NEAMT: 'Neamț', SALAJ: 'Sălaj', TIMIS: 'Timiș', VALCEA: 'Vâlcea',
}
const COMB: Record<string, string> = {
  MOTORINA: 'Motorină', BENZINA: 'Benzină', ELECTRIC: 'Electric', 'BENZINA+GPL': 'Benzină + GPL', 'BENZINA+GNC': 'Benzină + GNC',
  GPL: 'GPL', GNC: 'GNC', 'MOTORINA+GPL': 'Motorină + GPL', HIDROGEN: 'Hidrogen',
}
const DET: Record<string, string> = {
  'PERSOANA FIZICA': 'Persoane fizice', COMPANIE: 'Firme', 'PERSOANA STRAINA': 'Persoane străine', 'MISIUNE DIPLOMATICA': 'Misiuni diplomatice',
}
const cap = (s: string) => s.toLowerCase().replace(/(^|[\s-])[a-z]/g, m => m.toUpperCase())
const numeFrumos = (dim: Dim, k: string) =>
  dim === 'judet' ? JUDETE[k] ?? cap(k)
    : dim === 'combustibil' ? COMB[k] ?? (k.startsWith('HIBRID') ? `Hibrid (tip ${k.slice(7)})` : cap(k))
      : dim === 'detinator' ? DET[k] ?? cap(k)
        : k
const verde = (k: string) => k === 'ELECTRIC' || k.startsWith('HIBRID')

const nf = new Intl.NumberFormat('ro-RO')
const f0 = (n: number) => nf.format(Math.round(n))
const p1 = (n: number) => new Intl.NumberFormat('ro-RO', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(n) + '%'
const semn = (n: number) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${p1(Math.abs(n))}`
const masini = (n: number) => `${f0(n)} ${n % 100 >= 1 && n % 100 <= 19 && n !== 1 ? 'mașini' : n === 1 ? 'mașină' : 'de mașini'}`

/** cheie „2026_08” → { an: 2026, luna: 8 } */
const k2 = (k: string) => ({ an: +k.slice(0, 4), luna: +k.slice(5, 7) })
const cheie = (an: number, luna: number) => `${an}_${String(luna).padStart(2, '0')}`

type Rand = { k: string; nume: string; total: number; nou: number; uzat: number; pond: number }
type SortCol = 'nume' | 'total' | 'nou' | 'uzat' | 'pond'

export default function InmatriculariExplorer({ data, accent }: { data: ComertData; accent: string }) {
  const chei = useMemo(() => Object.keys(data.months).sort(), [data])
  const ultima = chei[chei.length - 1]
  const anCurent = k2(ultima).an
  const cheiAn = chei.filter(k => k2(k).an === anCurent)

  const [per, setPer] = useState<string>(ultima)  // o cheie de lună sau „AN”
  const [motiv, setMotiv] = useState<Motiv>('toate')
  const [tab, setTab] = useState<Tab>('evolutie')
  const [view, setView] = useState<'grafic' | 'tabel'>('grafic')
  const [cauta, setCauta] = useState('')
  const [sort, setSort] = useState<{ col: SortCol; dir: 1 | -1 }>({ col: 'total', dir: -1 })

  const luniSel = per === 'AN' ? cheiAn : [per]
  const numePer = per === 'AN'
    ? `${LUNI[k2(cheiAn[0]).luna - 1]}–${LUNI[k2(cheiAn[cheiAn.length - 1]).luna - 1]} ${anCurent}`
    : `${LUNI[k2(per).luna - 1]} ${k2(per).an}`
  const val = (l: Luna) => (motiv === 'nou' ? l.nou : motiv === 'uzat' ? l.uzat : l.total)
  const tipTxt = motiv === 'nou' ? 'noi' : motiv === 'uzat' ? 'rulate' : ''

  /* ── agregare pe dimensiune pentru perioada aleasă ── */
  const agrega = (dim: Dim, luni: string[]): Rand[] => {
    const m = new Map<string, { nou: number; uzat: number }>()
    for (const k of luni) for (const mv of ['nou', 'uzat'] as const)
      for (const [n, v] of data.months[k][dim][mv]) {
        const x = m.get(n) ?? { nou: 0, uzat: 0 }
        x[mv] += v
        m.set(n, x)
      }
    const r = Array.from(m, ([k, x]) => ({ k, nume: numeFrumos(dim, k), nou: x.nou, uzat: x.uzat, total: x.nou + x.uzat, pond: 0 }))
    const sel = (x: Rand) => (motiv === 'nou' ? x.nou : motiv === 'uzat' ? x.uzat : x.total)
    const tot = r.reduce((a, x) => a + sel(x), 0) || 1
    return r.map(x => ({ ...x, pond: sel(x) / tot * 100 }))
      .filter(x => sel(x) > 0).sort((a, b) => sel(b) - sel(a))
  }
  const sel = (x: Rand) => (motiv === 'nou' ? x.nou : motiv === 'uzat' ? x.uzat : x.total)

  /* ── seria lunară (cu goluri pentru lunile lipsă) ── */
  const lunar = useMemo(() => {
    const a = k2(chei[0]), b = k2(ultima)
    const out: { k: string; et: string; lung: string; l: Luna | null }[] = []
    for (let t = a.an * 12 + a.luna - 1; t <= b.an * 12 + b.luna - 1; t++) {
      const an = Math.floor(t / 12), luna = (t % 12) + 1, k = cheie(an, luna)
      out.push({ k, et: `${LUNI_SCURT[luna - 1]} ${String(an).slice(2)}`, lung: `${LUNI[luna - 1]} ${an}`, l: data.months[k] ?? null })
    }
    return out
  }, [chei, ultima, data])
  const lipsa = lunar.filter(x => !x.l).map(x => x.lung)

  const totalPer = luniSel.reduce((a, k) => a + val(data.months[k]), 0)
  const nouPer = luniSel.reduce((a, k) => a + data.months[k].nou, 0)
  const toatePer = luniSel.reduce((a, k) => a + data.months[k].total, 0)
  // comparația cu luna precedentă (doar când e aleasă o singură lună și precedenta există)
  const prec = per === 'AN' ? null : (() => { const { an, luna } = k2(per); return luna === 1 ? cheie(an - 1, 12) : cheie(an, luna - 1) })()
  const vPrec = prec && data.months[prec] ? val(data.months[prec]) : null
  const dPrec = vPrec ? (totalPer - vPrec) / vPrec * 100 : null

  const dim: Dim | null = tab === 'evolutie' ? null : tab
  const randuri = useMemo(() => (dim ? agrega(dim, luniSel) : []), [dim, per, motiv]) // eslint-disable-line react-hooks/exhaustive-deps

  /* ── KPI-uri și „pe scurt” ── */
  type K = { l: string; v: string; c?: string; dir?: 'up' | 'down'; h?: string }
  let kpis: K[] = [], pe_scurt = ''
  const kTotal: K = {
    l: `Mașini ${tipTxt ? tipTxt + ' ' : ''}înmatriculate — ${numePer}`, v: f0(totalPer),
    ...(dPrec != null ? { c: `${dPrec >= 0 ? '▲' : '▼'} ${semn(dPrec)} față de ${LUNI[k2(prec!).luna - 1]}`, dir: dPrec >= 0 ? 'up' as const : 'down' as const } : {}),
    h: per === 'AN' ? `${cheiAn.length} luni cu date publicate.` : 'Autoturisme înscrise în circulație în luna respectivă.',
  }
  if (!dim) {
    const vals = cheiAn.map(k => val(data.months[k]))
    const iMax = vals.indexOf(Math.max(...vals))
    kpis = [kTotal,
      { l: `Total ${anCurent} până acum`, v: f0(vals.reduce((a, b) => a + b, 0)), h: `Media: ${f0(vals.reduce((a, b) => a + b, 0) / vals.length)} pe lună.` },
      motiv === 'toate'
        ? { l: 'Cât din ele sunt noi', v: p1(nouPer / (toatePer || 1) * 100), h: `${f0(nouPer)} noi, ${f0(toatePer - nouPer)} rulate (aduse la mâna a doua).` }
        : { l: `Luna cu cele mai multe în ${anCurent}`, v: LUNI[k2(cheiAn[iMax]).luna - 1], h: f0(vals[iMax]) + ' mașini' }]
    pe_scurt = `În ${numePer} s-au înmatriculat ${masini(totalPer)}${tipTxt ? ' ' + tipTxt : ''}` +
      (dPrec != null ? `, cu ${p1(Math.abs(dPrec))} ${dPrec >= 0 ? 'mai multe' : 'mai puține'} decât în ${LUNI[k2(prec!).luna - 1]}.` : '.') +
      (motiv === 'toate' ? ` Cam ${Math.round((toatePer - nouPer) / (toatePer || 1) * 10)} din 10 sunt mașini rulate, aduse de obicei din străinătate.` : '')
  } else if (randuri.length) {
    const top = randuri[0]
    const top5 = randuri.slice(0, 5).reduce((a, x) => a + x.pond, 0)
    const kLider: K = { l: `Pe primul loc: ${top.nume}`, v: f0(sel(top)), c: p1(top.pond) + ' din total', h: dim === 'judet' ? 'Mașinile de firmă se înmatriculează adesea la sediul din București.' : `Urmează ${randuri.slice(1, 3).map(x => x.nume).join(' și ')}.` }
    if (dim === 'combustibil') {
      const v = randuri.filter(x => verde(x.k)).reduce((a, x) => a + x.pond, 0)
      const diesel = randuri.find(x => x.k === 'MOTORINA')?.pond ?? 0
      kpis = [kTotal, { l: 'Electrice + hibride', v: p1(v), h: 'Ponderea mașinilor care au și motor electric.' }, { l: 'Motorină', v: p1(diesel), h: 'Diesel-ul domină la mașinile rulate, aproape a dispărut la cele noi.' }]
      pe_scurt = `În ${numePer}, ${p1(v)} din mașinile ${tipTxt || 'înmatriculate'} au fost electrice sau hibride, iar ${p1(diesel)} pe motorină. Cel mai des: ${top.nume.toLowerCase()} (${p1(top.pond)}).`
    } else if (dim === 'detinator') {
      const pf = randuri.find(x => x.k === 'PERSOANA FIZICA')?.pond ?? 0, fi = randuri.find(x => x.k === 'COMPANIE')?.pond ?? 0
      kpis = [kTotal, { l: 'Cumpărate de persoane fizice', v: p1(pf) }, { l: 'Cumpărate de firme', v: p1(fi), h: 'Inclusiv leasing și flote.' }]
      pe_scurt = `În ${numePer}, ${p1(pf)} din mașinile ${tipTxt || 'înmatriculate'} au ajuns la persoane fizice și ${p1(fi)} la firme.` +
        (motiv !== 'uzat' ? ' La mașinile noi, firmele (cu leasing) cumpără de obicei cele mai multe.' : '')
    } else {
      kpis = [kTotal, kLider, { l: 'Primele 5 adunate', v: p1(top5), h: `Din ${randuri.length} ${dim === 'marca' ? 'mărci' : 'județe'} cu cel puțin o înmatriculare.` }]
      pe_scurt = `În ${numePer}, ${dim === 'marca' ? 'cea mai înmatriculată marcă' : 'județul cu cele mai multe înmatriculări'} a fost ${top.nume}: ${masini(sel(top))}${tipTxt ? ' ' + tipTxt : ''}, adică ${p1(top.pond)} din total. Primele 5 adună ${p1(top5)}.`
    }
  }

  /* ── Tabel ── */
  const q = cauta.trim().toLowerCase()
  const tabel: Rand[] = dim
    ? randuri
    : lunar.filter(x => x.l).map(x => ({ k: x.k, nume: x.lung, total: x.l!.total, nou: x.l!.nou, uzat: x.l!.uzat, pond: x.l!.nou / (x.l!.total || 1) * 100 }))
  const vizibile = tabel
    .filter(r => !q || r.nume.toLowerCase().includes(q) || r.k.toLowerCase().includes(q))
    .sort((a, b) => {
      const x = sort.col === 'nume' ? (dim ? a.nume : a.k) : a[sort.col], y = sort.col === 'nume' ? (dim ? b.nume : b.k) : b[sort.col]
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir
    })
  const sorteaza = (col: SortCol) => setSort(s => (s.col === col ? { col, dir: (s.dir * -1) as 1 | -1 } : { col, dir: col === 'nume' ? 1 : -1 }))
  const sageata = (col: SortCol) => (sort.col === col ? (sort.dir > 0 ? ' ▲' : ' ▼') : ' ↕')
  const schimbaTab = (t: Tab) => { setTab(t); setCauta(''); setSort(t === 'evolutie' ? { col: 'nume', dir: -1 } : { col: 'total', dir: -1 }) }

  /* ── Grafic ── */
  const top = randuri.slice(0, 15).map(r => ({ name: r.nume, v: sel(r), verde: dim === 'combustibil' && verde(r.k) }))
  const evol = lunar.map(x => ({ name: x.et, full: x.lung, nou: x.l && motiv !== 'uzat' ? x.l.nou : null, uzat: x.l && motiv !== 'nou' ? x.l.uzat : null }))
  const AX = { fontSize: 11, fill: '#9aa3b8' }
  const titlu = dim
    ? `${TABURI.find(t => t.key === tab)!.label} — ${numePer}${tipTxt ? `, mașini ${tipTxt}` : ''}`
    : `Înmatriculări pe luni${tipTxt ? ` — mașini ${tipTxt}` : ''}`

  return (
    <div className="im">
      <style dangerouslySetInnerHTML={{ __html: `
        .im{--acc:${accent}}
        .im-ctl{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 16px;display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-bottom:4px}
        .im-g{display:flex;gap:10px;align-items:center}
        .im-lbl{font-size:12px;font-weight:700;color:var(--mute)}
        .im select,.im input[type=search]{font:inherit;font-size:14px;color:var(--ink);background:#fff;border:1px solid var(--line);border-radius:9px;padding:8px 10px;min-width:0}
        .im select{font-weight:600}
        .im select:focus,.im input:focus{outline:2px solid var(--acc);outline-offset:1px}
        .im-tbl{overflow-x:auto;max-height:560px;overflow-y:auto}
        .im thead th{position:sticky;top:0;background:#fff;z-index:1;cursor:pointer;user-select:none}
        .im thead th:hover{color:var(--ink)}
        .im td.mute{color:var(--mute);width:36px}
        .im-bar{height:6px;border-radius:3px;background:var(--acc);opacity:.75;min-width:2px}
      ` }} />

      <div className="im-ctl">
        <div className="im-g">
          <span className="im-lbl">Perioada</span>
          <select value={per} onChange={e => setPer(e.target.value)} aria-label="Alege perioada">
            {[...chei].reverse().map(k => <option key={k} value={k}>{data.months[k].label}</option>)}
            {cheiAn.length > 1 && <option value="AN">Tot anul {anCurent} (până acum)</option>}
          </select>
        </div>
        <div className="im-g">
          <span className="im-lbl">Mașini</span>
          <div className="ma-seg">
            {([['toate', 'Toate'], ['nou', '✨ Noi'], ['uzat', '🔁 Rulate']] as [Motiv, string][]).map(([m, l]) => (
              <button key={m} className={motiv === m ? 'on' : ''} onClick={() => setMotiv(m)}>{l}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="ma-l2">
        {TABURI.map(t => <button key={t.key} className={tab === t.key ? 'on' : ''} onClick={() => schimbaTab(t.key)}>{t.label}</button>)}
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

      <div className="ma-plain">💡 {pe_scurt}</div>

      <div className="ma-card">
        <div className="ma-ch">
          <h3>{titlu}</h3>
          <div className="ma-seg">
            <button className={view === 'grafic' ? 'on' : ''} onClick={() => setView('grafic')}>📈 Grafic</button>
            <button className={view === 'tabel' ? 'on' : ''} onClick={() => setView('tabel')}>⊞ Tabel</button>
          </div>
        </div>

        {view === 'grafic' ? (
          dim ? (
            <div style={{ height: Math.max(260, top.length * 28) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={top} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid horizontal={false} stroke="#eef0f6" />
                  <XAxis type="number" tick={AX} tickFormatter={f0} />
                  <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 12, fill: '#1e2233' }} interval={0} />
                  <Tooltip formatter={(v: number) => [f0(v), 'mașini']} />
                  <Bar dataKey="v" radius={[0, 6, 6, 0]} barSize={18} isAnimationActive={false}>
                    {top.map((r, i) => <Cell key={i} fill={r.verde ? '#22b07d' : accent} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <>
              <div className="ma-legend">
                {motiv !== 'uzat' && <span><i style={{ background: C_NOU }} />Noi</span>}
                {motiv !== 'nou' && <span><i style={{ background: C_UZAT }} />Rulate</span>}
              </div>
              <div className="ma-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={evol}>
                    <CartesianGrid vertical={false} stroke="#eef0f6" />
                    <XAxis dataKey="name" tick={AX} />
                    <YAxis tick={AX} tickFormatter={f0} width={56} />
                    <Tooltip formatter={(v: number, k: string) => [f0(v), k === 'nou' ? 'Noi' : 'Rulate']}
                      labelFormatter={(_: unknown, p: { payload?: { full?: string } }[]) => p?.[0]?.payload?.full ?? ''} />
                    {motiv !== 'uzat' && <Bar dataKey="nou" stackId="a" fill={C_NOU} isAnimationActive={false} />}
                    {motiv !== 'nou' && <Bar dataKey="uzat" stackId="a" fill={C_UZAT} radius={[6, 6, 0, 0]} isAnimationActive={false} />}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
              <span className="im-lbl">{vizibile.length} {dim ? 'rânduri' : 'luni'} · clic pe antet pentru sortare</span>
              <input type="search" placeholder={dim === 'marca' ? 'Caută o marcă…' : dim === 'judet' ? 'Caută un județ…' : dim ? 'Caută…' : 'Caută: mai, 2026…'}
                value={cauta} onChange={e => setCauta(e.target.value)} aria-label="Filtrează tabelul" />
            </div>
            <div className="im-tbl">
              <table>
                <thead>
                  <tr>
                    {dim && <th>#</th>}
                    <th onClick={() => sorteaza('nume')}>{dim ? COL[dim] : 'Luna'}{sageata('nume')}</th>
                    {motiv === 'toate' && <th className="n" onClick={() => sorteaza('total')}>Total{sageata('total')}</th>}
                    {motiv !== 'uzat' && <th className="n" onClick={() => sorteaza('nou')}>Noi{sageata('nou')}</th>}
                    {motiv !== 'nou' && <th className="n" onClick={() => sorteaza('uzat')}>Rulate{sageata('uzat')}</th>}
                    <th className="n" onClick={() => sorteaza('pond')}>{dim ? 'Pondere' : 'Cât % sunt noi'}{sageata('pond')}</th>
                    {dim && <th style={{ width: 110 }} />}
                  </tr>
                </thead>
                <tbody>
                  {vizibile.map(r => (
                    <tr key={r.k}>
                      {dim && <td className="mute">{randuri.indexOf(r) + 1}</td>}
                      <td>{r.nume}</td>
                      {motiv === 'toate' && <td className="n">{f0(r.total)}</td>}
                      {motiv !== 'uzat' && <td className="n">{f0(r.nou)}</td>}
                      {motiv !== 'nou' && <td className="n">{f0(r.uzat)}</td>}
                      <td className="n">{p1(r.pond)}</td>
                      {dim && <td><div className="im-bar" style={{ width: `${r.pond / (randuri[0]?.pond || 1) * 100}%` }} /></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <div className="ma-src">
          📌 Sursă: DGPCI / DRPCIV · <a href="https://dgpci.mai.gov.ro/news-and-media/statistica" target="_blank" rel="noopener noreferrer">dgpci.mai.gov.ro</a> · Prelucrare: 24reco.com · actualizat lunar (ultima actualizare: {data.meta.updated})
          <br />Autoturisme (categoriile M1 și M1G). „Rulate” = mașini second-hand înmatriculate prima dată în România, de obicei aduse din străinătate.
          {dim === 'combustibil' && <><br />Tipurile de hibrid sunt codurile din datele DRPCIV; cu verde: electrice și hibride.</>}
          {lipsa.length > 0 && <><br />Lipsesc din date: {lipsa.join(', ')}.</>}
        </div>
      </div>
    </div>
  )
}
