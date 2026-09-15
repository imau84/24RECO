import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pensii în România — număr pensionari și pensia medie",
    description: "Câți pensionari are România și cât e pensia medie, pe categorii și județe. Date CNPP, actualizate lunar.",
    alternates: { canonical: "/institutii/casa-pensii" },
  };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
