"use client";
import { useState, useMemo } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ancpiMartie2026, totalNational, luna, sursa } from "@/data/ancpiData";

type ViewMode = "total" | "terenuri" | "unitati";

// Romania SVG map paths per judet
const JUDETE_PATHS: Record<string, string> = {
  "AB": "M 285 285 L 305 270 L 330 275 L 340 295 L 325 315 L 300 310 Z",
  "AR": "M 175 250 L 205 235 L 230 245 L 235 270 L 215 285 L 185 280 Z",
  "AG": "M 330 335 L 355 320 L 375 330 L 375 355 L 355 365 L 330 358 Z",
  "BC": "M 440 255 L 465 240 L 490 250 L 490 275 L 465 285 L 440 278 Z",
  "BH": "M 195 205 L 225 192 L 248 200 L 250 225 L 228 238 L 200 232 Z",
  "BN": "M 315 195 L 340 182 L 362 190 L 363 215 L 342 227 L 317 220 Z",
  "BT": "M 410 185 L 438 170 L 460 178 L 460 203 L 438 215 L 412 208 Z",
  "BR": "M 455 335 L 478 322 L 498 330 L 497 353 L 477 363 L 455 357 Z",
  "BV": "M 360 285 L 385 270 L 408 278 L 408 303 L 386 313 L 361 307 Z",
  "B":  "M 390 355 L 405 348 L 415 355 L 415 368 L 404 373 L 390 367 Z",
  "BZ": "M 425 305 L 450 292 L 472 300 L 472 323 L 450 333 L 425 327 Z",
  "CL": "M 420 375 L 445 362 L 465 370 L 465 393 L 444 403 L 420 396 Z",
  "CS": "M 210 315 L 238 302 L 260 310 L 260 335 L 238 345 L 211 338 Z",
  "CJ": "M 268 210 L 295 197 L 318 205 L 318 230 L 295 242 L 268 235 Z",
  "CT": "M 505 355 L 530 342 L 548 350 L 546 373 L 528 383 L 505 376 Z",
  "CV": "M 400 270 L 422 258 L 442 265 L 442 288 L 421 298 L 400 292 Z",
  "DB": "M 360 330 L 383 317 L 403 325 L 403 348 L 382 357 L 360 352 Z",
  "DJ": "M 270 365 L 298 352 L 320 360 L 320 383 L 297 393 L 270 386 Z",
  "GL": "M 480 300 L 505 287 L 526 295 L 526 318 L 504 328 L 480 322 Z",
  "GR": "M 360 378 L 385 365 L 406 373 L 406 396 L 384 406 L 360 399 Z",
  "GJ": "M 265 330 L 290 317 L 312 325 L 312 348 L 290 358 L 265 351 Z",
  "HR": "M 375 248 L 400 235 L 422 243 L 422 267 L 400 277 L 375 270 Z",
  "HD": "M 240 280 L 268 267 L 290 275 L 290 298 L 267 308 L 240 302 Z",
  "IL": "M 435 350 L 458 337 L 478 345 L 478 368 L 457 377 L 435 371 Z",
  "IS": "M 450 215 L 478 202 L 500 210 L 500 235 L 477 245 L 450 238 Z",
  "IF": "M 395 335 L 418 322 L 438 330 L 438 353 L 417 362 L 395 356 Z",
  "MM": "M 290 158 L 318 145 L 340 153 L 340 178 L 317 190 L 290 183 Z",
  "MH": "M 230 350 L 257 337 L 278 345 L 278 368 L 256 378 L 230 371 Z",
  "MS": "M 335 240 L 362 227 L 383 235 L 383 258 L 361 268 L 335 262 Z",
  "NT": "M 415 230 L 442 217 L 463 225 L 463 248 L 441 258 L 415 252 Z",
  "OT": "M 300 380 L 327 367 L 348 375 L 348 398 L 326 408 L 300 401 Z",
  "PH": "M 385 305 L 410 292 L 430 300 L 430 323 L 409 333 L 385 326 Z",
  "SJ": "M 248 192 L 273 179 L 295 187 L 295 212 L 272 224 L 248 217 Z",
  "SM": "M 232 158 L 260 145 L 283 153 L 283 178 L 260 190 L 232 183 Z",
  "SB": "M 298 295 L 325 282 L 347 290 L 347 313 L 325 323 L 298 317 Z",
  "SV": "M 360 175 L 390 162 L 413 170 L 413 195 L 389 207 L 360 200 Z",
  "TR": "M 330 395 L 356 382 L 376 390 L 376 413 L 355 422 L 330 415 Z",
  "TM": "M 165 285 L 195 272 L 218 280 L 218 305 L 194 315 L 165 308 Z",
  "TL": "M 500 320 L 528 307 L 548 315 L 547 338 L 527 348 L 500 341 Z",
  "VL": "M 305 330 L 330 317 L 352 325 L 352 348 L 329 358 L 305 351 Z",
  "VS": "M 475 240 L 502 227 L 523 235 L 522 258 L 501 268 L 475 262 Z",
  "VN": "M 455 268 L 480 255 L 500 263 L 500 286 L 479 296 L 455 290 Z",
};

function getColor(value: number, max: number, min: number): string {
  if (value === 0) return "#f3f4f6";
  const ratio = (value - min) / (max - min);
  // green scale: light to dark
  const r = Math.round(225 - ratio * 180);
  const g = Math.round(245 - ratio * 120);
  const b = Math.round(225 - ratio * 170);
  return `rgb(${r},${g},${b})`;
}

const PIE_COLORS = ["#1D9E75", "#378ADD", "#EF9F27", "#534AB7", "#E24B4A"];

export default function TranzactiiPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("total");
  const [hoveredJudet, setHoveredJudet] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<"judet" | "total" | "terenuri" | "unitati">("total");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const getValue = (d: typeof ancpiMartie2026[0]) => {
    if (viewMode === "total") return d.total;
    if (viewMode === "terenuri") return d.total_terenuri;
    return d.unitati_individuale;
  };

  const maxVal = useMemo(() => Math.max(...ancpiMartie2026.map(getValue)), [viewMode]);
  const minVal = useMemo(() => Math.min(...ancpiMartie2026.map(getValue)), [viewMode]);

  const hoveredData = ancpiMartie2026.find(d => d.cod === hoveredJudet);

  const top10 = [...ancpiMartie2026]
    .sort((a, b) => getValue(b) - getValue(a))
    .slice(0, 10);

  const pieData = [
    { name: "Extravilan agricol", value: totalNational.extravilan_agricol },
    { name: "Extravilan neagricol", value: totalNational.extravilan_neagricol },
    { name: "Intravilan cu constr.", value: totalNational.intravilan_cu_constructii },
    { name: "Intravilan fără constr.", value: totalNational.intravilan_fara_constructii },
    { name: "Unități individuale", value: totalNational.unitati_individuale },
  ];

  const sortedData = [...ancpiMartie2026].sort((a, b) => {
    let av = 0, bv = 0;
    if (sortBy === "judet") return sortDir === "asc" ? a.judet.localeCompare(b.judet) : b.judet.localeCompare(a.judet);
    if (sortBy === "total") { av = a.total; bv = b.total; }
    if (sortBy === "terenuri") { av = a.total_terenuri; bv = b.total_terenuri; }
    if (sortBy === "unitati") { av = a.unitati_individuale; bv = b.unitati_individuale; }
    return sortDir === "asc" ? av - bv : bv - av;
  });

  const handleSort = (col: typeof sortBy) => {
    if (sortBy === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortBy(col); setSortDir("desc"); }
  };

  const thStyle = (col: typeof sortBy) => ({
    padding: "10px 14px", textAlign: "left" as const,
    fontSize: 11, fontWeight: 500, textTransform: "uppercase" as const,
    letterSpacing: "0.6px", color: sortBy === col ? "#1D9E75" : "#9ca3af",
    borderBottom: "0.5px solid #e5e7eb", cursor: "pointer",
    whiteSpace: "nowrap" as const,
  });

  return (
    <main>
      <Navbar />

      {/* Breadcrumb */}
      <div style={{ padding: "10px 32px", fontSize: 12, color: "#9ca3af", borderBottom: "0.5px solid #e5e7eb" }}>
        <Link href="/" style={{ color: "#9ca3af" }}>Acasa</Link>
        {" / "}
        <Link href="/imobiliare" style={{ color: "#9ca3af" }}>Imobiliare</Link>
        {" / "}
        <span style={{ color: "#1a1a1a" }}>Tranzacții</span>
      </div>

      {/* Header */}
      <div style={{ padding: "32px 32px 24px", borderBottom: "0.5px solid #e5e7eb" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#EF9F27", marginBottom: 10 }}>
          Imobiliare · Tranzacții
        </p>
        <h1 style={{ fontSize: 32, marginBottom: 8 }}>Dinamică tranzacții — {luna}</h1>
        <p style={{ fontSize: 14, color: "#6b7280", maxWidth: 620 }}>
          Numărul cererilor de înscriere întemeiate pe acte juridice de transfer al dreptului de proprietate, înregistrate și soluționate lunar. Sursa: {sursa}.
        </p>
      </div>

      {/* Metric cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 12, padding: "24px 32px" }}>
        {[
          { val: totalNational.total.toLocaleString("ro-RO"), lbl: "Total imobile", color: "#1D9E75" },
          { val: totalNational.extravilan_agricol.toLocaleString("ro-RO"), lbl: "Extravilan agricol", color: "#378ADD" },
          { val: totalNational.intravilan_cu_constructii.toLocaleString("ro-RO"), lbl: "Intravilan cu constr.", color: "#EF9F27" },
          { val: totalNational.intravilan_fara_constructii.toLocaleString("ro-RO"), lbl: "Intravilan fără constr.", color: "#534AB7" },
          { val: totalNational.unitati_individuale.toLocaleString("ro-RO"), lbl: "Unități individuale", color: "#E24B4A" },
        ].map(m => (
          <div key={m.lbl} style={{ background: "#f9fafb", borderRadius: 8, padding: "14px 16px", borderLeft: `3px solid ${m.color}` }}>
            <div style={{ fontFamily: "var(--font-display)", fontSize: 20, fontWeight: 700, marginBottom: 2 }}>{m.val}</div>
            <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.7px" }}>{m.lbl}</div>
          </div>
        ))}
      </div>

      {/* MAP SECTION */}
      <section style={{ padding: "0 32px 32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600 }}>Hartă tranzacții pe județe</h2>
          <div style={{ display: "flex", gap: 8 }}>
            {(["total", "terenuri", "unitati"] as ViewMode[]).map(m => (
              <button key={m} onClick={() => setViewMode(m)} style={{
                fontSize: 12, padding: "5px 14px", borderRadius: 20, cursor: "pointer",
                border: "0.5px solid", transition: "all 0.15s",
                borderColor: viewMode === m ? "#EF9F27" : "#e5e7eb",
                background: viewMode === m ? "#EF9F27" : "#fff",
                color: viewMode === m ? "#fff" : "#6b7280",
              }}>
                {m === "total" ? "Total imobile" : m === "terenuri" ? "Terenuri" : "Unități individuale"}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>
          {/* SVG Map */}
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 16, background: "#fafafa", position: "relative" }}>
            <svg viewBox="140 140 420 300" style={{ width: "100%", height: 340 }}>
              {ancpiMartie2026.map(d => {
                const path = JUDETE_PATHS[d.cod];
                if (!path) return null;
                const val = getValue(d);
                const color = getColor(val, maxVal, minVal);
                const isHovered = hoveredJudet === d.cod;
                return (
                  <g key={d.cod}
                    onMouseEnter={() => setHoveredJudet(d.cod)}
                    onMouseLeave={() => setHoveredJudet(null)}
                    style={{ cursor: "pointer" }}
                  >
                    <path
                      d={path}
                      fill={color}
                      stroke={isHovered ? "#1D9E75" : "#fff"}
                      strokeWidth={isHovered ? 2 : 0.8}
                    />
                    <text
                      x={path.split(" ").filter((_, i) => i > 0 && i % 2 === 1).reduce((a, b) => a + parseFloat(b), 0) /
                        path.split(" ").filter((_, i) => i > 0 && i % 2 === 1).length || 0}
                      style={{ fontSize: 5.5, fill: "#374151", pointerEvents: "none", fontWeight: isHovered ? "bold" : "normal" }}
                      textAnchor="middle"
                    >
                      {d.cod}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Legend */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, justifyContent: "center" }}>
              <span style={{ fontSize: 11, color: "#9ca3af" }}>Mai puțin</span>
              {[0.1, 0.3, 0.5, 0.7, 0.9].map(r => (
                <div key={r} style={{
                  width: 24, height: 12, borderRadius: 2,
                  background: getColor(minVal + r * (maxVal - minVal), maxVal, minVal)
                }} />
              ))}
              <span style={{ fontSize: 11, color: "#9ca3af" }}>Mai mult</span>
            </div>
          </div>

          {/* Tooltip panel */}
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 20, background: "#fff" }}>
            {hoveredData ? (
              <>
                <div style={{ fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 700, marginBottom: 4 }}>
                  {hoveredData.judet}
                </div>
                <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.8px" }}>
                  {luna}
                </div>
                {[
                  { lbl: "Total imobile", val: hoveredData.total, color: "#1D9E75" },
                  { lbl: "Total terenuri", val: hoveredData.total_terenuri, color: "#378ADD" },
                  { lbl: "Extravilan agricol", val: hoveredData.extravilan_agricol, color: "#9ca3af" },
                  { lbl: "Extravilan neagricol", val: hoveredData.extravilan_neagricol, color: "#9ca3af" },
                  { lbl: "Intravilan cu constr.", val: hoveredData.intravilan_cu_constructii, color: "#9ca3af" },
                  { lbl: "Intravilan fără constr.", val: hoveredData.intravilan_fara_constructii, color: "#9ca3af" },
                  { lbl: "Unități individuale", val: hoveredData.unitati_individuale, color: "#534AB7" },
                ].map(r => (
                  <div key={r.lbl} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "0.5px solid #f3f4f6" }}>
                    <span style={{ fontSize: 12, color: "#6b7280" }}>{r.lbl}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: r.color }}>{r.val.toLocaleString("ro-RO")}</span>
                  </div>
                ))}
                <div style={{ marginTop: 12, fontSize: 11, color: "#9ca3af" }}>
                  Cotă națională: {((hoveredData.total / totalNational.total) * 100).toFixed(1)}%
                </div>
              </>
            ) : (
              <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "#9ca3af", fontSize: 13, textAlign: "center", gap: 8 }}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" strokeWidth="1.5"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
                Hover pe hartă pentru<br />detalii județ
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Two charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: "0 32px 32px" }}>

        {/* Top 10 bar chart */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Top 10 județe — {viewMode === "total" ? "Total imobile" : viewMode === "terenuri" ? "Terenuri" : "Unități individuale"}</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 16 }}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={top10} layout="vertical" margin={{ left: 80, right: 20, top: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="judet" tick={{ fontSize: 11, fill: "#374151" }} tickLine={false} axisLine={false} width={75} />
                <Tooltip
                  contentStyle={{ border: "0.5px solid #e5e7eb", borderRadius: 6, fontSize: 12 }}
                  formatter={(v: number) => [v.toLocaleString("ro-RO"), ""]}
                />
                <Bar dataKey={viewMode === "total" ? "total" : viewMode === "terenuri" ? "total_terenuri" : "unitati_individuale"}
                  fill="#EF9F27" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie chart */}
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Structură națională tranzacții</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 16 }}>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} dataKey="value" paddingAngle={2}>
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                </Pie>
                <Legend iconType="circle" iconSize={8}
                  formatter={(v) => <span style={{ fontSize: 11, color: "#6b7280" }}>{v}</span>} />
                <Tooltip
                  formatter={(v: number) => [v.toLocaleString("ro-RO"), ""]}
                  contentStyle={{ border: "0.5px solid #e5e7eb", borderRadius: 6, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Full data table */}
      <section style={{ padding: "0 32px 32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600 }}>Date complete pe județe</h2>
          <span style={{ fontSize: 12, color: "#9ca3af" }}>Click pe coloană pentru sortare</span>
        </div>
        <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb" }}>
                  <th onClick={() => handleSort("judet")} style={thStyle("judet")}>
                    Județ {sortBy === "judet" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Ext. Agricol</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Ext. Neagricol</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Intr. Cu Constr.</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Intr. Fără Constr.</th>
                  <th onClick={() => handleSort("terenuri")} style={thStyle("terenuri")}>
                    Total Terenuri {sortBy === "terenuri" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </th>
                  <th onClick={() => handleSort("unitati")} style={thStyle("unitati")}>
                    Unit. Individuale {sortBy === "unitati" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </th>
                  <th onClick={() => handleSort("total")} style={thStyle("total")}>
                    Total {sortBy === "total" ? (sortDir === "asc" ? "↑" : "↓") : ""}
                  </th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Cotă %</th>
                </tr>
              </thead>
              <tbody>
                {sortedData.map((row, i) => (
                  <tr key={row.judet}
                    style={{ borderBottom: "0.5px solid #e5e7eb", background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
                    <td style={{ padding: "9px 14px", fontWeight: 500 }}>{row.judet}</td>
                    <td style={{ padding: "9px 14px", color: "#6b7280" }}>{row.extravilan_agricol.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px", color: "#6b7280" }}>{row.extravilan_neagricol.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px", color: "#6b7280" }}>{row.intravilan_cu_constructii.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px", color: "#6b7280" }}>{row.intravilan_fara_constructii.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px", fontWeight: 500, color: "#378ADD" }}>{row.total_terenuri.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px", fontWeight: 500, color: "#534AB7" }}>{row.unitati_individuale.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px", fontWeight: 700 }}>{row.total.toLocaleString("ro-RO")}</td>
                    <td style={{ padding: "9px 14px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <div style={{ width: 40, height: 6, background: "#f3f4f6", borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${(row.total / 8641) * 100}%`, background: "#EF9F27", borderRadius: 3 }} />
                        </div>
                        <span style={{ fontSize: 11, color: "#9ca3af" }}>{((row.total / totalNational.total) * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
                {/* Total row */}
                <tr style={{ borderTop: "2px solid #e5e7eb", background: "#f9fafb", fontWeight: 700 }}>
                  <td style={{ padding: "10px 14px" }}>TOTAL NAȚIONAL</td>
                  <td style={{ padding: "10px 14px" }}>{totalNational.extravilan_agricol.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px" }}>{totalNational.extravilan_neagricol.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px" }}>{totalNational.intravilan_cu_constructii.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px" }}>{totalNational.intravilan_fara_constructii.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px", color: "#378ADD" }}>{totalNational.total_terenuri.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px", color: "#534AB7" }}>{totalNational.unitati_individuale.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px", color: "#1D9E75" }}>{totalNational.total.toLocaleString("ro-RO")}</td>
                  <td style={{ padding: "10px 14px" }}>100%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <div style={{ padding: "0 32px 16px", fontSize: 12, color: "#9ca3af" }}>
        {sursa}. Statisticile se raportează la numărul cererilor de înscriere care se întemeiază pe acte juridice de transfer al dreptului de proprietate, înregistrate și soluționate în luna de referință.
      </div>

      <Footer />
    </main>
  );
}
