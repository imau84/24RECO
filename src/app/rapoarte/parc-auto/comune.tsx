'use client'

import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { C, fmtD, n, type Index, type Vec } from './date'

/* Piese comune ale paginii Parc auto (tab-urile pe an și tab-ul Evoluție). */

export const ACCENT = '#7c5ce6'  // culoarea plăcii Parc auto de pe homepage
export const THEME = { accent: ACCENT, accent2: '#3b82f6', tint: '#f1eefd', tintBorder: '#dcd4fa', tintInk: '#3f2a8f' }
export const AXIS = { fontSize: 11, fill: '#9aa3b8' }
export const GRI = '#c3c8d6'
export const PALETA = ['#7c5ce6', '#e5544b', '#22b07d', '#e0a020', '#3b82f6', '#12a5b8', '#e0559c', '#5a6178']

export const VARSTA = [
  { k: C.v_0_4, l: '0–4 ani', c: '#22b07d' },
  { k: C.v_5_8, l: '5–8 ani', c: '#3b82f6' },
  { k: C.v_9_12, l: '9–12 ani', c: '#e0a020' },
  { k: C.v_peste_12, l: 'peste 12 ani', c: '#e5544b' },
]
export const VARSTA_6 = [
  { k: C.v_0_2, l: '0–2 ani', c: '#16a34a' }, { k: C.v_3_5, l: '3–5 ani', c: '#5cc98f' },
  { k: C.v_6_10, l: '6–10 ani', c: '#3b82f6' }, { k: C.v_11_15, l: '11–15 ani', c: '#e0a020' },
  { k: C.v_16_20, l: '16–20 ani', c: '#f08a4b' }, { k: C.v_peste_20, l: 'peste 20 ani', c: '#e5544b' },
]
export const COMBUSTIBIL = [
  { k: C.benzina, l: 'Benzină', c: '#e0a020' },
  { k: C.motorina, l: 'Motorină', c: '#5a6178' },
  { k: C.electric, l: 'Electric', c: '#22b07d' },
  { k: C.hibrid, l: 'Hibrid', c: '#12a5b8' },
  { k: C.gpl_altele, l: 'GPL / altele', c: '#c4b5fd' },
]

/* ── stare comună (selectorul de județ din bara de sus + filtrele din tab-uri) ── */
export type Stare = {
  judet: string; setJudet: (c: string) => void
  marcaV: string; setMarcaV: (m: string) => void
  modelV: string; setModelV: (m: string) => void
  marcaM: string; setMarcaM: (m: string) => void
}
export const Ctx = createContext<Stare | null>(null)
export const useStare = () => useContext(Ctx)!

/* ── piese comune ── */
export function Plain({ children }: { children: ReactNode }) {
  return <div className="ma-plain">💡 {children}</div>
}

/** an = număr („Parc auto la 31.12.2025”) sau perioadă („2012–2025”) */
export function Sursa({ an, nota }: { an: number | string; nota?: ReactNode }) {
  return (
    <div className="ma-src">
      📌 Sursă: DGPCI (MAI), {typeof an === 'number' ? `Parc auto la 31.12.${an}` : `Parc auto la 31 decembrie, anii ${an} (2012–2017 prin data.gov.ro)`} · <a href="https://dgpci.mai.gov.ro" target="_blank" rel="noopener noreferrer">dgpci.mai.gov.ro</a> · Prelucrare: 24reco.com
      {nota && <><br />{nota}</>}
    </div>
  )
}

export function Card({ titlu, dreapta, children, an, nota }: { titlu: string; dreapta?: ReactNode; children: ReactNode; an: number | string; nota?: ReactNode }) {
  return (
    <div className="ma-card pa-gap">
      <div className="ma-ch"><h3>{titlu}</h3>{dreapta}</div>
      {children}
      <Sursa an={an} nota={nota} />
    </div>
  )
}

export function Comutator({ v, set }: { v: 'grafic' | 'tabel'; set: (v: 'grafic' | 'tabel') => void }) {
  return (
    <div className="ma-seg">
      <button className={v === 'grafic' ? 'on' : ''} onClick={() => set('grafic')}>📈 Grafic</button>
      <button className={v === 'tabel' ? 'on' : ''} onClick={() => set('tabel')}>⊞ Tabel</button>
    </div>
  )
}

export function Legenda({ items }: { items: { l: string; c: string }[] }) {
  return <div className="ma-legend">{items.map(i => <span key={i.l}><i style={{ background: i.c }} />{i.l}</span>)}</div>
}

export const Asteapta = ({ eroare }: { eroare?: boolean }) =>
  <div className="ma-card pa-gap pa-wait">{eroare ? 'Datele nu s-au putut încărca. Reîncarcă pagina.' : 'Se încarcă datele…'}</div>

/** numele județului: „Timiș”; loc(): „în Timiș” / „la nivel național” */
export function useNume(idx: Pick<Index, 'judete'> | null) {
  return useMemo(() => {
    const m = new Map((idx?.judete ?? []).map(j => [j.cod, j.nume]))
    const nume = (c: string) => m.get(c) ?? c
    const loc = (c: string) => (c === 'RO' ? 'la nivel național' : `în ${nume(c)}`)
    const Loc = (c: string) => (c === 'RO' ? 'La nivel național' : `În ${nume(c)}`)
    return { nume, loc, Loc }
  }, [idx])
}

/** compară o valoare din județ cu media națională: „▲ peste media națională (12,3%)” */
export function comparatie(v: number, ro: number, f: (x: number) => string, invers = false) {
  if (Math.abs(v - ro) < 1e-9) return { t: `= media națională`, dir: '' }
  const sus = v > ro
  return { t: `${sus ? '▲ peste' : '▼ sub'} media națională (${f(ro)})`, dir: sus !== invers ? 'up' : 'down' }
}

export const la1000 = (v: Vec) => (n(v[C.total]) ? (n(v[C.electric]) / n(v[C.total])) * 1000 : 0)
