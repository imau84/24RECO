import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function InstitutiiPage() {
  return (
    <main>
      <Navbar />
      <div style={{ padding: "64px 32px", textAlign: "center" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#534AB7", marginBottom: 14 }}>Institutii Publice</p>
        <h1 style={{ fontSize: 36, marginBottom: 16 }}>Institutii publice</h1>
        <p style={{ fontSize: 15, color: "#6b7280", maxWidth: 480, margin: "0 auto 32px" }}>
          Rapoartele pentru Institutii Publice sunt in curs de pregatire. Surse: data.gov.ro, transparenta.gov.ro.
        </p>
        <Link href="/" style={{ fontSize: 13, padding: "8px 16px", border: "0.5px solid #d1d5db", borderRadius: 6, background: "#fff" }}>
          ← Inapoi la acasa
        </Link>
      </div>
      <Footer />
    </main>
  );
}
