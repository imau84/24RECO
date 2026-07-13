"use client";

import { useCallback, useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

// -------------------------------------------------------------- tipuri

type Firma = {
  cui: number;
  denumire: string;
  tip_unitate: string | null;
  localitate: string | null;
  strada: string | null;
  nr: string | null;
  data_inregistrare: string | null;
  telefon: string | null;
  judet_comert: string | null;
  nr_comert: string | null;
  an_comert: string | null;
  cod_postal: string | null;
  data_stare: string | null;
  stare: string | null;
  judet: string | null;
};

type Lista = {
  total: number;
  pageSize: number;
  page: number;
  rows: Pick<Firma, "cui" | "denumire" | "localitate" | "strada" | "nr" | "stare" | "data_inregistrare">[];
};

const API = "/api/firme";

// -------------------------------------------------------------- pagina

export default function DateIdentificarePage() {
  // --- cautare dupa CUI ---
  const [cuiInput, setCuiInput] = useState("");
  const [firma, setFirma] = useState<Firma | null>(null);
  const [firmaErr, setFirmaErr] = useState("");
  const [firmaLoading, setFirmaLoading] = useState(false);

  // --- filtre in cascada ---
  const [judete, setJudete] = useState<string[]>([]);
  const [judet, setJudet] = useState("");
  const [localitati, setLocalitati] = useState<string[]>([]);
  const [localitate, setLocalitate] = useState("");
  const [strazi, setStrazi] = useState<string[]>([]);
  const [strada, setStrada] = useState("");

  // --- rezultate lista ---
  const [lista, setLista] = useState<Lista | null>(null);
  const [listaLoading, setListaLoading] = useState(false);
  const [listaErr, setListaErr] = useState("");
  const [page, setPage] = useState(0);

  // ------------------------------------------------ cautare dupa CUI

  const cautaCui = useCallback(async (valoare?: string) => {
    const cui = (valoare ?? cuiInput).replace(/\D/g, "");
    if (!cui) return;
    setFirmaLoading(true);
    setFirmaErr("");
    setFirma(null);
    try {
      const r = await fetch(`${API}?cui=${cui}`);
      const data = await r.json();
      if (!r.ok) {
        setFirmaErr(data.error || "Eroare la căutare");
      } else {
        setFirma(data);
      }
    } catch {
      setFirmaErr("Nu am putut contacta serverul. Încearcă din nou.");
    } finally {
      setFirmaLoading(false);
    }
  }, [cuiInput]);

  // ------------------------------------------------ incarcare fatete

  useEffect(() => {
    fetch(`${API}?mode=judete`)
      .then(r => r.json())
      .then(d => Array.isArray(d) && setJudete(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLocalitati([]);
    setLocalitate("");
    setStrazi([]);
    setStrada("");
    setLista(null);
    setPage(0);
    if (!judet) return;
    fetch(`${API}?mode=localitati&judet=${encodeURIComponent(judet)}`)
      .then(r => r.json())
      .then(d => Array.isArray(d) && setLocalitati(d))
      .catch(() => {});
  }, [judet]);

  useEffect(() => {
    setStrazi([]);
    setStrada("");
    setPage(0);
    if (!judet || !localitate) return;
    fetch(`${API}?mode=strazi&judet=${encodeURIComponent(judet)}&localitate=${encodeURIComponent(localitate)}`)
      .then(r => r.json())
      .then(d => Array.isArray(d) && setStrazi(d))
      .catch(() => {});
  }, [judet, localitate]);

  // ------------------------------------------------ lista firmelor

  useEffect(() => {
    if (!judet) return;
    setListaLoading(true);
    setListaErr("");
    const params = new URLSearchParams({ mode: "lista", judet, page: String(page) });
    if (localitate) params.set("localitate", localitate);
    if (strada) params.set("strada", strada);
    fetch(`${API}?${params}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) setListaErr(d.error);
        else setLista(d);
      })
      .catch(() => setListaErr("Nu am putut încărca lista de firme."))
      .finally(() => setListaLoading(false));
  }, [judet, localitate, strada, page]);

  const totalPagini = lista ? Math.ceil(lista.total / lista.pageSize) : 0;

  const adresa = (f: { strada: string | null; nr: string | null }) =>
    [f.strada, f.nr].filter(Boolean).join(" nr. ") || "—";

  // ------------------------------------------------ randare

  return (
    <main>
      <Navbar />
      <div className="di-wrap">
      <style>{`
        .di-wrap { max-width: 1180px; margin: 0 auto; padding: 32px 24px 64px; color: #1a1a1a; }
        .di-wrap h1 { font-size: 1.7rem; margin: 0 0 4px; }
        .di-sub { color: #6b7280; margin: 0 0 28px; font-size: .95rem; }
        .di-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
                   padding: 20px; margin-bottom: 24px; }
        .di-card h2 { font-size: 1.05rem; margin: 0 0 14px; color: var(--green-dark, #0F6E56); }
        .di-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
        .di-field { display: flex; flex-direction: column; gap: 4px; min-width: 180px; flex: 1; }
        .di-field label { font-size: .8rem; color: #4b5563; font-weight: 600; }
        .di-field input, .di-field select {
          padding: 9px 10px; border: 1px solid #d1d5db; border-radius: 7px;
          font-size: .95rem; background: #fff; color: inherit; font-family: inherit; }
        .di-field input:focus, .di-field select:focus {
          outline: 2px solid var(--green, #1D9E75); outline-offset: 1px;
          border-color: var(--green, #1D9E75); }
        .di-btn { padding: 9px 20px; border: none; border-radius: 7px;
                  background: var(--green, #1D9E75); color: #fff; font-size: .95rem;
                  font-weight: 600; cursor: pointer; font-family: inherit; }
        .di-btn:hover { background: var(--green-dark, #0F6E56); }
        .di-btn:disabled { background: #9ca3af; cursor: default; }
        .di-err { color: #b91c1c; font-size: .9rem; margin-top: 10px; }
        .di-info { color: #6b7280; font-size: .9rem; margin-top: 10px; }
        .di-detail { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
                     gap: 12px 20px; margin-top: 16px; }
        .di-detail dt { font-size: .75rem; text-transform: uppercase; letter-spacing: .04em;
                        color: #6b7280; margin-bottom: 2px; }
        .di-detail dd { margin: 0; font-size: .95rem; }
        .di-detail .full { grid-column: 1 / -1; }
        .di-detail .full dd { font-size: 1.1rem; font-weight: 700; }
        .di-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: .9rem; }
        .di-table th { text-align: left; padding: 8px 10px; background: var(--green-light, #E1F5EE);
                       color: var(--green-dark, #0F6E56); font-size: .78rem;
                       text-transform: uppercase; letter-spacing: .04em; }
        .di-table td { padding: 8px 10px; border-top: 1px solid #e5e7eb; }
        .di-table tbody tr { cursor: pointer; }
        .di-table tbody tr:hover { background: var(--green-light, #E1F5EE); }
        .di-cui-link { color: var(--green-dark, #0F6E56); font-weight: 600; }
        .di-pager { display: flex; gap: 10px; align-items: center; margin-top: 14px;
                    font-size: .9rem; color: #4b5563; }
        .di-pager button { padding: 6px 14px; border: 1px solid #d1d5db; background: #fff;
                           border-radius: 7px; cursor: pointer; font-size: .9rem;
                           font-family: inherit; }
        .di-pager button:disabled { opacity: .45; cursor: default; }
        .di-total { font-weight: 600; color: var(--green-dark, #0F6E56); }
        @media (max-width: 640px) {
          .di-table .hide-sm { display: none; }
          .di-field { min-width: 140px; }
        }
      `}</style>

      <h1>Date de identificare plătitori</h1>
      <p className="di-sub">
        Registrul ANAF al plătitorilor, ediția iunie 2026 — firmele cu situații financiare
        depuse pentru 2025. Caută după CUI sau explorează pe județ, localitate și stradă.
      </p>

      {/* ------------------------------------------------ cautare CUI */}
      <section className="di-card">
        <h2>Căutare după CUI</h2>
        <div className="di-row">
          <div className="di-field" style={{ maxWidth: 260 }}>
            <label htmlFor="di-cui">Cod unic de identificare</label>
            <input
              id="di-cui"
              inputMode="numeric"
              placeholder="ex. 4440511"
              value={cuiInput}
              onChange={e => setCuiInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && cautaCui()}
            />
          </div>
          <button className="di-btn" onClick={() => cautaCui()} disabled={firmaLoading || !cuiInput.trim()}>
            {firmaLoading ? "Caut..." : "Caută firma"}
          </button>
        </div>
        {firmaErr && <p className="di-err">{firmaErr}</p>}

        {firma && (
          <dl className="di-detail">
            <div className="full">
              <dt>Denumire</dt>
              <dd>{firma.denumire}</dd>
            </div>
            <div><dt>CUI</dt><dd>{firma.cui}</dd></div>
            <div><dt>Nr. Registrul Comerțului</dt>
              <dd>{firma.nr_comert ? `${firma.judet_comert || ""}${firma.nr_comert}/${firma.an_comert || ""}` : "—"}</dd></div>
            <div><dt>Tip unitate</dt><dd>{firma.tip_unitate || "—"}</dd></div>
            <div><dt>Stare</dt><dd>{firma.stare || "—"}</dd></div>
            <div><dt>Data stării</dt><dd>{firma.data_stare || "—"}</dd></div>
            <div><dt>Data înregistrării</dt><dd>{firma.data_inregistrare || "—"}</dd></div>
            <div><dt>Județ</dt><dd>{firma.judet || "—"}</dd></div>
            <div><dt>Localitate</dt><dd>{firma.localitate || "—"}</dd></div>
            <div><dt>Adresă</dt><dd>{adresa(firma)}</dd></div>
            <div><dt>Cod poștal</dt><dd>{firma.cod_postal || "—"}</dd></div>
            <div><dt>Telefon</dt><dd>{firma.telefon || "—"}</dd></div>
          </dl>
        )}
      </section>

      {/* ------------------------------------------------ filtre cascada */}
      <section className="di-card">
        <h2>Explorare pe județ, localitate și stradă</h2>
        <div className="di-row">
          <div className="di-field">
            <label htmlFor="di-judet">Județ</label>
            <select id="di-judet" value={judet} onChange={e => setJudet(e.target.value)}>
              <option value="">— alege județul —</option>
              {judete.map(j => <option key={j} value={j}>{j}</option>)}
            </select>
          </div>
          <div className="di-field">
            <label htmlFor="di-loc">Localitate</label>
            <select id="di-loc" value={localitate} disabled={!judet}
                    onChange={e => setLocalitate(e.target.value)}>
              <option value="">{judet ? "— toate localitățile —" : "alege întâi județul"}</option>
              {localitati.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>
          <div className="di-field">
            <label htmlFor="di-strada">Stradă</label>
            <input id="di-strada" list="di-strazi" disabled={!localitate}
                   placeholder={localitate ? "toate străzile — tastează pentru a filtra" : "alege întâi localitatea"}
                   value={strada}
                   onChange={e => { setStrada(e.target.value); setPage(0); }} />
            <datalist id="di-strazi">
              {strazi.map(s => <option key={s} value={s} />)}
            </datalist>
          </div>
        </div>

        {!judet && <p className="di-info">Alege un județ pentru a vedea firmele.</p>}
        {listaErr && <p className="di-err">{listaErr}</p>}
        {listaLoading && <p className="di-info">Încarc firmele...</p>}

        {lista && !listaLoading && (
          <>
            <p className="di-info">
              <span className="di-total">{lista.total.toLocaleString("ro-RO")}</span> firme găsite
              {localitate ? ` în ${localitate}` : ` în ${judet}`}
              {strada ? `, ${strada}` : ""}. Apasă pe o firmă pentru fișa completă.
            </p>
            <table className="di-table">
              <thead>
                <tr>
                  <th>CUI</th>
                  <th>Denumire</th>
                  <th className="hide-sm">Localitate</th>
                  <th className="hide-sm">Adresă</th>
                  <th>Stare</th>
                  <th className="hide-sm">Înregistrată</th>
                </tr>
              </thead>
              <tbody>
                {lista.rows.map(f => (
                  <tr key={f.cui}
                      onClick={() => { setCuiInput(String(f.cui)); cautaCui(String(f.cui));
                                       window.scrollTo({ top: 0, behavior: "smooth" }); }}>
                    <td className="di-cui-link">{f.cui}</td>
                    <td>{f.denumire}</td>
                    <td className="hide-sm">{f.localitate || "—"}</td>
                    <td className="hide-sm">{adresa(f)}</td>
                    <td>{f.stare || "—"}</td>
                    <td className="hide-sm">{f.data_inregistrare || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {totalPagini > 1 && (
              <div className="di-pager">
                <button onClick={() => setPage(p => p - 1)} disabled={page === 0}>← Înapoi</button>
                <span>Pagina {page + 1} din {totalPagini.toLocaleString("ro-RO")}</span>
                <button onClick={() => setPage(p => p + 1)}
                        disabled={page + 1 >= totalPagini}>Înainte →</button>
              </div>
            )}
          </>
        )}
      </section>

      <p className="di-info">
        Sursa datelor: ANAF / data.gov.ro — „Date de identificare plătitori”, actualizat iunie 2026.
        Sunt afișate entitățile care au depus situații financiare pentru exercițiul 2025.
      </p>
      </div>
      <Footer />
    </main>
  );
}
