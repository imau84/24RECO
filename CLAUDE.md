# 24reco.com — context proiect

Platformă de rapoarte din date publice românești. Next.js 14 (App Router) + TypeScript + Tailwind + Recharts/D3, Neon (PostgreSQL) pentru datele ANAF. Deploy automat pe Vercel la push pe `main`.

## Structură (pe scurt)
- `scripts/*.py` + `.github/workflows/*.yml` — joburi cron care descarcă datele și comit JSON-uri în `public/`.
- `src/app/` — paginile (App Router); `src/app/api/firme/route.ts` — API peste Neon (tabelele `platitori`, `situatii_financiare`).
- `src/data/` — date statice importate la build (auto, ANCPI, agricultură, construcții, industrie).
- `src/components/` — Navbar, Footer.

## Redesign în curs

### Decizii de design (alese deja)
- **Homepage nou „Colorat & prietenos”** — plăci mari colorate per categorie, hero „Date publice. Pe înțelesul tuturor.” E DEJA LIVE (`src/app/page.tsx`).
- **Șablon pentru paginile de date = „Model A”**: tab-uri pe 2 niveluri (nivel 1 = sursa datelor, nivel 2 = analize), fiecare cu grafic + tabel, stil prietenos. Există ca demo la ruta `/model-a` (`src/app/model-a/page.tsx`), cu date auto reale august 2026.
- **Domeniu canonic:** `24reco.com` (fără www).
- **Public nespecialist** („românii nu prea înțeleg cifre”) → limbaj simplu lângă fiecare cifră.

### Etapa 0 (SEO) — FĂCUTĂ ȘI LIVE
- `robots.ts`, `sitemap.ts`, `metadataBase` + `title.template` în root layout.
- `layout.tsx` cu title/description/canonical pentru fiecare secțiune de date.
- Redirect 301 în `next.config.mjs` de la vechile URL-uri `.html` cu spații către rutele curate.

### De știut
- Paginile de date sunt `"use client"` (randate din client, arată „Se încarcă datele…”) → Google nu vede datele. De migrat la Server Components + ISR din Neon când ajungem la SEO pe conținut.

### Următorii pași posibili
1. Migrăm restul paginilor reale pe `ModelA` (Comerț, Industrie și Transport sunt deja mutate; seturile Eurostat/BCE folosesc `EurostatExplorer` + câte un `scripts/fetch_eurostat_*.py` lunar).
2. Conectăm cifre reale pe plăcile din homepage.
