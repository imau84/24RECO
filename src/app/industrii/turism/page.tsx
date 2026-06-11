"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

/* ───────────────────────── tipuri ───────────────────────── */

type YearMap = Record<string, (number | null)[]>;            // "2025" -> [12 valori]
type TuristiMap = Record<string, YearMap>;                   // Total/Romani/Straini
type TurismData = {
  CHART_DATA: Record<string, TuristiMap>;                    // [structura][turisti][an]
  COUNTY_DATA: Record<string, Record<string, Record<string, YearMap>>>; // [structura][turisti][judet][an]
  CAT_DATA: Record<string, Record<string, TuristiMap>>;      // [structura][categorie][turisti][an]
  LOC_DATA: Record<string, Record<string, Record<string, YearMap>>>;    // [structura][judet][localitate][an]
  STRUCTURI_DISPLAY: Record<string, string>;
  CATEGORII_ORDER: string[];
  CATEGORII_COLORS?: Record<string, string>;
  META?: { updated: string; lastMonth: string; source: string };
};

type SubTab = "national" | "judete" | "categorii" | "localitati";

/* ───────────────────────── constante ───────────────────────── */

const C = {
  bg: "#f4f5f7", card: "#fff", border: "#e8eaed",
  navy: "#0f2044", blue: "#1a56db", amber: "#f59e0b",
  green: "#0e7245", red: "#b91c1c",
  text: "#1a1f2e", muted: "#5f6368", subtle: "#9aa0a6",
};

const LUNI = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const LUNI_FULL = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
  "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"];

const TURISTI_LABEL: Record<string, string> = {
  Total: "Toți turiștii", Romani: "Turiști români", Straini: "Turiști străini",
};

const CAT_FALLBACK = ["#1a56db", "#0f2044", "#0e7245", "#f59e0b", "#7c3aed",
  "#b91c1c", "#0891b2", "#475569", "#10b981", "#d97706", "#6366f1", "#ec4899"];

const fmt = (n: number) => new Intl.NumberFormat("ro-RO").format(Math.round(n));
const pct = (n: number | null) =>
  n == null ? "—" : `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;

/* ───────────────────────── helpers de date ───────────────────────── */

function sum(arr: (number | null)[] | undefined, upTo?: number): number {
  if (!arr) return 0;
  let s = 0;
  const n = upTo == null ? arr.length : Math.min(upTo, arr.length);
  for (let i = 0; i < n; i++) s += arr[i] || 0;
  return s;
}

function yoy(cur: number, prev: number): number | null {
  return prev > 0 ? ((cur - prev) / prev) * 100 : null;
}

/** Anii prezenți (sortați crescător) într-un YearMap. */
function yearsOf(ym: YearMap | undefined): string[] {
  if (!ym) return [];
  return Object.keys(ym).filter((y) => /^\d{4}$/.test(y) && (ym[y] || []).length >= 1).sort();
}

/** Indexul ultimei luni cu valoare (0-based) din seria anului dat. */
function lastIdx(arr: (number | null)[] | undefined): number {
  if (!arr) return -1;
  for (let i = arr.length - 1; i >= 0; i--) if (arr[i] != null) return i;
  return -1;
}

function stripCode(loc: string): string {
  return loc.replace(/^\d+\s*/, "");
}

/** Citește seria unui an, cu fallback pe formatul vechi y25/y26 din LOC_DATA. */
function getYearSeries(ym: YearMap | undefined, year: string): (number | null)[] {
  if (!ym || !year) return [];
  if (ym[year]) return ym[year];
  const legacy = (ym as Record<string, (number | null)[]>)["y" + year.slice(2)];
  return legacy || [];
}

/* ───────────────────────── componente mici ───────────────────────── */

function KPICard({ label, value, sub, delta }: {
  label: string; value: string; sub?: string; delta?: number | null;
}) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 18px", flex: 1, minWidth: 170 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: C.muted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: C.navy, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: C.subtle, marginTop: 4 }}>{sub}</div>}
      {delta != null && (
        <div style={{ fontSize: 11, fontWeight: 600, color: delta >= 0 ? C.green : C.red, marginTop: 6 }}>
          {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

function Select({ label, value, options, display, onChange }: {
  label: string; value: string; options: string[];
  display?: (o: string) => string; onChange: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 12, color: C.text, background: "#fff", minWidth: 180 }}
      >
        {options.map((o) => (
          <option key={o} value={o}>{display ? display(o) : o}</option>
        ))}
      </select>
    </div>
  );
}

function Panel({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18, marginBottom: 16 }}>
      {title && <div style={{ fontSize: 13, fontWeight: 700, color: C.navy, marginBottom: 14 }}>{title}</div>}
      {children}
    </div>
  );
}

const thStyle: CSSProperties = {
  padding: "9px 12px", fontWeight: 600, color: "#fff", textAlign: "right",
  whiteSpace: "nowrap", fontSize: 11, cursor: "pointer", userSelect: "none",
};
const tdNum: CSSProperties = {
  padding: "7px 12px", textAlign: "right", color: C.text,
  borderBottom: `1px solid ${C.bg}`, fontVariantNumeric: "tabular-nums", fontSize: 12,
};
const tdText: CSSProperties = { ...tdNum, textAlign: "left", fontWeight: 500 };

/* ───────────────────────── pagina ───────────────────────── */

export default function TurismPage() {
  const [data, setData] = useState<TurismData | null>(null);
  const [err, setErr] = useState(false);
  const [tab, setTab] = useState<SubTab>("national");

  // selecții partajate
  const [structura, setStructura] = useState("Total");
  const [turisti, setTuristi] = useState("Total");
  // județe
  const [jdStructura, setJdStructura] = useState("Total");
  const [jdTuristi, setJdTuristi] = useState("Total");
  // categorii
  const [catStructura, setCatStructura] = useState("Hoteluri");
  const [catTuristi, setCatTuristi] = useState("Total");
  // localități
  const [locStructura, setLocStructura] = useState("Total");
  const [locJudet, setLocJudet] = useState("__ALL__");
  const [locSearch, setLocSearch] = useState("");
  const [locSort, setLocSort] = useState<{ key: string; dir: 1 | -1 }>({ key: "ytdCur", dir: -1 });

  useEffect(() => {
    fetch("/turism_data.json")
      .then((r) => r.json())
      .then(setData)
      .catch(() => setErr(true));
  }, []);

  /* ── ani: detectați dinamic din seria națională Total/Total ── */
  const years = useMemo(() => yearsOf(data?.CHART_DATA?.Total?.Total), [data]);
  const curY = years[years.length - 1] || "";
  const prevY = years.length > 1 ? years[years.length - 2] : "";
  const lastM = useMemo(
    () => lastIdx(data?.CHART_DATA?.Total?.Total?.[curY]),
    [data, curY]
  );

  /* ── Tab 1: național ── */
  const natSeries = data?.CHART_DATA?.[structura]?.[turisti];
  const natChart = useMemo(() => {
    if (!natSeries) return [];
    const cur = natSeries[curY] || [];
    const prev = natSeries[prevY] || [];
    return LUNI.map((l, i) => ({
      luna: l,
      [prevY]: prev[i] ?? null,
      [curY]: cur[i] ?? null,
    }));
  }, [natSeries, curY, prevY]);

  const natKpi = useMemo(() => {
    if (!natSeries) return null;
    const cur = natSeries[curY] || [];
    const prev = natSeries[prevY] || [];
    const li = lastIdx(cur);
    if (li < 0) return null;
    const v = cur[li] || 0;
    const mom = li > 0 ? yoy(v, cur[li - 1] || 0) : null;
    const yy = yoy(v, prev[li] || 0);
    const ytdCur = sum(cur, li + 1);
    const ytdPrev = sum(prev, li + 1);
    return { li, v, mom, yy, ytdCur, ytdPrev, ytdYoy: yoy(ytdCur, ytdPrev) };
  }, [natSeries, curY, prevY]);

  /* ── Tab 2: județe ── */
  const jdRows = useMemo(() => {
    const dict = data?.COUNTY_DATA?.[jdStructura]?.[jdTuristi] || {};
    const rows = Object.keys(dict).map((j) => {
      const cur = dict[j][curY] || [];
      const prev = dict[j][prevY] || [];
      const li = lastIdx(cur);
      const ytdCur = sum(cur, li + 1);
      const ytdPrev = sum(prev, li + 1);
      return { judet: j, ytdCur, ytdPrev, yoy: yoy(ytdCur, ytdPrev), totalPrev: sum(prev) };
    });
    rows.sort((a, b) => b.ytdCur - a.ytdCur);
    return rows;
  }, [data, jdStructura, jdTuristi, curY, prevY]);

  /* ── Tab 3: categorii ── */
  const catInfo = useMemo(() => {
    const root = data?.CAT_DATA?.[catStructura] || {};
    const order = (data?.CATEGORII_ORDER || []).filter((c) => c !== "Total" && root[c]);
    const extra = Object.keys(root).filter((c) => c !== "Total" && order.indexOf(c) < 0);
    const cats = order.concat(extra);

    const chart = LUNI.map((l, i) => {
      const row: Record<string, string | number | null> = { luna: l };
      cats.forEach((c) => {
        const arr = root[c]?.[catTuristi]?.[curY] || [];
        row[c] = arr[i] ?? null;
      });
      return row;
    });

    const table = cats.map((c) => {
      const cur = root[c]?.[catTuristi]?.[curY] || [];
      const prev = root[c]?.[catTuristi]?.[prevY] || [];
      const li = lastIdx(cur);
      const ytdCur = sum(cur, li + 1);
      const ytdPrev = sum(prev, li + 1);
      return { cat: c, ytdCur, ytdPrev, yoy: yoy(ytdCur, ytdPrev) };
    });
    const totalYtd = table.reduce((a, r) => a + r.ytdCur, 0);
    return { cats, chart, table, totalYtd };
  }, [data, catStructura, catTuristi, curY, prevY]);

  /* ── Tab 4: localități ── */
  const locJudete = useMemo(() => {
    const d = data?.LOC_DATA?.[locStructura] || data?.LOC_DATA?.Total || {};
    return Object.keys(d).sort((a, b) => a.localeCompare(b, "ro"));
  }, [data, locStructura]);

  const locRows = useMemo(() => {
    const sd = data?.LOC_DATA?.[locStructura] || {};
    const judete = locJudet === "__ALL__" ? Object.keys(sd) : [locJudet];
    const out: { loc: string; judet: string; ytdCur: number; ytdPrev: number; yoy: number | null; totalPrev: number }[] = [];
    judete.forEach((j) => {
      const jd = sd[j] || {};
      Object.keys(jd).forEach((locName) => {
        if (locName === "TOTAL") return; // totalul de județ apare în tabelul de județe
        const cur = getYearSeries(jd[locName], curY);
        const prev = getYearSeries(jd[locName], prevY);
        const li = lastIdx(cur);
        const ytdCur = sum(cur, li + 1);
        const ytdPrev = sum(prev, li + 1);
        const totalPrev = sum(prev);
        if (ytdCur === 0 && totalPrev === 0) return;
        out.push({ loc: stripCode(locName), judet: j, ytdCur, ytdPrev, yoy: yoy(ytdCur, ytdPrev), totalPrev });
      });
    });
    const q = locSearch.trim().toLowerCase()
      .replace(/ă/g, "a").replace(/â/g, "a").replace(/î/g, "i").replace(/ș/g, "s").replace(/ț/g, "t");
    const filtered = q
      ? out.filter((r) => (r.loc + " " + r.judet).toLowerCase()
          .replace(/ă/g, "a").replace(/â/g, "a").replace(/î/g, "i").replace(/ș/g, "s").replace(/ț/g, "t")
          .indexOf(q) >= 0)
      : out;
    const k = locSort.key as keyof typeof filtered[0];
    filtered.sort((a, b) => {
      const av = a[k], bv = b[k];
      if (typeof av === "string" && typeof bv === "string") return av.localeCompare(bv, "ro") * locSort.dir;
      return (((av as number) ?? -Infinity) - ((bv as number) ?? -Infinity)) * locSort.dir;
    });
    return filtered;
  }, [data, locStructura, locJudet, locSearch, locSort, curY, prevY]);

  /* ── stări de încărcare ── */
  if (err) {
    return (
      <div style={{ background: C.bg, minHeight: "100vh" }}>
        <Navbar />
        <div style={{ padding: 60, textAlign: "center", color: C.muted, fontSize: 13 }}>
          Datele nu au putut fi încărcate. Reîncarcă pagina sau revino mai târziu.
        </div>
        <Footer />
      </div>
    );
  }
  if (!data) {
    return (
      <div style={{ background: C.bg, minHeight: "100vh" }}>
        <Navbar />
        <div style={{ padding: 60, textAlign: "center", color: C.subtle, fontSize: 13 }}>Se încarcă datele…</div>
        <Footer />
      </div>
    );
  }

  const structuriAll = Object.keys(data.CHART_DATA);
  const disp = (s: string) => data.STRUCTURI_DISPLAY[s] || s;
  const turistiOpts = ["Total", "Romani", "Straini"];
  const perioadaLabel = lastM >= 0 ? `ianuarie–${LUNI_FULL[lastM]} ${curY}` : curY;
  const catColors = data.CATEGORII_COLORS || {};
  const colorOf = (c: string, i: number) => catColors[c] || CAT_FALLBACK[i % CAT_FALLBACK.length];

  const tabs: { id: SubTab; label: string }[] = [
    { id: "national", label: "🇷🇴 Total național" },
    { id: "judete", label: "📍 Județe" },
    { id: "categorii", label: "⭐ Categorii (stele/flori)" },
    { id: "localitati", label: "🏘️ Localități" },
  ];

  return (
    <div style={{ background: C.bg, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Navbar />

      {/* header */}
      <div style={{ background: "#fff", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "14px 24px" }}>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 6 }}>
            <Link href="/" style={{ color: C.muted }}>Acasă</Link>
            <span style={{ color: C.subtle }}> / Industrii / </span>
            <span style={{ color: C.text, fontWeight: 500 }}>Turism</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ width: 40, height: 40, background: "#fef3c7", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>✈️</div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: C.navy }}>Turism — Sosiri în structuri de cazare</div>
              <div style={{ fontSize: 11, color: C.muted }}>
                Sursa: INS TEMPO-Online · actualizare lunară automată
                {data.META?.lastMonth ? ` · ultima lună: ${data.META.lastMonth}` : ""}
              </div>
            </div>
          </div>
        </div>
      </div>

      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "20px 24px", width: "100%", flex: 1 }}>
        {/* subtabs */}
        <div style={{ display: "flex", borderBottom: `1px solid ${C.border}`, marginBottom: 20, flexWrap: "wrap" }}>
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              style={{
                padding: "10px 18px", fontSize: 12, background: "none", border: "none",
                cursor: "pointer", marginBottom: -1,
                fontWeight: tab === t.id ? 600 : 400,
                color: tab === t.id ? C.blue : C.muted,
                borderBottom: tab === t.id ? `2px solid ${C.blue}` : "2px solid transparent",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── TAB: național ── */}
        {tab === "national" && (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, background: "#fff", border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <Select label="Tip structură" value={structura} options={structuriAll} display={disp} onChange={setStructura} />
              <Select label="Tip turiști" value={turisti} options={turistiOpts} display={(t) => TURISTI_LABEL[t] || t} onChange={setTuristi} />
            </div>

            {natKpi && (
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
                <KPICard label={`Sosiri ${LUNI_FULL[natKpi.li]} ${curY}`} value={fmt(natKpi.v)} sub={`${disp(structura)} · ${TURISTI_LABEL[turisti]}`} />
                <KPICard label="Față de luna precedentă" value={pct(natKpi.mom)} delta={natKpi.mom} />
                <KPICard label={`Față de ${LUNI_FULL[natKpi.li]} ${prevY}`} value={pct(natKpi.yy)} delta={natKpi.yy} />
                <KPICard label={`Cumulat ${perioadaLabel}`} value={fmt(natKpi.ytdCur)} sub={`vs ${fmt(natKpi.ytdPrev)} în ${prevY}`} delta={natKpi.ytdYoy} />
              </div>
            )}

            <Panel title={`Sosiri lunare — ${disp(structura)} · ${TURISTI_LABEL[turisti]}`}>
              <div style={{ width: "100%", height: 340 }}>
                <ResponsiveContainer>
                  <BarChart data={natChart} margin={{ left: 8, right: 8, top: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                    <XAxis dataKey="luna" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => (v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`)} width={48} />
                    <Tooltip formatter={(v: number) => fmt(v)} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey={prevY} fill="#9aa0a6" radius={[3, 3, 0, 0]} />
                    <Bar dataKey={curY} fill={C.blue} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </>
        )}

        {/* ── TAB: județe ── */}
        {tab === "judete" && (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, background: "#fff", border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <Select label="Tip structură" value={jdStructura} options={Object.keys(data.COUNTY_DATA)} display={disp} onChange={setJdStructura} />
              <Select label="Tip turiști" value={jdTuristi} options={turistiOpts} display={(t) => TURISTI_LABEL[t] || t} onChange={setJdTuristi} />
            </div>

            <Panel title={`Top 15 județe — sosiri ${perioadaLabel}`}>
              <div style={{ width: "100%", height: 420 }}>
                <ResponsiveContainer>
                  <BarChart data={jdRows.slice(0, 15)} layout="vertical" margin={{ left: 16, right: 28, top: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => (v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`)} />
                    <YAxis type="category" dataKey="judet" width={110} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => fmt(v)} />
                    <Bar dataKey="ytdCur" name={`Sosiri ${perioadaLabel}`} fill={C.blue} radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title={`Sosiri pe județe — ${disp(jdStructura)} · ${TURISTI_LABEL[jdTuristi]}`}>
              <div style={{ overflowX: "auto", border: `1px solid ${C.border}`, borderRadius: 8 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: C.navy }}>
                      <th style={{ ...thStyle, textAlign: "left" }}>Județ</th>
                      <th style={thStyle}>{perioadaLabel}</th>
                      <th style={thStyle}>aceeași perioadă {prevY}</th>
                      <th style={thStyle}>evoluție</th>
                      <th style={thStyle}>total {prevY}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jdRows.map((r, i) => (
                      <tr key={r.judet} style={{ background: i % 2 ? "#fff" : "#fafafa" }}>
                        <td style={tdText}>{r.judet}</td>
                        <td style={{ ...tdNum, fontWeight: 700, color: C.navy }}>{fmt(r.ytdCur)}</td>
                        <td style={tdNum}>{fmt(r.ytdPrev)}</td>
                        <td style={{ ...tdNum, fontWeight: 600, color: r.yoy == null ? C.subtle : r.yoy >= 0 ? C.green : C.red }}>{pct(r.yoy)}</td>
                        <td style={tdNum}>{fmt(r.totalPrev)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </>
        )}

        {/* ── TAB: categorii ── */}
        {tab === "categorii" && (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, background: "#fff", border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <Select label="Tip structură" value={catStructura} options={Object.keys(data.CAT_DATA)} display={disp} onChange={setCatStructura} />
              <Select label="Tip turiști" value={catTuristi} options={turistiOpts} display={(t) => TURISTI_LABEL[t] || t} onChange={setCatTuristi} />
            </div>

            <Panel title={`Sosiri lunare ${curY} pe categorii — ${disp(catStructura)}`}>
              <div style={{ width: "100%", height: 360 }}>
                <ResponsiveContainer>
                  <BarChart data={catInfo.chart} margin={{ left: 8, right: 8, top: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                    <XAxis dataKey="luna" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => (v >= 1000000 ? `${(v / 1000000).toFixed(1)}M` : v >= 1000 ? `${Math.round(v / 1000)}k` : `${v}`)} width={48} />
                    <Tooltip formatter={(v: number) => fmt(v)} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {catInfo.cats.map((c, i) => (
                      <Bar key={c} dataKey={c} stackId="cat" fill={colorOf(c, i)} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title={`Structura pe categorii — cumulat ${perioadaLabel}`}>
              <div style={{ overflowX: "auto", border: `1px solid ${C.border}`, borderRadius: 8 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: C.navy }}>
                      <th style={{ ...thStyle, textAlign: "left" }}>Categorie</th>
                      <th style={thStyle}>{perioadaLabel}</th>
                      <th style={thStyle}>aceeași perioadă {prevY}</th>
                      <th style={thStyle}>evoluție</th>
                      <th style={thStyle}>pondere</th>
                    </tr>
                  </thead>
                  <tbody>
                    {catInfo.table.map((r, i) => (
                      <tr key={r.cat} style={{ background: i % 2 ? "#fff" : "#fafafa" }}>
                        <td style={tdText}>
                          <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, background: colorOf(r.cat, i), marginRight: 7, verticalAlign: "middle" }} />
                          {r.cat}
                        </td>
                        <td style={{ ...tdNum, fontWeight: 700, color: C.navy }}>{fmt(r.ytdCur)}</td>
                        <td style={tdNum}>{fmt(r.ytdPrev)}</td>
                        <td style={{ ...tdNum, fontWeight: 600, color: r.yoy == null ? C.subtle : r.yoy >= 0 ? C.green : C.red }}>{pct(r.yoy)}</td>
                        <td style={tdNum}>{catInfo.totalYtd > 0 ? `${((r.ytdCur / catInfo.totalYtd) * 100).toFixed(1)}%` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </>
        )}

        {/* ── TAB: localități ── */}
        {tab === "localitati" && (
          <>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end", background: "#fff", border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 16px", marginBottom: 16 }}>
              <Select
                label="Județ" value={locJudet}
                options={["__ALL__"].concat(locJudete)}
                display={(j) => (j === "__ALL__" ? "Toate județele" : j)}
                onChange={setLocJudet}
              />
              <Select label="Tip structură" value={locStructura} options={Object.keys(data.LOC_DATA)} display={disp} onChange={setLocStructura} />
              <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, textTransform: "uppercase", letterSpacing: ".05em" }}>Caută localitate</div>
                <input
                  value={locSearch}
                  onChange={(e) => setLocSearch(e.target.value)}
                  placeholder="ex: Brașov, Sinaia…"
                  style={{ border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 12, minWidth: 200 }}
                />
              </div>
              <div style={{ fontSize: 11, color: C.subtle, paddingBottom: 8 }}>{fmt(locRows.length)} localități</div>
            </div>

            <Panel title={`Sosiri pe localități — ${disp(locStructura)} · ${perioadaLabel}`}>
              <div style={{ overflowX: "auto", border: `1px solid ${C.border}`, borderRadius: 8, maxHeight: 640, overflowY: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: C.navy, position: "sticky", top: 0 }}>
                      <th style={{ ...thStyle, textAlign: "left" }} onClick={() => setLocSort((s) => ({ key: "loc", dir: s.key === "loc" ? (s.dir === 1 ? -1 : 1) : 1 }))}>Localitate {locSort.key === "loc" ? (locSort.dir === 1 ? "▲" : "▼") : ""}</th>
                      <th style={{ ...thStyle, textAlign: "left" }}>Județ</th>
                      <th style={thStyle} onClick={() => setLocSort((s) => ({ key: "ytdCur", dir: s.key === "ytdCur" ? (s.dir === 1 ? -1 : 1) : -1 }))}>{perioadaLabel} {locSort.key === "ytdCur" ? (locSort.dir === 1 ? "▲" : "▼") : ""}</th>
                      <th style={thStyle}>aceeași perioadă {prevY}</th>
                      <th style={thStyle} onClick={() => setLocSort((s) => ({ key: "yoy", dir: s.key === "yoy" ? (s.dir === 1 ? -1 : 1) : -1 }))}>evoluție {locSort.key === "yoy" ? (locSort.dir === 1 ? "▲" : "▼") : ""}</th>
                      <th style={thStyle}>total {prevY}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {locRows.slice(0, 300).map((r, i) => (
                      <tr key={r.judet + r.loc} style={{ background: i % 2 ? "#fff" : "#fafafa" }}>
                        <td style={tdText}>{r.loc}</td>
                        <td style={{ ...tdText, color: C.muted, fontWeight: 400 }}>{r.judet}</td>
                        <td style={{ ...tdNum, fontWeight: 700, color: C.navy }}>{fmt(r.ytdCur)}</td>
                        <td style={tdNum}>{fmt(r.ytdPrev)}</td>
                        <td style={{ ...tdNum, fontWeight: 600, color: r.yoy == null ? C.subtle : r.yoy >= 0 ? C.green : C.red }}>{pct(r.yoy)}</td>
                        <td style={tdNum}>{fmt(r.totalPrev)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {locRows.length > 300 && (
                <div style={{ fontSize: 11, color: C.subtle, marginTop: 8 }}>
                  Se afișează primele 300 din {fmt(locRows.length)} localități — folosește căutarea sau filtrul de județ pentru a restrânge lista.
                </div>
              )}
            </Panel>
          </>
        )}

        <div style={{ fontSize: 11, color: C.subtle, marginTop: 8 }}>
          Sursa datelor: Institutul Național de Statistică, TEMPO-Online (sosiri în structurile de primire turistică).
          Datele se actualizează automat când INS publică o lună nouă
          {data.META?.updated ? ` · ultima verificare: ${data.META.updated}` : ""}.
        </div>
      </main>

      <Footer />
    </div>
  );
}
