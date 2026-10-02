import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Industrie — exporturi și salariați, pe produse, județe și domenii",
  description: "Cât exportă România lunar, ce produse vinde, către UE sau în afara ei și ce județe exportă cel mai mult, plus câți salariați are industria lună de lună. Date oficiale INS, actualizate lunar.",
  alternates: { canonical: "/industrii/industrie" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
