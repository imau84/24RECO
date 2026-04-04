import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "24reco.com — Rapoarte date publice Romania",
  description: "Statistici lunare din surse publice oficiale: inmatriculari auto, tranzactii imobiliare, transport si institutii publice din Romania.",
  keywords: "date publice romania, inmatriculari auto, statistici romania, rapoarte economice",
  openGraph: {
    title: "24reco.com — Rapoarte date publice Romania",
    description: "Statistici lunare din surse publice oficiale din Romania",
    url: "https://24reco.com",
    siteName: "24reco.com",
    locale: "ro_RO",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ro">
      <body>{children}</body>
    </html>
  );
}
