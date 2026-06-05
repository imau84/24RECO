"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, CartesianGrid,
} from "recharts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

// ---- tipuri ----
type Pair = [string, number];
type DimByMotiv = { nou: Pair[]; uzat: Pair[] };
type MonthEntry = {
  label: string;
  total: number;
  nou: number;
  uzat: number;
  marca: DimByMotiv;
  judet: DimByMotiv;
  combustibil: DimByMotiv;
  detinator: DimByMotiv;
};
type ComertData = {
  meta: { source: string; category: string; updated: string };
  months: Record<string, MonthEntry>;
};

type Motiv = "toate" | "nou" | "uzat";
type DimKey = "marca" | "judet" | "combustibil" | "detinator";

const C = {
  navy: "#0f2044", blue: "#1a56db", amber: "#f59e0b",
  green: "#0e7245", red: "#b91c1c", bg: "#f4f5f7",
  border: "#e8eaed", text: "#1a1f2e", muted: "#5f6368",
};

const DIM_LABEL: Record<DimKey, string> = {
  marca: "Marcă", judet: "Județ", combustibil: "Combustibil", detinator: "Deținător",
};

const BRAND_COLORS = ["#1a56db", "#0f2044", "#2563eb", "#3b82f6", "#1d4ed8", "#60a5fa"];
const FUEL_COLORS: Record<string, string> = {
  MOTORINA: "#475569", BENZINA: "#1a56db", ELECTRIC: "#0e7245",
  "HIBRID 01": "#10b981", "HIBRID 02": "#059669", "HIBRID 04": "#34d399",
  "HIBRID 05": "#6ee7b7", "HIBRID 06": "#a7f3d0", "BENZINA+GPL": "#f59e0b",
  "BENZINA+GNC": "#fbbf24", GPL: "#d97706", GNC: "#b45309",
};
const PIE_FALLBACK = ["#1a56db", "#0f2044", "#0e7245", "#f59e0b", "#7c3aed",
  "#b91c1c", "#0891b2", "#475569", "#10b981", "#d97706", "#6366f1", "#ec4899"];

const fmt = (n: number) => new Intl.NumberFormat("ro-RO").format(Math.round(n));

// merge nou+uzat (sau întoarce direct seria pentru motivul cerut)
function dimSeries(entry: MonthEntry, dim: DimKey, motiv: Motiv): Pair[] {
  if (motiv === "nou") return entry[dim].nou;
  if (motiv === "uzat") return entry[dim].uzat;
  const m = new Map<string, number>();
  for (const [k, v] of [...entry[dim].nou, ...entry[dim].uzat]) m.set(k, (m.get(k) || 0) + v);
  return Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
}

// agregă mai multe luni într-o singură intrare (pentru "Toate 2026")
function mergeMonths(entries: MonthEntry[]): MonthEntry {
  const acc: MonthEntry = {
    label: "Toate lunile", total: 0, nou: 0, uzat: 0,
    marca: { nou: [], uzat: [] }, judet: { nou: [], uzat: [] },
    combustibil: { nou: [], uzat: [] }, detinator: { nou: [], uzat: [] },
  };
  const dims: DimKey[] = ["marca", "judet", "combustibil", "detinator"];
  const maps: Record<DimKey, { nou: Map<string, number>; uzat: Map<string, number> }> = {
    marca: { nou: new Map(), uzat: new Map() }, judet: { nou: new Map(), uzat: new Map() },
    combustibil: { nou: new Map(), uzat: new Map() }, detinator: { nou: new Map(), uzat: new Map() },
  };
  for (const e of entries) {
    acc.total += e.total; acc.nou += e.nou; acc.uzat += e.uzat;
    for (const d of dims) for (const mv of ["nou", "uzat"] as const)
      for (const [k, v] of e[d][mv]) maps[d][mv].set(k, (maps[d][mv].get(k) || 0) + v);
  }
  for (const d of dims) for (const mv of ["nou", "uzat"] as const)
    acc[d][mv] = Array.from(maps[d][mv].entries()).sort((a, b) => b[1] - a[1]);
  return acc;
}

function HBar({ data, color }: { data: Pair[]; color: string | ((i: number) => string) }) {
  const rows = data.slice(0, 12).map(([name, value]) => ({ name, value }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 26)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 28, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="#eef0f3" />
        <XAxis type="number" tick={{ fontSize: 10, fill: C.muted }} tickFormatter={fmt} />
        <YAxis type="category" dataKey="name" width={108}
          tick={{ fontSize: 10, fill: C.text }} interval={0} />
        <Tooltip formatter={(v: number) => fmt(v)} labelStyle={{ color: C.navy, fontWeight: 700 }}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}` }} />
        <Bar dataKey="value" radius={[0, 3, 3, 0]} barSize={16}>
          {rows.map((_, i) => (
            <Cell key={i} fill={typeof color === "function" ? color(i) : color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function Donut({ data }: { data: Pair[] }) {
  const top = data.slice(0, 8);
  const rest = data.slice(8).reduce((s, [, v]) => s + v, 0);
  const rows = [...top.map(([name, value]) => ({ name, value })),
  ...(rest > 0 ? [{ name: "Altele", value: rest }] : [])];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={rows} dataKey="value" nameKey="name" cx="50%" cy="50%"
          innerRadius={58} outerRadius={92} paddingAngle={2}>
          {rows.map((r, i) => (
            <Cell key={i} fill={FUEL_COLORS[r.name] || PIE_FALLBACK[i % PIE_FALLBACK.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => fmt(v)}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}` }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function Legend({ data }: { data: Pair[] }) {
  const top = data.slice(0, 8);
  const total = data.reduce((s, [, v]) => s + v, 0) || 1;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", marginTop: 10 }}>
      {top.map(([k, v], i) => (
        <div key={k} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: C.text }}>
          <span style={{ width: 9, height: 9, borderRadius: 2, background: FUEL_COLORS[k] || PIE_FALLBACK[i % PIE_FALLBACK.length] }} />
          {k} <span style={{ color: C.muted, fontFamily: "'DM Mono',monospace" }}>{(v / total * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

export default function ComertPage() {
  const [data, setData] = useState<ComertData | null>(null);
  const [error, setError] = useState("");
  const [monthKey, setMonthKey] = useState<string>("");
  const [motiv, setMotiv] = useState<Motiv>("toate");
  const [view, setView] = useState<"grafic" | "tabel">("grafic");
  const [tableDim, setTableDim] = useState<DimKey>("marca");
  const [sortDir, setSortDir] = useState(-1);

  useEffect(() => {
    fetch("/comert_data.json")
      .then((r) => { if (!r.ok) throw new Error("nu pot încărca datele"); return r.json(); })
      .then((d: ComertData) => {
        setData(d);
        const keys = Object.keys(d.months).sort().reverse();
        setMonthKey(keys[0] || "");
      })
      .catch((e) => setError(e.message));
  }, []);

  const monthKeys = useMemo(
    () => (data ? Object.keys(data.months).sort().reverse() : []),
    [data]);

  const entry = useMemo<MonthEntry | null>(() => {
    if (!data) return null;
    if (monthKey === "ALL") return mergeMonths(monthKeys.map((k) => data.months[k]));
    return data.months[monthKey] || null;
  }, [data, monthKey, monthKeys]);

  const trend = useMemo(
    () => monthKeys.slice().reverse().map((k) => ({
      name: data!.months[k].label.split(" ")[0].slice(0, 3),
      value: motiv === "nou" ? data!.months[k].nou
        : motiv === "uzat" ? data!.months[k].uzat : data!.months[k].total,
    })),
    [monthKeys, data, motiv]);

  if (error) return (
    <main><Navbar />
      <div style={{ padding: 60, textAlign: "center", color: C.muted }}>
        Nu am putut încărca datele de înmatriculări. ({error})
      </div><Footer /></main>
  );
  if (!data || !entry) return (
    <main><Navbar />
      <div style={{ padding: 60, textAlign: "center", color: C.muted }}>Se încarcă datele…</div>
      <Footer /></main>
  );

  const totalSel = motiv === "nou" ? entry.nou : motiv === "uzat" ? entry.uzat : entry.total;
  const elecSeries = dimSeries(entry, "combustibil", motiv);
  const elec = elecSeries
    .filter(([k]) => k === "ELECTRIC" || k.startsWith("HIBRID"))
    .reduce((s, [, v]) => s + v, 0);
  const topBrand = dimSeries(entry, "marca", motiv)[0];

  const tableData = dimSeries(entry, tableDim, motiv)
    .slice().sort((a, b) => sortDir * (a[1] - b[1]));
  const tableMax = Math.max(...tableData.map(([, v]) => v), 1);
  const tableTotal = tableData.reduce((s, [, v]) => s + v, 0) || 1;

  const KPI = ({ label, value, sub }: { label: string; value: string; sub?: string }) => (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );

  return (
    <main>
      <style>{`
        *,*::before,*::after{box-sizing:border-box}
        .wrap{max-width:1180px;margin:0 auto;padding:0 24px}
        .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px}
        .kpi-card{background:#fff;border:1px solid ${C.border};border-radius:10px;padding:14px 18px}
        .kpi-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:${C.muted};margin-bottom:6px}
        .kpi-value{font-size:24px;font-weight:700;color:${C.navy};line-height:1;font-family:'DM Mono',monospace}
        .kpi-sub{font-size:11px;color:#9aa0a6;margin-top:5px}
        .controls{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;background:#fff;border:1px solid ${C.border};border-radius:10px;padding:14px 16px;margin-bottom:16px}
        .ctrl-group{display:flex;flex-direction:column;gap:5px}
        .ctrl-label{font-size:10px;font-weight:600;color:${C.muted};text-transform:uppercase;letter-spacing:.05em}
        select{border:1px solid ${C.border};border-radius:6px;padding:6px 10px;font-size:12px;color:${C.text};background:#fff;outline:none;min-width:150px;font-family:inherit}
        select:focus{border-color:${C.blue};box-shadow:0 0 0 2px rgba(26,86,219,.15)}
        .seg{display:flex;gap:4px}
        .seg-btn{padding:6px 13px;font-size:11px;font-weight:500;cursor:pointer;color:${C.muted};background:#fff;border:1px solid ${C.border};border-radius:6px;font-family:inherit}
        .seg-btn.active{background:${C.navy};color:#fff;border-color:${C.navy}}
        .panel{background:#fff;border:1px solid ${C.border};border-radius:10px;padding:18px;margin-bottom:16px}
        .panel-title{font-size:13px;font-weight:700;color:${C.navy};margin-bottom:14px}
        .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
        @media(max-width:760px){.grid2{grid-template-columns:1fr}}
        table{width:100%;border-collapse:collapse;font-size:12px}
        thead tr{background:${C.navy}}
        th{padding:9px 12px;font-weight:600;color:#fff;text-align:right;white-space:nowrap;font-size:11px;cursor:pointer;user-select:none}
        th.l{text-align:left}
        td{padding:7px 12px;text-align:right;color:${C.text};border-bottom:1px solid #f4f5f7;font-family:'DM Mono',monospace}
        td.l{text-align:left;font-weight:500;font-family:'DM Sans',sans-serif}
        td.rank{color:#9aa0a6;text-align:center}
        tbody tr:nth-child(odd){background:#fafafa}
        tbody tr:hover{background:#f0f7ff}
        .total-row td{background:#fef9c3!important;border-top:2px solid ${C.amber};font-weight:700;color:${C.navy}}
        .mbar-bg{background:${C.border};border-radius:2px;height:5px;overflow:hidden;min-width:70px}
        .mbar-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,${C.blue},${C.navy})}
      `}</style>

      <Navbar />
      <div style={{ minHeight: "100vh", background: C.bg, fontFamily: "'DM Sans',system-ui,sans-serif", color: C.text, fontSize: 14, paddingBottom: 40 }}>
        {/* breadcrumb + header */}
        <div style={{ background: "#fff", borderBottom: `1px solid ${C.border}` }}>
          <div className="wrap" style={{ padding: "10px 24px", fontSize: 12, color: "#9aa0a6" }}>
            <Link href="/" style={{ color: "#9aa0a6" }}>Acasă</Link>{" / "}
            <span style={{ color: C.text }}>Comerț</span>{" / Înmatriculări auto"}
          </div>
          <div className="wrap" style={{ paddingBottom: 18 }}>
            <h1 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: C.navy, margin: "0 0 4px" }}>
              Înmatriculări autoturisme (M1, M1G)
            </h1>
            <div style={{ fontSize: 12, color: C.muted }}>
              Sursă: DGPCI / DRPCIV — date publice oficiale. Actualizat lunar (ziua 10).
              Ultima actualizare: {data.meta.updated}
            </div>
          </div>
        </div>

        <div className="wrap" style={{ paddingTop: 18 }}>
          {/* controls */}
          <div className="controls">
            <div className="ctrl-group">
              <span className="ctrl-label">Perioadă</span>
              <select value={monthKey} onChange={(e) => setMonthKey(e.target.value)}>
                {monthKeys.map((k) => <option key={k} value={k}>{data.months[k].label}</option>)}
                {monthKeys.length > 1 && <option value="ALL">Toate lunile</option>}
              </select>
            </div>
            <div className="ctrl-group">
              <span className="ctrl-label">Tip vehicul</span>
              <div className="seg">
                {([["toate", "Toate"], ["nou", "Noi"], ["uzat", "Rulate"]] as [Motiv, string][]).map(([m, l]) => (
                  <button key={m} className={`seg-btn${motiv === m ? " active" : ""}`} onClick={() => setMotiv(m)}>{l}</button>
                ))}
              </div>
            </div>
            <div className="ctrl-group" style={{ marginLeft: "auto" }}>
              <span className="ctrl-label">Vizualizare</span>
              <div className="seg">
                {([["grafic", "Grafic"], ["tabel", "Tabel"]] as ["grafic" | "tabel", string][]).map(([v, l]) => (
                  <button key={v} className={`seg-btn${view === v ? " active" : ""}`} onClick={() => setView(v)}>{l}</button>
                ))}
              </div>
            </div>
          </div>

          {/* KPIs */}
          <div className="kpi-grid">
            <KPI label={`Total ${entry.label}`} value={fmt(totalSel)} sub="autoturisme înmatriculate" />
            <KPI label="Vehicule noi" value={fmt(motiv === "uzat" ? 0 : entry.nou)} sub={`${(entry.nou / (entry.total || 1) * 100).toFixed(1)}% din total`} />
            <KPI label="Vehicule rulate" value={fmt(motiv === "nou" ? 0 : entry.uzat)} sub={`${(entry.uzat / (entry.total || 1) * 100).toFixed(1)}% din total`} />
            <KPI label="Electrice + hibride" value={fmt(elec)} sub={`${(elec / (totalSel || 1) * 100).toFixed(1)}% • top: ${topBrand ? topBrand[0] : "—"}`} />
          </div>

          {/* trend pe luni */}
          {monthKeys.length > 1 && (
            <div className="panel">
              <div className="panel-title">Evoluție lunară {new Date().getFullYear()} ({motiv === "toate" ? "total" : motiv === "nou" ? "noi" : "rulate"})</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={trend} margin={{ left: 4, right: 8, top: 4, bottom: 4 }}>
                  <CartesianGrid vertical={false} stroke="#eef0f3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: C.muted }} />
                  <YAxis tick={{ fontSize: 10, fill: C.muted }} tickFormatter={fmt} />
                  <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ fontSize: 12, borderRadius: 8, border: `1px solid ${C.border}` }} />
                  <Bar dataKey="value" fill={C.blue} radius={[3, 3, 0, 0]} barSize={36} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {view === "grafic" ? (
            <>
              <div className="grid2">
                <div className="panel">
                  <div className="panel-title">Top mărci — {entry.label}</div>
                  <HBar data={dimSeries(entry, "marca", motiv)} color={(i) => BRAND_COLORS[i % BRAND_COLORS.length]} />
                </div>
                <div className="panel">
                  <div className="panel-title">Top județe — {entry.label}</div>
                  <HBar data={dimSeries(entry, "judet", motiv)} color={C.navy} />
                </div>
              </div>
              <div className="grid2">
                <div className="panel">
                  <div className="panel-title">Distribuție pe combustibil</div>
                  <Donut data={dimSeries(entry, "combustibil", motiv)} />
                  <Legend data={dimSeries(entry, "combustibil", motiv)} />
                </div>
                <div className="panel">
                  <div className="panel-title">Tip deținător</div>
                  <Donut data={dimSeries(entry, "detinator", motiv)} />
                  <Legend data={dimSeries(entry, "detinator", motiv)} />
                </div>
              </div>
            </>
          ) : (
            <div className="panel">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
                <div className="panel-title" style={{ margin: 0 }}>Tabel detaliat — {entry.label}</div>
                <div className="seg">
                  {(Object.keys(DIM_LABEL) as DimKey[]).map((d) => (
                    <button key={d} className={`seg-btn${tableDim === d ? " active" : ""}`} onClick={() => setTableDim(d)}>{DIM_LABEL[d]}</button>
                  ))}
                </div>
              </div>
              <div style={{ overflowX: "auto", border: `1px solid ${C.border}`, borderRadius: 8 }}>
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: 36 }}>#</th>
                      <th className="l">{DIM_LABEL[tableDim]}</th>
                      <th onClick={() => setSortDir(-sortDir)}>Înmatriculări {sortDir < 0 ? "▼" : "▲"}</th>
                      <th>Pondere</th>
                      <th style={{ width: 120 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.map(([k, v], i) => (
                      <tr key={k}>
                        <td className="rank">{i + 1}</td>
                        <td className="l">{k}</td>
                        <td>{fmt(v)}</td>
                        <td>{(v / tableTotal * 100).toFixed(1)}%</td>
                        <td><div className="mbar-bg"><div className="mbar-fill" style={{ width: `${v / tableMax * 100}%` }} /></div></td>
                      </tr>
                    ))}
                    <tr className="total-row">
                      <td></td><td className="l">TOTAL</td><td>{fmt(tableTotal)}</td><td>100%</td><td></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div style={{ fontSize: 11, color: "#9aa0a6", marginTop: 8 }}>
            Sursă: DGPCI — Direcția Generală Permise de Conducere și Înmatriculări. Date individuale per înmatriculare,
            agregate pe marcă / județ / combustibil / deținător. Mărcile noi și rulate sunt unificate (alias-uri normalizate).
          </div>
        </div>
      </div>
      <Footer />
    </main>
  );
}
