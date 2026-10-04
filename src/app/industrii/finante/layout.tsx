import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Finanțe în România — bursă, dobânzi, ROBOR, asigurări, investiții și pensii private",
  description: "Bursa de Valori București și indicii BET, randamentul titlurilor de stat, ROBOR, dobânzile la credite și depozite, cursul leului, prețul asigurărilor și soliditatea asigurătorilor, depozitele și averea financiară a românilor, fondurile de investiții, Pilonul II și Pilonul III. Date oficiale Eurostat, BCE, BVB, ASF și EIOPA, actualizate lunar.",
  alternates: { canonical: "/industrii/finante" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
