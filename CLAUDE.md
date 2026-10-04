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
- Toate paginile din Industrii, Instituții Publice și Rapoarte sunt acum pe `ModelA`. Excepții rămase pe formatul vechi: `/auto`, `/imobiliare/tranzactii`, `/despre`.
- Paginile cu căutare (Situații financiare → API Neon) și Educație (date de ~5 MB din `public/`) rămân interactive în browser, ca subtab-uri `content` în ModelA.
- Vechile pagini statice `public/*.html` mai există, dar `next.config.mjs` le redirecționează (301) spre rutele noi.

### Următorii pași posibili
1. Migrăm restul paginilor reale pe `ModelA` (Comerț, Industrie, Transport, Turism, IT&Comunicații, Finanțe și Energie sunt deja mutate; seturile Eurostat/BCE folosesc `EurostatExplorer` + câte un `scripts/fetch_eurostat_*.py` lunar).
2. Conectăm cifre reale pe plăcile din homepage.

### Finanțe (`/industrii/finante`)
- Datele vin din pachetul `scripts/financiara/` (20 de scripturi copiate neschimbate; Eurostat, BCE, BIS, BVB, ASF, EIOPA) care scrie Excel-uri în `scripts/financiara/out/` (ignorat de git); `scripts/fetch_finante.py` le rulează și convertește foile de serii în `src/data/finante/date.json`.
- Seturile BVB (01 02, 01 03, 01 05) parsează PDF-uri cu `pdftotext` din **poppler** (Linux/CI). Pe Windows, `pdftotext` din Git/mingw e xpdf și aliniază coloanele altfel → parserul eșuează; local folosește `--doar-conversie`.

### Energie (`/industrii/energie`)
- Un tab per sursă (Eurostat, Ember, Comisia Europeană, OPCOM); `scripts/fetch_energie.py` → `src/data/energie/date.json`. Tab-urile vin din `src/components/temeDinJson.tsx` (comun cu Finanțe).
- OPCOM are doar export pe zi → istoricul lunar stă în `scripts/data/opcom_pzu_lunar.csv`; scriptul recalculează doar lunile neîncheiate din ultimele 3 luni.
- `EurostatExplorer` acceptă și `freq: 'S'` (semestrial, „2025-S2”), folosit la prețurile finale la electricitate și gaz.

### Instituții Publice și Rapoarte (migrate pe Model A)
- `/institutii-publice/ministerul-finantelor` — tab-uri Execuție Bugetară + Datorie Publică (vechile sub-rute fac 301 aici). Scripturile MF găsesc coloanele/perioadele după antet, nu după poziție (formatul fișierelor se schimbă).
- `/institutii/bnr` — seriile din `public/bnr_data.json` în `EurostatExplorer`; `/institutii/casa-pensii` — `cnpp_asigurati.json` (`cnpp_data.json` e vechi, nefolosit).
- `/institutii/educatie` — `EduApp.tsx` = codul portat din vechiul HTML (`// @ts-nocheck`).
- `/rapoarte/date-financiare` și `/rapoarte/date-identificare` — aceeași pagină, deschisă pe subtab-ul propriu; `/rapoarte/alegeri-locale-2024` — 41 de județe, fără București.
