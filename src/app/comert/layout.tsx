import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Înmatriculări auto în România — date DRPCIV",
  description:
    "Câte mașini se înmatriculează lunar în România: pe mărci, tip de combustibil și nou vs. rulat. Date oficiale DRPCIV, actualizate lunar.",
  alternates: { canonical: "/comert" },
};

export default function ComertLayout({ children }: { children: React.ReactNode }) {
  return children;
}
