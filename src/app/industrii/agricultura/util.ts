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

export type Punct = { an: number; luna: number } // luna: 0 = ianuarie
export const numeLuna = (p: Punct) => `${LUNI[p.luna]} ${p.an}`
export const eticheta = (p: Punct) => `${LUNI_SCURT[p.luna]} ${String(p.an).slice(2)}`
export const parsePerioada = (s: string): Punct => {
  const [an, luna] = s.split('-').map(Number)
  return { an, luna: luna - 1 }
}
