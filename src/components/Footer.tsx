export default function Footer() {
  return (
    <footer style={{
      borderTop: "0.5px solid #e5e7eb", padding: "20px 32px",
      display: "flex", justifyContent: "space-between", alignItems: "center",
      fontSize: 12, color: "#9ca3af", marginTop: 48,
    }}>
      <span>© {new Date().getFullYear()} 24reco.com — Date publice Romania</span>
      <div style={{ display: "flex", gap: 20 }}>
        <a href="/metodologie" style={{ color: "#9ca3af" }}>Metodologie</a>
        <a href="/surse" style={{ color: "#9ca3af" }}>Surse</a>
        <a href="/contact" style={{ color: "#9ca3af" }}>Contact</a>
      </div>
    </footer>
  );
}
