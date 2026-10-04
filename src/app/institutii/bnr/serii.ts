import type { EurostatSet } from '@/components/EurostatExplorer'
import bnr from '../../../../public/bnr_data.json'

/* Seriile lunare BNR (balanța de plăți, investiții directe, depozite, credite) transformate în
   seturi pentru EurostatExplorer. public/bnr_data.json e actualizat de scripts/fetch_bnr.py (GitHub Actions, lunea). */

type Rand = { d: string } & Record<string, number | null | string>
const D = bnr as unknown as Record<'BP_DATA' | 'ISD_DATA' | 'DEP' | 'CR', Rand[]>

export type SetBnr = EurostatSet & { icon: string }

const URL_BNR = 'https://www.bnr.ro/1928-statistica'

function set(cheie: keyof typeof D, meta: Omit<EurostatSet, 'perioade' | 'serii' | 'actualizat' | 'cod' | 'url' | 'sursa' | 'freq'> & { icon: string; cod: string },
             serii: [string, string][]): SetBnr {
  const randuri = D[cheie].filter(r => serii.some(([k]) => typeof r[k] === 'number'))  // fără lunile goale de la început
  return {
    ...meta, freq: 'M', url: URL_BNR, sursa: 'Banca Națională a României', actualizat: randuri[randuri.length - 1].d,
    perioade: randuri.map(r => r.d),
    serii: serii.map(([k, nume]) => ({ nume, valori: randuri.map(r => (typeof r[k] === 'number' ? (r[k] as number) : null)), provizorii: [] })),
  }
}

export const SETURI_BNR: SetBnr[] = [
  set('BP_DATA', {
    key: 'balanta', scurt: 'Balanța de plăți', icon: '🌍', cod: 'Balanța de plăți (BPM6)',
    titlu: 'Balanța de plăți: câți bani intră și ies din țară',
    descriere: 'Diferența dintre banii care intră în România și cei care ies, în fiecare lună, în milioane de euro. ' +
      'Minus = au ieșit mai mulți bani decât au intrat (de exemplu, am importat mai mult decât am exportat).',
    unitate: 'mil. euro', zecimale: 0, agregare: 'suma',
    note: ['Contul curent = bunuri + servicii + venituri primare + venituri secundare.',
      'Bunuri: România importă constant mai mult decât exportă, de aceea soldul e negativ.',
      'Servicii: soldul pozitiv vine mai ales din IT și transport.',
      'Venituri secundare: banii trimiși acasă de românii din străinătate și o parte din fondurile UE; contul de capital: fondurile UE pentru investiții.'],
  }, [['cc', 'Contul curent (total)'], ['b', 'Bunuri (export − import)'], ['s', 'Servicii (export − import)'],
      ['vp', 'Venituri primare (dividende, dobânzi, salarii)'], ['vs', 'Venituri secundare (bani trimiși din străinătate, transferuri)'], ['ck', 'Contul de capital (fonduri UE pentru investiții)']]),
  set('ISD_DATA', {
    key: 'isd', scurt: 'Investiții străine', icon: '🏗️', cod: 'Investiții directe (principiul direcțional)',
    titlu: 'Investițiile străine directe',
    descriere: 'Câți bani au investit firmele străine în firme din România (și invers), lună de lună, în milioane de euro. ' +
      'Include capital nou, profit reinvestit și împrumuturi de la firma-mamă.',
    unitate: 'mil. euro', zecimale: 1, agregare: 'suma',
    note: ['Valori nete: plus = au intrat bani, minus = au ieșit (de ex. firma-mamă și-a luat înapoi un împrumut).',
      '„Participații la capital” include profitul reinvestit; „instrumente de datorie” sunt împrumuturile între firme din același grup.',
      'Lunile se schimbă mult de la una la alta — compară totalul pe tot anul.'],
  }, [['idt', 'Total investiții directe (net)'], ['nro', 'Investiții străine în România'], ['res', 'Investiții ale românilor în străinătate'],
      ['ns', 'Străini în bănci'], ['nx', 'Străini în alte firme'], ['nxc', '  din care capital și profit reinvestit'], ['nxd', '  din care împrumuturi de la firma-mamă']]),
  set('DEP', {
    key: 'depozite', scurt: 'Depozite', icon: '🐷', cod: 'Depozite pe sectoare instituționale',
    titlu: 'Câți bani țin românii și firmele în bănci',
    descriere: 'Soldul depozitelor la bănci la sfârșitul fiecărei luni, în miliarde de lei (cele în valută sunt transformate în lei).',
    unitate: 'mld. lei', zecimale: 1, agregare: 'medie',
    note: ['„La vedere” = bani în cont curent, care pot fi scoși oricând; „la termen” = depozite pe o perioadă fixă.',
      'Depozitele în valută sunt transformate în lei la cursul de la final de lună, deci cresc și când se depreciază leul.',
      'Media anuală e media soldurilor lunare.'],
  }, [['gp', 'Populație (total)'], ['gpo', 'Populație — la vedere'], ['gpol', 'Populație — la vedere, în lei'], ['gpoe', 'Populație — la vedere, în valută'],
      ['gpt', 'Populație — la termen'], ['gptl', 'Populație — la termen, în lei'], ['gpte', 'Populație — la termen, în valută'],
      ['sn', 'Firme'], ['ap', 'Administrație publică'], ['apc', 'Administrație centrală'], ['apl', 'Administrație locală']]),
  set('CR', {
    key: 'credite', scurt: 'Credite', icon: '🏠', cod: 'Credite pe sectoare instituționale',
    titlu: 'Câți bani au împrumutat românii și firmele de la bănci',
    descriere: 'Soldul creditelor la sfârșitul fiecărei luni, în miliarde de lei: pentru casă, de consum, pentru firme.',
    unitate: 'mld. lei', zecimale: 1, agregare: 'medie',
    note: ['Soldul = cât mai e de plătit din toate creditele, nu cât s-a împrumutat într-o lună.',
      'Creditele în valută sunt transformate în lei la cursul de la final de lună.',
      'Ponderea creditelor în valută a scăzut mult după 2012, după ce BNR a restrâns creditele în valută pentru populație.'],
  }, [['g', 'Populație (total)'], ['glo', 'Populație — pentru locuință'], ['gc', 'Populație — de consum'], ['gx', 'Populație — alte scopuri'],
      ['gl', 'Populație — în lei'], ['ge', 'Populație — în valută'], ['gll', 'Locuință — în lei'], ['gle', 'Locuință — în valută'],
      ['gcl', 'Consum — în lei'], ['gce', 'Consum — în valută'],
      ['sn', 'Firme (total)'], ['snl', 'Firme — în lei'], ['sne', 'Firme — în valută'],
      ['ifn', 'Instituții financiare nebancare'], ['ap', 'Administrație publică'], ['apc', 'Administrație centrală'], ['apl', 'Administrație locală']]),
]
