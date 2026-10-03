import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Comerț — înmatriculări auto, vânzări cu amănuntul, inflație și credite",
  description:
    "Câte mașini se înmatriculează lunar în România (pe mărci, județe, combustibil, noi vs. rulate), cât cumpără românii din magazine și online, cât de repede cresc prețurile față de UE și cât datorăm băncilor. Date oficiale DRPCIV, Eurostat și BCE, actualizate lunar.",
  alternates: { canonical: "/comert" },
};

export default function ComertLayout({ children }: { children: React.ReactNode }) {
  return children;
}
