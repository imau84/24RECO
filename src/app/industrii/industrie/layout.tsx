import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Industrie — exporturile României pe produse și județe",
  description: "Cât exportă România lunar, ce produse vinde, către UE sau în afara ei și ce județe exportă cel mai mult. Date oficiale INS, actualizate lunar.",
  alternates: { canonical: "/industrii/industrie" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
