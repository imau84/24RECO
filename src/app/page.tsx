'use client'

import Link from 'next/link'

type Item = { icon: string; title: string; sub: string; href: string; color: string }

const INDUSTRII: Item[] = [
  { icon: '🌾', title: 'Agricultură', sub: 'Prețuri cereale · BRM', href: '/industrii/agricultura', color: '#22b07d' },
  { icon: '🏗️', title: 'Construcții', sub: 'Autorizații · INS', href: '/industrii/constructii', color: '#e0a020' },
  { icon: '🏠', title: 'Imobiliare', sub: 'Tranzacții · ANCPI', href: '/imobiliare', color: '#3b82f6' },
  { icon: '🚛', title: 'Transport', sub: 'Marfă · Operatori', href: '/transport', color: '#12a5b8' },
  { icon: '🏭', title: 'Industrie', sub: 'Exporturi · INS', href: '/industrii/industrie', color: '#5a6178' },
  { icon: '🛒', title: 'Comerț', sub: 'Înmatriculări auto · DRPCIV', href: '/comert', color: '#e5544b' },
  { icon: '✈️', title: 'Turism', sub: 'Sosiri · Cazare', href: '/industrii/turism', color: '#e0559c' },
]

const INSTITUTII: Item[] = [
  { icon: '🏦', title: 'BNR', sub: 'Curs · Credite', href: '/institutii/bnr', color: '#334670' },
  { icon: '👴', title: 'Casa de Pensii', sub: 'Pensionari · Pensia medie', href: '/institutii/casa-pensii', color: '#0ea5b7' },
  { icon: '📚', title: 'Min. Educației', sub: 'Elevi · Unități', href: '/Institutii publice - Ministerul Educatiei.html', color: '#63a615' },
  { icon: '💰', title: 'Execuție Bugetară', sub: 'Venituri · Cheltuieli', href: '/institutii-publice/ministerul-finantelor/executie-bugetara', color: '#f0883e' },
  { icon: '📈', title: 'Datorie Publică', sub: 'Structură · Evoluție', href: '/institutii-publice/ministerul-finantelor/datorie-publica', color: '#7c5ce6' },
]

const RAPOARTE: Item[] = [
  { icon: '📊', title: 'Situații Financiare', sub: 'Bilanțuri companii · ANAF', href: '/rapoarte/date-financiare', color: '#5a6178' },
  { icon: '🗳️', title: 'Alegeri Locale 2024', sub: 'Județe · Comune', href: '/Rapoarte - Alegeri Locale 2024.html', color: '#e5544b' },
]

function Tile({ icon, title, sub, href, color }: Item) {
  return (
    <a href={href} className="t" style={{ background: color }}>
      <span className="t-ic">{icon}</span>
      <span className="t-ti">{title}</span>
      <span className="t-su">{sub}</span>
    </a>
  )
}

function Band({ title, items }: { title: string; items: Item[] }) {
  return (
    <section className="band">
      <h2 className="band-t">{title}</h2>
      <div className="grid">{items.map(i => <Tile key={i.title} {...i} />)}</div>
    </section>
  )
}

export default function HomePage() {
  return (
    <main className="wrap">
      <style>{`
        :root{--ink:#1e2233;--ink2:#5a6178;--mute:#9aa3b8;--line:#e8ebf1;--brand:#5b4be0}
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:#fbfbfd;color:var(--ink)}
        .wrap{max-width:1120px;margin:0 auto;padding:0 22px 48px}
        .top{display:flex;align-items:center;gap:22px;padding:18px 0}
        .logo{font-size:20px;font-weight:800}
        .logo span{color:var(--mute);font-weight:500}
        .nav{display:flex;gap:18px;font-size:14px;font-weight:600;color:var(--ink2)}
        .nav a{color:inherit;text-decoration:none}
        .sub-btn{margin-left:auto;background:var(--brand);color:#fff;border:none;font-weight:700;font-size:14px;padding:9px 17px;border-radius:100px;cursor:pointer;text-decoration:none}
        .hero{text-align:center;padding:34px 0 8px}
        .hero h1{font-size:36px;font-weight:800;letter-spacing:-.02em}
        .hero p{font-size:17px;color:var(--ink2);margin-top:8px}
        .band{margin-top:26px}
        .band-t{font-size:12px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--mute);margin-bottom:12px}
        .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
        .t{border-radius:18px;padding:18px;text-decoration:none;color:#fff;min-height:118px;display:flex;flex-direction:column;transition:transform .15s}
        .t:hover{transform:translateY(-3px)}
        .t-ic{font-size:28px}
        .t-ti{font-size:17px;font-weight:800;margin-top:8px}
        .t-su{font-size:12.5px;opacity:.92;margin-top:auto}
        .foot{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);font-size:13px;color:var(--mute);display:flex;flex-wrap:wrap;gap:8px}
        .foot .m{margin-left:auto}
        @media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:28px}.nav{display:none}}
        @media(max-width:520px){.grid{grid-template-columns:1fr 1fr}}
      `}</style>

      <div className="top">
        <span className="logo">24reco<span>.com</span></span>
        <nav className="nav"><a href="#industrii">Industrii</a><a href="#institutii">Instituții</a><a href="#rapoarte">Rapoarte</a></nav>
        <Link href="/despre" className="sub-btn">Despre · Contact</Link>
      </div>

      <div className="hero">
        <h1>Date publice. Pe înțelesul tuturor.</h1>
        <p>Alege un domeniu și vezi cifrele care contează, explicate simplu.</p>
      </div>

      <div id="industrii"><Band title="Industrii" items={INDUSTRII} /></div>
      <div id="institutii"><Band title="Instituții Publice" items={INSTITUTII} /></div>
      <div id="rapoarte"><Band title="Rapoarte" items={RAPOARTE} /></div>

      <div className="foot">
        <span>24reco.com — Date publice din România</span>
        <span className="m">Surse: INS · BNR · MF · ME · ARR · AEP</span>
      </div>
    </main>
  )
}
