import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BNR — balanța de plăți, investiții străine, depozite și credite",
  description: "Statistici lunare ale Băncii Naționale a României: contul curent și balanța de plăți, investițiile străine directe, depozitele și creditele populației și firmelor, în lei și în valută. Date oficiale BNR, actualizate lunar.",
  alternates: { canonical: "/institutii/bnr" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
