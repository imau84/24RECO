'use client'

import { useEffect, useState } from 'react'

/* Datele paginii vin din public/parc-auto/<an>/ (scripts/parc-auto/05_build_page_data.py). */

/** ordinea coloanelor din fiecare array (index.json → „coloane”) */
export const COLOANE = [
  'total', 'v_0_2', 'v_3_5', 'v_6_10', 'v_11_15', 'v_16_20', 'v_peste_20',
  'v_0_4', 'v_5_8', 'v_9_12', 'v_peste_12',
  'benzina', 'motorina', 'electric', 'hibrid', 'gpl_altele',
] as const
export type Coloana = typeof COLOANE[number]
export const C = Object.fromEntries(COLOANE.map((c, i) => [c, i])) as Record<Coloana, number>

/** null doar la electric/hibrid în 2018–2019 */
export type Vec = (number | null)[]

export type Bloc = {
  total: Vec
  model_nespecificat: number
  numar_marci: number
  marci: [string, Vec][]
  familii: [string, string, Vec][]
  electrice: [string, string, Vec][] | null
  hibride: [string, Vec][] | null
}

export type Index = {
  an: number
  actualizat: string
  sursa: string
  coloane: string[]
  judete: { cod: string; nume: string }[]
  date: Record<string, Bloc>
}

/** judete/<COD>.json: marcă → total + familii de modele */
export type FisierJudet = Record<string, { total: Vec; modele: Record<string, Vec> }>

export const NESPECIFICAT = 'nespecificat'

/** cheile unui obiect ordonate după total (JS pune cheile numerice, ex. „1100”, primele) */
export const dupaTotal = <T,>(o: Record<string, T>, total: (x: T) => number | null) =>
  Object.entries(o).sort((a, z) => (total(z[1]) ?? 0) - (total(a[1]) ?? 0))

/** public/parc-auto/serii.json (scripts/parc-auto/06_build_series.py) */
export type Serii = {
  ani: number[]
  actualizat: string
  coloane: string[]
  judete: { cod: string; nume: string }[]
  /** total: un vector pe an; marci: mașini pe an */
  date: Record<string, { total: Vec[]; marci: Record<string, number[]> }>
}
export const URL_SERII = '/parc-auto/serii.json'

export const urlIndex = (an: number) => `/parc-auto/${an}/index.json`
export const urlJudet = (an: number, cod: string) => `/parc-auto/${an}/judete/${cod}.json`

const cache = new Map<string, Promise<unknown>>()

/** fetch JSON cu cache pe sesiune; url = null → nu încarcă nimic */
export function useJson<T>(url: string | null): { data: T | null; error: boolean } {
  const [st, setSt] = useState<{ url: string | null; data: T | null; error: boolean }>({ url: null, data: null, error: false })
  useEffect(() => {
    if (!url) return
    let viu = true
    if (!cache.has(url)) {
      cache.set(url, fetch(url).then(r => {
        if (!r.ok) throw new Error(`${url}: ${r.status}`)
        return r.json()
      }))
    }
    cache.get(url)!.then(
      d => { if (viu) setSt({ url, data: d as T, error: false }) },
      () => { cache.delete(url); if (viu) setSt({ url, data: null, error: true }) },
    )
    return () => { viu = false }
  }, [url])
  return st.url === url ? st : { data: null, error: false }
}

/* ── formatare ── */
export const n = (v: number | null | undefined) => v ?? 0
export const pct = (a: number | null | undefined, b: number | null | undefined) => (n(b) ? (n(a) / n(b)) * 100 : 0)
export const fmt = (v: number | null | undefined) => (v == null ? '—' : new Intl.NumberFormat('ro-RO').format(Math.round(v)))
export const fmtP = (x: number, zec = 1) =>
  new Intl.NumberFormat('ro-RO', { minimumFractionDigits: zec, maximumFractionDigits: zec }).format(x) + '%'
export const fmtD = (x: number, zec = 1) =>
  new Intl.NumberFormat('ro-RO', { minimumFractionDigits: zec, maximumFractionDigits: zec }).format(x)

/** „de” după numerale de la 20 în sus (20 de mașini, dar 19 mașini) */
export function de(v: number) {
  const r = Math.abs(Math.round(v)), u = r % 100
  return u >= 20 || (u === 0 && r !== 0) ? ' de' : ''
}

const MAJUSCULE = new Set(['BMW', 'MG', 'DS', 'BYD', 'GMC', 'MAN', 'DAF', 'UAZ', 'GAZ', 'VAZ', 'ZAZ', 'ARO', 'TVR', 'AMC', 'VW', 'JAC', 'GWM', 'XEV', 'KTM', 'SWM', 'DR', 'NIO', 'IMS', 'ZX'])

/** VOLKSWAGEN → Volkswagen, MERCEDES-BENZ → Mercedes-Benz, BMW rămâne BMW */
export function numeMarca(m: string) {
  return m.split(/([ -])/).map(w => {
    if (w === ' ' || w === '-' || MAJUSCULE.has(w) || /\d/.test(w)) return w
    return w.charAt(0) + w.slice(1).toLowerCase()
  }).join('')
}

export const numeModel = (marca: string, familie: string) =>
  familie === NESPECIFICAT ? `${numeMarca(marca)} (model nespecificat)` : `${numeMarca(marca)} ${familie}`
