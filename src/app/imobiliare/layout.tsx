import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tranzacții imobiliare în România — date ANCPI",
    description: "Câte apartamente, case și terenuri se vând lunar în România, pe județe. Date oficiale ANCPI, actualizate lunar.",
      alternates: { canonical: "/imobiliare" },
      };

      export default function Layout({ children }: { children: React.ReactNode }) {
        return children;
        }
        
