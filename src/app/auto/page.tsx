"use client";
import { useState } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { monthlyData, topBrands, topJudete, combustibilData } from "@/data/autoData";

const years = ["2024", "2025", "Toti"];

const MetricCard = ({ val, lbl, delta, up }: { val: string; lbl: string; delta: string; up: boolean }) => (
  <div style={{ background: "#f9fafb", borderRadius: 8, padding: "14px 16px" }}>
    <div style={{ fontFamily: "var(--font-display)", fontSize: 22, fontWeight: 700, marginBottom: 2 }}>{val}</div>
    <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.8px" }}>{lbl}</div>
    <div style={{ fontSize: 11, marginTop: 4, color: up ? "#1D9E75" : "#E24B4A" }}>{delta}</div>
  </div>
);

export default function AutoPage() {
  const [year, setYear] = useState("2025");

  const filtered = year === "Toti" ? monthlyData : monthlyData.filter(d => d.luna.includes(year.slice(2)));
  const maxJudet = topJudete[0].unitati;

  return (
    <main>
      <Navbar />

      {/* Breadcrumb */}
      <div style={{ padding: "10px 32px", fontSize: 12, color: "#9ca3af", borderBottom: "0.5px solid #e5e7eb" }}>
        <Link href="/" style={{ color: "#9ca3af" }}>Acasa</Link>
        {" / "}
        <span style={{ color: "#1a1a1a" }}>Auto</span>
        {" / Inmatriculari"}
      </div>

      {/* Header */}
      <div style={{ padding: "32px 32px 24px", borderBottom: "0.5px solid #e5e7eb" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "var(--green)", marginBottom: 10 }}>Sector Auto</p>
        <h1 style={{ fontSize: 32, marginBottom: 8 }}>Inmatriculari vehicule noi</h1>
        <p style={{ fontSize: 14, color: "#6b7280", maxWidth: 560 }}>
          Date lunare oficiale privind inmatricularile de vehicule noi in Romania. Sursa: DRPCIV / RAR. Actualizat lunar.
        </p>
      </div>

      {/* Filter bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 32px", borderBottom: "0.5px solid #e5e7eb", background: "#f9fafb" }}>
        <span style={{ fontSize: 12, color: "#6b7280", marginRight: 4 }}>Perioada:</span>
        {years.map(y => (
          <button key={y} onClick={() => setYear(y)} style={{
            fontSize: 12, padding: "5px 14px", borderRadius: 20, cursor: "pointer",
            border: "0.5px solid", transition: "all 0.15s",
            borderColor: year === y ? "var(--green)" : "#e5e7eb",
            background: year === y ? "var(--green)" : "#fff",
            color: year === y ? "#fff" : "#6b7280",
          }}>{y}</button>
        ))}
        <div style={{ flex: 1 }} />
        <a
          href="/api/auto-csv"
          style={{ fontSize: 12, padding: "6px 14px", border: "0.5px solid #d1d5db", borderRadius: 6, background: "#fff", color: "#374151", cursor: "pointer" }}
        >
          ↓ Descarca CSV
        </a>
      </div>

      {/* Metrics */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, padding: "24px 32px" }}>
        <MetricCard val="32.481" lbl="Inmatriculari martie" delta="▲ 6.2% vs feb" up={true} />
        <MetricCard val="87.344" lbl="Total 2025 (YTD)" delta="▲ 3.8% vs 2024" up={true} />
        <MetricCard val="18.4%" lbl="Cota Dacia" delta="▼ 1.1% vs feb" up={false} />
        <MetricCard val="28.3%" lbl="Vehicule electrice+hibrid" delta="▲ 4.2% vs feb" up={true} />
      </div>

      {/* Monthly bar chart */}
      <section style={{ padding: "0 32px 32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600 }}>Evolutie lunara</h2>
          <span style={{ fontSize: 12, color: "#9ca3af" }}>Total inmatriculari / luna</span>
        </div>
        <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 20 }}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={filtered} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="luna" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ border: "0.5px solid #e5e7eb", borderRadius: 6, fontSize: 12 }}
                formatter={(v: number) => [v.toLocaleString("ro-RO"), "Total"]}
              />
              <Bar dataKey="total" fill="#1D9E75" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Two column: brands + fuel */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: "0 32px 32px" }}>

        {/* Top brands */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Top marci — Martie 2025</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 18 }}>
            {topBrands.map(b => (
              <div key={b.marca} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 12, color: "#6b7280", width: 80, textAlign: "right", flexShrink: 0 }}>{b.marca}</span>
                <div style={{ flex: 1, height: 14, background: "#f3f4f6", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(b.cota / 18.4) * 100}%`, background: "var(--green)", borderRadius: 3 }} />
                </div>
                <span style={{ fontSize: 12, fontWeight: 500, width: 44, flexShrink: 0 }}>{b.cota}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Fuel type pie */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Tip combustibil</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 18 }}>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={combustibilData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" paddingAngle={2}>
                  {combustibilData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Legend
                  iconType="circle" iconSize={8}
                  formatter={(value) => <span style={{ fontSize: 12, color: "#6b7280" }}>{value}</span>}
                />
                <Tooltip formatter={(v: number) => [`${v}%`, ""]} contentStyle={{ fontSize: 12, border: "0.5px solid #e5e7eb", borderRadius: 6 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Two column: counties + stacked chart */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: "0 32px 32px" }}>

        {/* Top judete */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Top judete — Martie 2025</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 18 }}>
            {topJudete.map(j => (
              <div key={j.judet} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span style={{ fontSize: 12, color: "#6b7280", width: 80, textAlign: "right", flexShrink: 0 }}>{j.judet}</span>
                <div style={{ flex: 1, height: 14, background: "#f3f4f6", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${(j.unitati / maxJudet) * 100}%`, background: "#378ADD", borderRadius: 3 }} />
                </div>
                <span style={{ fontSize: 12, fontWeight: 500, width: 44, flexShrink: 0 }}>{j.unitati.toLocaleString("ro-RO")}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stacked combustibil trend */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Trend combustibil 2025</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 18 }}>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={filtered.slice(-6)} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="luna" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ border: "0.5px solid #e5e7eb", borderRadius: 6, fontSize: 11 }} />
                <Bar dataKey="hibrid" stackId="a" fill="#1D9E75" name="Hibrid" />
                <Bar dataKey="electrice" stackId="a" fill="#534AB7" name="Electric" />
                <Bar dataKey="benzina" stackId="a" fill="#EF9F27" name="Benzina" />
                <Bar dataKey="diesel" stackId="a" fill="#378ADD" name="Diesel" radius={[3,3,0,0]} name="Diesel" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Table */}
      <section style={{ padding: "0 32px 32px" }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Detaliu lunar 2025</h2>
        <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                {["Luna", "Total", "Electrice", "Hibrid", "Benzina", "Diesel", "vs luna prec."].map(h => (
                  <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.6px", color: "#9ca3af", borderBottom: "0.5px solid #e5e7eb" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.slice().reverse().map((row, i) => {
                const prev = filtered[filtered.length - 2 - i];
                const delta = prev ? ((row.total - prev.total) / prev.total * 100) : null;
                return (
                  <tr key={row.luna} style={{ borderBottom: "0.5px solid #e5e7eb" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "#f9fafb")}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  >
                    <td style={{ padding: "10px 14px", fontWeight: 500 }}>{row.luna}</td>
                    <td style={{ padding: "10px 14px" }}>{row.total.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "10px 14px" }}>{row.electrice.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "10px 14px" }}>{row.hibrid.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "10px 14px" }}>{row.benzina.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "10px 14px" }}>{row.diesel.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "10px 14px" }}>
                      {delta !== null && (
                        <span style={{
                          fontSize: 11, padding: "2px 7px", borderRadius: 4,
                          background: delta >= 0 ? "#E1F5EE" : "#FCEBEB",
                          color: delta >= 0 ? "#085041" : "#501313",
                        }}>
                          {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Source note */}
      <div style={{ padding: "0 32px 16px", fontSize: 12, color: "#9ca3af" }}>
        Sursa: DRPCIV, RAR — date publice oficiale. Ultima actualizare: 1 Apr 2025. Datele sunt orientative, pot exista diferente minore fata de comunicatele oficiale.
      </div>

      <Footer />
    </main>
  );
}
