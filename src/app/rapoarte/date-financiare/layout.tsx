import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Situații financiare firme — bilanțuri (ANAF)",
    description: "Bilanțuri și indicatori financiari ai companiilor din România. Date ANAF și Ministerul Finanțelor, actualizate anual.",
    alternates: { canonical: "/rapoarte/date-financiare" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return children;
}
