import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BNR — curs valutar, credite și indicatori",
    description: "Cursul euro/leu, creditarea și principalii indicatori ai Băncii Naționale a României. Date oficiale BNR.",
      alternates: { canonical: "/institutii/bnr" },
      };

      export default function Layout({ children }: { children: React.ReactNode }) {
        return children;
        }
        
