import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Alegeri locale 2024 — primari și consilii județene, rezultate pe județe și localități",
  description: "Rezultatele finale ale alegerilor locale din 9 iunie 2024: primarii aleși în cele 3.186 de localități (pe partide, județe și localități, cu toți candidații) și voturile pentru consiliile județene, cu prezența la vot. Date din procesele-verbale centralizate de AEP.",
  alternates: { canonical: "/rapoarte/alegeri-locale-2024" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
