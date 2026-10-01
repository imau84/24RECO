import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Autorizații de construire în România — evoluție lunară",
  description: "Cât se construiește în România: suprafața clădirilor autorizate lunar, locuințe vs. alte clădiri și comparația cu UE. Date Eurostat/INS, actualizate lunar.",
  alternates: { canonical: "/industrii/constructii" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
