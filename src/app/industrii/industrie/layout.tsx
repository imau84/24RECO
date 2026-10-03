import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Industrie — exporturi, salariați, producție, prețuri și energie",
  description: "Cât exportă România lunar, ce produse vinde, către UE sau în afara ei și ce județe exportă cel mai mult, câți salariați are industria, cât produc fabricile, cum cresc prețurile și cât curent produce și consumă țara. Date oficiale INS și Eurostat, actualizate lunar.",
  alternates: { canonical: "/industrii/industrie" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
