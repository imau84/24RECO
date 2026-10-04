import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Casa de Pensii — câți salariați plătesc pensia și cât câștigă, pe tranșe și județe",
  description: "Câți salariați au contribuții la pensie în România, cât câștigă pe tranșe de venit brut, câți sunt sub salariul minim și salariul mediu în fiecare județ, lună de lună. Date oficiale CNPP (Pilon I), actualizate lunar.",
  alternates: { canonical: "/institutii/casa-pensii" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
