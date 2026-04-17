"use client";
import { useState, useMemo, useEffect, useRef } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from "recharts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { ancpiMartie2026, totalNational, luna, sursa } from "@/data/ancpiData";

type ViewMode = "total" | "terenuri" | "unitati";

const NAME_MAP: Record<string, string> = {
  "Alba": "AB", "Arad": "AR", "Arges": "AG", "Bacau": "BC",
  "Bihor": "BH", "Bistrita-Nasaud": "BN", "Botosani": "BT",
  "Braila": "BR", "Brasov": "BV", "Bucuresti": "B",
  "Buzau": "BZ", "Calarasi": "CL", "Caras-Severin": "CS",
  "Cluj": "CJ", "Constanta": "CT", "Covasna": "CV",
  "Dambovita": "DB", "Dolj": "DJ", "Galati": "GL",
  "Giurgiu": "GR", "Gorj": "GJ", "Harghita": "HR",
  "Hunedoara": "HD", "Ialomita": "IL", "Iasi": "IS",
  "Ilfov": "IF", "Maramures": "MM", "Mehedinti": "MH",
  "Mures": "MS", "Neamt": "NT", "Olt": "OT", "Prahova": "PH",
  "Salaj": "SJ", "Satu Mare": "SM", "Sibiu": "SB",
  "Suceava": "SV", "Teleorman": "TR", "Timis": "TM",
  "Tulcea": "TL", "Vaslui": "VS", "Valcea": "VL", "Vrancea": "VN",
};

function getColor(value: number, max: number): string {
  if (!value || max === 0) return "#f3f4f6";
  const colors = ["#EAF3DE","#C0DD97","#97C459","#639922","#3B6D11","#27500A","#173404"];
  const idx = Math.min(Math.floor((value / max) * colors.length), colors.length - 1);
  return colors[idx];
}

const PIE_COLORS = ["#1D9E75","#378ADD","#EF9F27","#534AB7","#E24B4A"];

function RomaniaMap({ ancpiData, viewMode, getValue, maxVal }: {
  ancpiData: typeof ancpiMartie2026;
  viewMode: ViewMode;
  getValue: (d: typeof ancpiMartie2026[0]) => number;
  maxVal: number;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredCod, setHoveredCod] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{x: number; y: number; cod: string} | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function draw() {
      try {
        const [d3, topojson] = await Promise.all([
          import("d3"),
          import("topojson-client"),
        ]);
        const topo = await fetch(
          "https://cdn.jsdelivr.net/npm/datamaps@0.5.10/src/js/data/rou.topo.json"
        ).then(r => r.json());
        if (cancelled || !svgRef.current) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();

        const w = svgRef.current.clientWidth || 680;
        const h = 360;

        const proj = d3.geoMercator().center([25, 45.8]).scale(w * 3.0).translate([w / 2, h * 0.55]);
        const pathGen = d3.geoPath(proj);
        const key = Object.keys(topo.objects)[0];
        const features = (topojson.feature(topo, topo.objects[key] as any) as any).features;

        svg.selectAll<SVGPathElement, any>("path")
          .data(features)
          .join("path")
          .attr("d", (d: any) => pathGen(d) || "")
          .attr("stroke", "#fff")
          .attr("stroke-width", "0.8")
          .style("cursor", "pointer")
          .attr("fill", (d: any) => {
            const raw: string = d.properties?.NAME_1 || "";
            const cod = NAME_MAP[raw] || "";
            const row = ancpiData.find(r => r.cod === cod);
            return row ? getColor(getValue(row), maxVal) : "#f3f4f6";
          })
          .on("mouseenter", function(this: SVGPathElement, event: MouseEvent, d: any) {
            d3.select(this).attr("stroke", "#1D9E75").attr("stroke-width", "2");
            const raw: string = d.properties?.NAME_1 || "";
            const cod = NAME_MAP[raw] || "";
            const rect = svgRef.current!.getBoundingClientRect();
            setHoveredCod(cod);
            setTooltip({ x: event.clientX - rect.left, y: event.clientY - rect.top, cod });
          })
          .on("mousemove", function(this: SVGPathElement, event: MouseEvent) {
            const rect = svgRef.current!.getBoundingClientRect();
            setTooltip(prev => prev ? { ...prev, x: event.clientX - rect.left, y: event.clientY - rect.top } : null);
          })
          .on("mouseleave", function(this: SVGPathElement) {
            d3.select(this).attr("stroke", "#fff").attr("stroke-width", "0.8");
            setHoveredCod(null);
            setTooltip(null);
          });

        setMapLoaded(true);
      } catch(e) { console.error(e); }
    }
    draw();
    return () => { cancelled = true; };
  }, [ancpiData, viewMode, maxVal]);

  const hoveredData = hoveredCod ? ancpiData.find(d => d.cod === hoveredCod) : null;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16 }}>
      <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 16, background: "#fafafa", position: "relative" }}>
        <svg ref={svgRef} viewBox="0 0 680 420" style={{ width: "100%", display: "block" }} />
        {!mapLoaded && (
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#9ca3af", fontSize: 13 }}>
            Se încarcă harta...
          </div>
        )}
        {tooltip && hoveredData && (
          <div style={{
            position: "absolute", left: tooltip.x + 12, top: tooltip.y - 40,
            background: "#fff", border: "0.5px solid #e5e7eb", borderRadius: 8,
            padding: "6px 10px", pointerEvents: "none", zIndex: 10,
            transform: tooltip.x > 500 ? "translateX(-110%)" : undefined,
          }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>{hoveredData.judet}</div>
            <div style={{ fontSize: 11, color: "#6b7280" }}>{getValue(hoveredData).toLocaleString("ro-RO")} tranzacții</div>
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, justifyContent: "center" }}>
          <span style={{ fontSize: 11, color: "#9ca3af" }}>Mai puțin</span>
          {["#EAF3DE","#C0DD97","#97C459","#639922","#3B6D11","#27500A","#173404"].map(c => (
            <div key={c} style={{ width: 22, height: 10, borderRadius: 2, background: c }} />
          ))}
          <span style={{ fontSize: 11, color: "#9ca3af" }}>Mai mult</span>
        </div>
      </div>

      <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 20, background: "#fff" }}>
        {hoveredData ? (
          <>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>{hoveredData.judet}</div>
            <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.8px" }}>{luna}</div>
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
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" strokeWidth="1.5">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
              <circle cx="12" cy="9" r="2.5"/>
            </svg>
            Hover pe hartă pentru<br />detalii județ
          </div>
        )}
      </div>
    </div>
  );
}

export default function TranzactiiPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("total");
  const [sortBy, setSortBy] = useState<"judet" | "total" | "terenuri" | "unitati">("total");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const getValue = (d: typeof ancpiMartie2026[0]) => {
    if (viewMode === "total") return d.total;
    if (viewMode === "terenuri") return d.total_terenuri;
    return d.unitati_individuale;
  };

  const maxVal = useMemo(() => Math.max(...ancpiMartie2026.map(getValue)), [viewMode]);

  const top10 = [...ancpiMartie2026].sort((a, b) => getValue(b) - getValue(a)).slice(0, 10);

  const pieData = [
    { name: "Extravilan agricol", value: totalNational.extravilan_agricol },
    { name: "Extravilan neagricol", value: totalNational.extravilan_neagricol },
    { name: "Intravilan cu constr.", value: totalNational.intravilan_cu_constructii },
    { name: "Intravilan fără constr.", value: totalNational.intravilan_fara_constructii },
    { name: "Unități individuale", value: totalNational.unitati_individuale },
  ];

  const sortedData = [...ancpiMartie2026].sort((a, b) => {
    if (sortBy === "judet") return sortDir === "asc" ? a.judet.localeCompare(b.judet) : b.judet.localeCompare(a.judet);
    const av = sortBy === "total" ? a.total : sortBy === "terenuri" ? a.total_terenuri : a.unitati_individuale;
    const bv = sortBy === "total" ? b.total : sortBy === "terenuri" ? b.total_terenuri : b.unitati_individuale;
    return sortDir === "asc" ? av - bv : bv - av;
  });

  const handleSort = (col: typeof sortBy) => {
    if (sortBy === col) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortBy(col); setSortDir("desc"); }
  };

  const thStyle = (col: typeof sortBy) => ({
    padding: "10px 14px", textAlign: "left" as const, fontSize: 11, fontWeight: 500,
    textTransform: "uppercase" as const, letterSpacing: "0.6px",
    color: sortBy === col ? "#1D9E75" : "#9ca3af",
    borderBottom: "0.5px solid #e5e7eb", cursor: "pointer", whiteSpace: "nowrap" as const,
  });

  return (
    <main>
      <Navbar />
      <div style={{ padding: "10px 32px", fontSize: 12, color: "#9ca3af", borderBottom: "0.5px solid #e5e7eb" }}>
        <Link href="/" style={{ color: "#9ca3af" }}>Acasa</Link>{" / "}
        <Link href="/imobiliare" style={{ color: "#9ca3af" }}>Imobiliare</Link>{" / "}
        <span style={{ color: "#1a1a1a" }}>Tranzacții</span>
      </div>

      <div style={{ padding: "32px 32px 24px", borderBottom: "0.5px solid #e5e7eb" }}>
        <p style={{ fontSize: 11, fontWeight: 500, letterSpacing: "1.5px", textTransform: "uppercase", color: "#EF9F27", marginBottom: 10 }}>
          Imobiliare · Tranzacții
        </p>
        <h1 style={{ fontSize: 32, marginBottom: 8 }}>Dinamică tranzacții — {luna}</h1>
        <p style={{ fontSize: 14, color: "#6b7280", maxWidth: 620 }}>
          Numărul cererilor de înscriere întemeiate pe acte juridice de transfer al dreptului de proprietate, înregistrate și soluționate lunar. Sursa: {sursa}.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 12, padding: "24px 32px" }}>
        {[
          { val: totalNational.total.toLocaleString("ro-RO"), lbl: "Total imobile", color: "#1D9E75" },
          { val: totalNational.extravilan_agricol.toLocaleString("ro-RO"), lbl: "Extravilan agricol", color: "#378ADD" },
          { val: totalNational.intravilan_cu_constructii.toLocaleString("ro-RO"), lbl: "Intravilan cu constr.", color: "#EF9F27" },
          { val: totalNational.intravilan_fara_constructii.toLocaleString("ro-RO"), lbl: "Intravilan fără constr.", color: "#534AB7" },
          { val: totalNational.unitati_individuale.toLocaleString("ro-RO"), lbl: "Unități individuale", color: "#E24B4A" },
        ].map(m => (
          <div key={m.lbl} style={{ background: "#f9fafb", borderRadius: 8, padding: "14px 16px", borderLeft: `3px solid ${m.color}` }}>
            <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 2 }}>{m.val}</div>
            <div style={{ fontSize: 11, color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.7px" }}>{m.lbl}</div>
          </div>
        ))}
      </div>

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
        <RomaniaMap ancpiData={ancpiMartie2026} viewMode={viewMode} getValue={getValue} maxVal={maxVal} />
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, padding: "0 32px 32px" }}>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>
            Top 10 județe — {viewMode === "total" ? "Total imobile" : viewMode === "terenuri" ? "Terenuri" : "Unități individuale"}
          </h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 16 }}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={top10} layout="vertical" margin={{ left: 80, right: 20, top: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="judet" tick={{ fontSize: 11, fill: "#374151" }} tickLine={false} axisLine={false} width={75} />
                <Tooltip contentStyle={{ border: "0.5px solid #e5e7eb", borderRadius: 6, fontSize: 12 }} formatter={(v: number) => [v.toLocaleString("ro-RO"), ""]} />
                <Bar dataKey={viewMode === "total" ? "total" : viewMode === "terenuri" ? "total_terenuri" : "unitati_individuale"} fill="#EF9F27" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>Structură națională tranzacții</h2>
          <div style={{ border: "0.5px solid #e5e7eb", borderRadius: 10, padding: 16 }}>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={90} dataKey="value" paddingAngle={2}>
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                </Pie>
                <Legend iconType="circle" iconSize={8} formatter={(v) => <span style={{ fontSize: 11, color: "#6b7280" }}>{v}</span>} />
                <Tooltip formatter={(v: number) => [v.toLocaleString("ro-RO"), ""]} contentStyle={{ border: "0.5px solid #e5e7eb", borderRadius: 6, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

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
                  <th onClick={() => handleSort("judet")} style={thStyle("judet")}>Județ {sortBy === "judet" ? (sortDir === "asc" ? "↑" : "↓") : ""}</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Ext. Agricol</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Ext. Neagricol</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Intr. Cu Constr.</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Intr. Fără Constr.</th>
                  <th onClick={() => handleSort("terenuri")} style={thStyle("terenuri")}>Total Terenuri {sortBy === "terenuri" ? (sortDir === "asc" ? "↑" : "↓") : ""}</th>
                  <th onClick={() => handleSort("unitati")} style={thStyle("unitati")}>Unit. Individuale {sortBy === "unitati" ? (sortDir === "asc" ? "↑" : "↓") : ""}</th>
                  <th onClick={() => handleSort("total")} style={thStyle("total")}>Total {sortBy === "total" ? (sortDir === "asc" ? "↑" : "↓") : ""}</th>
                  <th style={{ ...thStyle("judet"), cursor: "default" }}>Cotă %</th>
                </tr>
              </thead>
              <tbody>
                {sortedData.map((row, i) => (
                  <tr key={row.judet} style={{ borderBottom: "0.5px solid #e5e7eb", background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
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
