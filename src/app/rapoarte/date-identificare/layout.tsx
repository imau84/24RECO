import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Date de identificare firme din România — ANAF",
    description: "Informații publice de identificare a companiilor din România. Date ANAF, actualizate anual.",
    alternates: { canonical: "/rapoarte/date-identificare" },
  };

export default function Layout({ children }: { children: React.ReactNode }) {
    return children;
  }
