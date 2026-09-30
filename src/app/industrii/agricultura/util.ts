/* Funcții comune pentru analizele lunare din Agricultură (lapte, sacrificări…). */

export const LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august', 'septembrie', 'octombrie', 'noiembrie', 'decembrie']
export const LUNI_SCURT = ['ian', 'feb', 'mar', 'apr', 'mai', 'iun', 'iul', 'aug', 'sep', 'oct', 'noi', 'dec']

const nf = (d: number) => (n: number) => new Intl.NumberFormat('ro-RO', { minimumFractionDigits: d, maximumFractionDigits: d }).format(n)
export const fmt0 = nf(0), fmt1 = nf(1), fmt2 = nf(2)

export const pct = (a: number, b: number) => (a - b) / b * 100
export const semn = (p: number) => `${p > 0 ? '+' : p < 0 ? '−' : ''}${fmt1(Math.abs(p))}%`
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

/** „cu 9,1% mai puțin” / „de 2,3 ori mai mult” — pentru schimbări mari, „de X ori” e mai ușor de citit */
export const diferenta = (a: number, b: number) => {
  const p = pct(a, b)
  if (p >= 100) return `de ${fmt1(a / b)} ori mai mult`
  return `cu ${fmt1(Math.abs(p))}% ${p < 0 ? 'mai puțin' : 'mai mult'}`
}

/** „a crescut cu 16,2%” / „a scăzut cu 3,1%” / „a crescut de 2,3 ori” / „a rămas cam la fel” */
export const schimbare = (a: number, b: number) => {
  const p = pct(a, b)
  if (Math.abs(p) < 1) return 'a rămas cam la fel'
  if (p >= 100) return `a crescut de ${fmt1(a / b)} ori`
  return `${p > 0 ? 'a crescut' : 'a scăzut'} cu ${fmt1(Math.abs(p))}%`
}

/** „308 mii”, dar „70 de mii” (regula lui „de” după numerale ≥ 20); sub 100 cu o zecimală */
export const mii = (v: number) => {
  if (v < 100) return `${fmt1(v)} mii`
  const r = Math.round(v) % 100
  return `${fmt0(v)} ${r === 0 || r >= 20 ? 'de ' : ''}mii`
}

export type Punct = { an: number; luna: number } // luna: 0 = ianuarie
export const numeLuna = (p: Punct) => `${LUNI[p.luna]} ${p.an}`
export const eticheta = (p: Punct) => `${LUNI_SCURT[p.luna]} ${String(p.an).slice(2)}`
export const parsePerioada = (s: string): Punct => {
  const [an, luna] = s.split('-').map(Number)
  return { an, luna: luna - 1 }
}
