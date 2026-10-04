import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Energie în România — electricitate, gaze, petrol, carburanți, prețul la bursă și emisii",
  description: "Producția de electricitate pe surse (hidro, nuclear, cărbune, gaz, eolian, solar), consumul și importul, bilanțul gazelor și importurile pe țări, cărbunele, țițeiul și carburanții, prețurile la pompă, prețul angro OPCOM, inflația la energie, prețurile la factură și emisiile de CO₂. Date oficiale Eurostat, Ember, Comisia Europeană și OPCOM, actualizate lunar.",
  alternates: { canonical: "/industrii/energie" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
