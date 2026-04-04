import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function TransportPage() {
  return (
    <main>
      <Navbar />
      <div style={{ padding: "64px 32px", textAlign: "center" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#378ADD", marginBottom: 14 }}>Sector Transport</p>
        <h1 style={{ fontSize: 36, marginBottom: 16 }}>Transport</h1>
        <p style={{ fontSize: 15, color: "#6b7280", maxWidth: 480, margin: "0 auto 32px" }}>
          Rapoartele pentru sectorul Transport sunt in curs de pregatire. Surse: Ministerul Transporturilor, INS.
        </p>
        <Link href="/" style={{ fontSize: 13, padding: "8px 16px", border: "0.5px solid #d1d5db", borderRadius: 6, background: "#fff" }}>
          ← Inapoi la acasa
        </Link>
      </div>
      <Footer />
    </main>
  );
}
