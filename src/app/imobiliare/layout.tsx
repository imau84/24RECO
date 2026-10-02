import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Imobiliare în România — autorizații de construire și tranzacții",
  description: "Câte clădiri se autorizează (INS, pe județe și localități) și câte case, apartamente și terenuri se vând lunar (ANCPI) în România. Date oficiale, explicate simplu.",
  alternates: { canonical: "/imobiliare" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
