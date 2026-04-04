"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/auto", label: "Auto" },
  { href: "/transport", label: "Transport" },
  { href: "/imobiliare", label: "Imobiliare" },
  { href: "/institutii", label: "Institutii" },
  { href: "/despre", label: "Despre" },
];

export default function Navbar() {
  const path = usePathname();
  return (
    <nav style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "16px 32px", borderBottom: "0.5px solid #e5e7eb",
      position: "sticky", top: 0, background: "#fff", zIndex: 50,
    }}>
      <Link href="/" style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, letterSpacing: "-0.5px" }}>
        24<span style={{ color: "var(--green)" }}>reco</span>.com
      </Link>
      <div style={{ display: "flex", gap: 24 }}>
        {links.map(l => (
          <Link key={l.href} href={l.href} style={{
            fontSize: 13, fontWeight: 400,
            color: path.startsWith(l.href) ? "var(--green)" : "#6b7280",
            borderBottom: path.startsWith(l.href) ? "1px solid var(--green)" : "none",
            paddingBottom: 2,
          }}>
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
