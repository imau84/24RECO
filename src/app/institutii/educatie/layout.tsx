import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ministerul Educației — elevi pe școli, Evaluarea Națională și Bacalaureat 2025",
  description: "Câți elevi sunt înscriși în fiecare școală, localitate și județ în anul școlar 2025–2026, notele de la Evaluarea Națională 2025 și rezultatele la Bacalaureat 2025, pe județe, școli și licee. Date oficiale Ministerul Educației.",
  alternates: { canonical: "/institutii/educatie" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
