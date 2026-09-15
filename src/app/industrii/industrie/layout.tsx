import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Industrie și exporturi în România — date INS",
    description: "Evoluția producției industriale și a exporturilor României. Date INS, actualizate lunar.",
      alternates: { canonical: "/industrii/industrie" },
      };

      export default function Layout({ children }: { children: React.ReactNode }) {
        return children;
        }
        
