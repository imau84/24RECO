import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Parc auto România 2025 — mașini pe județe, mărci, modele și vechime",
  description: "Câte autoturisme sunt înmatriculate în fiecare județ, cât de vechi sunt, ce combustibil folosesc și care sunt cele mai răspândite mărci și modele. Date DGPCI (MAI), parc auto la 31.12.2025.",
  alternates: { canonical: "https://24reco.com/rapoarte/parc-auto" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
