"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from "recharts";

const C = {
  bg: "#f4f5f7", card: "#ffffff", border: "#e8eaed",
  navy: "#0f2044", blue: "#1a56db", blueLight: "#e8f0fe",
  green: "#0e7245", greenLight: "#d4edda",
  red: "#b91c1c", redLight: "#fee2e2",
  text: "#1a1d23", muted: "#6b7280", subtle: "#9ca3af",
};

const MONTH_LABELS: Record<string, string> = {
  ian: "Ian", feb: "Feb", mar: "Mar", apr: "Apr", mai: "Mai", iun: "Iun",
  iul: "Iul", aug: "Aug", sep: "Sep", oct: "Oct", nov: "Nov", dec: "Dec",
};

type Row = {
  label: string;
  bold?: boolean;
  indent?: number;
  cat: "venituri" | "cheltuieli" | "deficit";
  cum26: number;
  cum25: number;
  var: number | null;
  [key: string]: any; // ian26, feb26, mar26, apr26, ian25, feb25, ...
};

type DataShape = {
  title: string;
  subtitle: string;
  sursa: string;
  pib2026: number;
  months: string[];
  lastUpdated: string;
  rows: Row[];
};

const fmt = (v: number | null | undefined, d = 1) =>
  v === null || v === undefined
    ? "—"
    : new Intl.NumberFormat("ro-RO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);

export default function ExecutieBugetaraPage() {
  const [data, setData] = useState<DataShape | null>(null);
  const [tab, setTab] = useState<"grafic" | "tabel">("grafic");
  const [catFilter, setCatFilter] = useState<"toate" | "venituri" | "cheltuieli" | "deficit">("toate");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/executie-bugetara_data.json")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  const monthly = useMemo(() => {
    if (!data) return [];
    const venituri = data.rows.find((r) => r.label === "VENITURI TOTALE");
    const cheltuieli = data.rows.find((r) => r.label === "CHELTUIELI TOTALE");
    const deficit = data.rows.find((r) => r.label.includes("EXCEDENT"));
    if (!venituri || !cheltuieli || !deficit) return [];
    return data.months.map((m) => ({
      luna: MONTH_LABELS[m] || m,
      "Venituri 2026": venituri[`${m}26`],
      "Cheltuieli 2026": cheltuieli[`${m}26`],
      "Deficit 2026": deficit[`${m}26`],
      "Venituri 2025": venituri[`${m}25`],
      "Cheltuieli 2025": cheltuieli[`${m}25`],
      "Deficit 2025": deficit[`${m}25`],
    }));
  }, [data]);

  const filteredRows = useMemo(() => {
    if (!data) return [];
    return data.rows.filter((r) => {
      if (catFilter !== "toate" && r.cat !== catFilter) return false;
      if (search && !r.label.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [data, catFilter, search]);

  if (!data) {
    return <div style={{ padding: 40, color: C.muted, fontFamily: "DM Sans, sans-serif" }}>Se încarcă datele…</div>;
  }

  const lastMonth = data.months[data.months.length - 1];
  const venituriTot = data.rows.find((r) => r.label === "VENITURI TOTALE")!;
  const cheltuieliTot = data.rows.find((r) => r.label === "CHELTUIELI TOTALE")!;
  const deficitTot = data.rows.find((r) => r.label.includes("EXCEDENT"))!;

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: C.bg, color: C.text, minHeight: "100vh", padding: "24px 16px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, color: C.navy, marginBottom: 4 }}>{data.title}</h1>
        <div style={{ fontSize: 13, color: C.muted, marginBottom: 2 }}>{data.subtitle}</div>
        <div style={{ fontSize: 12, color: C.subtle, marginBottom: 20 }}>{data.sursa}</div>

        {/* KPI cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
          {[
            { label: `Venituri cumulate (ian–${MONTH_LABELS[lastMonth]})`, v: venituriTot.cum26, prev: venituriTot.cum25, color: C.blue, bg: C.blueLight },
            { label: `Cheltuieli cumulate (ian–${MONTH_LABELS[lastMonth]})`, v: cheltuieliTot.cum26, prev: cheltuieliTot.cum25, color: C.red, bg: C.redLight },
            { label: `Deficit cumulat (ian–${MONTH_LABELS[lastMonth]})`, v: deficitTot.cum26, prev: deficitTot.cum25, color: deficitTot.cum26 < 0 ? C.red : C.green, bg: deficitTot.cum26 < 0 ? C.redLight : C.greenLight },
          ].map((k) => (
            <div key={k.label} style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>{k.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: k.color, fontFamily: "'DM Mono', monospace" }}>
                {fmt(k.v, 0)} <span style={{ fontSize: 12, fontWeight: 400, color: C.muted }}>mil. lei</span>
              </div>
              <div style={{ fontSize: 11, color: C.subtle, marginTop: 4 }}>
                {data.months[data.months.length - 1] && `vs ${fmt(k.prev, 0)} mil. lei în 2025`}
              </div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, borderBottom: `1px solid ${C.border}`, marginBottom: 16 }}>
          {[
            { id: "grafic", label: "📊 Grafic comparativ" },
            { id: "tabel", label: "⊞ Tabel date" },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              style={{
                padding: "10px 16px", background: "transparent", border: "none", cursor: "pointer",
                fontSize: 13, fontWeight: tab === t.id ? 600 : 400,
                color: tab === t.id ? C.blue : C.muted,
                borderBottom: tab === t.id ? `2px solid ${C.blue}` : "2px solid transparent",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "grafic" && (
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: C.navy }}>
              Venituri vs. Cheltuieli pe lună — 2026 vs. 2025 (mil. lei)
            </div>
            <ResponsiveContainer width="100%" height={360}>
              <BarChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="luna" tick={{ fontSize: 12, fill: C.muted }} />
                <YAxis tick={{ fontSize: 12, fill: C.muted }} />
                <Tooltip formatter={(v: number) => fmt(v, 0)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Venituri 2026" fill={C.blue} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Cheltuieli 2026" fill={C.red} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Venituri 2025" fill={C.blue} fillOpacity={0.35} radius={[4, 4, 0, 0]} />
                <Bar dataKey="Cheltuieli 2025" fill={C.red} fillOpacity={0.35} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>

            <div style={{ fontSize: 13, fontWeight: 600, margin: "24px 0 12px", color: C.navy }}>
              Evoluție deficit lunar (mil. lei)
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="luna" tick={{ fontSize: 12, fill: C.muted }} />
                <YAxis tick={{ fontSize: 12, fill: C.muted }} />
                <Tooltip formatter={(v: number) => fmt(v, 0)} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <ReferenceLine y={0} stroke={C.subtle} />
                <Line type="monotone" dataKey="Deficit 2026" stroke={C.red} strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="Deficit 2025" stroke={C.muted} strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {tab === "tabel" && (
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
            <div style={{ display: "flex", gap: 8, padding: 12, borderBottom: `1px solid ${C.border}`, flexWrap: "wrap" }}>
              <input
                placeholder="Caută..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ padding: "6px 10px", border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 13, flex: 1, minWidth: 160 }}
              />
              {["toate", "venituri", "cheltuieli", "deficit"].map((c) => (
                <button
                  key={c}
                  onClick={() => setCatFilter(c as any)}
                  style={{
                    padding: "6px 12px", borderRadius: 6, fontSize: 12, cursor: "pointer",
                    border: `1px solid ${catFilter === c ? C.blue : C.border}`,
                    background: catFilter === c ? C.blueLight : "transparent",
                    color: catFilter === c ? C.blue : C.muted,
                  }}
                >
                  {c}
                </button>
              ))}
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
                <thead>
                  <tr style={{ background: "#fafbfc", borderBottom: `1px solid ${C.border}` }}>
                    <th style={{ textAlign: "left", padding: "8px 10px" }}>Indicator</th>
                    {data.months.map((m) => (
                      <th key={m} style={{ textAlign: "right", padding: "8px 10px" }}>{MONTH_LABELS[m]} 26</th>
                    ))}
                    <th style={{ textAlign: "right", padding: "8px 10px", fontWeight: 700 }}>Cum. 26</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>Cum. 25</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>Var. %</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((r) => (
                    <tr key={r.label} style={{ borderBottom: `1px solid ${C.border}`, fontWeight: r.bold ? 700 : 400 }}>
                      <td style={{ padding: "7px 10px", paddingLeft: 10 + (r.indent || 0) * 14 }}>{r.label}</td>
                      {data.months.map((m) => (
                        <td key={m} style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace" }}>
                          {fmt(r[`${m}26`])}
                        </td>
                      ))}
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace", fontWeight: 700 }}>
                        {fmt(r.cum26)}
                      </td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace", color: C.muted }}>
                        {fmt(r.cum25)}
                      </td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace", color: (r.var ?? 0) >= 0 ? C.green : C.red }}>
                        {r.var === null ? "—" : `${r.var >= 0 ? "+" : ""}${fmt(r.var)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div style={{ fontSize: 11, color: C.subtle, marginTop: 16 }}>
          Date actualizate automat săptămânal din fișierele „Sinteza" publicate de Ministerul Finanțelor. Ultima actualizare: {data.lastUpdated}.
        </div>
      </div>
    </div>
  );
}
