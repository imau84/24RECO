import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "IT și comunicații în România — cifra de afaceri, salarii, export, internet și IPv6",
  description: "Cât încasează firmele de IT și telecom din România, câți angajați au și cum cresc salariile, cât export de servicii IT facem, cât costă telefonul și internetul, câte rețele și adrese IP are România și cât de răspândit e IPv6. Date oficiale Eurostat, RIPE NCC și APNIC, actualizate lunar.",
  alternates: { canonical: "/industrii/it-comunicatii" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
