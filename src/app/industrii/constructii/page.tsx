"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

// ─── Tipuri ────────────────────────────────────────────────────────────────────
interface DataPoint {
  luna: string;
  valoare: number | null;
}

interface ConstructiiData {
  ultima_actualizare: string;
  unitate: string;
  sursa: string;
  matrice?: string;
  categorii: string[];
  perioade: string[];
  date: Record<string, DataPoint[]>;
}

// ─── Helpers ───────────────────────────────────────────────────────────────────
function fmt(val: number | null | undefined): string {
  if (val == null) return "—";
  return val.toLocaleString("ro-RO");
}

function pct(curr: number | null, prev: number | null): string {
  if (!curr || !prev || prev === 0) return "—";
  const p = ((curr - prev) / prev) * 100;
  return (p >= 0 ? "+" : "") + p.toFixed(1) + "%";
}

function colorPct(curr: number | null, prev: number | null): string {
  if (!curr || !prev || prev === 0) return "#9ca3af";
  return curr >= prev ? "#22c55e" : "#ef4444";
}

// ─── Mini-grafic SVG inline ────────────────────────────────────────────────────
function Sparkline({ data, color = "#378ADD" }: { data: (number | null)[]; color?: string }) {
  const vals = data.filter((v): v is number => v != null);
  if (vals.length < 2) return null;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const W = 120, H = 40, pad = 4;
  const pts = vals.map((v, i) => {
    const x = pad + (i / (vals.length - 1)) * (W - 2 * pad);
    const y = H - pad - ((v - min) / range) * (H - 2 * pad);
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="opacity-70">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Grafic principal ──────────────────────────────────────────────────────────
function LineChart({
  data,
  perioade,
  categorieActiva,
}: {
  data: Record<string, DataPoint[]>;
  perioade: string[];
  categorieActiva: string;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const seriesRaw = data[categorieActiva] ?? [];
  // Filtram ultimele 24 luni
  const recent = seriesRaw.slice(-24);
  const vals = recent.map((d) => d.valoare);
  const labels = recent.map((d) => {
    const parts = d.luna.split(" ");
    return parts.length >= 3 ? `${parts[1].slice(0, 3)} ${parts[2]}` : d.luna;
  });

  const validVals = vals.filter((v): v is number => v != null);
  if (validVals.length < 2)
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        Date insuficiente pentru grafic
      </div>
    );

  const W = 780, H = 280, padL = 80, padR = 20, padT = 20, padB = 60;
  const min = 0;
  const max = Math.max(...validVals) * 1.1;
  const range = max - min || 1;

  const xOf = (i: number) => padL + (i / (recent.length - 1)) * (W - padL - padR);
  const yOf = (v: number | null) =>
    v == null ? null : padT + ((max - v) / range) * (H - padT - padB);

  const points = recent
    .map((d, i) => {
      const y = yOf(d.valoare);
      return y != null ? `${xOf(i)},${y}` : null;
    })
    .filter(Boolean)
    .join(" ");

  const yTicks = 5;
  const stepY = (max - min) / yTicks;

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMinYMid meet"
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Grid Y */}
        {Array.from({ length: yTicks + 1 }, (_, i) => {
          const v = min + i * stepY;
          const y = yOf(v)!;
          return (
            <g key={i}>
              <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="#374151" strokeWidth="0.5" strokeDasharray="4 4" />
              <text x={padL - 8} y={y + 4} textAnchor="end" fontSize="11" fill="#9ca3af">
                {v >= 1000000 ? (v / 1000000).toFixed(1) + "M" : v >= 1000 ? (v / 1000).toFixed(0) + "k" : v.toFixed(0)}
              </text>
            </g>
          );
        })}

        {/* Area fill */}
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#378ADD" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#378ADD" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {points && (
          <>
            <polygon
              points={`${xOf(0)},${H - padB} ${points} ${xOf(recent.length - 1)},${H - padB}`}
              fill="url(#areaGrad)"
            />
            <polyline points={points} fill="none" stroke="#378ADD" strokeWidth="2.5" strokeLinejoin="round" />
          </>
        )}

        {/* X ticks (la fiecare 3 luni) */}
        {recent.map((d, i) => {
          if (i % 3 !== 0) return null;
          return (
            <text key={i} x={xOf(i)} y={H - padB + 18} textAnchor="middle" fontSize="10" fill="#9ca3af">
              {labels[i]}
            </text>
          );
        })}

        {/* Hover overlay */}
        {recent.map((d, i) => {
          const x = xOf(i);
          const y = yOf(d.valoare);
          return (
            <rect
              key={i}
              x={x - (W - padL - padR) / recent.length / 2}
              y={padT}
              width={(W - padL - padR) / recent.length}
              height={H - padT - padB}
              fill="transparent"
              onMouseEnter={() => setHoverIdx(i)}
            />
          );
        })}

        {/* Hover indicator */}
        {hoverIdx != null && (() => {
          const d = recent[hoverIdx];
          const x = xOf(hoverIdx);
          const y = yOf(d.valoare);
          if (y == null) return null;
          const tipW = 160, tipH = 50;
          const tipX = x + 10 + tipW > W ? x - tipW - 10 : x + 10;
          const tipY = Math.max(padT, y - tipH / 2);
          return (
            <g>
              <line x1={x} y1={padT} x2={x} y2={H - padB} stroke="#378ADD" strokeWidth="1" strokeDasharray="4 2" />
              <circle cx={x} cy={y} r={5} fill="#378ADD" stroke="#1a2744" strokeWidth="2" />
              <rect x={tipX} y={tipY} width={tipW} height={tipH} rx="6" fill="#1e3a5f" stroke="#378ADD" strokeWidth="1" />
              <text x={tipX + 8} y={tipY + 16} fontSize="10" fill="#9ca3af">{d.luna}</text>
              <text x={tipX + 8} y={tipY + 34} fontSize="13" fill="#ffffff" fontWeight="bold">
                {fmt(d.valoare)} mp
              </text>
            </g>
          );
        })()}
      </svg>
    </div>
  );
}

// ─── Pagina principala ─────────────────────────────────────────────────────────
export default function ConstructiiPage() {
  const [constructiiData, setConstructiiData] = useState<ConstructiiData | null>(null);
  const [loading, setLoading] = useState(true);
  const [categorieActiva, setCategorieActiva] = useState<string>("");
  const [tab, setTab] = useState<"grafic" | "tabel">("grafic");

  useEffect(() => {
    fetch("/data/constructii/constructii_data.json")
      .then((r) => r.json())
      .then((d: ConstructiiData) => {
        setConstructiiData(d);
        // Setam categoria implicita: TOTAL sau prima din lista
        const total = d.categorii.find((c) => c.toUpperCase().includes("TOTAL")) ?? d.categorii[0] ?? "";
        setCategorieActiva(total);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main style={{ background: "#111827", minHeight: "100vh", color: "#f9fafb", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "#9ca3af" }}>Se încarcă datele...</p>
      </main>
    );
  }

  if (!constructiiData) {
    return (
      <main style={{ background: "#111827", minHeight: "100vh", color: "#f9fafb", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "#ef4444" }}>Eroare la încărcarea datelor. Reveniți mai târziu.</p>
      </main>
    );
  }

  const { categorii, date, ultima_actualizare, unitate } = constructiiData;
  const serieActiva: DataPoint[] = date[categorieActiva] ?? [];
  const recent = serieActiva.slice(-12);

  // KPI: ultima luna, luna precedenta, aceeasi luna an trecut, total YTD
  const last = recent[recent.length - 1];
  const prev = recent[recent.length - 2];
  const sameLastYear = serieActiva[serieActiva.length - 13] ?? null;

  // YTD: suma lunilor din anul curent
  const currentYear = last?.luna?.split(" ").pop() ?? "";
  const ytdVals = serieActiva.filter((d) => d.luna.endsWith(currentYear)).map((d) => d.valoare ?? 0);
  const ytdTotal = ytdVals.reduce((a, b) => a + b, 0);

  // Sparkline data pentru KPI cards
  const sparkData = recent.map((d) => d.valoare);

  return (
    <main style={{ background: "#111827", minHeight: "100vh", color: "#f9fafb", fontFamily: "system-ui, sans-serif" }}>
      {/* Navbar simplu */}
      <nav style={{ background: "#1f2937", borderBottom: "1px solid #374151", padding: "0 24px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link href="/" style={{ color: "#378ADD", fontWeight: 700, fontSize: 18, textDecoration: "none" }}>
          📊 DatePublice.ro
        </Link>
        <div style={{ display: "flex", gap: 24, fontSize: 14 }}>
          <Link href="/industrii" style={{ color: "#d1d5db", textDecoration: "none" }}>Industrii</Link>
          <Link href="/institutii" style={{ color: "#d1d5db", textDecoration: "none" }}>Instituții</Link>
        </div>
      </nav>

      {/* Breadcrumb */}
      <div style={{ padding: "12px 32px", fontSize: 13, color: "#6b7280", borderBottom: "1px solid #1f2937" }}>
        <Link href="/" style={{ color: "#9ca3af", textDecoration: "none" }}>Acasă</Link>
        {" › "}
        <Link href="/industrii" style={{ color: "#9ca3af", textDecoration: "none" }}>Industrii</Link>
        {" › "}
        <span style={{ color: "#f9fafb" }}>Construcții</span>
      </div>

      {/* Header */}
      <div style={{ padding: "32px 32px 0" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
              <span style={{ fontSize: 36 }}>🏗️</span>
              <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>Construcții</h1>
            </div>
            <p style={{ color: "#9ca3af", margin: 0, fontSize: 14 }}>
              INS — Institutul Național de Statistică • seria {constructiiData.matrice ?? "LOC108A"}
            </p>
            <p style={{ color: "#6b7280", margin: "4px 0 0", fontSize: 13 }}>
              Suprafața utilă autorizată la construire (mp), pe categorii de clădiri, nivel național
            </p>
          </div>
          <div style={{ textAlign: "right", fontSize: 13, color: "#6b7280" }}>
            <div>Ultima actualizare: <span style={{ color: "#9ca3af" }}>{ultima_actualizare}</span></div>
            <div>Unitate: <span style={{ color: "#9ca3af" }}>{unitate}</span></div>
          </div>
        </div>
      </div>

      {/* Selector categorie */}
      <div style={{ padding: "20px 32px 0", display: "flex", gap: 8, flexWrap: "wrap" }}>
        {categorii.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategorieActiva(cat)}
            style={{
              padding: "6px 14px",
              borderRadius: 20,
              border: categorieActiva === cat ? "1.5px solid #378ADD" : "1.5px solid #374151",
              background: categorieActiva === cat ? "#1e3a5f" : "#1f2937",
              color: categorieActiva === cat ? "#7fb7e8" : "#9ca3af",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: categorieActiva === cat ? 600 : 400,
              transition: "all 0.15s",
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* KPI Cards */}
      <div style={{ padding: "20px 32px 0", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
        {/* Ultima luna */}
        <div style={{ background: "#1f2937", borderRadius: 12, padding: "18px 20px", border: "1px solid #374151" }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>Ultima lună ({last?.luna ?? "—"})</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#378ADD" }}>{fmt(last?.valoare)} <span style={{ fontSize: 13, color: "#6b7280" }}>mp</span></div>
          <div style={{ fontSize: 13, marginTop: 4, color: colorPct(last?.valoare ?? null, prev?.valoare ?? null) }}>
            {pct(last?.valoare ?? null, prev?.valoare ?? null)} față de luna anterioară
          </div>
          <div style={{ marginTop: 8 }}>
            <Sparkline data={sparkData} color="#378ADD" />
          </div>
        </div>

        {/* Luna anterioară */}
        <div style={{ background: "#1f2937", borderRadius: 12, padding: "18px 20px", border: "1px solid #374151" }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>Luna anterioară ({prev?.luna ?? "—"})</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#e5e7eb" }}>{fmt(prev?.valoare)} <span style={{ fontSize: 13, color: "#6b7280" }}>mp</span></div>
          <div style={{ fontSize: 13, marginTop: 4, color: colorPct(prev?.valoare ?? null, sameLastYear?.valoare ?? null) }}>
            {pct(prev?.valoare ?? null, sameLastYear?.valoare ?? null)} față de aceeași perioadă an trecut
          </div>
        </div>

        {/* Aceeași lună an trecut */}
        <div style={{ background: "#1f2937", borderRadius: 12, padding: "18px 20px", border: "1px solid #374151" }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>Aceeași lună, an trecut</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#e5e7eb" }}>{fmt(sameLastYear?.valoare ?? null)} <span style={{ fontSize: 13, color: "#6b7280" }}>mp</span></div>
          <div style={{ fontSize: 13, marginTop: 4, color: "#6b7280" }}>{sameLastYear?.luna ?? "—"}</div>
        </div>

        {/* YTD */}
        <div style={{ background: "#1f2937", borderRadius: 12, padding: "18px 20px", border: "1px solid #374151" }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 4 }}>Total {currentYear} (YTD)</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#1D9E75" }}>{fmt(ytdTotal)} <span style={{ fontSize: 13, color: "#6b7280" }}>mp</span></div>
          <div style={{ fontSize: 13, marginTop: 4, color: "#6b7280" }}>{ytdVals.length} luni raportate</div>
        </div>
      </div>

      {/* Tab grafic / tabel */}
      <div style={{ padding: "24px 32px 0" }}>
        <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #374151", marginBottom: 0 }}>
          {(["grafic", "tabel"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "8px 20px",
                background: "transparent",
                border: "none",
                borderBottom: tab === t ? "2px solid #378ADD" : "2px solid transparent",
                color: tab === t ? "#378ADD" : "#9ca3af",
                cursor: "pointer",
                fontSize: 14,
                fontWeight: tab === t ? 600 : 400,
                marginBottom: -1,
              }}
            >
              {t === "grafic" ? "📈 Evoluție" : "⊞ Tabel"}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "20px 32px" }}>
        {tab === "grafic" && (
          <div style={{ background: "#1f2937", borderRadius: 12, padding: 24, border: "1px solid #374151" }}>
            <div style={{ fontSize: 14, color: "#9ca3af", marginBottom: 16 }}>
              Evoluție lunară — {categorieActiva} (ultimele 24 luni)
            </div>
            <LineChart data={date} perioade={constructiiData.perioade} categorieActiva={categorieActiva} />
          </div>
        )}

        {tab === "tabel" && (
          <div style={{ background: "#1f2937", borderRadius: 12, border: "1px solid #374151", overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #374151", fontSize: 14, color: "#9ca3af" }}>
              Date tabelare — {categorieActiva}
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#111827" }}>
                    <th style={{ padding: "10px 16px", textAlign: "left", color: "#6b7280", fontWeight: 500, borderBottom: "1px solid #374151" }}>Perioadă</th>
                    <th style={{ padding: "10px 16px", textAlign: "right", color: "#6b7280", fontWeight: 500, borderBottom: "1px solid #374151" }}>Suprafață (mp)</th>
                    <th style={{ padding: "10px 16px", textAlign: "right", color: "#6b7280", fontWeight: 500, borderBottom: "1px solid #374151" }}>Variație lunară</th>
                    <th style={{ padding: "10px 16px", textAlign: "right", color: "#6b7280", fontWeight: 500, borderBottom: "1px solid #374151" }}>Var. an/an</th>
                  </tr>
                </thead>
                <tbody>
                  {[...serieActiva].reverse().slice(0, 24).map((d, i) => {
                    const idx = serieActiva.length - 1 - i;
                    const prevD = serieActiva[idx - 1] ?? null;
                    const prevYear = serieActiva[idx - 12] ?? null;
                    return (
                      <tr key={d.luna} style={{ borderBottom: "1px solid #1f2937", background: i % 2 === 0 ? "transparent" : "#111827" }}>
                        <td style={{ padding: "9px 16px", color: "#e5e7eb" }}>{d.luna}</td>
                        <td style={{ padding: "9px 16px", textAlign: "right", color: "#378ADD", fontWeight: 500 }}>{fmt(d.valoare)}</td>
                        <td style={{ padding: "9px 16px", textAlign: "right", color: colorPct(d.valoare, prevD?.valoare ?? null) }}>
                          {pct(d.valoare, prevD?.valoare ?? null)}
                        </td>
                        <td style={{ padding: "9px 16px", textAlign: "right", color: colorPct(d.valoare, prevYear?.valoare ?? null) }}>
                          {pct(d.valoare, prevYear?.valoare ?? null)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Footer sursa */}
      <div style={{ padding: "0 32px 32px", fontSize: 12, color: "#6b7280", borderTop: "1px solid #1f2937", paddingTop: 16 }}>
        Sursa: {constructiiData.sursa} •{" "}
        <a href="http://statistici.insse.ro:8077/tempo-online/" target="_blank" rel="noopener noreferrer" style={{ color: "#378ADD" }}>
          🔗 insse.ro — Tempo Online
        </a>{" "}
        • Ultima actualizare: {ultima_actualizare} • Frecvență: lunar
      </div>
    </main>
  );
}
