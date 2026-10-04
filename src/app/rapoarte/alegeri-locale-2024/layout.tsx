import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Alegeri locale 2024 — rezultate consilii județene, prezență pe județe",
  description: "Rezultatele finale ale alegerilor locale din 9 iunie 2024 pentru consiliile județene din cele 41 de județe: voturi pe partide, prezența la vot în fiecare județ, voturi valabile și nule, din procesele-verbale centralizate de AEP.",
  alternates: { canonical: "/rapoarte/alegeri-locale-2024" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
