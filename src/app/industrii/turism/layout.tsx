import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Turism în România — sosiri și înnoptări",
    description: "Câți turiști vizitează România și unde se cazează, pe regiuni. Date INS, actualizate lunar.",
      alternates: { canonical: "/industrii/turism" },
      };

      export default function Layout({ children }: { children: React.ReactNode }) {
        return children;
        }
        
