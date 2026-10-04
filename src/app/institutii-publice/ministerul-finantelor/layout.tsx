import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ministerul Finanțelor — execuția bugetară și datoria publică a României",
  description: "Veniturile și cheltuielile statului lună de lună, deficitul bugetar ca procent din PIB, de unde vin banii (TVA, contribuții, impozite) și pe ce se cheltuie, plus datoria publică: evoluție din 2010, procent din PIB, internă și externă, în lei și euro. Date oficiale Ministerul Finanțelor, actualizate lunar.",
  alternates: { canonical: "/institutii-publice/ministerul-finantelor" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
