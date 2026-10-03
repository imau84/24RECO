import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Turism în România — sosiri, hoteluri, pasageri aerieni și prețuri",
  description: "Câți turiști vin lunar în hotelurile și pensiunile din România, români și străini, pe județe, localități și număr de stele, plus încasările hotelurilor și restaurantelor, pasagerii din aeroporturi, prețurile vacanțelor și gradul de ocupare față de alte țări. Date oficiale INS și Eurostat, actualizate lunar.",
  alternates: { canonical: "/industrii/turism" },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
