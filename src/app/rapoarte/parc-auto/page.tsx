'use client'

import { useState, type ReactNode } from 'react'
import {
  BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine,
} from 'recharts'
import ModelA, { type Analysis, type Source } from '@/components/ModelA'
import { TABURI_EVOLUTIE } from './evolutie'
import { CSS_DETALIAT, DateComplete } from './detaliat'
import {
  C, NESPECIFICAT, de, dupaTotal, fmt, fmtD, fmtP, n, numeMarca, numeModel, pct, urlIndex, urlJudet, useJson,
  type Bloc, type FisierJudet, type Index, type Vec,
} from './date'
import {
  ACCENT, AXIS, COMBUSTIBIL, Card, Comutator, Ctx, GRI, Legenda, Plain, THEME, VARSTA, VARSTA_6, Asteapta,
  comparatie, la1000, useNume, useStare,
} from './comune'

/* Parc auto — autoturisme (DGPCI). Un tab de nivel 1 pe an: pentru un an nou se adaugă
   anul în ANI și se rulează scripts/parc-auto/05_build_page_data.py <an> (și 07_build_detaliat.py <an>
   pentru tab-ul „Date complete”). Ultimul tab de nivel 1,
   „Evoluție”, citește public/parc-auto/serii.json (06_build_series.py); la un an nou se
   actualizează și PERIOADA. */

const ANI = [2025]
const PERIOADA = '2012–2025'

/* ═════════════ Pe scurt ═════════════ */
function PeScurt({ an }: { an: number }) {
  const { judet } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const { nume, loc, Loc } = useNume(idx)
  if (!idx) return <Asteapta eroare={error} />
  const b = idx.date[judet], r = idx.date.RO, v = b.total, vr = r.total
  const t = n(v[C.total]), tr = n(vr[C.total])
  const areEl = v[C.electric] != null
  const p = (x: Vec, k: number) => pct(x[k], x[C.total])
  const ro = judet !== 'RO'
  const marca1 = b.marci[0], marca1r = r.marci[0]

  const placi: { l: string; v: string; s?: string; c: string; cmp?: { t: string; dir: string } }[] = [
    {
      l: 'Autoturisme', v: fmt(t), c: '#7c5ce6',
      s: ro ? `${fmtP(pct(t, tr))} din mașinile țării` : 'înmatriculate la 31 decembrie',
      cmp: ro ? { t: `media pe județ: ${fmt(tr / 42)}`, dir: t > tr / 42 ? 'up' : 'down' } : undefined,
    },
    {
      l: 'Peste 12 ani', v: fmtP(p(v, C.v_peste_12), 0), c: '#e5544b', s: 'din mașini sunt mai vechi de 12 ani',
      cmp: ro ? comparatie(p(v, C.v_peste_12), p(vr, C.v_peste_12), x => fmtP(x, 0), true) : undefined,
    },
    {
      l: 'Sub 5 ani', v: fmtP(p(v, C.v_0_4), 0), c: '#22b07d', s: 'din mașini au cel mult 4 ani',
      cmp: ro ? comparatie(p(v, C.v_0_4), p(vr, C.v_0_4), x => fmtP(x, 0)) : undefined,
    },
    {
      l: 'Motorină', v: fmtP(p(v, C.motorina), 0), c: '#5a6178', s: 'din mașini merg pe motorină',
      cmp: ro ? comparatie(p(v, C.motorina), p(vr, C.motorina), x => fmtP(x, 0), true) : undefined,
    },
    {
      l: 'Electrice', v: areEl ? fmt(v[C.electric]) : '—', c: '#16a34a',
      s: areEl ? `${fmtD(la1000(v))} la 1.000 de mașini` : 'nepublicat separat în acest an',
      cmp: ro && areEl ? comparatie(la1000(v), la1000(vr), x => `${fmtD(x)} la 1.000`) : undefined,
    },
    {
      l: 'Hibride', v: areEl ? fmt(v[C.hibrid]) : '—', c: '#12a5b8',
      s: areEl ? `${fmtP(p(v, C.hibrid))} din mașini` : 'nepublicat separat în acest an',
      cmp: ro && areEl ? comparatie(p(v, C.hibrid), p(vr, C.hibrid), x => fmtP(x)) : undefined,
    },
    {
      l: 'Marca nr. 1', v: numeMarca(marca1[0]), c: '#e0a020',
      s: `${fmt(marca1[1][C.total])} mașini · ${fmtP(pct(marca1[1][C.total], t))}`,
      cmp: ro ? { t: `în țară: ${numeMarca(marca1r[0])} (${fmtP(pct(marca1r[1][C.total], tr))})`, dir: '' } : undefined,
    },
  ]

  const p12 = p(v, C.v_peste_12)
  return <>
    <Plain>
      {Loc(judet)} sunt înmatriculate {fmt(t)}{de(t)} autoturisme. {fmtP(p12, 0)} au peste 12 ani — cam {Math.round(p12 / 10)} din 10 mașini
      {ro && <>, față de {fmtP(p(vr, C.v_peste_12), 0)} în toată țara</>}. Cea mai răspândită marcă este {numeMarca(marca1[0])}.
    </Plain>
    <div className="pa-tiles">
      {placi.map(x => (
        <div key={x.l} className="pa-tile" style={{ background: x.c }}>
          <div className="l">{x.l}</div>
          <div className="v">{x.v}</div>
          {x.s && <div className="s">{x.s}</div>}
          {x.cmp && <div className="cmp">{x.cmp.t}</div>}
        </div>
      ))}
    </div>
    <Card titlu="Despre date" an={an}>
      <ul className="pa-despre">
        <li><b>Ce mașini sunt numărate.</b> Toate autoturismele înmatriculate: M1 = autoturisme obișnuite (cel mult 8 locuri
          plus șoferul), M1G = autoturisme de teren, M1S = autoturisme speciale (ambulanțe, autorulote, mașini blindate sau
          mortuare), M1GS = autoturisme de teren speciale.</li>
        <li><b>Județul este cel de înmatriculare</b>, nu neapărat cel în care circulă mașina. Firmele de leasing și flotele mari
          își înmatriculează mașinile mai ales în București și Ilfov, așa că acolo cifrele sunt mai mari, iar mașinile par mai noi.</li>
        <li><b>„GPL / altele”</b> este diferența până la total: mașini pe GPL, pe alți combustibili sau fără combustibil
          completat în registru.</li>
        <li><b>Model nespecificat:</b> {fmt(b.model_nespecificat)}{de(b.model_nespecificat)} mașini {loc(judet)} ({fmtP(pct(b.model_nespecificat, t))}) nu
          au modelul trecut în registru. Le numărăm la marcă, dar nu apar în topurile de modele.</li>
        <li><b>Numele mărcilor și modelelor au fost unificate:</b> am pus la un loc variantele de scriere (MERCEDES BENZ /
          MERCEDES-BENZ, VW / VOLKSWAGEN) și greșelile de tastare, iar versiunile sunt grupate pe familii (BMW 320d → Seria 3,
          C 220 → Clasa C, Logan MCV → Logan). După unificare rămân {fmt(b.numar_marci)} de mărci {loc(judet)}.</li>
      </ul>
    </Card>
    {ro && <p className="pa-mic">Compari {nume(judet)} cu toată țara. Alege „România” din bara de sus pentru totalul național.</p>}
  </>
}

/* ═════════════ Vechime ═════════════ */
function Vechime({ an }: { an: number }) {
  const { judet, setJudet, marcaV, setMarcaV, modelV, setModelV } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const { data: fj } = useJson<FisierJudet>(urlJudet(an, judet))
  const vreauRO = judet !== 'RO' && marcaV !== 'toate'
  const { data: fro } = useJson<FisierJudet>(vreauRO ? urlJudet(an, 'RO') : null)
  const { nume, loc, Loc } = useNume(idx)
  if (!idx) return <Asteapta eroare={error} />

  // marca/modelul ales se aplică doar dacă există în județ
  const marca = fj && marcaV !== 'toate' && fj[marcaV] ? marcaV : 'toate'
  const model = marca !== 'toate' && modelV !== 'toate' && fj![marca].modele[modelV] ? modelV : 'toate'
  const alege = (f: FisierJudet | null, b: Bloc): Vec | null => {
    if (marca === 'toate') return b.total
    if (!f) return null
    const m = f[marca]
    if (!m) return null
    return model === 'toate' ? m.total : m.modele[model] ?? null
  }
  const v = alege(fj, idx.date[judet])!
  const vr = judet === 'RO' ? v : alege(fro, idx.date.RO)
  const ce = marca === 'toate' ? 'autoturisme' : model === 'toate' ? numeMarca(marca) : numeModel(marca, model)
  const ro = judet !== 'RO'

  const rows = VARSTA.map(x => ({ name: x.l, j: pct(v[x.k], v[C.total]), r: vr ? pct(vr[x.k], vr[C.total]) : 0 }))
  const p12 = rows[3].j, p12r = rows[3].r

  return <>
    <Plain>
      {Loc(judet)}, {fmtP(p12, 0)} din {marca === 'toate' ? 'autoturisme' : ce} au peste 12 ani
      {ro && vr && <>, față de {fmtP(p12r, 0)} la nivel național</>}. Doar {fmtP(rows[0].j, 0)} au sub 5 ani
      {' '}({fmt(v[C.total])}{de(n(v[C.total]))} mașini în total).
    </Plain>
    <div className="pa-filtre">
      <label>Județ
        <select value={judet} onChange={e => setJudet(e.target.value)}>
          {idx.judete.map(j => <option key={j.cod} value={j.cod}>{j.nume}</option>)}
        </select>
      </label>
      <label>Marcă
        <select value={marca} disabled={!fj} onChange={e => { setMarcaV(e.target.value); setModelV('toate') }}>
          <option value="toate">Toate mărcile</option>
          {fj && dupaTotal(fj, x => x.total[C.total]).map(([m]) => <option key={m} value={m}>{numeMarca(m)}</option>)}
        </select>
      </label>
      <label>Model
        <select value={model} disabled={marca === 'toate'} onChange={e => setModelV(e.target.value)}>
          <option value="toate">Toate modelele</option>
          {marca !== 'toate' && dupaTotal(fj![marca].modele, v => v[C.total]).map(([f]) =>
            <option key={f} value={f}>{f === NESPECIFICAT ? '(model nespecificat)' : f}</option>)}
        </select>
      </label>
    </div>
    <Card titlu={`Vechimea: ${ce} ${loc(judet)} — % din mașini`} an={an}
      nota="Intervalele sunt cele din fișierul DGPCI (vârsta mașinii la 31 decembrie, după anul fabricației).">
      {ro && <Legenda items={[{ l: nume(judet), c: ACCENT }, { l: 'România', c: GRI }]} />}
      <div className="ma-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <CartesianGrid vertical={false} stroke="#eef0f6" />
            <XAxis dataKey="name" tick={AXIS} />
            <YAxis tick={AXIS} unit="%" width={44} />
            <Tooltip formatter={(x, k) => [fmtP(Number(x)), k === 'j' ? nume(judet) : 'România']} />
            <Bar dataKey="j" fill={ACCENT} radius={[6, 6, 0, 0]} isAnimationActive={false} />
            {ro && <Bar dataKey="r" fill={GRI} radius={[6, 6, 0, 0]} isAnimationActive={false} />}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="ma-tbl">
        <table>
          <thead><tr>
            <th>Vechime</th><th className="n">Mașini</th><th className="n">% {ro ? nume(judet) : ''}</th>
            {ro && <th className="n">% România</th>}
          </tr></thead>
          <tbody>
            {VARSTA.map((x, i) => (
              <tr key={x.l}>
                <td>{x.l}</td><td className="n">{fmt(v[x.k])}</td><td className="n">{fmtP(rows[i].j)}</td>
                {ro && <td className="n">{vr ? fmtP(rows[i].r) : '…'}</td>}
              </tr>
            ))}
            <tr className="pa-tot"><td>Total</td><td className="n">{fmt(v[C.total])}</td><td className="n">100%</td>{ro && <td className="n">100%</td>}</tr>
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/* ═════════════ Combustibil ═════════════ */
function Combustibil({ an }: { an: number }) {
  const { judet } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const { nume, Loc } = useNume(idx)
  if (!idx) return <Asteapta eroare={error} />
  const v = idx.date[judet].total, vr = idx.date.RO.total
  const ro = judet !== 'RO'
  const cat = COMBUSTIBIL.filter(x => v[x.k] != null)
  const rand = (name: string, x: Vec) => ({ name, ...Object.fromEntries(cat.map(c => [String(c.k), pct(x[c.k], x[C.total])])) })
  const rows = ro ? [rand(nume(judet), v), rand('România', vr)] : [rand('România', v)]
  const p = (k: number) => pct(v[k], v[C.total])

  return <>
    <Plain>
      {Loc(judet)}, {fmtP(p(C.motorina), 0)} din mașini merg pe motorină și {fmtP(p(C.benzina), 0)} pe benzină.
      {v[C.electric] != null
        ? <> Electricele sunt {fmtP(p(C.electric))}, iar hibridele {fmtP(p(C.hibrid))} din total.</>
        : <> În acest an DGPCI nu a publicat separat electricele și hibridele.</>}
    </Plain>
    <Card titlu={`Combustibil — % din mașini${ro ? `, ${nume(judet)} față de România` : ''}`} an={an}
      nota="„GPL / altele” = total minus benzină, motorină, electric și hibrid (GPL, alți combustibili sau necompletat). „Hibrid” = benzină+electric, motorină+electric și GPL+electric la un loc.">
      <Legenda items={cat} />
      <div style={{ height: rows.length * 56 + 40 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 12 }}>
            <XAxis type="number" domain={[0, 100]} unit="%" tick={AXIS} />
            <YAxis type="category" dataKey="name" tick={AXIS} width={86} />
            <Tooltip formatter={(x, k) => [fmtP(Number(x)), cat.find(c => String(c.k) === k)?.l ?? '']} />
            {cat.map(c => <Bar key={c.k} dataKey={String(c.k)} stackId="a" fill={c.c} isAnimationActive={false} barSize={30} />)}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="ma-tbl">
        <table>
          <thead><tr>
            <th>Combustibil</th><th className="n">Mașini</th><th className="n">% {ro ? nume(judet) : ''}</th>
            {ro && <th className="n">% România</th>}
          </tr></thead>
          <tbody>
            {cat.map(c => (
              <tr key={c.k}>
                <td><i className="pa-dot" style={{ background: c.c }} />{c.l}</td>
                <td className="n">{fmt(v[c.k])}</td><td className="n">{fmtP(p(c.k))}</td>
                {ro && <td className="n">{fmtP(pct(vr[c.k], vr[C.total]))}</td>}
              </tr>
            ))}
            <tr className="pa-tot"><td>Total</td><td className="n">{fmt(v[C.total])}</td><td className="n">100%</td>{ro && <td className="n">100%</td>}</tr>
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/* ═════════════ Mărci ═════════════ */
function GraficVarsta({ rows, inaltime }: { rows: { name: string; v: Vec }[]; inaltime?: number }) {
  const data = rows.map(r => ({ name: r.name, ...Object.fromEntries(VARSTA.map(x => [String(x.k), n(r.v[x.k])])) }))
  return <>
    <Legenda items={VARSTA.map(x => ({ l: x.l, c: x.c }))} />
    <div style={{ height: inaltime ?? rows.length * 30 + 40 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 12 }}>
          <CartesianGrid horizontal={false} stroke="#eef0f6" />
          <XAxis type="number" tick={AXIS} tickFormatter={x => fmt(Number(x))} />
          <YAxis type="category" dataKey="name" tick={AXIS} width={112} interval={0} />
          <Tooltip formatter={(x, k) => [fmt(Number(x)), VARSTA.find(c => String(c.k) === k)?.l ?? '']} />
          {VARSTA.map(x => <Bar key={x.k} dataKey={String(x.k)} stackId="a" fill={x.c} isAnimationActive={false} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  </>
}

function Marci({ an }: { an: number }) {
  const { judet } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const { loc } = useNume(idx)
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  if (!idx) return <Asteapta eroare={error} />
  const b = idx.date[judet], t = n(b.total[C.total])
  const top = b.marci
  const p = (v: Vec, k: number) => pct(v[k], v[C.total])
  const top3 = top.slice(0, 3)
  const nou = [...top].sort((a, z) => p(z[1], C.v_0_4) - p(a[1], C.v_0_4))[0]
  const areEl = b.total[C.electric] != null

  return <>
    <Plain>
      Primele 3 mărci {loc(judet)} — {top3.map(m => numeMarca(m[0])).join(', ')} — au împreună{' '}
      {fmtP(pct(top3.reduce((s, m) => s + n(m[1][C.total]), 0), t), 0)} din mașini.
      {' '}Dintre primele 15, cea mai nouă este {numeMarca(nou[0])}: {fmtP(p(nou[1], C.v_0_4), 0)} din mașinile ei au sub 5 ani.
    </Plain>
    <Card titlu={`Top 15 mărci ${loc(judet)}`} an={an} dreapta={<Comutator v={vedere} set={setVedere} />}
      nota="Graficul arată câte mașini are fiecare marcă, împărțite pe vârstă.">
      {vedere === 'grafic'
        ? <GraficVarsta rows={top.map(m => ({ name: numeMarca(m[0]), v: m[1] }))} />
        : (
          <div className="ma-tbl">
            <table>
              <thead><tr>
                <th>#</th><th>Marcă</th><th className="n">Mașini</th><th className="n">Cotă</th><th className="n">% sub 5 ani</th>
                <th className="n">% peste 12 ani</th><th className="n">% motorină</th>
                {areEl && <><th className="n">Electrice</th><th className="n">Hibride</th></>}
              </tr></thead>
              <tbody>
                {top.map(([m, v], i) => (
                  <tr key={m}>
                    <td>{i + 1}</td><td>{numeMarca(m)}</td><td className="n">{fmt(v[C.total])}</td>
                    <td className="n">{fmtP(pct(v[C.total], t))}</td><td className="n">{fmtP(p(v, C.v_0_4))}</td>
                    <td className="n">{fmtP(p(v, C.v_peste_12))}</td><td className="n">{fmtP(p(v, C.motorina))}</td>
                    {areEl && <><td className="n">{fmt(v[C.electric])}</td><td className="n">{fmt(v[C.hibrid])}</td></>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </Card>
  </>
}

/* ═════════════ Modele ═════════════ */
function Modele({ an }: { an: number }) {
  const { judet, marcaM, setMarcaM } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const { data: fj } = useJson<FisierJudet>(urlJudet(an, judet))
  const { loc, Loc } = useNume(idx)
  if (!idx) return <Asteapta eroare={error} />
  const b = idx.date[judet]
  const marca = fj && marcaM !== 'toate' && fj[marcaM] ? marcaM : 'toate'
  const totalMarca = (m: string) => n(fj?.[m]?.total[C.total] ?? b.marci.find(x => x[0] === m)?.[1][C.total])
  const p = (v: Vec, k: number) => pct(v[k], v[C.total])

  // rânduri: [marcă, familie, vector]
  const rows: [string, string, Vec][] = marca === 'toate'
    ? b.familii
    : dupaTotal(fj![marca].modele, v => v[C.total]).map(([f, v]) => [marca, f, v])
  const specificate = rows.filter(r => r[1] !== NESPECIFICAT)
  const grafic = specificate.slice(0, 20)
  const eticheta = (m: string, f: string) => (marca === 'toate' ? numeModel(m, f) : f === NESPECIFICAT ? '(model nespecificat)' : f)

  const primul = specificate[0]
  const tm = marca === 'toate' ? 0 : totalMarca(marca)
  const prag = Math.max(10, tm * 0.01)
  const nou = [...specificate].filter(r => n(r[2][C.total]) >= (marca === 'toate' ? 0 : prag))
    .sort((a, z) => p(z[2], C.v_0_4) - p(a[2], C.v_0_4))[0]

  return <>
    <Plain>
      {!primul ? <>{Loc(judet)} nu sunt modele cunoscute pentru această marcă.</> : marca === 'toate'
        ? <>Cel mai răspândit model {loc(judet)} este {numeModel(primul[0], primul[1])}, cu {fmt(primul[2][C.total])}{de(n(primul[2][C.total]))} mașini.
          {nou && <> Dintre primele 20, cel mai nou este {numeModel(nou[0], nou[1])}: {fmtP(p(nou[2], C.v_0_4), 0)} au sub 5 ani.</>}
          {' '}Alege o marcă pentru a vedea toate modelele ei.</>
        : <>La {numeMarca(marca)}, {loc(judet)}, cel mai răspândit model este {primul[1]} ({fmt(primul[2][C.total])}{de(n(primul[2][C.total]))} mașini,
          {' '}{fmtP(pct(primul[2][C.total], tm), 0)} din {numeMarca(marca)}).
          {nou && <> Cel mai nou este {nou[1]}: {fmtP(p(nou[2], C.v_0_4), 0)} din mașini au sub 5 ani.</>}</>}
    </Plain>
    <div className="pa-filtre">
      <label>Marcă
        <select value={marca} disabled={!fj} onChange={e => setMarcaM(e.target.value)}>
          <option value="toate">Toate mărcile (top 20 modele)</option>
          {fj && dupaTotal(fj, x => x.total[C.total]).map(([m]) => <option key={m} value={m}>{numeMarca(m)}</option>)}
        </select>
      </label>
    </div>
    <Card titlu={marca === 'toate' ? `Top 20 modele ${loc(judet)}` : `Modele ${numeMarca(marca)} ${loc(judet)}`} an={an}
      nota={<>Modelele sunt grupate pe familii (de ex. 320d și 318i → Seria 3).{' '}
        {marca !== 'toate' && specificate.length > 20 && 'Graficul arată primele 20 de modele; tabelul le are pe toate. '}
        Mașinile cu model nespecificat apar doar în tabel.</>}>
      {grafic.length > 0 && <GraficVarsta rows={grafic.map(r => ({ name: eticheta(r[0], r[1]), v: r[2] }))} />}
      <div className="ma-tbl pa-lung">
        <table>
          <thead><tr>
            <th>Model</th><th className="n">Mașini</th><th className="n">Cotă din marcă</th>
            <th className="n">% peste 12 ani</th><th className="n">% motorină</th>
          </tr></thead>
          <tbody>
            {rows.map(([m, f, v]) => (
              <tr key={m + f}>
                <td>{eticheta(m, f)}</td><td className="n">{fmt(v[C.total])}</td>
                <td className="n">{totalMarca(m) ? fmtP(pct(v[C.total], totalMarca(m))) : '…'}</td>
                <td className="n">{fmtP(p(v, C.v_peste_12))}</td><td className="n">{fmtP(p(v, C.motorina))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/* ═════════════ Electrice și hibride ═════════════ */
function GraficSimplu({ rows, culoare }: { rows: { name: string; v: number }[]; culoare: string }) {
  return (
    <div style={{ height: rows.length * 28 + 30 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 16 }}>
          <CartesianGrid horizontal={false} stroke="#eef0f6" />
          <XAxis type="number" tick={AXIS} tickFormatter={x => fmt(Number(x))} />
          <YAxis type="category" dataKey="name" tick={AXIS} width={118} interval={0} />
          <Tooltip formatter={x => [fmt(Number(x)), 'Mașini']} />
          <Bar dataKey="v" fill={culoare} radius={[0, 6, 6, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function Electrice({ an }: { an: number }) {
  const { judet } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const { nume, loc, Loc } = useNume(idx)
  if (!idx) return <Asteapta eroare={error} />
  const b = idx.date[judet], v = b.total, vr = idx.date.RO.total
  const ro = judet !== 'RO'
  if (!b.electrice || !b.hibride) {
    return <Card titlu="Electrice și hibride" an={an}><p>În acest an DGPCI nu a publicat separat mașinile electrice și hibride.</p></Card>
  }
  const h1000 = (x: Vec) => pct(x[C.hibrid], x[C.total]) * 10
  const el = b.electrice[0]
  const ind = [
    { l: 'Electrice la 1.000 de mașini', a: la1000(v), r: la1000(vr), c: '#16a34a', nr: v[C.electric] },
    { l: 'Hibride la 1.000 de mașini', a: h1000(v), r: h1000(vr), c: '#12a5b8', nr: v[C.hibrid] },
  ]

  return <>
    <Plain>
      {Loc(judet)} sunt {fmt(v[C.electric])}{de(n(v[C.electric]))} mașini electrice — {fmtD(la1000(v))} la fiecare 1.000 de autoturisme
      {ro && <> (în toată țara: {fmtD(la1000(vr))})</>}. {el && <>Cel mai răspândit model electric este {numeModel(el[0], el[1])}.</>}
      {' '}Hibridele sunt de {fmtD(n(v[C.hibrid]) / Math.max(1, n(v[C.electric])))} ori mai multe decât electricele.
    </Plain>
    <div className="pa-tiles pa-tiles2">
      {ind.map(x => {
        const cmp = comparatie(x.a, x.r, y => fmtD(y))
        return (
          <div key={x.l} className="pa-tile" style={{ background: x.c }}>
            <div className="l">{x.l}</div>
            <div className="v">{fmtD(x.a)}</div>
            <div className="s">{fmt(x.nr)}{de(n(x.nr))} mașini {loc(judet)}</div>
            {ro && <div className="cmp">{cmp.t}</div>}
          </div>
        )
      })}
    </div>
    <div className="pa-dublu">
      <Card titlu={`Top modele electrice ${loc(judet)}`} an={an}>
        <GraficSimplu culoare="#16a34a" rows={b.electrice.map(([m, f, x]) => ({ name: numeModel(m, f), v: n(x[C.electric]) }))} />
      </Card>
      <Card titlu={`Top mărci hibride ${loc(judet)}`} an={an}
        nota="Hibrid = benzină+electric, motorină+electric și GPL+electric la un loc.">
        <GraficSimplu culoare="#12a5b8" rows={b.hibride.map(([m, x]) => ({ name: numeMarca(m), v: n(x[C.hibrid]) }))} />
      </Card>
    </div>
    {ro && <p className="pa-mic">Valorile sunt pentru {nume(judet)}. Alege „România” din bara de sus pentru totalul național.</p>}
  </>
}

/* ═════════════ Județe ═════════════ */
type Indicator = { k: string; l: string; f: (v: Vec) => number; fmt: (x: number) => string; sus: string; jos: string }
const INDICATORI: Indicator[] = [
  { k: 'total', l: 'Autoturisme înmatriculate', f: v => n(v[C.total]), fmt: fmt, sus: 'Cele mai multe mașini', jos: 'Cele mai puține' },
  ...VARSTA_6.map((x, i): Indicator => ({
    k: String(x.k), l: `% ${x.l}`, f: v => pct(v[x.k], v[C.total]), fmt: y => fmtP(y),
    sus: i === 0 ? 'Cele mai noi mașini (cele mai multe de 0–2 ani)' : i === 5 ? 'Cele mai vechi mașini (cele mai multe peste 20 de ani)' : `Cele mai multe mașini de ${x.l}`,
    jos: i === 0 ? 'Cele mai puține mașini noi' : i === 5 ? 'Cele mai puține mașini foarte vechi' : 'Cele mai puține',
  })),
  { k: 'motorina', l: '% motorină', f: v => pct(v[C.motorina], v[C.total]), fmt: y => fmtP(y), sus: 'Cea mai mare pondere a motorinei', jos: 'Cea mai mică' },
  { k: 'el', l: 'Electrice la 1.000 de mașini', f: la1000, fmt: y => fmtD(y), sus: 'Cele mai multe electrice', jos: 'Cele mai puține' },
  { k: 'hib', l: '% hibride', f: v => pct(v[C.hibrid], v[C.total]), fmt: y => fmtP(y), sus: 'Cele mai multe hibride', jos: 'Cele mai puține' },
]

type ColJ = { k: string; l: string; f: (v: Vec) => number; fmt: (x: number) => string }
const COL_JUDETE: ColJ[] = [
  { k: 'total', l: 'Autoturisme', f: v => n(v[C.total]), fmt: fmt },
  ...VARSTA_6.map(x => ({ k: String(x.k), l: `% ${x.l}`, f: (v: Vec) => pct(v[x.k], v[C.total]), fmt: (y: number) => fmtP(y) })),
  { k: 'motorina', l: '% motorină', f: v => pct(v[C.motorina], v[C.total]), fmt: y => fmtP(y) },
  { k: 'el', l: 'Electrice / 1.000', f: la1000, fmt: y => fmtD(y) },
  { k: 'hib', l: '% hibride', f: v => pct(v[C.hibrid], v[C.total]), fmt: y => fmtP(y) },
]

function Judete({ an }: { an: number }) {
  const { judet, setJudet } = useStare()
  const { data: idx, error } = useJson<Index>(urlIndex(an))
  const [indK, setIndK] = useState('total')
  const [sort, setSort] = useState<{ k: string; desc: boolean }>({ k: 'total', desc: true })
  if (!idx) return <Asteapta eroare={error} />
  const areEl = idx.date.RO.total[C.electric] != null
  const indicatori = INDICATORI.filter(i => areEl || (i.k !== 'el' && i.k !== 'hib'))
  const coloane = COL_JUDETE.filter(i => areEl || (i.k !== 'el' && i.k !== 'hib'))
  const ind = indicatori.find(i => i.k === indK) ?? indicatori[0]
  const judete = idx.judete.filter(j => j.cod !== 'RO')
  const vr = idx.date.RO.total
  const medie = ind.k === 'total' ? n(vr[C.total]) / judete.length : ind.f(vr)
  const rows = judete.map(j => ({ cod: j.cod, name: j.nume, v: ind.f(idx.date[j.cod].total) })).sort((a, z) => z.v - a.v)
  const lista = (r: typeof rows) => r.map(x => `${x.name} (${ind.fmt(x.v)})`).join(', ')

  const col = coloane.find(c => c.k === sort.k)
  const tabel = judete.map(j => ({ j, v: idx.date[j.cod].total })).sort((a, z) => {
    const d = col ? col.f(a.v) - col.f(z.v) : a.j.nume.localeCompare(z.j.nume, 'ro')
    return sort.desc ? -d : d
  })
  const sorteaza = (k: string) => setSort(s => ({ k, desc: s.k === k ? !s.desc : k !== 'nume' }))
  const sageata = (k: string) => (sort.k === k ? (sort.desc ? ' ▼' : ' ▲') : '')

  return <>
    <Plain>
      <b>{ind.sus}:</b> {lista(rows.slice(0, 5))}. <b>{ind.jos}:</b> {lista(rows.slice(-5).reverse())}.
      {' '}{ind.k === 'total' ? <>Media pe județ este de {fmt(medie)} de mașini.</> : <>Media națională: {ind.fmt(medie)}.</>}
    </Plain>
    <div className="pa-filtre">
      <label>Indicator
        <select value={ind.k} onChange={e => setIndK(e.target.value)}>
          {indicatori.map(i => <option key={i.k} value={i.k}>{i.l}</option>)}
        </select>
      </label>
    </div>
    <Card titlu={`${ind.l} — toate județele`} an={an}
      nota={<>Linia verticală = {ind.k === 'total' ? 'media pe județ' : 'media națională'}. Apasă pe un județ ca să-l alegi pentru toată pagina.</>}>
      <div style={{ height: rows.length * 21 + 40 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 20 }}>
            <CartesianGrid horizontal={false} stroke="#eef0f6" />
            <XAxis type="number" tick={AXIS} tickFormatter={x => ind.k === 'total' ? fmt(Number(x)) : fmtD(Number(x), 0)} />
            <YAxis type="category" dataKey="name" tick={AXIS} width={104} interval={0} />
            <Tooltip formatter={x => [ind.fmt(Number(x)), ind.l]} />
            <ReferenceLine x={medie} stroke="#1e2233" strokeDasharray="4 3"
              label={{ value: ind.k === 'total' ? 'media' : 'România', position: 'top', fontSize: 11, fill: '#1e2233' }} />
            <Bar dataKey="v" isAnimationActive={false} radius={[0, 4, 4, 0]} cursor="pointer"
              onClick={d => { const c = (d as { payload?: { cod?: string } }).payload?.cod; if (c) setJudet(c) }}>
              {rows.map(r => <Cell key={r.cod} fill={r.cod === judet ? ACCENT : '#cfc7f5'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
    <Card titlu="Toate județele, toți indicatorii" an={an} nota="Apasă pe antetul unei coloane ca să sortezi.">
      <div className="ma-tbl pa-lung">
        <table className="pa-sort">
          <thead><tr>
            <th onClick={() => sorteaza('nume')}>Județ{sageata('nume')}</th>
            {coloane.map(c => <th key={c.k} className="n" onClick={() => sorteaza(c.k)}>{c.l}{sageata(c.k)}</th>)}
          </tr></thead>
          <tbody>
            {tabel.map(({ j, v }) => (
              <tr key={j.cod} className={j.cod === judet ? 'pa-ales' : ''}>
                <td>{j.nume}</td>{coloane.map(c => <td key={c.k} className="n">{c.fmt(c.f(v))}</td>)}
              </tr>
            ))}
            <tr className="pa-tot"><td>România</td>{coloane.map(c => <td key={c.k} className="n">{c.fmt(c.f(vr))}</td>)}</tr>
          </tbody>
        </table>
      </div>
    </Card>
  </>
}

/* ═════════════ pagina ═════════════ */
const tab = (name: string, hash: string, content: ReactNode): Analysis => ({
  name, hash, content, type: 'table', unit: '', plain: '', labels: [], series: [{ name: '', data: [] }], labelCol: '', kpis: [],
})

export default function ParcAutoPage() {
  const [judet, setJudet] = useState('RO')
  const [marcaV, setMarcaV] = useState('toate')
  const [modelV, setModelV] = useState('toate')
  const [marcaM, setMarcaM] = useState('toate')
  const ultim = ANI[ANI.length - 1]
  const { data: idx } = useJson<Index>(urlIndex(ultim))

  const sources: Source[] = [...ANI.map((an): Source => ({
    key: String(an), label: `Parc auto ${an}`, credit: 'DGPCI (MAI)', link: 'dgpci.mai.gov.ro',
    url: 'https://dgpci.mai.gov.ro', freq: 'anual',
    analyses: [
      tab('Pe scurt', 'pe-scurt', <PeScurt an={an} />),
      tab('Vechime', 'vechime', <Vechime an={an} />),
      tab('Combustibil', 'combustibil', <Combustibil an={an} />),
      tab('Mărci', 'marci', <Marci an={an} />),
      tab('Modele', 'modele', <Modele an={an} />),
      tab('Electrice și hibride', 'electrice', <Electrice an={an} />),
      tab('Județe', 'judete', <Judete an={an} />),
      tab('Date complete', 'date-complete', <DateComplete an={an} />),
    ],
  })), {
    key: 'evolutie', label: `Evoluție ${PERIOADA}`, credit: 'DGPCI (MAI)', link: 'dgpci.mai.gov.ro',
    url: 'https://dgpci.mai.gov.ro', freq: 'anual',
    analyses: TABURI_EVOLUTIE.map(t => tab(t.name, t.hash, t.content)),
  }]

  const selector = (
    <label className="pa-jud">
      <span>📍 Județ</span>
      <select value={judet} onChange={e => setJudet(e.target.value)}>
        {(idx?.judete ?? [{ cod: 'RO', nume: 'România' }]).map(j => <option key={j.cod} value={j.cod}>{j.nume}</option>)}
      </select>
    </label>
  )

  return (
    <Ctx.Provider value={{ judet, setJudet, marcaV, setMarcaV, modelV, setModelV, marcaM, setMarcaM }}>
      <style dangerouslySetInnerHTML={{ __html: `
        .pa-jud{display:inline-flex;align-items:center;gap:10px;background:rgba(255,255,255,.18);border-radius:12px;padding:8px 12px;font-size:14px;font-weight:700;max-width:100%}
        .pa-jud select{font:inherit;font-size:15px;font-weight:700;color:#1e2233;background:#fff;border:none;border-radius:8px;padding:7px 10px;min-width:0;max-width:220px}
        .pa-gap{margin-top:16px}
        .pa-wait{color:#5a6178;font-size:14px}
        .pa-tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0 0}
        .pa-tiles2{grid-template-columns:repeat(2,1fr)}
        .pa-tile{border-radius:16px;padding:16px;color:#fff;min-width:0}
        .pa-tile .l{font-size:12.5px;font-weight:700;opacity:.92}
        .pa-tile .v{font-size:28px;font-weight:800;margin-top:4px;letter-spacing:-.01em;overflow-wrap:anywhere}
        .pa-tile .s{font-size:12.5px;opacity:.95;margin-top:2px}
        .pa-tile .cmp{font-size:12px;font-weight:700;margin-top:8px;background:rgba(255,255,255,.2);border-radius:8px;padding:4px 8px;display:inline-block}
        .pa-despre{padding-left:18px;display:grid;gap:8px;font-size:14px;line-height:1.5;color:#3a4057}
        .pa-mic{font-size:12.5px;color:#9aa3b8;margin-top:10px}
        .pa-filtre{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 4px}
        .pa-filtre label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:#9aa3b8;min-width:0;flex:1 1 180px;max-width:280px}
        .pa-filtre select{font:inherit;font-size:14px;font-weight:600;color:#1e2233;background:#fff;border:1px solid #e8ebf1;border-radius:9px;padding:8px 10px;width:100%}
        .pa-filtre select:disabled{opacity:.55}
        .pa-dot{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:8px;vertical-align:-1px}
        .pa-tot td{font-weight:800;border-top:2px solid #e8ebf1}
        .pa-lung{max-height:560px;overflow:auto}
        .pa-lung thead th{position:sticky;top:0;background:#fff;z-index:1}
        .pa-sort th{cursor:pointer;user-select:none}
        .pa-ales td{background:#f1eefd;font-weight:800}
        .pa-dublu{display:grid;grid-template-columns:1fr 1fr;gap:16px}
        .pa-dublu .ma-card{min-width:0}
        .ma-card{min-width:0}
        @media(max-width:820px){.pa-tiles{grid-template-columns:1fr 1fr}.pa-dublu{grid-template-columns:1fr}}
        @media(max-width:420px){.pa-tiles{grid-template-columns:1fr}.pa-tile .v{font-size:24px}}
        ${CSS_DETALIAT}
      ` }} />
      <ModelA
        crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Rapoarte', href: '/#rapoarte' }, { label: 'Parc auto' }]}
        icon="🚗"
        title="Parc auto România"
        sub="Câte mașini sunt în fiecare județ, cât de vechi sunt și ce mărci conduc românii"
        chips={[`● Situația la 31 decembrie ${ultim}`, '🔁 anual', '📊 grafic + tabel']}
        theme={THEME}
        sources={sources}
        heroExtra={selector}
      />
    </Ctx.Provider>
  )
}
