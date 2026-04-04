import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function DesprePage() {
  return (
    <main>
      <Navbar />
      <div style={{ padding: "48px 32px", maxWidth: 640 }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "var(--green)", marginBottom: 14 }}>Despre noi</p>
        <h1 style={{ fontSize: 32, marginBottom: 16 }}>Ce este 24reco.com?</h1>
        <p style={{ fontSize: 15, color: "#374151", lineHeight: 1.7, marginBottom: 16 }}>
          24reco.com este o platforma independenta de raportare a datelor publice din Romania. Colectam, prelucram si publicam statistici lunare din surse oficiale.
        </p>
        <p style={{ fontSize: 15, color: "#374151", lineHeight: 1.7, marginBottom: 16 }}>
          Toate datele provin din surse publice: DRPCIV, RAR, ANCPI, INS, Ministerul Transporturilor si data.gov.ro. Nu modificam datele — le prezentam asa cum sunt publicate oficial.
        </p>
        <h2 style={{ fontSize: 19, marginTop: 32, marginBottom: 12 }}>Sectoare acoperite</h2>
        <ul style={{ fontSize: 15, color: "#374151", lineHeight: 2, paddingLeft: 20 }}>
          <li>Auto — inmatriculari vehicule noi, parc auto, marci</li>
          <li>Transport — marfuri, pasageri, infrastructura</li>
          <li>Imobiliare — tranzactii, autorizatii constructie</li>
          <li>Institutii publice — cheltuieli, achizitii publice</li>
        </ul>
        <div style={{ marginTop: 32 }}>
          <Link href="/" style={{ fontSize: 13, padding: "8px 16px", border: "0.5px solid #d1d5db", borderRadius: 6, background: "#fff" }}>
            ← Inapoi la acasa
          </Link>
        </div>
      </div>
      <Footer />
    </main>
  );
}
