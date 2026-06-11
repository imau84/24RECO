"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend, ReferenceLine,
} from "recharts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

// ---- tipuri ----
type Row = Record<string, string | number | null>;
type BnrData = { BP_DATA: Row[]; ISD_DATA: Row[]; DEP: Row[]; CR: Row[] };

type IndConfig = { label: string; color: string };
type TabKey = "balanta" | "isd" | "depozite" | "credite";

type TabConfig = {
  key: TabKey;
  title: string;
  dataKey: keyof BnrData;
  dateKey: string;            // 'p' (Ian 2020) sau 'd' (2013-01)
  unit: string;
  unitShort: string;
  decimals: number;
  yoyAsPercent: boolean;      // delta KPI: % (stocuri) sau absolut (fluxuri)
  inds: Record<string, IndConfig>;
  defaultActive: string[];
  defaultStartYear: number;
  note: string;
  estimated?: boolean;
};

const C = {
  navy: "#0f2044", blue: "#1a56db", amber: "#f59e0b",
  green: "#0e7245", red: "#b91c1c", bg: "#f4f5f7",
  border: "#e8eaed", text: "#1a1f2e", muted: "#5f6368",
};

const TABS: TabConfig[] = [
  {
    key: "balanta", title: "Balanța de plăți", dataKey: "BP_DATA",
    dateKey: "p", unit: "milioane EUR", unitShort: "mil. EUR", decimals: 0,
    yoyAsPercent: false,
    inds: {
      cc: { label: "Cont curent", color: "#1a56db" },
      b:  { label: "Bunuri", color: "#7c3aed" },
      s:  { label: "Servicii", color: "#0e7245" },
      vp: { label: "Venituri primare", color: "#c2410c" },
      vs: { label: "Venituri secundare", color: "#b91c1c" },
      ck: { label: "Cont capital", color: "#0891b2" },
    },
    defaultActive: ["cc", "b", "s"],
    defaultStartYear: 2020,
    note: "Serii lunare · Metodologie BPM6 · Valori nete în mil. EUR",
    estimated: true,
  },
  {
    key: "isd", title: "Investiții directe", dataKey: "ISD_DATA",
    dateKey: "d", unit: "milioane EUR", unitShort: "mil. EUR", decimals: 0,
    yoyAsPercent: false,
    inds: {
      idt: { label: "ISD total", color: "#1a56db" },
      res: { label: "Rezultat reinvestit", color: "#7c3aed" },
      nro: { label: "ISD excl. reinvestiri", color: "#0e7245" },
      ns:  { label: "Participații la capital (net)", color: "#c2410c" },
      nx:  { label: "Instrumente de natura datoriei (net)", color: "#b91c1c" },
    },
    defaultActive: ["idt", "res", "nro"],
    defaultStartYear: 2018,
    note: "Tranzacții · principiul direcțional · serii lunare · mil. EUR",
  },
  {
    key: "depozite", title: "Depozite", dataKey: "DEP",
    dateKey: "d", unit: "miliarde RON", unitShort: "mld. RON", decimals: 1,
    yoyAsPercent: true,
    inds: {
      gp: { label: "Gospodăriile populației", color: "#1a56db" },
      gpo: { label: "Gospodării — overnight", color: "#7c3aed" },
      gpt: { label: "Gospodării — la termen", color: "#0e7245" },
      sn: { label: "Societăți nefinanciare", color: "#c2410c" },
      ap: { label: "Administrație publică", color: "#b91c1c" },
    },
    defaultActive: ["gp", "sn", "ap"],
    defaultStartYear: 2015,
    note: "Depozite pe sectoare instituționale · solduri lunare · mld. RON",
  },
  {
    key: "credite", title: "Credite", dataKey: "CR",
    dateKey: "d", unit: "miliarde RON", unitShort: "mld. RON", decimals: 1,
    yoyAsPercent: true,
    inds: {
      g:   { label: "Credite gospodării", color: "#1a56db" },
      gc:  { label: "Credite consum", color: "#7c3aed" },
      glo: { label: "Credite locuințe", color: "#0e7245" },
      sn:  { label: "Societăți nefinanciare", color: "#c2410c" },
      ifn: { label: "Instituții fin. nebancare", color: "#b91c1c" },
      ap:  { label: "Administrație publică", color: "#0891b2" },
    },
    defaultActive: ["g", "gc", "glo", "sn"],
    defaultStartYear: 2015,
    note: "Credite pe sectoare instituționale (incl. neperformante) · solduri lunare · mld. RON",
  },
];

const fmt = (n: number | null | undefined, d = 0) =>
  n == null ? "—" : new Intl.NumberFormat("ro-RO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(n);
const fmtSig = (n: number | null | undefined, d = 0, suffix = "") =>
  n == null ? "—" : (n >= 0 ? "+" : "") + new Intl.NumberFormat("ro-RO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(n) + suffix;

function rowYear(r: Row, dateKey: string): number {
  const v = String(r[dateKey] ?? "");
  if (dateKey === "p") return parseInt(v.split(" ")[1] || "0", 10);
  return parseInt(v.substring(0, 4) || "0", 10);
}
function rowLabel(r: Row, dateKey: string): string {
  return String(r[dateKey] ?? "");
}

// ---- un tab de serii ----
function SeriesTab({ cfg, rows }: { cfg: TabConfig; rows: Row[] }) {
  const [active, setActive] = useState<string[]>(cfg.defaultActive);
  const [startYear, setStartYear] = useState<number>(cfg.defaultStartYear);
  const [chartType, setChartType] = useState<"line" | "bar">("line");

  const years = useMemo(() => {
    const ys = new Set<number>();
    rows.forEach((r) => ys.add(rowYear(r, cfg.dateKey)));
    return Array.from(ys).filter((y) => y > 0).sort();
  }, [rows, cfg.dateKey]);

  const filtered = useMemo(
    () => rows.filter((r) => rowYear(r, cfg.dateKey) >= startYear),
    [rows, startYear, cfg.dateKey]);

  const chartData = useMemo(
    () => filtered.map((r) => {
      const o: Record<string, string | number | null> = { name: rowLabel(r, cfg.dateKey) };
      Object.keys(cfg.inds).forEach((k) => { o[k] = (r[k] as number) ?? null; });
      return o;
    }),
    [filtered, cfg]);

  const last = rows[rows.length - 1];
  const prev12 = rows[rows.length - 13];

  const toggle = (k: string) =>
    setActive((a) => (a.indexOf(k) >= 0 ? a.filter((x) => x !== k) : a.concat(k)));

  const lastLabel = last ? rowLabel(last, cfg.dateKey) : "—";
  const tableRows = filtered.slice().reverse();
  const indKeys = Object.keys(cfg.inds);

  return (
    <div>
      <div className="note" style={cfg.estimated ? { background: "#fffbe6", borderColor: "#fde68a", color: "#92400e" } : undefined}>
        {cfg.estimated ? "⚠️ Date estimative — vor fi înlocuite cu seria oficială BNR la conectarea sursei automate. " : "ℹ️ "}
        {cfg.note} · Ultima lună: <strong>{lastLabel}</strong>
      </div>

      {/* KPI */}
      <div className="kpi-grid">
        {cfg.defaultActive.map((k) => {
          const v = last ? (last[k] as number) : null;
          const vp = prev12 ? (prev12[k] as number) : null;
          let delta: number | null = null;
          if (v != null && vp != null) {
            delta = cfg.yoyAsPercent ? (vp !== 0 ? ((v - vp) / vp) * 100 : null) : v - vp;
          }
          return (
            <div className="kpi-card" key={k}>
              <div className="kpi-label">{cfg.inds[k].label}</div>
              <div className="kpi-value">{fmt(v, cfg.decimals)}</div>
              <div className="kpi-sub">
                {cfg.unitShort} ·{" "}
                <span style={{ color: delta == null ? "#9aa0a6" : delta >= 0 ? C.green : C.red, fontWeight: 600 }}>
                  {cfg.yoyAsPercent ? fmtSig(delta, 1, "%") : fmtSig(delta, cfg.decimals)}
                </span>{" "}
                vs. an precedent
              </div>
            </div>
          );
        })}
      </div>

      {/* controale */}
      <div className="controls">
        <div className="ctrl-group">
          <span className="ctrl-label">Începând cu anul</span>
          <select value={startYear} onChange={(e) => setStartYear(parseInt(e.target.value, 10))}>
            {years.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <div className="ctrl-group">
          <span className="ctrl-label">Tip grafic</span>
          <div className="seg">
            <button className={`seg-btn ${chartType === "line" ? "active" : ""}`} onClick={() => setChartType("line")}>Linie</button>
            <button className={`seg-btn ${chartType === "bar" ? "active" : ""}`} onClick={() => setChartType("bar")}>Bare</button>
          </div>
        </div>
        <div className="ctrl-group" style={{ flex: 1, minWidth: 260 }}>
          <span className="ctrl-label">Indicatori</span>
          <div className="pills">
            {indKeys.map((k) => (
              <button key={k}
                className={`pill ${active.indexOf(k) >= 0 ? "on" : ""}`}
                style={active.indexOf(k) >= 0 ? { background: cfg.inds[k].color, borderColor: cfg.inds[k].color } : undefined}
                onClick={() => toggle(k)}>
                {cfg.inds[k].label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* grafic principal */}
      <div className="panel">
        <div className="panel-title">{cfg.title} — evoluție lunară ({cfg.unit})</div>
        <div style={{ width: "100%", height: 360 }}>
          <ResponsiveContainer>
            {chartType === "line" ? (
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} minTickGap={28} />
                <YAxis tick={{ fontSize: 10 }} width={56}
                  tickFormatter={(v: number) => fmt(v, 0)} />
                <Tooltip formatter={(v: number, n: string) => [fmt(v, cfg.decimals) + " " + cfg.unitShort, cfg.inds[n]?.label || n]} />
                <Legend formatter={(v: string) => cfg.inds[v]?.label || v} wrapperStyle={{ fontSize: 11 }} />
                <ReferenceLine y={0} stroke="#cbd5e1" />
                {active.map((k) => (
                  <Line key={k} type="monotone" dataKey={k} stroke={cfg.inds[k].color}
                    strokeWidth={2} dot={false} connectNulls />
                ))}
              </LineChart>
            ) : (
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} minTickGap={28} />
                <YAxis tick={{ fontSize: 10 }} width={56}
                  tickFormatter={(v: number) => fmt(v, 0)} />
                <Tooltip formatter={(v: number, n: string) => [fmt(v, cfg.decimals) + " " + cfg.unitShort, cfg.inds[n]?.label || n]} />
                <Legend formatter={(v: string) => cfg.inds[v]?.label || v} wrapperStyle={{ fontSize: 11 }} />
                <ReferenceLine y={0} stroke="#cbd5e1" />
                {active.map((k) => (
                  <Bar key={k} dataKey={k} fill={cfg.inds[k].color} />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>

      {/* tabel */}
      <div className="panel">
        <div className="panel-title">Date detaliate ({cfg.unitShort}) — cele mai recente luni</div>
        <div style={{ maxHeight: 420, overflow: "auto", border: `1px solid ${C.border}`, borderRadius: 8 }}>
          <table>
            <thead>
              <tr>
                <th className="l">Luna</th>
                {indKeys.map((k) => <th key={k}>{cfg.inds[k].label}</th>)}
              </tr>
            </thead>
            <tbody>
              {tableRows.map((r, i) => (
                <tr key={i}>
                  <td className="l">{rowLabel(r, cfg.dateKey)}</td>
                  {indKeys.map((k) => {
                    const v = r[k] as number | null;
                    return (
                      <td key={k} style={{ color: v != null && v < 0 ? C.red : undefined }}>
                        {fmt(v, cfg.decimals)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ fontSize: 10, color: "#9aa0a6", marginTop: 8 }}>
          Sursa: Banca Națională a României — Baza de date interactivă · {cfg.note}
        </div>
      </div>
    </div>
  );
}

// ---- pagina ----
export default function BnrPage() {
  const [data, setData] = useState<BnrData | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<TabKey>("balanta");

  useEffect(() => {
    fetch("/bnr_data.json")
      .then((r) => { if (!r.ok) throw new Error("nu pot încărca datele"); return r.json(); })
      .then((d: BnrData) => setData(d))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return (
    <main><Navbar />
      <div style={{ padding: 60, textAlign: "center", color: C.muted }}>
        Nu am putut încărca datele BNR. ({error})
      </div><Footer /></main>
  );
  if (!data) return (
    <main><Navbar />
      <div style={{ padding: 60, textAlign: "center", color: C.muted }}>Se încarcă datele…</div>
      <Footer /></main>
  );

  const cfg = TABS.filter((t) => t.key === tab)[0];
  const rows = data[cfg.dataKey] || [];

  return (
    <main>
      <style>{`
        *,*::before,*::after{box-sizing:border-box}
        .wrap{max-width:1180px;margin:0 auto;padding:0 24px}
        .note{background:#eff6ff;border:1px solid #bfdbfe;color:#1e40af;border-radius:8px;padding:10px 14px;font-size:12px;margin-bottom:14px;line-height:1.5}
        .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px}
        .kpi-card{background:#fff;border:1px solid ${C.border};border-radius:10px;padding:14px 18px}
        .kpi-label{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:${C.muted};margin-bottom:6px}
        .kpi-value{font-size:24px;font-weight:700;color:${C.navy};line-height:1;font-family:'DM Mono',monospace}
        .kpi-sub{font-size:11px;color:#9aa0a6;margin-top:5px}
        .controls{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start;background:#fff;border:1px solid ${C.border};border-radius:10px;padding:14px 16px;margin-bottom:16px}
        .ctrl-group{display:flex;flex-direction:column;gap:5px}
        .ctrl-label{font-size:10px;font-weight:600;color:${C.muted};text-transform:uppercase;letter-spacing:.05em}
        select{border:1px solid ${C.border};border-radius:6px;padding:6px 10px;font-size:12px;color:${C.text};background:#fff;outline:none;min-width:110px;font-family:inherit}
        select:focus{border-color:${C.blue};box-shadow:0 0 0 2px rgba(26,86,219,.15)}
        .seg{display:flex;gap:4px}
        .seg-btn{padding:6px 13px;font-size:11px;font-weight:500;cursor:pointer;color:${C.muted};background:#fff;border:1px solid ${C.border};border-radius:6px;font-family:inherit}
        .seg-btn.active{background:${C.navy};color:#fff;border-color:${C.navy}}
        .pills{display:flex;flex-wrap:wrap;gap:6px}
        .pill{padding:5px 11px;font-size:11px;font-weight:500;cursor:pointer;color:${C.muted};background:#fff;border:1px solid ${C.border};border-radius:20px;font-family:inherit}
        .pill.on{color:#fff}
        .tabs{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
        .tab-btn{padding:8px 16px;font-size:12px;font-weight:600;cursor:pointer;color:${C.muted};background:#fff;border:1px solid ${C.border};border-radius:8px 8px 0 0;border-bottom:none;font-family:inherit}
        .tab-btn.active{background:${C.navy};color:#fff;border-color:${C.navy}}
        .panel{background:#fff;border:1px solid ${C.border};border-radius:10px;padding:18px;margin-bottom:16px}
        .panel-title{font-size:13px;font-weight:700;color:${C.navy};margin-bottom:14px}
        table{width:100%;border-collapse:collapse;font-size:12px}
        thead tr{background:${C.navy};position:sticky;top:0}
        th{padding:9px 12px;font-weight:600;color:#fff;text-align:right;white-space:nowrap;font-size:11px}
        th.l{text-align:left}
        td{padding:7px 12px;text-align:right;color:${C.text};border-bottom:1px solid #f4f5f7;font-family:'DM Mono',monospace;white-space:nowrap}
        td.l{text-align:left;font-weight:500;font-family:'DM Sans',sans-serif}
        tbody tr:nth-child(odd){background:#fafafa}
        tbody tr:hover{background:#f0f7ff}
      `}</style>

      <Navbar />
      <div style={{ minHeight: "100vh", background: C.bg, fontFamily: "'DM Sans',system-ui,sans-serif", color: C.text, fontSize: 14, paddingBottom: 40 }}>
        <div style={{ background: "#fff", borderBottom: `1px solid ${C.border}` }}>
          <div className="wrap" style={{ padding: "10px 24px", fontSize: 12, color: "#9aa0a6" }}>
            <Link href="/" style={{ color: "#9aa0a6" }}>Acasă</Link>{" / "}
            <span style={{ color: C.text }}>Instituții publice</span>{" / BNR"}
          </div>
          <div className="wrap">
            <h1 style={{ fontFamily: "var(--font-display)", fontSize: 26, fontWeight: 700, color: C.navy, margin: "0 0 4px" }}>
              Banca Națională a României
            </h1>
            <div style={{ fontSize: 13, color: C.muted }}>
              Statistici oficiale BNR — serii lunare ·{" "}
              <a href="https://www.bnr.ro/1928-statistica" target="_blank" rel="noopener noreferrer" style={{ color: C.blue }}>
                Sursa: BNR.ro ↗
              </a>
            </div>
            <div className="tabs">
              {TABS.map((t) => (
                <button key={t.key}
                  className={`tab-btn ${tab === t.key ? "active" : ""}`}
                  onClick={() => setTab(t.key)}>
                  {t.title}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="wrap" style={{ paddingTop: 18 }}>
          <SeriesTab key={cfg.key} cfg={cfg} rows={rows} />
        </div>
      </div>
      <Footer />
    </main>
  );
}
