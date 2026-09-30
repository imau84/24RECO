import ModelA, { type Source } from '@/components/ModelA'

// Demo pentru șablonul „Model A” — date auto reale, august 2026.
const SOURCES: Source[] = [
  {
    key: 'DRPCIV', tag: 'oficial', label: 'DRPCIV', link: 'dgpci.mai.gov.ro', freq: 'lunar',
    analyses: [
      {
        name: 'Top mărci', type: 'bar', unit: 'mașini noi',
        plain: 'Dacia conduce detașat — aproape de 2 ori mai multe mașini noi decât Toyota.',
        labels: ['Dacia', 'Toyota', 'Skoda', 'VW', 'BYD', 'BMW', 'Mercedes', 'Renault'],
        series: [{ name: 'Înmatriculări', data: [2142, 1240, 845, 708, 653, 428, 409, 385] }],
        labelCol: 'Marcă',
        share: true,
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
        series: [{ name: 'Mașini', data: [5525, 1591, 1245, 671, 515] }],
        labelCol: 'Combustibil',
        share: true,
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
        series: [{ name: 'Total', data: [12449, 12827, 13877, 21308, 7922, 8958, 10374, 10202, 11245, 16114, 11723, 9948] }],
        labelCol: 'Luna',
        share: true,
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
        series: [{ name: 'Număr', data: [9552, 25923] }],
        labelCol: 'Tip',
        share: true,
        kpis: [
          { label: 'Rulate', value: '25.923', chg: '73% din piață' },
          { label: 'Noi', value: '9.552', chg: '27% din piață' },
          { label: 'Total', value: '35.475', chg: 'august 2026' },
        ],
      },
    ],
  },
  {
    key: 'ACAROM', tag: 'asociație', label: 'ACAROM', link: 'acarom.ro', freq: 'lunar',
    analyses: [
      {
        name: 'Producție națională', type: 'bar', unit: 'mii vehicule',
        plain: 'Producția a atins vârful în 2023 (514 mii), apoi a scăzut. 2026 sunt date parțiale.',
        labels: ['2021', '2022', '2023', '2024', '2025', '2026*'],
        series: [{ name: 'Producție (mii)', data: [438, 509, 514, 480, 452, 210] }],
        labelCol: 'An',
        share: true,
        kpis: [
          { label: 'Vârf', value: '2023', chg: '514 mii', dir: 'up' },
          { label: '2025', value: '452 mii', chg: '▼ în scădere', dir: 'down' },
          { label: '2026*', value: '210 mii', chg: 'parțial' },
        ],
      },
    ],
  },
]

export default function ModelADemo() {
  return (
    <ModelA
      crumbs={[{ label: 'Acasă', href: '/' }, { label: 'Industrii', href: '/#industrii' }, { label: 'Comerț · MODEL A (demo)' }]}
      icon="🚗"
      title="Înmatriculări auto"
      sub="Câte mașini se înmatriculează în România, lunar"
      chips={['● Actualizat: august 2026', '🔁 lunar', '📊 grafic + tabel']}
      theme={{ accent: '#e5544b', accent2: '#e0728a', tint: '#fdeeec', tintBorder: '#f8d5d1', tintInk: '#8a2a24' }}
      sources={SOURCES}
    />
  )
}