"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

// -------------------------------------------------------------- tipuri

type Rezultat = { cui: number; denumire: string; localitate: string | null; judet: string | null };

type Fin = {
  cui: number; an: number; sursa: string; caen: number | null;
  active_imobilizate: number | null; active_circulante: number | null;
  stocuri: number | null; creante: number | null; casa_conturi: number | null;
  cheltuieli_in_avans: number | null; datorii: number | null;
  venituri_in_avans: number | null; provizioane: number | null;
  capitaluri_total: number | null; capital_subscris: number | null;
  patrimoniul_regiei: number | null; cifra_afaceri_neta: number | null;
  venituri_totale: number | null; cheltuieli_totale: number | null;
  profit_brut: number | null; pierdere_bruta: number | null;
  profit_net: number | null; pierdere_neta: number | null;
  numar_salariati: number | null;
  denumire: string | null; localitate: string | null; judet: string | null;
};

const API = "/api/firme";

const SURSA_LABEL: Record<string, string> = {
  BL_BS_SL: "Bilanț entități mari, mijlocii și mici",
  IR: "Raportare instituții de credit / IFN",
  UU: "Bilanț microentități",
};

// -------------------------------------------------------------- pagina

export default function DateFinanciarePage() {
  const [query, setQuery] = useState("");
  const [rezultate, setRezultate] = useState<Rezultat[] | null>(null);
  const [fin, setFin] = useState<Fin | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const nr = (v: number | null) =>
    v == null ? "–" : v.toLocaleString("en-US"); // separator de mii: virgula (ex. 149,904,552)

  // ------------------------------------------------ cautare

  async function cauta() {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setErr("");
    setRezultate(null);
    setFin(null);
    try {
      if (/^\d+$/.test(q.replace(/\s/g, ""))) {
        // e un CUI -> direct la fisa financiara
        await incarcaFin(q.replace(/\s/g, ""));
      } else {
        const r = await fetch(`${API}?search=${encodeURIComponent(q)}`);
        const data = await r.json();
        if (!r.ok) setErr(data.error || "Eroare la căutare");
        else if (data.length === 0) setErr("Nicio firmă găsită cu acest nume.");
        else if (data.length === 1) await incarcaFin(String(data[0].cui));
        else setRezultate(data);
      }
    } catch {
      setErr("Nu am putut contacta serverul. Încearcă din nou.");
    } finally {
      setLoading(false);
    }
  }

  async function incarcaFin(cui: string) {
    setErr("");
    setRezultate(null);
    const r = await fetch(`${API}?financiare=${cui}`);
    const data = await r.json();
    if (!r.ok) {
      setErr(data.error || "Eroare la încărcarea datelor financiare");
      setFin(null);
    } else {
      setFin(data[0]); // cel mai recent an
    }
  }

  // ------------------------------------------------ randari ajutatoare

  const Row = ({ label, val, indent }: { label: string; val: number | null; indent?: boolean }) => (
    <tr>
      <td className={indent ? "df-ind" : ""}>{label}</td>
      <td className="df-val">{nr(val)}</td>
    </tr>
  );

  const Sect = ({ titlu }: { titlu: string }) => (
    <tr className="df-sect"><td colSpan={2}>{titlu}</td></tr>
  );

  // ------------------------------------------------ pagina

  return (
    <main>
      <Navbar />
      <div className="df-wrap">
      <style>{`
        .df-wrap { max-width: 1180px; margin: 0 auto; padding: 32px 24px 64px; color: #1a1a1a; }
        .df-wrap h1 { font-size: 1.7rem; margin: 0 0 4px; }
        .df-sub { color: #6b7280; margin: 0 0 28px; font-size: .95rem; }
        .df-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
                   padding: 20px; margin-bottom: 24px; }
        .df-card h2 { font-size: 1.05rem; margin: 0 0 14px; color: var(--green-dark, #0F6E56); }
        .df-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
        .df-field { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 220px; }
        .df-field label { font-size: .8rem; color: #4b5563; font-weight: 600; }
        .df-field input { padding: 9px 10px; border: 1px solid #d1d5db; border-radius: 7px;
                          font-size: .95rem; font-family: inherit; }
        .df-field input:focus { outline: 2px solid var(--green, #1D9E75); outline-offset: 1px;
                                border-color: var(--green, #1D9E75); }
        .df-btn { padding: 9px 20px; border: none; border-radius: 7px;
                  background: var(--green, #1D9E75); color: #fff; font-size: .95rem;
                  font-weight: 600; cursor: pointer; font-family: inherit; }
        .df-btn:hover { background: var(--green-dark, #0F6E56); }
        .df-btn:disabled { background: #9ca3af; cursor: default; }
        .df-err { color: #b91c1c; font-size: .9rem; margin-top: 10px; }
        .df-info { color: #6b7280; font-size: .9rem; margin-top: 10px; }
        .df-rez { list-style: none; margin: 14px 0 0; padding: 0; }
        .df-rez li { padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 8px;
                     margin-bottom: 8px; cursor: pointer; display: flex; flex-wrap: wrap;
                     gap: 6px 14px; align-items: baseline; }
        .df-rez li:hover { background: var(--green-light, #E1F5EE);
                           border-color: var(--green, #1D9E75); }
        .df-rez .nume { font-weight: 600; }
        .df-rez .meta { color: #6b7280; font-size: .85rem; }
        .df-firma { margin: 0 0 2px; font-size: 1.25rem; }
        .df-firma-meta { color: #6b7280; font-size: .9rem; margin: 0 0 16px; }
        .df-table { width: 100%; border-collapse: collapse; font-size: .92rem; }
        .df-table td { padding: 8px 12px; border: 1px solid #e5e7eb; }
        .df-table .df-val { text-align: right; font-variant-numeric: tabular-nums;
                            white-space: nowrap; width: 180px; }
        .df-table .df-ind { padding-left: 30px; color: #4b5563; }
        .df-sect td { background: var(--green, #1D9E75); color: #fff; font-weight: 700;
                      font-size: .82rem; text-transform: uppercase; letter-spacing: .05em; }
        .df-note { color: #6b7280; font-size: .82rem; margin-top: 12px; font-style: italic; }
        @media (max-width: 640px) { .df-table .df-val { width: auto; } }
      `}</style>

      <h1>Date financiare</h1>
      <p className="df-sub">
        Indicatori din situațiile financiare anuale la 31 decembrie 2025, depuse la ANAF.
        Caută firma după denumire sau CUI.
      </p>

      {/* ------------------------------------------------ cautare */}
      <section className="df-card">
        <h2>Alege firma</h2>
        <div className="df-row">
          <div className="df-field">
            <label htmlFor="df-q">Denumire firmă sau CUI</label>
            <input
              id="df-q"
              placeholder="ex. BUCUR OBOR sau 4440511"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && cauta()}
            />
          </div>
          <button className="df-btn" onClick={cauta} disabled={loading || !query.trim()}>
            {loading ? "Caut..." : "Caută"}
          </button>
        </div>
        {err && <p className="df-err">{err}</p>}

        {rezultate && (
          <>
            <p className="df-info">Am găsit {rezultate.length} firme — alege una:</p>
            <ul className="df-rez">
              {rezultate.map(f => (
                <li key={f.cui} onClick={() => incarcaFin(String(f.cui))}>
                  <span className="nume">{f.denumire}</span>
                  <span className="meta">CUI {f.cui}</span>
                  <span className="meta">{[f.localitate, f.judet].filter(Boolean).join(", ")}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* ------------------------------------------------ indicatori */}
      {fin && (
        <section className="df-card">
          <h2 className="df-firma">{fin.denumire || `CUI ${fin.cui}`}</h2>
          <p className="df-firma-meta">
            CUI {fin.cui}
            {fin.localitate ? ` · ${fin.localitate}` : ""}
            {fin.judet ? `, ${fin.judet}` : ""}
            {" · "}Exercițiul financiar {fin.an}
            {" · "}{SURSA_LABEL[fin.sursa] || fin.sursa}
            {fin.caen ? ` · CAEN ${fin.caen}` : ""}
          </p>

          <table className="df-table">
            <tbody>
              <Sect titlu="Indicatori din BILANȚ" />
              <Row label="ACTIVE IMOBILIZATE — TOTAL" val={fin.active_imobilizate} />
              <Row label="ACTIVE CIRCULANTE — TOTAL, din care" val={fin.active_circulante} />
              <Row indent label="Stocuri (materii prime, materiale, producție în curs de execuție, semifabricate, produse finite, mărfuri etc.)" val={fin.stocuri} />
              <Row indent label="Creanțe" val={fin.creante} />
              <Row indent label="Casa și conturi la bănci" val={fin.casa_conturi} />
              <Row label="CHELTUIELI ÎN AVANS" val={fin.cheltuieli_in_avans} />
              <Row label="DATORII" val={fin.datorii} />
              <Row label="VENITURI ÎN AVANS" val={fin.venituri_in_avans} />
              <Row label="PROVIZIOANE" val={fin.provizioane} />
              <Row label="CAPITALURI — TOTAL, din care:" val={fin.capitaluri_total} />
              <Row indent label="Capital subscris vărsat" val={fin.capital_subscris} />
              <Row indent label="Patrimoniul regiei" val={fin.patrimoniul_regiei} />

              <Sect titlu="Indicatori din CONTUL DE PROFIT ȘI PIERDERE" />
              <Row label="Cifra de afaceri netă" val={fin.cifra_afaceri_neta} />
              <Row label="VENITURI TOTALE" val={fin.venituri_totale} />
              <Row label="CHELTUIELI TOTALE" val={fin.cheltuieli_totale} />
              <tr><td>Profitul sau pierderea brut(ă)</td><td className="df-val"></td></tr>
              <Row indent label="— Profit" val={fin.profit_brut} />
              <Row indent label="— Pierdere" val={fin.pierdere_bruta} />
              <tr><td>Profitul sau pierderea net(ă) a exercițiului financiar</td><td className="df-val"></td></tr>
              <Row indent label="— Profit" val={fin.profit_net} />
              <Row indent label="— Pierdere" val={fin.pierdere_neta} />

              <Sect titlu="Indicatori din DATE INFORMATIVE" />
              <Row label="Număr mediu de salariați" val={fin.numar_salariati} />
            </tbody>
          </table>

          <p className="df-note">
            Valorile sunt exprimate în lei. Operatorii economici răspund pentru corectitudinea
            informațiilor raportate, potrivit legii.
          </p>
        </section>
      )}

      <p className="df-info">
        Sursa datelor: ANAF / data.gov.ro — „Situații financiare 2025”. Indicatori conform
        OMFP nr. 1802/2014, cu modificările și completările ulterioare.
      </p>
      </div>
      <Footer />
    </main>
  );
}
