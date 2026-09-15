import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Autorizații de construire în România — date INS",
    description: "Câte autorizații de construire se emit lunar în România și pentru ce tip de clădiri. Date INS, actualizate lunar.",
    alternates: { canonical: "/industrii/constructii" },
  };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
