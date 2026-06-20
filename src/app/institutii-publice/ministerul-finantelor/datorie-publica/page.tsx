"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer, ComposedChart, BarChart, Bar, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";

const C = {
  bg: "#f4f5f7", card: "#ffffff", border: "#e8eaed",
  navy: "#0f2044", blue: "#1a56db", blueLight: "#e8f0fe",
  green: "#0e7245", greenLight: "#d4edda",
  red: "#b91c1c", redLight: "#fee2e2",
  orange: "#c2410c",
  text: "#1a1d23", muted: "#6b7280", subtle: "#9ca3af",
};

type Detail = {
  total?: (number | null)[];
  pctPIB: (number | null)[];
  termenScurt: (number | null)[];
  termenMediuLung: (number | null)[];
  numerarDepozite: (number | null)[];
  titluriStat: (number | null)[];
  imprumuturi: (number | null)[];
  lei: (number | null)[];
  euro: (number | null)[];
  usd: (number | null)[];
  altii: (number | null)[];
};

type DataShape = {
  periods: string[];
  pib: number[];
  total: number[];
  pctPIB: number[];
  interna: number[];
  externa: number[];
  detailed_from: string;
  total_detail: Detail;
  interna_detail: Detail;
  externa_detail: Detail;
  sursa: string;
  lastUpdated: string;
};

const fmt = (v: number | null | undefined, d = 1) =>
  v === null || v === undefined
    ? "—"
    : new Intl.NumberFormat("ro-RO", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);

const fmtPct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);

export default function DatoriePublicaPage() {
  const [data, setData] = useState<DataShape | null>(null);
  const [tab, setTab] = useState<"evolutie" | "structura" | "tabel">("evolutie");

  useEffect(() => {
    fetch("/datorie-publica_data.json")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  const evolChart = useMemo(() => {
    if (!data) return [];
    return data.periods.map((p, i) => ({
      an: p,
      "Datorie totală (mld. lei)": Math.round((data.total[i] / 1000) * 100) / 100,
      "% din PIB": data.pctPIB[i] ? Math.round(data.pctPIB[i] * 1000) / 10 : null,
    }));
  }, [data]);

  const intExtChart = useMemo(() => {
    if (!data) return [];
    return data.periods.map((p, i) => ({
      an: p,
      Internă: Math.round((data.interna[i] / 1000) * 100) / 100,
      Externă: Math.round((data.externa[i] / 1000) * 100) / 100,
    }));
  }, [data]);

  const detailIdx = useMemo(() => {
    if (!data) return [];
    return data.total_detail.pctPIB.map((_, i) => i);
  }, [data]);

  const structuraChart = useMemo(() => {
    if (!data) return [];
    const d = data.total_detail;
    return data.periods.filter((p) => p >= data.detailed_from).map((p, i) => ({
      an: p,
      "Titluri de stat": d.titluriStat[i] ? Math.round((d.titluriStat[i]! / 1000) * 100) / 100 : null,
      "Împrumuturi": d.imprumuturi[i] ? Math.round((d.imprumuturi[i]! / 1000) * 100) / 100 : null,
      "Numerar/depozite": d.numerarDepozite[i] ? Math.round((d.numerarDepozite[i]! / 1000) * 100) / 100 : null,
    }));
  }, [data]);

  const valutaChart = useMemo(() => {
    if (!data) return [];
    const d = data.total_detail;
    return data.periods.filter((p) => p >= data.detailed_from).map((p, i) => ({
      an: p,
      Lei: d.lei[i] ? Math.round((d.lei[i]! / 1000) * 100) / 100 : null,
      Euro: d.euro[i] ? Math.round((d.euro[i]! / 1000) * 100) / 100 : null,
      USD: d.usd[i] ? Math.round((d.usd[i]! / 1000) * 100) / 100 : null,
      Altele: d.altii[i] ? Math.round((d.altii[i]! / 1000) * 100) / 100 : null,
    }));
  }, [data]);

  if (!data) {
    return <div style={{ padding: 40, color: C.muted, fontFamily: "DM Sans, sans-serif" }}>Se încarcă datele…</div>;
  }

  const lastIdx = data.periods.length - 1;
  const prevYearIdx = data.periods.findIndex((p) => p === "2025");

  return (
    <div style={{ fontFamily: "'DM Sans', sans-serif", background: C.bg, color: C.text, minHeight: "100vh", padding: "24px 16px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <h1 style={{ fontSize: 18, fontWeight: 700, color: C.navy, marginBottom: 4 }}>
          Datoria Guvernamentală — Evoluție 2010–{data.periods[lastIdx]}
        </h1>
        <div style={{ fontSize: 12, color: C.subtle, marginBottom: 20 }}>{data.sursa}</div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>Datorie totală ({data.periods[lastIdx]})</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: C.navy, fontFamily: "'DM Mono', monospace" }}>
              {fmt(data.total[lastIdx] / 1000, 1)} <span style={{ fontSize: 12, fontWeight: 400, color: C.muted }}>mld. lei</span>
            </div>
            <div style={{ fontSize: 11, color: C.subtle, marginTop: 4 }}>{fmtPct(data.pctPIB[lastIdx])} din PIB</div>
          </div>
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>Datorie internă</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: C.blue, fontFamily: "'DM Mono', monospace" }}>
              {fmt(data.interna[lastIdx] / 1000, 1)} <span style={{ fontSize: 12, fontWeight: 400, color: C.muted }}>mld. lei</span>
            </div>
            <div style={{ fontSize: 11, color: C.subtle, marginTop: 4 }}>
              {fmt((data.interna[lastIdx] / data.total[lastIdx]) * 100, 0)}% din total
            </div>
          </div>
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 12, color: C.muted, marginBottom: 6 }}>Datorie externă</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: C.orange, fontFamily: "'DM Mono', monospace" }}>
              {fmt(data.externa[lastIdx] / 1000, 1)} <span style={{ fontSize: 12, fontWeight: 400, color: C.muted }}>mld. lei</span>
            </div>
            <div style={{ fontSize: 11, color: C.subtle, marginTop: 4 }}>
              {fmt((data.externa[lastIdx] / data.total[lastIdx]) * 100, 0)}% din total
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 4, borderBottom: `1px solid ${C.border}`, marginBottom: 16 }}>
          {[
            { id: "evolutie", label: "📈 Evoluție 2010–2026" },
            { id: "structura", label: "🧩 Structură (din 2020)" },
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

        {tab === "evolutie" && (
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: C.navy }}>
              Datorie guvernamentală totală (mld. lei) și % din PIB
            </div>
            <ResponsiveContainer width="100%" height={360}>
              <ComposedChart data={evolChart}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="an" tick={{ fontSize: 11, fill: C.muted }} />
                <YAxis yAxisId="left" tick={{ fontSize: 12, fill: C.muted }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12, fill: C.muted }} unit="%" />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar yAxisId="left" dataKey="Datorie totală (mld. lei)" fill={C.blue} radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="% din PIB" stroke={C.red} strokeWidth={2} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>

            <div style={{ fontSize: 13, fontWeight: 600, margin: "24px 0 12px", color: C.navy }}>
              Datorie internă vs. externă (mld. lei)
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={intExtChart}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="an" tick={{ fontSize: 11, fill: C.muted }} />
                <YAxis tick={{ fontSize: 12, fill: C.muted }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="Internă" stackId="1" stroke={C.blue} fill={C.blueLight} />
                <Area type="monotone" dataKey="Externă" stackId="1" stroke={C.orange} fill="#fde4d0" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {tab === "structura" && (
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: C.navy }}>
              Structură după instrument (mld. lei)
            </div>
            <div style={{ fontSize: 11, color: C.subtle, marginBottom: 12 }}>
              Defalcare detaliată disponibilă doar începând cu {data.detailed_from} (sursă: fișierul Excel lunar)
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={structuraChart}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="an" tick={{ fontSize: 11, fill: C.muted }} />
                <YAxis tick={{ fontSize: 12, fill: C.muted }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Titluri de stat" stackId="a" fill={C.blue} />
                <Bar dataKey="Împrumuturi" stackId="a" fill={C.orange} />
                <Bar dataKey="Numerar/depozite" stackId="a" fill={C.green} />
              </BarChart>
            </ResponsiveContainer>

            <div style={{ fontSize: 13, fontWeight: 600, margin: "24px 0 12px", color: C.navy }}>
              Structură după valută (mld. lei)
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={valutaChart}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                <XAxis dataKey="an" tick={{ fontSize: 11, fill: C.muted }} />
                <YAxis tick={{ fontSize: 12, fill: C.muted }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Lei" stackId="b" fill={C.green} />
                <Bar dataKey="Euro" stackId="b" fill={C.blue} />
                <Bar dataKey="USD" stackId="b" fill={C.orange} />
                <Bar dataKey="Altele" stackId="b" fill={C.subtle} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {tab === "tabel" && (
          <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
                <thead>
                  <tr style={{ background: "#fafbfc", borderBottom: `1px solid ${C.border}` }}>
                    <th style={{ textAlign: "left", padding: "8px 10px" }}>Perioadă</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>Total (mld. lei)</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>% PIB</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>Internă</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>Externă</th>
                    <th style={{ textAlign: "right", padding: "8px 10px" }}>PIB (mil. lei)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.periods.map((p, i) => (
                    <tr key={p} style={{ borderBottom: `1px solid ${C.border}` }}>
                      <td style={{ padding: "7px 10px", fontWeight: 600 }}>{p}</td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace" }}>{fmt(data.total[i] / 1000)}</td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace" }}>{fmtPct(data.pctPIB[i])}</td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace" }}>{fmt(data.interna[i] / 1000)}</td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace" }}>{fmt(data.externa[i] / 1000)}</td>
                      <td style={{ textAlign: "right", padding: "7px 10px", fontFamily: "'DM Mono', monospace", color: C.muted }}>{fmt(data.pib[i], 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div style={{ fontSize: 11, color: C.subtle, marginTop: 16 }}>
          Date actualizate automat săptămânal din fișierul Excel publicat de Trezorerie. Ultima actualizare: {data.lastUpdated}.
        </div>
      </div>
    </div>
  );
}
