import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const sectors = [
  {
    href: "/auto",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0F6E56" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M7 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm10 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4z"/>
        <path d="M5 17H3v-4l2-5h11l2 5v4h-2M5 17h10"/>
      </svg>
    ),
    iconBg: "#E1F5EE",
    title: "Auto",
    desc: "Inmatriculari lunare, parc auto national, top marci si modele inregistrate in Romania.",
    tags: ["Inmatriculari", "Marci", "Judete"],
    sursa: "DRPCIV / RAR",
    reports: 4,
  },
  {
    href: "/transport",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#185FA5" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="1" y="3" width="15" height="13" rx="2"/>
        <path d="M16 8h4l3 5v3h-7V8z"/>
        <circle cx="5.5" cy="18.5" r="2.5"/>
        <circle cx="18.5" cy="18.5" r="2.5"/>
      </svg>
    ),
    iconBg: "#E6F1FB",
    title: "Transport",
    desc: "Statistici marfuri, pasageri si infrastructura de transport rutier, feroviar si aerian.",
    tags: ["Marfuri", "Pasageri", "Infrastructura"],
    sursa: "MT / INS",
    reports: 3,
  },
  {
    href: "/imobiliare",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#854F0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
      </svg>
    ),
    iconBg: "#FAEEDA",
    title: "Imobiliare",
    desc: "Tranzactii imobiliare, autorizatii de constructie si evolutia pietei rezidentiale pe judete.",
    tags: ["Tranzactii", "Constructii", "ANCPI"],
    sursa: "ANCPI / INS",
    reports: 3,
  },
  {
    href: "/institutii",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#534AB7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 22V12M21 22V12M12 22V2M3 12l9-10 9 10M3 22h18"/>
      </svg>
    ),
    iconBg: "#EEEDFE",
    title: "Institutii publice",
    desc: "Cheltuieli publice, achizitii si date bugetare din transparenta institutionala.",
    tags: ["Buget", "Achizitii", "Transparenta"],
    sursa: "data.gov.ro",
    reports: 3,
  },
];

const stats = [
  { val: "4", lbl: "Sectoare" },
  { val: "12+", lbl: "Rapoarte" },
  { val: "Lunar", lbl: "Actualizat" },
  { val: "100%", lbl: "Date publice" },
];

export default function Home() {
  return (
    <main>
      <Navbar />

      {/* Hero */}
      <section style={{ padding: "64px 32px 48px", maxWidth: 760 }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "var(--green)", marginBottom: 14 }}>
          Date publice Romania
        </p>
        <h1 style={{ fontSize: 44, lineHeight: 1.12, marginBottom: 16 }}>
          Rapoarte bazate<br />pe date reale
        </h1>
        <p style={{ fontSize: 16, color: "#6b7280", lineHeight: 1.65, maxWidth: 520 }}>
          Statistici lunare din surse publice oficiale — inmatriculari auto, tranzactii imobiliare, transport si institutii publice din Romania.
        </p>
      </section>

      {/* Stats bar */}
      <div style={{ display: "flex", gap: 40, padding: "18px 32px", borderTop: "0.5px solid #e5e7eb", borderBottom: "0.5px solid #e5e7eb", background: "#f9fafb" }}>
        {stats.map(s => (
          <div key={s.lbl}>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700 }}>{s.val}</div>
            <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.8px", marginTop: 2 }}>{s.lbl}</div>
          </div>
        ))}
      </div>

      {/* Sectors */}
      <section style={{ padding: "40px 32px" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#9ca3af", marginBottom: 20 }}>Sectoare</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
          {sectors.map(s => (
            <Link key={s.href} href={s.href} style={{
              display: "block", padding: 24,
              border: "0.5px solid #e5e7eb", borderRadius: 12,
              background: "#fff", transition: "border-color 0.15s",
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = "#9ca3af")}
              onMouseLeave={e => (e.currentTarget.style.borderColor = "#e5e7eb")}
            >
              <div style={{ width: 36, height: 36, borderRadius: 8, background: s.iconBg, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                {s.icon}
              </div>
              <div style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 600, marginBottom: 6 }}>{s.title}</div>
              <div style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.55, marginBottom: 16 }}>{s.desc}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {s.tags.map(t => (
                  <span key={t} style={{ fontSize: 11, padding: "3px 8px", border: "0.5px solid #e5e7eb", borderRadius: 4, color: "#6b7280", background: "#f9fafb" }}>{t}</span>
                ))}
              </div>
              <div style={{ marginTop: 16, paddingTop: 14, borderTop: "0.5px solid #e5e7eb", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 11, color: "#9ca3af" }}>Sursa: {s.sursa}</span>
                <span style={{ fontSize: 14, color: "#9ca3af" }}>→</span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Latest report teaser */}
      <section style={{ padding: "0 32px 48px" }}>
        <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 12, padding: 24, background: "#f9fafb" }}>
          <p style={{ fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "1px", color: "var(--green)", marginBottom: 10 }}>Ultimul raport</p>
          <h2 style={{ fontSize: 19, fontWeight: 700, marginBottom: 6 }}>Inmatriculari auto — Martie 2025</h2>
          <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 20 }}>32.481 vehicule inmatriculate. Dacia conduce cu 18.4% cota de piata. Crestere de 6.2% fata de februarie.</p>
          <Link href="/auto" style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            fontSize: 13, padding: "8px 16px",
            border: "0.5px solid #d1d5db", borderRadius: 6,
            background: "#fff", color: "#1a1a1a",
          }}>
            Vezi raportul complet →
          </Link>
        </div>
      </section>

      <Footer />
    </main>
  );
}
