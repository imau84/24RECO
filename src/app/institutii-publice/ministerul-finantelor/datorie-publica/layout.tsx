import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Datoria publică a României — structură și evoluție",
    description: "Cât datorează statul român și cum evoluează datoria publică, pe structură. Date Ministerul Finanțelor, actualizate lunar.",
    alternates: { canonical: "/institutii-publice/ministerul-finantelor/datorie-publica" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return children;
}
