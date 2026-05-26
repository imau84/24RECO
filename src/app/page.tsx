import Link from 'next/link'

export default function HomePage() {
  return (
    <main style={{ fontFamily: "'DM Sans', system-ui, sans-serif", fontSize: 13, background: '#f4f5f7', color: '#1a1f2e', minHeight: '100vh' }}>

      {/* NAVBAR */}
      <nav style={{ background: '#0f2044', height: 48, display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', letterSpacing: '-0.3px', whiteSpace: 'nowrap' }}>
          📊 24reco.com
        </div>
        <div style={{ display: 'flex', gap: 2, flex: 1 }}>
          {[
            { label: 'Industrii', href: '#industrii' },
            { label: 'Instituții publice', href: '#institutii' },
            { label: 'Rapoarte', href: '#rapoarte' },
          ].map(({ label, href }) => (
            <a key={label} href={href} style={{ fontSize: 12, color: 'rgba(255,255,255,.55)', padding: '5px 12px', borderRadius: 5, textDecoration: 'none', transition: 'color .15s' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
              onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,.55)')}>
              {label}
            </a>
          ))}
        </div>
        <Link href="/despre" style={{ fontSize: 11, color: 'rgba(255,255,255,.5)', padding: '4px 10px', border: '1px solid rgba(255,255,255,.15)', borderRadius: 5, textDecoration: 'none' }}>
          Despre · Contact
        </Link>
      </nav>

      {/* HERO */}
      <div style={{ background: '#0f2044', padding: '22px 24px 20px', borderBottom: '1px solid #1a2d5a' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#fff', lineHeight: 1.2, marginBottom: 5 }}>Date publice. Simplu.</h1>
          <p style={{ fontSize: 12, color: 'rgba(255,255,255,.55)', lineHeight: 1.6 }}>Analizează industrii, instituții și rapoarte din România</p>
        </div>
      </div>

      {/* MAIN */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '20px 24px' }}>

        {/* INDUSTRII */}
        <section id="industrii" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#1a1f2e', whiteSpace: 'nowrap' }}>Industrii</span>
            <div style={{ flex: 1, height: 1, background: '#e8eaed' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {[
              { icon: '🌾', title: 'Agricultură', sub: 'Producție · Suprafețe', href: '/Industrii - Agricultura.html' },
              { icon: '🏗️', title: 'Construcții', sub: 'Autorizații · Lucrări', href: '/Industrii - Constructii.html' },
              { icon: '🏠', title: 'Imobiliare', sub: 'Tranzacții · ANCPI', href: '/Industrii - Imobiliare.html' },
              { icon: '🚛', title: 'Transport', sub: 'Marfă · Operatori', href: '/Industrii - Transport.html' },
              { icon: '🏭', title: 'Industrie', sub: 'IPI · CAEN', href: '/Industrii - Industrie.html' },
              { icon: '🛒', title: 'Comerț', sub: 'Retail · CA', href: '/Industrii - Comert.html' },
              { icon: '✈️', title: 'Turism', sub: 'Sosiri · Cazare', href: '/Industrii - Turism.html' },
            ].map(({ icon, title, sub, href }) => (
              <Card key={title} icon={icon} title={title} sub={sub} href={href} />
            ))}
          </div>
        </section>

        {/* INSTITUTII */}
        <section id="institutii" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#1a1f2e', whiteSpace: 'nowrap' }}>Instituții Publice</span>
            <div style={{ flex: 1, height: 1, background: '#e8eaed' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {[
              { icon: '🏦', title: 'BNR', sub: 'BPM6 · ISD · Credite', href: '/Institutii publice - BNR.html' },
              { icon: '👴', title: 'Casa Pensii', sub: 'Pensionari · Medie', href: '/Institutii publice - Casa de Pensii.html' },
              { icon: '📚', title: 'Min. Educației', sub: 'Elevi · Unități', href: '/Institutii publice - Ministerul Educatiei.html' },
              { icon: '💰', title: 'Execuție Bugetară', sub: 'Venituri · Cheltuieli', href: '/Institutii publice - Ministerul Finantelor - Executie Bugetara.html' },
              { icon: '📈', title: 'Datorie Publică', sub: 'Structură · Evoluție', href: '/Institutii publice - Ministerul Finantelor - Datorie Publica.html' },
            ].map(({ icon, title, sub, href }) => (
              <Card key={title} icon={icon} title={title} sub={sub} href={href} />
            ))}
          </div>
        </section>

        {/* RAPOARTE */}
        <section id="rapoarte" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#1a1f2e', whiteSpace: 'nowrap' }}>Rapoarte</span>
            <div style={{ flex: 1, height: 1, background: '#e8eaed' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
            {[
              { icon: '📊', title: 'Situații Financiare', sub: 'Bilanț · Companii', href: '/Rapoarte - Situatii Financiare.html' },
              { icon: '🗳️', title: 'Alegeri Locale 2024', sub: 'Județe · Comune', href: '/Rapoarte - Alegeri Locale 2024.html' },
            ].map(({ icon, title, sub, href }) => (
              <Card key={title} icon={icon} title={title} sub={sub} href={href} />
            ))}
          </div>
        </section>

        {/* FOOTER */}
        <div style={{ borderTop: '1px solid #e8eaed', background: '#fff', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8, borderRadius: 8 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
          <span style={{ fontSize: 11, color: '#5f6368' }}>24reco.com — Date publice din România</span>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: '#9aa0a6' }}>Surse: INS · BNR · MF · ME · ARR · AEP</span>
        </div>

      </div>
    </main>
  )
}

function Card({ icon, title, sub, href }: { icon: string; title: string; sub: string; href: string }) {
  return (
    <a href={href} style={{
      background: '#fff', border: '1px solid #e8eaed', borderRadius: 8,
      padding: '10px 12px', cursor: 'pointer', textDecoration: 'none',
      display: 'flex', alignItems: 'center', gap: 9, transition: 'all .15s',
    }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = '#1a56db'
        e.currentTarget.style.boxShadow = '0 2px 6px rgba(26,86,219,.08)'
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = '#e8eaed'
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.transform = 'translateY(0)'
      }}>
      <div style={{ fontSize: 16, flexShrink: 0, width: 24, textAlign: 'center' }}>{icon}</div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#0f2044', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{title}</div>
        <div style={{ fontSize: 10, color: '#9aa0a6', marginTop: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{sub}</div>
      </div>
    </a>
  )
}
