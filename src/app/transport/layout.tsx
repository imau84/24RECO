import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Transport de marfă în România — firme, camioane și prețul motorinei",
  description: "Câte firme de transport rutier de marfă și câte camioane are România, pe mărime și localități, plus prețul motorinei comparat cu restul UE. Date oficiale, actualizate lunar și săptămânal.",
  alternates: { canonical: "/transport" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
