import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Execuție bugetară — veniturile și cheltuielile statului",
    description: "Cât încasează și cât cheltuie statul român, cu deficitul lunar. Date Ministerul Finanțelor, actualizate lunar.",
      alternates: { canonical: "/institutii-publice/ministerul-finantelor/executie-bugetara" },
      };

      export default function Layout({ children }: { children: React.ReactNode }) {
        return children;
        }
        
