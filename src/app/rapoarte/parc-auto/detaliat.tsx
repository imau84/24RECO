'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { NESPECIFICAT, de, fmt, numeMarca, useJson } from './date'
import { Asteapta, Plain, Sursa } from './comune'

/* Tab-ul „Date complete”: toate autoturismele la nivel de model, doar la nivel național,
   din public/parc-auto/<an>/detaliat/RO.json (scripts/parc-auto/07_build_detaliat.py). */

type Detaliat = {
  an: number
  categorii: string[]
  marci: string[]
  /** [indice marcă, familie] */
  familii: [number, string][]
  /** [indice categorie, indice familie, model, ...15 valori în ordinea din COL] */
  randuri: (number | string)[][]
}

const COL = [
  { l: 'Număr', f: 'Număr' },
  ...['0–2', '3–5', '6–10', '11–15', '16–20', '>20'].map(l => ({ l, f: `Vechime ${l}` })),
  ...['Benzină', 'Motorină', 'Electric', 'Hibrid'].map(l => ({ l, f: `Carburant · ${l}` })),
  ...['0–4', '5–8', '9–12', 'peste 12'].map(l => ({ l, f: `Vechime ${l}` })),
]
const GRUPE = [{ l: 'Vechime (ani)', n: 6 }, { l: 'Carburant', n: 4 }, { l: 'Vechime (ani)', n: 4 }]
const OPERATORI = ['>', '≥', '<', '≤', '='] as const
type Op = typeof OPERATORI[number]
type Filtru = { c: number; op: Op; v: number }
type Sort = { k: 'nume' | 'cat' | number; desc: boolean }

type Model = { cat: number; fam: number; marca: number; model: string; v: number[] }
type Rand = { nume: string; cat: string; v: number[] }

const PE_PAGINA = 50
const zero = () => COL.map(() => 0)
const aduna = (a: number[], b: number[]) => { for (let i = 0; i < a.length; i++) a[i] += b[i] }
const z = (x: number) => (x === 0 ? '–' : fmt(x))
const compact = (s: string) => s.toUpperCase().replace(/\s+/g, '')
const numeModelRaport = (m: string) => (m.trim() === '' ? '(necompletat)' : m)
/** „1 familie”, „5 familii”, „67 de familii” */
const cate = (x: number, unu: string, multe: string) => (x === 1 ? `1 ${unu}` : `${fmt(x)}${de(x)} ${multe}`)
const numeFamilie =(f: string) => (f === NESPECIFICAT ? '(model nespecificat)' : f)

function trece(f: Filtru, v: number[]) {
  const x = v[f.c]
  switch (f.op) {
    case '>': return x > f.v
    case '≥': return x >= f.v
    case '<': return x < f.v
    case '≤': return x <= f.v
    default: return x === f.v
  }
}

function sorteaza<T extends Rand>(r: T[], s: Sort): T[] {
  const cmp = (a: T, b: T) => {
    if (s.k === 'nume') return a.nume.localeCompare(b.nume, 'ro')
    if (s.k === 'cat') return a.cat.localeCompare(b.cat)
    return a.v[s.k] - b.v[s.k]
  }
  return [...r].sort((a, b) => (s.desc ? -cmp(a, b) : cmp(a, b)) || b.v[0] - a.v[0] || a.nume.localeCompare(b.nume, 'ro'))
}

/* ── listă derulantă cu căutare ── */
function AlegeMarca({ marci, totaluri, valoare, set }: {
  marci: string[]; totaluri: number[]; valoare: number | null; set: (m: number | null) => void
}) {
  const [deschis, setDeschis] = useState(false)
  const [q, setQ] = useState('')
  const [hi, setHi] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!deschis) return
    const inchide = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setDeschis(false) }
    document.addEventListener('mousedown', inchide)
    return () => document.removeEventListener('mousedown', inchide)
  }, [deschis])

  const optiuni: (number | null)[] = useMemo(() => {
    const c = compact(q)
    const gasite = marci.map((_, i) => i).filter(i => !c || compact(marci[i]).includes(c))
    return c ? gasite : [null, ...gasite]
  }, [q, marci])
  const alege = (m: number | null) => { set(m); setDeschis(false); setQ('') }

  return (
    <div className="pd-cb" ref={ref}>
      <button type="button" className="pd-cb-btn" onClick={() => { setDeschis(d => !d); setHi(0) }}>
        <span>{valoare == null ? 'Toate mărcile' : numeMarca(marci[valoare])}</span><span aria-hidden>▾</span>
      </button>
      {deschis && (
        <div className="pd-cb-pop">
          <input autoFocus placeholder="Caută marca…" value={q}
            onChange={e => { setQ(e.target.value); setHi(0) }}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setHi(h => Math.min(h + 1, optiuni.length - 1)) }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setHi(h => Math.max(h - 1, 0)) }
              else if (e.key === 'Enter' && optiuni[hi] !== undefined) alege(optiuni[hi])
              else if (e.key === 'Escape') setDeschis(false)
            }} />
          <ul>
            {optiuni.length === 0 && <li className="pd-cb-gol">Nicio marcă găsită</li>}
            {optiuni.map((m, i) => (
              <li key={m ?? 'toate'} className={(i === hi ? 'hi ' : '') + (m === valoare ? 'on' : '')}
                onMouseEnter={() => setHi(i)} onMouseDown={e => { e.preventDefault(); alege(m) }}>
                <span>{m == null ? 'Toate mărcile' : numeMarca(marci[m])}</span>
                {m != null && <small>{fmt(totaluri[m])}</small>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ── CSV (separator ;, cu BOM pentru Excel) ── */
function descarcaCsv(nume: string, antet: string[], randuri: (string | number)[][]) {
  const cel = (x: string | number) => (typeof x === 'number' ? String(x) : /[;"\n]/.test(x) ? `"${x.replace(/"/g, '""')}"` : x)
  const text = '﻿' + [antet, ...randuri].map(r => r.map(cel).join(';')).join('\r\n')
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = nume
  a.click()
  URL.revokeObjectURL(url)
}

export function DateComplete({ an }: { an: number }) {
  const { data, error } = useJson<Detaliat>(`/parc-auto/${an}/detaliat/RO.json`)
  const [mod, setMod] = useState<'grupat' | 'lista'>('grupat')
  const [marca, setMarca] = useState<number | null>(null)
  const [cat, setCat] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [filtre, setFiltre] = useState<Filtru[]>([])
  const [nou, setNou] = useState<{ c: number; op: Op; v: string } | null>(null)
  const [sort, setSort] = useState<Sort>({ k: 0, desc: true })
  const [pagina, setPagina] = useState(0)
  const [deschise, setDeschise] = useState<Set<number>>(new Set())

  const modele: Model[] = useMemo(() => (data?.randuri ?? []).map(r => ({
    cat: r[0] as number, fam: r[1] as number, marca: data!.familii[r[1] as number][0], model: r[2] as string,
    v: r.slice(3) as number[],
  })), [data])
  const totaluriMarci = useMemo(() => {
    const t = (data?.marci ?? []).map(() => 0)
    for (const m of modele) t[m.marca] += m.v[0]
    return t
  }, [data, modele])

  const filtrate = useMemo(() => {
    const c = compact(q)
    return modele.filter(m => (marca == null || m.marca === marca) && (cat == null || m.cat === cat)
      && (!c || compact(m.model).includes(c)) && filtre.every(f => trece(f, m.v)))
  }, [modele, marca, cat, q, filtre])

  useEffect(() => { setPagina(0) }, [mod, marca, cat, q, filtre, sort])
  useEffect(() => { setDeschise(new Set()) }, [marca])

  if (!data) return <Asteapta eroare={error} />
  const categorie = (i: number) => data.categorii[i]
  const filtrat = cat != null || q.trim() !== '' || filtre.length > 0

  // ── rândurile tabelului, după mod ──
  type RandModel = Rand & { m: Model }
  type RandFamilie = Rand & { fam: number; modele: RandModel[] }
  type RandMarca = Rand & { marca: number; nModele: number }
  const rm = (m: Model): RandModel => ({ nume: m.model, cat: categorie(m.cat), v: m.v, m })

  let lista: RandModel[] = [], familii: RandFamilie[] = [], marciR: RandMarca[] = []
  const total = zero()
  for (const m of filtrate) aduna(total, m.v)
  if (mod === 'lista') {
    lista = sorteaza(filtrate.map(rm), sort)
  } else if (marca == null) {
    const pe = new Map<number, RandMarca>()
    for (const m of filtrate) {
      let r = pe.get(m.marca)
      if (!r) pe.set(m.marca, r = { nume: numeMarca(data.marci[m.marca]), cat: '', v: zero(), marca: m.marca, nModele: 0 })
      aduna(r.v, m.v)
      r.nModele++
    }
    marciR = sorteaza(Array.from(pe.values()), sort)
  } else {
    const pe = new Map<number, RandFamilie & { cats: Set<number> }>()
    for (const m of filtrate) {
      let r = pe.get(m.fam)
      if (!r) pe.set(m.fam, r = { nume: numeFamilie(data.familii[m.fam][1]), cat: '', v: zero(), fam: m.fam, modele: [], cats: new Set() })
      aduna(r.v, m.v)
      r.modele.push(rm(m))
      r.cats.add(m.cat)
    }
    familii = sorteaza(Array.from(pe.values()).map(r => ({
      ...r, cat: Array.from(r.cats).sort().map(categorie).join(', '), modele: sorteaza(r.modele, sort),
    })), sort)
  }
  const nRanduri = mod === 'lista' ? lista.length : marca == null ? marciR.length : familii.length
  const pagini = Math.max(1, Math.ceil(nRanduri / PE_PAGINA))
  const pg = Math.min(pagina, pagini - 1)
  const felie = <T,>(r: T[]) => r.slice(pg * PE_PAGINA, (pg + 1) * PE_PAGINA)

  // ── sumar ──
  const nMarciFiltrate = new Set(filtrate.map(m => m.marca)).size
  const nFamilii = new Set(filtrate.map(m => m.fam)).size
  const sumar = marca != null
    ? `${numeMarca(data.marci[marca])} · ${cate(filtrate.length, 'model', 'modele')} în ${cate(nFamilii, 'familie', 'familii')} · ${cate(total[0], 'autoturism', 'autoturisme')}`
    : `Toate mărcile · ${cate(filtrate.length, 'model', 'modele')} din ${cate(nMarciFiltrate, 'marcă', 'mărci')} · ${cate(total[0], 'autoturism', 'autoturisme')}`

  // ── sortare ──
  const clic = (k: Sort['k']) => setSort(s => (s.k === k ? { k, desc: !s.desc } : { k, desc: true }))
  const sageata = (k: Sort['k']) => (sort.k === k ? <span className="pd-sg">{sort.desc ? '▼' : '▲'}</span> : null)
  const Th = ({ k, l, cls, rs }: { k: Sort['k']; l: string; cls?: string; rs?: number }) =>
    <th rowSpan={rs} className={(cls ?? 'n') + (sort.k === k ? ' on' : '')} onClick={() => clic(k)}>{l}{sageata(k)}</th>

  const arataMarca = mod === 'lista'
  const prima = mod === 'grupat' && marca == null ? 'Marcă' : 'Model'
  const valori = (v: number[]) => v.map((x, i) => <td key={i} className="n">{z(x)}</td>)

  // ── CSV ──
  const csv = () => {
    const vals = COL.map(c => c.f)
    const nume = `parc-auto-${an}-${marca == null ? 'toate-marcile' : data.marci[marca].toLowerCase().replace(/[^a-z0-9]+/g, '-')}.csv`
    if (mod === 'lista') {
      descarcaCsv(nume, ['Marcă', 'Model', 'Categorie', ...vals],
        lista.map(r => [data.marci[r.m.marca], r.m.model, r.cat, ...r.v]))
    } else if (marca == null) {
      descarcaCsv(nume, ['Marcă', 'Modele', ...vals], marciR.map(r => [data.marci[r.marca], r.nModele, ...r.v]))
    } else {
      descarcaCsv(nume, ['Marcă', 'Familie', 'Model', 'Categorie', ...vals],
        familii.flatMap(f => f.modele.map(r => [data.marci[marca], data.familii[f.fam][1], r.m.model, r.cat, ...r.v])))
    }
  }

  const adaugaFiltru = () => {
    if (!nou) return
    const v = Number(nou.v.replace(/\./g, '').replace(',', '.'))
    if (nou.v.trim() === '' || !Number.isFinite(v)) return
    setFiltre(f => [...f, { c: nou.c, op: nou.op, v }])
    setNou(null)
  }
  const stergeTot = () => { setFiltre([]); setCat(null); setQ(''); setNou(null) }

  return <>
    <Plain>
      Aici sunt toate autoturismele din registrul DGPCI, model cu model, pentru toată țara. Alege o marcă și apasă pe
      {' '}▸ ca să vezi versiunile din fiecare familie, sau treci pe „Listă modele” ca să compari modele din toate mărcile.
      Apasă pe antetul unei coloane ca să sortezi.
    </Plain>
    <div className="ma-card pa-gap pd">
      <div className="ma-ch">
        <h3>Toate modelele, cu vechime și carburant <span className="pd-eticheta">🇷🇴 România (total național)</span></h3>
      </div>

      <div className="pd-bara">
        <div className="ma-seg">
          <button className={mod === 'grupat' ? 'on' : ''} onClick={() => setMod('grupat')}>▤ Grupat pe model</button>
          <button className={mod === 'lista' ? 'on' : ''} onClick={() => setMod('lista')}>☰ Listă modele</button>
        </div>
        <label>Marcă
          <AlegeMarca marci={data.marci} totaluri={totaluriMarci} valoare={marca} set={setMarca} />
        </label>
        <label>Categorie
          <select value={cat ?? ''} onChange={e => setCat(e.target.value === '' ? null : Number(e.target.value))}>
            <option value="">Toate</option>
            {data.categorii.map((c, i) => <option key={c} value={i}>{c}</option>)}
          </select>
        </label>
        <label>Caută model
          <input type="search" placeholder="ex. M340, 320D, Logan" value={q} onChange={e => setQ(e.target.value)} />
        </label>
      </div>

      <div className="pd-filtre">
        {filtre.map((f, i) => (
          <span key={i} className="pd-chip">
            {COL[f.c].f} {f.op} {fmt(f.v)}
            <button aria-label="Șterge filtrul" onClick={() => setFiltre(x => x.filter((_, j) => j !== i))}>×</button>
          </span>
        ))}
        {nou ? (
          <span className="pd-nou">
            <select value={nou.c} onChange={e => setNou({ ...nou, c: Number(e.target.value) })}>
              {COL.map((c, i) => <option key={i} value={i}>{c.f}</option>)}
            </select>
            <select value={nou.op} onChange={e => setNou({ ...nou, op: e.target.value as Op })}>
              {OPERATORI.map(o => <option key={o} value={o}>{o}</option>)}
            </select>
            <input inputMode="numeric" autoFocus placeholder="valoare" value={nou.v}
              onChange={e => setNou({ ...nou, v: e.target.value })}
              onKeyDown={e => { if (e.key === 'Enter') adaugaFiltru(); else if (e.key === 'Escape') setNou(null) }} />
            <button className="pd-btn pd-prim" onClick={adaugaFiltru}>Adaugă</button>
            <button className="pd-btn" onClick={() => setNou(null)}>Renunță</button>
          </span>
        ) : (
          <button className="pd-btn" onClick={() => setNou({ c: 9, op: '>', v: '' })}>+ Adaugă filtru</button>
        )}
        {filtre.length > 1 && <span className="pd-si">filtrele se combină cu „ȘI”</span>}
        {filtrat && <button className="pd-btn pd-link" onClick={stergeTot}>Șterge filtrele</button>}
      </div>

      <div className="pd-sumar">
        <b>{sumar}</b>
        <span className="pd-act">
          {mod === 'grupat' && marca != null && <>
            <button className="pd-btn" onClick={() => setDeschise(new Set(familii.map(f => f.fam)))}>Extinde tot</button>
            <button className="pd-btn" onClick={() => setDeschise(new Set())}>Restrânge tot</button>
          </>}
          <button className="pd-btn" onClick={csv} disabled={nRanduri === 0}>⬇ Descarcă CSV</button>
        </span>
      </div>
      {mod === 'grupat' && marca == null && <p className="pd-ind">Alege o marcă (din listă sau cu un clic pe rând) ca să vezi familiile ei de modele.</p>}

      <div className="pd-tbl">
        <table>
          <thead>
            <tr>
              <Th k="nume" l={prima} cls="pd-c1" rs={2} />
              {arataMarca && <th rowSpan={2}>Marcă</th>}
              {!(mod === 'grupat' && marca == null) ? <Th k="cat" l="Categorie" cls="" rs={2} /> : <th rowSpan={2} className="n">Modele</th>}
              <Th k={0} l="Număr" rs={2} />
              {GRUPE.map((g, i) => <th key={i} colSpan={g.n} className="pd-grup">{g.l}</th>)}
            </tr>
            <tr>{COL.slice(1).map((c, i) => <Th key={i} k={i + 1} l={c.l} />)}</tr>
          </thead>
          <tbody>
            {nRanduri > 0 && mod === 'grupat' && marca != null && (
              <tr className="pd-total">
                <td className="pd-c1">Total {numeMarca(data.marci[marca])}</td><td />{valori(total)}
              </tr>
            )}
            {mod === 'lista' && felie(lista).map((r, i) => (
              <tr key={i}>
                <td className="pd-c1">{numeModelRaport(r.nume)}</td>
                <td>{numeMarca(data.marci[r.m.marca])}</td>
                <td>{r.cat}</td>{valori(r.v)}
              </tr>
            ))}
            {mod === 'grupat' && marca == null && felie(marciR).map(r => (
              <tr key={r.marca} className="pd-clic" onClick={() => setMarca(r.marca)}>
                <td className="pd-c1">{r.nume} <span className="pd-mut">›</span></td>
                <td className="n">{fmt(r.nModele)}</td>{valori(r.v)}
              </tr>
            ))}
            {mod === 'grupat' && marca != null && felie(familii).flatMap(f => {
              const ext = deschise.has(f.fam)
              const comuta = () => setDeschise(s => { const x = new Set(s); if (ext) x.delete(f.fam); else x.add(f.fam); return x })
              return [
                <tr key={f.fam} className="pd-fam pd-clic" onClick={comuta}>
                  <td className="pd-c1">
                    <button className="pd-sag" aria-expanded={ext} aria-label={ext ? 'Restrânge' : 'Extinde'}>{ext ? '▾' : '▸'}</button>
                    {f.nume} <span className="pd-mut">({f.modele.length})</span>
                  </td>
                  <td className="pd-mut">{f.cat}</td>{valori(f.v)}
                </tr>,
                ...(ext ? f.modele.map((r, i) => (
                  <tr key={`${f.fam}-${i}`} className="pd-mod">
                    <td className="pd-c1">{numeModelRaport(r.nume)}</td><td>{r.cat}</td>{valori(r.v)}
                  </tr>
                )) : []),
              ]
            })}
            {nRanduri === 0 && <tr><td className="pd-c1 pd-gol" colSpan={COL.length + 3}>Niciun model nu trece filtrele.</td></tr>}
          </tbody>
        </table>
      </div>

      {pagini > 1 && (
        <div className="pd-pag">
          <button className="pd-btn" disabled={pg === 0} onClick={() => setPagina(pg - 1)}>‹ Înapoi</button>
          <span>Pagina {pg + 1} din {pagini} · {fmt(nRanduri)}{de(nRanduri)} {mod === 'lista' ? 'modele' : marca == null ? 'mărci' : 'familii'}</span>
          <button className="pd-btn" disabled={pg >= pagini - 1} onClick={() => setPagina(pg + 1)}>Înainte ›</button>
        </div>
      )}
      {mod === 'grupat' && filtrat && <p className="pd-ind">Subtotaluri calculate pe modelele filtrate.</p>}
      <Sursa an={an} nota={<>Denumirile modelelor sunt exact cele din registrul DGPCI. Gruparea pe familii (de exemplu Seria 3)
        este făcută de 24reco pentru ușurința citirii. Valorile 0 apar ca „–”. Hibrid = benzină+electric, motorină+electric și
        GPL+electric la un loc.</>} />
    </div>
  </>
}

export const CSS_DETALIAT = `
  .pd-eticheta{display:inline-block;margin-left:8px;font-size:12px;font-weight:700;color:#3f2a8f;background:#f1eefd;border:1px solid #dcd4fa;border-radius:999px;padding:3px 10px;vertical-align:2px;white-space:nowrap}
  .pd-bara{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:10px}
  .pd-bara label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:#9aa3b8;min-width:0;flex:1 1 160px;max-width:260px}
  .pd-bara select,.pd-bara input,.pd-nou select,.pd-nou input{font:inherit;font-size:14px;font-weight:600;color:#1e2233;background:#fff;border:1px solid #e8ebf1;border-radius:9px;padding:8px 10px;width:100%;min-width:0}
  .pd-cb{position:relative}
  .pd-cb-btn{font:inherit;font-size:14px;font-weight:600;color:#1e2233;background:#fff;border:1px solid #e8ebf1;border-radius:9px;padding:8px 10px;width:100%;display:flex;justify-content:space-between;gap:8px;cursor:pointer;text-align:left}
  .pd-cb-pop{position:absolute;z-index:20;top:calc(100% + 4px);left:0;width:max(100%,260px);background:#fff;border:1px solid #e8ebf1;border-radius:12px;box-shadow:0 10px 30px rgba(30,34,51,.14);padding:8px}
  .pd-cb-pop ul{list-style:none;margin:6px 0 0;padding:0;max-height:300px;overflow:auto}
  .pd-cb-pop li{display:flex;justify-content:space-between;gap:10px;padding:7px 9px;border-radius:7px;cursor:pointer;font-size:14px;color:#1e2233;font-weight:600}
  .pd-cb-pop li small{color:#9aa3b8;font-weight:600;font-variant-numeric:tabular-nums}
  .pd-cb-pop li.hi{background:#f4f2fd}
  .pd-cb-pop li.on{color:#7c5ce6}
  .pd-cb-pop .pd-cb-gol{color:#9aa3b8;cursor:default}
  .pd-filtre{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
  .pd-chip{display:inline-flex;align-items:center;gap:6px;background:#f1eefd;color:#3f2a8f;border:1px solid #dcd4fa;border-radius:999px;padding:4px 6px 4px 12px;font-size:13px;font-weight:700}
  .pd-chip button{border:none;background:#dcd4fa;color:#3f2a8f;border-radius:999px;width:20px;height:20px;cursor:pointer;font-size:14px;line-height:1}
  .pd-nou{display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:#f7f8fb;border:1px solid #e8ebf1;border-radius:12px;padding:8px}
  .pd-nou select:first-child{width:auto;max-width:220px}
  .pd-nou select:nth-child(2){width:64px}
  .pd-nou input{width:120px}
  .pd-btn{font:inherit;font-size:13px;font-weight:700;color:#3a4057;background:#fff;border:1px solid #e8ebf1;border-radius:9px;padding:7px 12px;cursor:pointer;white-space:nowrap}
  .pd-btn:disabled{opacity:.5;cursor:default}
  .pd-prim{background:#7c5ce6;border-color:#7c5ce6;color:#fff}
  .pd-link{border:none;background:none;color:#7c5ce6;padding:7px 4px}
  .pd-si{font-size:12.5px;color:#9aa3b8;font-weight:600}
  .pd-sumar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;font-size:14px;color:#1e2233;margin-bottom:8px}
  .pd-act{display:flex;gap:8px;flex-wrap:wrap}
  .pd-ind{font-size:12.5px;color:#9aa3b8;margin:4px 0 8px}
  .pd-tbl{overflow-x:auto;border:1px solid #eef0f6;border-radius:10px}
  .pd-tbl table{font-size:13px}
  .pd-tbl th{cursor:pointer;user-select:none;background:#fff;padding:8px}
  .pd-tbl th.on{color:#7c5ce6}
  .pd-tbl th.pd-grup{text-align:center;cursor:default;border-left:1px solid #eef0f6;color:#5a6178}
  .pd-tbl td{padding:7px 8px;white-space:nowrap}
  .pd-sg{margin-left:3px;font-size:10px}
  .pd-c1{position:sticky;left:0;z-index:1;background:#fff;min-width:150px;max-width:240px;white-space:normal!important;box-shadow:1px 0 0 #eef0f6}
  th.pd-c1{z-index:2}
  .pd-total td{font-weight:800;background:#f7f8fb;border-bottom:2px solid #e8ebf1}
  .pd-total .pd-c1{background:#f7f8fb}
  .pd-fam td{font-weight:700}
  .pd-fam:hover td,.pd-clic:hover td{background:#faf9ff}
  .pd-clic{cursor:pointer}
  .pd-mod td{color:#3a4057;background:#fcfcfe}
  .pd-mod td.n{font-weight:600}
  .pd-mod .pd-c1{padding-left:34px;background:#fcfcfe}
  .pd-sag{border:none;background:none;cursor:pointer;color:#7c5ce6;font-size:13px;width:20px;padding:0;margin-right:4px}
  .pd-mut{color:#9aa3b8;font-weight:600}
  .pd-gol{color:#9aa3b8;text-align:center}
  .pd-pag{display:flex;justify-content:center;align-items:center;gap:12px;margin-top:12px;font-size:13px;color:#5a6178;flex-wrap:wrap}
  @media(max-width:640px){
    .pd-bara{flex-direction:column;align-items:stretch}
    .pd-bara label{max-width:none;flex:none}
    .pd-nou{flex-direction:column;align-items:stretch}
    .pd-nou select:first-child,.pd-nou select:nth-child(2),.pd-nou input{width:100%;max-width:none}
    .pd-c1{min-width:120px;max-width:150px}
  }
`
