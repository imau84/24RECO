import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://24reco.com"),
  title: {
    default: "24reco.com — Date publice din România, pe înțelesul tuturor",
    template: "%s · 24reco.com",
  },
  description:
    "Statistici lunare din surse oficiale (INS, BNR, ANCPI, DRPCIV): înmatriculări auto, tranzacții imobiliare, prețuri, pensii și buget — explicate simplu.",
  keywords:
    "date publice romania, inmatriculari auto, statistici romania, rapoarte economice",
  openGraph: {
    title: "24reco.com — Date publice din România",
    description:
      "Statistici lunare din surse publice oficiale din România, explicate simplu.",
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
