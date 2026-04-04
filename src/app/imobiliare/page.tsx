import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function ImobiliarePage() {
  return (
    <main>
      <Navbar />
      <div style={{ padding: "32px 32px 24px", borderBottom: "0.5px solid #e5e7eb" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#EF9F27", marginBottom: 10 }}>Sector Imobiliare</p>
        <h1 style={{ fontSize: 32, marginBottom: 8 }}>Imobiliare</h1>
        <p style={{ fontSize: 14, color: "#6b7280", maxWidth: 560 }}>Statistici lunare privind piața imobiliară din România: tranzacții, autorizații de construire și ipoteci. Surse: ANCPI, INS.</p>
      </div>
      <section style={{ padding: "40px 32px" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#9ca3af", marginBottom: 20 }}>Rapoarte disponibile</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          <Link href="/imobiliare/tranzactii" style={{ display: "block", padding: 24, border: "0.5px solid #e5e7eb", borderRadius: 12, background: "#fff", textDecoration: "none" }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: "#FAEEDA", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#854F0B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 600, marginBottom: 6 }}>Tranzacții</div>
            <div style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.55, marginBottom: 16 }}>Vânzări naționale pe județe: terenuri extravilan, intravilan și unități individuale. Date lunare ANCPI.</div>
            <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
              {["Terenuri","Unități individuale","Județe"].map(t => <span key={t} style={{ fontSize: 11, padding: "3px 8px", border: "0.5px solid #e5e7eb", borderRadius: 4, color: "#6b7280", background: "#f9fafb" }}>{t}</span>)}
            </div>
            <div style={{ paddingTop: 14, borderTop: "0.5px solid #e5e7eb", display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 11, color: "#9ca3af" }}>Sursa: ANCPI</span>
              <span style={{ fontSize: 14, color: "#EF9F27" }}>→</span>
            </div>
          </Link>
          {["Autorizații construcție","Ipoteci"].map(t => (
            <div key={t} style={{ padding: 24, border: "0.5px solid #e5e7eb", borderRadius: 12, background: "#fafafa", opacity: 0.6, position: "relative" }}>
              <div style={{ position: "absolute", top: 12, right: 12, fontSize: 10, padding: "2px 8px", borderRadius: 4, background: "#f3f4f6", color: "#9ca3af" }}>În curând</div>
              <div style={{ width: 36, height: 36, borderRadius: 8, background: "#f3f4f6", marginBottom: 16 }} />
              <div style={{ fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 600, marginBottom: 6, color: "#9ca3af" }}>{t}</div>
              <div style={{ fontSize: 13, color: "#9ca3af" }}>Raport în pregătire.</div>
            </div>
          ))}
        </div>
      </section>
      <Footer />
    </main>
  );
}
