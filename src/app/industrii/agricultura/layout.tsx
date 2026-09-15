import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Prețuri cereale în România — cotații BRM",
    description: "Prețul grâului, porumbului și al altor cereale pe zone de livrare. Cotații Bursa Română de Mărfuri, actualizate săptămânal.",
      alternates: { canonical: "/industrii/agricultura" },
      };

      export default function Layout({ children }: { children: React.ReactNode }) {
        return children;
        }
        
