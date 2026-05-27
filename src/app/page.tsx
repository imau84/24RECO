'use client'

import Link from 'next/link'

const INDUSTRII = [
  { icon: '🌾', title: 'Agricultură', sub: 'Producție · Suprafețe', href: '/Industrii - Agricultura.html' },
  { icon: '🏗️', title: 'Construcții', sub: 'Autorizații · Lucrări', href: '/Industrii - Constructii.html' },
  { icon: '🏠', title: 'Imobiliare', sub: 'Tranzacții · ANCPI', href: '/Industrii - Imobiliare.html' },
  { icon: '🚛', title: 'Transport', sub: 'Marfă · Operatori', href: '/Industrii - Transport.html' },
  { icon: '🏭', title: 'Industrie', sub: 'IPI · CAEN', href: '/Industrii - Industrie.html' },
  { icon: '🛒', title: 'Comerț', sub: 'Retail · CA', href: '/Industrii - Comert.html' },
  { icon: '✈️', title: 'Turism', sub: 'Sosiri · Cazare', href: '/Industrii - Turism.html' },
]

const INSTITUTII = [
  { icon: '🏦', title: 'BNR', sub: 'BPM6 · ISD · Credite', href: '/Institutii publice - BNR.html' },
  { icon: '👴', title: 'Casa Pensii', sub: 'Pensionari · Medie', href: '/Institutii publice - Casa de Pensii.html' },
  { icon: '📚', title: 'Min. Educației', sub: 'Elevi · Unități', href: '/Institutii publice - Ministerul Educatiei.html' },
  { icon: '💰', title: 'Execuție Bugetară', sub: 'Venituri · Cheltuieli', href: '/Institutii publice - Ministerul Finantelor - Executie Bugetara.html' },
  { icon: '📈', title: 'Datorie Publică', sub: 'Structură · Evoluție', href: '/Institutii publice - Ministerul Finantelor - Datorie Publica.html' },
]

const RAPOARTE = [
  { icon: '📊', title: 'Situații Financiare', sub: 'Bilanț · Companii', href: '/Rapoarte - Situatii Financiare.html' },
  { icon: '🗳️', title: 'Alegeri Locale 2024', sub: 'Județe · Comune', href: '/Rapoarte - Alegeri Locale 2024.html' },
]

function Card({ icon, title, sub, href }: { icon: string; title: string; sub: string; href: string }) {
  return (
    <a href={href} className="hp-card">
      <span className="hp-card-icon">{icon}</span>
      <span className="hp-card-body">
        <span className="hp-card-title">{title}</span>
        <span className="hp-card-sub">{sub}</span>
      </span>
    </a>
  )
}

function Section({ id, title, items }: { id: string; title: string; items: typeof INDUSTRII }) {
  return (
    <section id={id} className="hp-section">
      <div className="hp-sec-header">
        <span className="hp-sec-title">{title}</span>
        <div className="hp-sec-line" />
      </div>
      <div className="hp-grid">
        {items.map(item => <Card key={item.title} {...item} />)}
      </div>
    </section>
  )
}

export default function HomePage() {
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        html{-webkit-text-size-adjust:100%}
        body{font-family:'DM Sans',system-ui,sans-serif;font-size:13px;background:#f4f5f7;color:#1a1f2e;-webkit-font-smoothing:antialiased}

        /* NAVBAR */
        .hp-nav{background:#0f2044;height:48px;display:flex;align-items:center;padding:0 20px;gap:12px;position:sticky;top:0;z-index:100}
        .hp-logo{font-size:14px;font-weight:700;color:#fff;letter-spacing:-0.3px;white-space:nowrap;text-decoration:none}
        .hp-navlinks{display:flex;gap:2px;flex:1;overflow:hidden}
        .hp-navlink{font-size:12px;color:rgba(255,255,255,.55);padding:5px 10px;border-radius:5px;text-decoration:none;transition:color .15s;white-space:nowrap}
        .hp-navlink:hover{color:#fff}
        .hp-about{font-size:11px;color:rgba(255,255,255,.5);padding:4px 10px;border:1px solid rgba(255,255,255,.15);border-radius:5px;text-decoration:none;transition:all .15s;white-space:nowrap;flex-shrink:0}
        .hp-about:hover{color:#fff;border-color:rgba(255,255,255,.35)}

        /* HERO */
        .hp-hero{background:#0f2044;padding:24px 20px 22px;border-bottom:1px solid #1a2d5a}
        .hp-hero-inner{max-width:1200px;margin:0 auto}
        .hp-hero h1{font-size:22px;font-weight:700;color:#fff;line-height:1.2;margin-bottom:5px}
        .hp-hero p{font-size:12px;color:rgba(255,255,255,.55);line-height:1.6}

        /* MAIN */
        .hp-main{max-width:1200px;margin:0 auto;padding:20px 20px}
        .hp-section{margin-bottom:20px}
        .hp-sec-header{display:flex;align-items:center;gap:10px;margin-bottom:10px}
        .hp-sec-title{font-size:12px;font-weight:700;color:#1a1f2e;white-space:nowrap}
        .hp-sec-line{flex:1;height:1px;background:#e8eaed}

        /* GRID — responsive */
        .hp-grid{display:grid;gap:8px;grid-template-columns:repeat(4,1fr)}

        /* CARD */
        .hp-card{background:#fff;border:1px solid #e8eaed;border-radius:8px;padding:10px 12px;text-decoration:none;display:flex;align-items:center;gap:9px;transition:all .15s}
        .hp-card:hover{border-color:#1a56db;box-shadow:0 2px 6px rgba(26,86,219,.08);transform:translateY(-1px)}
        .hp-card-icon{font-size:16px;flex-shrink:0;width:24px;text-align:center}
        .hp-card-body{display:flex;flex-direction:column;min-width:0}
        .hp-card-title{font-size:12px;font-weight:600;color:#0f2044;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .hp-card-sub{font-size:10px;color:#9aa0a6;margin-top:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

        /* FOOTER */
        .hp-footer{border-top:1px solid #e8eaed;background:#fff;padding:10px 16px;display:flex;align-items:center;gap:8px;border-radius:8px;margin-top:4px;flex-wrap:wrap;row-gap:4px}
        .hp-footer-dot{width:6px;height:6px;border-radius:50%;background:#22c55e;flex-shrink:0}
        .hp-footer-text{font-size:11px;color:#5f6368}
        .hp-footer-meta{font-size:11px;color:#9aa0a6;margin-left:auto}

        /* TABLET: 768px - 1024px → 3 coloane */
        @media(max-width:1024px){
          .hp-grid{grid-template-columns:repeat(3,1fr)}
          .hp-hero h1{font-size:20px}
        }

        /* TABLET MIC: 600px - 768px → 2 coloane */
        @media(max-width:768px){
          .hp-grid{grid-template-columns:repeat(2,1fr)}
          .hp-nav{padding:0 16px}
          .hp-main{padding:16px}
          .hp-hero{padding:20px 16px 18px}
          .hp-hero h1{font-size:18px}
          .hp-navlinks{gap:0}
          .hp-navlink{font-size:11px;padding:5px 8px}
          .hp-footer-meta{margin-left:0;width:100%}
        }

        /* MOBIL: < 480px → 1 coloană, navbar simplificat */
        @media(max-width:480px){
          .hp-grid{grid-template-columns:1fr 1fr}
          .hp-card{padding:10px}
          .hp-card-title{font-size:11px}
          .hp-navlinks{display:none}
          .hp-hero h1{font-size:17px}
          .hp-about{font-size:10px;padding:3px 8px}
        }

        @media(max-width:360px){
          .hp-grid{grid-template-columns:1fr}
        }
      `}</style>

      <nav className="hp-nav">
        <a href="/" className="hp-logo">📊 24reco.com</a>
        <div className="hp-navlinks">
          <a href="#industrii" className="hp-navlink">Industrii</a>
          <a href="#institutii" className="hp-navlink">Instituții publice</a>
          <a href="#rapoarte" className="hp-navlink">Rapoarte</a>
        </div>
        <Link href="/despre" className="hp-about">Despre · Contact</Link>
      </nav>

      <div className="hp-hero">
        <div className="hp-hero-inner">
          <h1>Date publice. Simplu.</h1>
          <p>Analizează industrii, instituții și rapoarte din România</p>
        </div>
      </div>

      <div className="hp-main">
        <Section id="industrii" title="Industrii" items={INDUSTRII} />
        <Section id="institutii" title="Instituții Publice" items={INSTITUTII} />
        <Section id="rapoarte" title="Rapoarte" items={RAPOARTE} />

        <div className="hp-footer">
          <div className="hp-footer-dot" />
          <span className="hp-footer-text">24reco.com — Date publice din România</span>
          <span className="hp-footer-meta">Surse: INS · BNR · MF · ME · ARR · AEP</span>
        </div>
      </div>
    </>
  )
}
