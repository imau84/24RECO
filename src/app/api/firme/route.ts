import { neon } from "@neondatabase/serverless";
import { NextRequest, NextResponse } from "next/server";

// API pentru datele de identificare ANAF (tabela platitori, Neon PostgreSQL)
//   GET /api/firme?cui=123                                  -> fisa unei firme
//   GET /api/firme?search=NUME                              -> cautare dupa denumire (max 20)
//   GET /api/firme?financiare=123                           -> indicatorii financiari ai firmei
//   GET /api/firme?mode=judete                              -> lista judetelor
//   GET /api/firme?mode=localitati&judet=X                  -> localitatile din judet
//   GET /api/firme?mode=strazi&judet=X&localitate=Y         -> strazile din localitate
//   GET /api/firme?mode=lista&judet=X[&localitate=Y][&strada=Z][&page=0]
//                                                           -> firmele filtrate, paginat

const sql = neon(process.env.DATABASE_URL!);
const PAGE_SIZE = 50;

const CACHE_FACETS = { "Cache-Control": "public, s-maxage=86400, stale-while-revalidate=604800" };
const CACHE_LISTA = { "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" };

export async function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;

  try {
    // ---- fisa firmei dupa CUI --------------------------------------------
    const cuiRaw = sp.get("cui");
    if (cuiRaw) {
      const cui = Number(cuiRaw.replace(/\D/g, ""));
      if (!cui || !Number.isSafeInteger(cui)) {
        return NextResponse.json({ error: "CUI invalid" }, { status: 400 });
      }
      const rows = await sql`
        SELECT cui, denumire, tip_unitate, localitate, strada, nr,
               to_char(data_inregistrare, 'DD.MM.YYYY') AS data_inregistrare,
               telefon, judet_comert, nr_comert, an_comert, cod_postal,
               to_char(data_stare, 'DD.MM.YYYY') AS data_stare, stare, judet
        FROM platitori WHERE cui = ${cui}`;
      if (rows.length === 0) {
        return NextResponse.json({ error: "Nu am găsit nicio firmă cu acest CUI" }, { status: 404 });
      }
      return NextResponse.json(rows[0], { headers: CACHE_LISTA });
    }

    // ---- cautare dupa denumire -------------------------------------------
    const search = sp.get("search");
    if (search) {
      const q = search.trim();
      if (q.length < 3) {
        return NextResponse.json({ error: "Introdu cel puțin 3 caractere" }, { status: 400 });
      }
      const rows = await sql`
        SELECT cui, denumire, localitate, judet
        FROM platitori
        WHERE denumire ILIKE ${"%" + q + "%"}
        ORDER BY denumire
        LIMIT 20`;
      return NextResponse.json(rows, { headers: CACHE_LISTA });
    }

    // ---- indicatorii financiari ai unei firme ----------------------------
    const finRaw = sp.get("financiare");
    if (finRaw) {
      const cui = Number(finRaw.replace(/\D/g, ""));
      if (!cui || !Number.isSafeInteger(cui)) {
        return NextResponse.json({ error: "CUI invalid" }, { status: 400 });
      }
      const rows = await sql`
        SELECT s.cui, s.an, s.sursa, s.caen,
               s.active_imobilizate, s.active_circulante, s.stocuri, s.creante,
               s.casa_conturi, s.cheltuieli_in_avans, s.datorii, s.venituri_in_avans,
               s.provizioane, s.capitaluri_total, s.capital_subscris, s.patrimoniul_regiei,
               s.cifra_afaceri_neta, s.venituri_totale, s.cheltuieli_totale,
               s.profit_brut, s.pierdere_bruta, s.profit_net, s.pierdere_neta,
               s.numar_salariati,
               p.denumire, p.localitate, p.judet
        FROM situatii_financiare s
        LEFT JOIN platitori p ON p.cui = s.cui
        WHERE s.cui = ${cui}
        ORDER BY s.an DESC`;
      if (rows.length === 0) {
        return NextResponse.json(
          { error: "Nu am găsit situații financiare pentru acest CUI" },
          { status: 404 },
        );
      }
      return NextResponse.json(rows, { headers: CACHE_LISTA });
    }

    const mode = sp.get("mode");
    const judet = sp.get("judet");
    const localitate = sp.get("localitate");
    const strada = sp.get("strada");

    // ---- fatete pentru filtrele in cascada -------------------------------
    if (mode === "judete") {
      const rows = await sql`
        SELECT DISTINCT judet FROM platitori
        WHERE judet IS NOT NULL ORDER BY judet`;
      return NextResponse.json(rows.map(r => r.judet), { headers: CACHE_FACETS });
    }

    if (mode === "localitati") {
      if (!judet) return NextResponse.json({ error: "Lipsește județul" }, { status: 400 });
      const rows = await sql`
        SELECT DISTINCT localitate FROM platitori
        WHERE judet = ${judet} AND localitate IS NOT NULL
        ORDER BY localitate`;
      return NextResponse.json(rows.map(r => r.localitate), { headers: CACHE_FACETS });
    }

    if (mode === "strazi") {
      if (!judet || !localitate) {
        return NextResponse.json({ error: "Lipsește județul sau localitatea" }, { status: 400 });
      }
      const rows = await sql`
        SELECT DISTINCT strada FROM platitori
        WHERE judet = ${judet} AND localitate = ${localitate} AND strada IS NOT NULL
        ORDER BY strada`;
      return NextResponse.json(rows.map(r => r.strada), { headers: CACHE_FACETS });
    }

    // ---- lista firmelor filtrate, paginata -------------------------------
    if (mode === "lista") {
      if (!judet) return NextResponse.json({ error: "Lipsește județul" }, { status: 400 });
      const page = Math.max(0, Number(sp.get("page") || 0));
      const offset = page * PAGE_SIZE;

      const [rows, cnt] = await Promise.all([
        sql`
          SELECT cui, denumire, localitate, strada, nr, stare,
                 to_char(data_inregistrare, 'DD.MM.YYYY') AS data_inregistrare
          FROM platitori
          WHERE judet = ${judet}
            AND (${localitate}::text IS NULL OR localitate = ${localitate})
            AND (${strada}::text IS NULL OR strada = ${strada})
          ORDER BY denumire
          LIMIT ${PAGE_SIZE} OFFSET ${offset}`,
        sql`
          SELECT count(*)::int AS n FROM platitori
          WHERE judet = ${judet}
            AND (${localitate}::text IS NULL OR localitate = ${localitate})
            AND (${strada}::text IS NULL OR strada = ${strada})`,
      ]);

      return NextResponse.json(
        { total: cnt[0].n, pageSize: PAGE_SIZE, page, rows },
        { headers: CACHE_LISTA },
      );
    }

    return NextResponse.json({ error: "Parametri lipsă: cui, search, financiare sau mode" }, { status: 400 });
  } catch (e) {
    console.error("api/firme:", e);
    return NextResponse.json({ error: "Eroare internă" }, { status: 500 });
  }
}
