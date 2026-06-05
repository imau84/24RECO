"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import industrieData from "@/data/industrie/industrie_data.json";

/* ─── Tipuri ─────────────────────────────────────────────────────────────── */
type MonthMap = Record<string, number | null>;
type YearMap = Record<string, MonthMap>;
type DestMap = Record<string, YearMap>;          // Total / Intra-UE / Extra-UE
type RawMap = Record<string, DestMap>;           // sectiune -> dest -> an -> luna
type JdMap = Record<string, Record<string, YearMap>>; // judet -> sectiune -> an -> luna

const DATA = industrieData as unknown as {
  RAW: RawMap; JD: JdMap; ultima_actualizare?: string; ultima_luna?: string;
};
const RAW = DATA.RAW;
const JD = DATA.JD;

/* ─── Constante ──────────────────────────────────────────────────────────── */
const C = {
  navy: "#0f2044", blue: "#1a56db", blueSoft: "rgba(26,86,219,.12)",
  purple: "#7c3aed", green: "#0e7245", red: "#b91c1c",
  border: "#e8eaed", card: "#fff", bg: "#f4f5f7",
  text: "#1a1f2e", muted: "#5f6368", subtle: "#9aa0a6",
};

const MONTHS_RO = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_FULL = ["Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie", "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"];

const SEC_SHORT: Record<string, string> = {
  "Total": "Total Exporturi",
  "Produse alimentare si animale vii": "Produse alimentare & animale vii",
  "Bauturi si tutun": "Băuturi și tutun",
  "Materiale crude  necomestibile  exclusiv combustibili": "Materiale crude necomestibile",
  "Combustibili minerali  lubrifianti si materiale conexe": "Combustibili minerali",
  "Uleiuri  grasimi si ceruri de origine vegetala si animala": "Uleiuri, grăsimi, ceruri",
  "Produse chimice si produse conexe  nespecificate in alta parte": "Produse chimice",
  "Produse prelucrate clasificate in principal dupa materia prima": "Produse prelucrate (mat. primă)",
  "Masini si echipamente de transport": "Mașini și echipamente transport",
  "Articole manufacturate diverse": "Articole manufacturate diverse",
  "Bunuri necuprinse in alta sectiune": "Bunuri necuprinse în altă secțiune",
};
const secLabel = (s: string) => SEC_SHORT[s] || s;

const SECTIONS = Object.keys(RAW);
const EU_KEYS = Object.keys(RAW["Total"] || {});            // [Total, Intra-UE, Extra-UE]
const JUDETE = Object.keys(JD).filter((j) => j !== "TOTAL").sort((a, b) => a.localeCompare(b, "ro"));

/* Ani disponibili (dinamic) */
function yearsOf(dest: YearMap | undefined): number[] {
  if (!dest) return [];
  return Object.keys(dest).map(Number).sort((a, b) => a - b);
}
const ALL_YEARS = yearsOf(RAW["Total"]?.["Total"]);
const LATEST_YEAR = ALL_YEARS.length ? Math.max(...ALL_YEARS) : new Date().getFullYear();
const PREV_YEAR = LATEST_YEAR - 1;

/* ─── Format ─────────────────────────────────────────────────────────────── */
const fmt = (n: number | null | undefined) => (n == null ? "—" : Math.round(n).toLocaleString("en-US"));
const fmtMd = (n: number | null | undefined) => (n == null ? "—" : (n / 1000).toLocaleString("en-US", { maximumFractionDigits: 1 }));
const sum = (o: MonthMap | undefined) => Object.values(o || {}).reduce<number>((a, b) => a + (b || 0), 0);
const asciiRo = (s: string) => s.toLowerCase().replace(/ă/g, "a").replace(/â/g, "a").replace(/î/g, "i").replace(/ș/g, "s").replace(/ț/g, "t");

/* ─── UI helpers ─────────────────────────────────────────────────────────── */
function KPI({ label, value, sub, delta, big }: { label: string; value: string; sub?: string; delta?: number | null; big?: boolean }) {
  return (
    <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 18px" }}>
      <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".05em", color: C.muted, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: big ? 16 : 22, fontWeight: 700, color: C.navy, lineHeight: 1, fontFamily: "'DM Mono', monospace" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: C.subtle, marginTop: 4 }}>{sub}</div>}
      {delta != null && (
        <div style={{ fontSize: 11, fontWeight: 600, marginTop: 6, color: delta >= 0 ? C.green : C.red }}>
          {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

function Select({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: { v: string; t: string }[];
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, textTransform: "uppercase", letterSpacing: ".05em" }}>{label}</div>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        style={{ border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 12, color: C.text, background: "#fff", minWidth: 170 }}>
        {options.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}
      </select>
    </div>
  );
}

const ctrlBar = { display: "flex", flexWrap: "wrap" as const, gap: 12, alignItems: "flex-end", background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 16px", marginBottom: 16 };
const kpiGrid = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 16 };
const panel = { background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 18, marginBottom: 16 };
const panelTitle = { fontSize: 13, fontWeight: 700, color: C.navy, marginBottom: 14 };

const euroTick = (v: number) => `${Math.round(v / 1000)}M€`;
function ChartTip({ active, payload, label, suffix = "mii EUR" }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: `1px solid ${C.border}`, borderRadius: 6, padding: "8px 10px", fontSize: 12, boxShadow: "0 2px 8px rgba(0,0,0,.08)" }}>
      <div style={{ fontWeight: 600, marginBottom: 4, color: C.navy }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color }}>{p.name}: {p.value == null ? "—" : Math.round(p.value).toLocaleString("en-US")} {suffix}</div>
      ))}
    </div>
  );
}

/* ═════════════ TAB 1 — EVOLUȚIE ═════════════ */
function Evolutie() {
  const [section, setSection] = useState("Total");
  const [dest, setDest] = useState("Total");
  const [startYear, setStartYear] = useState(Math.max(2020, ALL_YEARS[0] ?? 2013));

  const series = useMemo(() => {
    const data = RAW[section]?.[dest] || {};
    const years = Object.keys(data).map(Number).filter((y) => y >= startYear).sort((a, b) => a - b);
    const pts: { label: string; v: number | null }[] = [];
    for (const y of years) {
      for (let m = 1; m <= 12; m++) {
        const v = data[String(y)]?.[String(m)];
        if (v === undefined) continue;
        pts.push({ label: `${MONTHS_RO[m - 1]} ${String(y).slice(2)}`, v: v ?? null });
      }
    }
    return pts;
  }, [section, dest, startYear]);

  const vals = series.map((p) => p.v).filter((v): v is number => v != null);
  const last = vals[vals.length - 1] ?? null;
  const peak = vals.length ? Math.max(...vals) : null;
  const sum12 = vals.slice(-12).reduce((a, b) => a + b, 0);

  // crestere anuala (ultimul an complet vs precedent)
  const data = RAW[section]?.[dest] || {};
  const fullYears = Object.keys(data).filter((y) => Object.values(data[y]).filter((v) => v != null).length === 12).map(Number).sort((a, b) => a - b);
  const fy = fullYears[fullYears.length - 1];
  const annualNow = fy ? sum(data[String(fy)]) : null;
  const annualPrev = fy && data[String(fy - 1)] ? sum(data[String(fy - 1)]) : null;
  const annualGrowth = annualNow && annualPrev ? ((annualNow - annualPrev) / annualPrev) * 100 : null;

  const startOptions = [2013, 2015, 2018, 2020, 2022, LATEST_YEAR - 1].filter((y, i, a) => y >= (ALL_YEARS[0] ?? 2013) && a.indexOf(y) === i);

  return (
    <>
      <div style={ctrlBar}>
        <Select label="Secțiune CSCI" value={section} onChange={setSection} options={SECTIONS.map((s) => ({ v: s, t: secLabel(s) }))} />
        <Select label="Destinație" value={dest} onChange={setDest} options={EU_KEYS.map((k) => ({ v: k, t: k }))} />
        <Select label="An început" value={String(startYear)} onChange={(v) => setStartYear(Number(v))} options={startOptions.map((y) => ({ v: String(y), t: String(y) }))} />
      </div>
      <div style={kpiGrid}>
        <KPI label={`Total ${fy ?? ""} (anual)`} value={fmtMd(annualNow)} sub="miliarde EUR" delta={annualGrowth} />
        <KPI label="Ultimele 12 luni" value={fmtMd(sum12)} sub="miliarde EUR cumulat" />
        <KPI label="Ultima lună disponibilă" value={fmtMd(last)} sub={`${series[series.length - 1]?.label ?? "—"} (mld EUR)`} />
        <KPI label="Vârf istoric" value={fmtMd(peak)} sub={series[vals.indexOf(peak as number)]?.label ?? ""} />
      </div>
      <div style={panel}>
        <div style={panelTitle}>Evoluție exporturi — {secLabel(section)} ({dest})</div>
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={series} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#f0f1f3" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: C.muted }} interval="preserveStartEnd" minTickGap={28} />
              <YAxis tickFormatter={euroTick} tick={{ fontSize: 11, fill: C.muted }} width={48} />
              <Tooltip content={<ChartTip />} />
              <Line type="monotone" dataKey="v" name={secLabel(section)} stroke={C.blue} strokeWidth={2} dot={false} activeDot={{ r: 4 }} fill={C.blueSoft} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </>
  );
}

/* ═════════════ TAB 2 — COMPARAȚIE (dinamic: ultimul an vs precedent) ═════════════ */
function Comparatie() {
  const [section, setSection] = useState("Total");
  const [dest, setDest] = useState("Total");

  const data = RAW[section]?.[dest] || {};
  const dNow = data[String(LATEST_YEAR)] || {};
  const dPrev = data[String(PREV_YEAR)] || {};

  const cmpMonths = Object.keys(dNow).filter((m) => dNow[m] != null).map(Number);
  const tPrev = cmpMonths.reduce((s, m) => s + (dPrev[String(m)] || 0), 0);
  const tNow = cmpMonths.reduce((s, m) => s + (dNow[String(m)] || 0), 0);
  const pct = tPrev > 0 ? ((tNow - tPrev) / tPrev) * 100 : 0;
  const totalPrevYear = sum(dPrev);
  const monthsLabel = cmpMonths.map((m) => MONTHS_RO[m - 1]).join(", ");

  const chart = MONTHS_RO.map((mn, i) => ({
    label: mn,
    [PREV_YEAR]: dPrev[String(i + 1)] ?? null,
    [LATEST_YEAR]: dNow[String(i + 1)] ?? null,
  }));

  return (
    <>
      <div style={ctrlBar}>
        <Select label="Secțiune CSCI" value={section} onChange={setSection} options={SECTIONS.map((s) => ({ v: s, t: secLabel(s) }))} />
        <Select label="Destinație" value={dest} onChange={setDest} options={EU_KEYS.map((k) => ({ v: k, t: k }))} />
      </div>
      <div style={kpiGrid}>
        <KPI label={`Total ${PREV_YEAR} (anual)`} value={fmtMd(totalPrevYear)} sub="mld EUR — referință" />
        <KPI label={`${monthsLabel} ${PREV_YEAR}`} value={fmtMd(tPrev)} sub="mld EUR (perioadă comparabilă)" />
        <KPI label={`${monthsLabel} ${LATEST_YEAR}`} value={fmtMd(tNow)} sub={`Δ ${tNow >= tPrev ? "+" : ""}${fmt(tNow - tPrev)} mii EUR`} delta={pct} />
      </div>
      <div style={panel}>
        <div style={panelTitle}>Comparație lunară {LATEST_YEAR} vs {PREV_YEAR} — {secLabel(section)}</div>
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <BarChart data={chart} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#f0f1f3" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: C.muted }} />
              <YAxis tickFormatter={euroTick} tick={{ fontSize: 11, fill: C.muted }} width={48} />
              <Tooltip content={<ChartTip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey={String(PREV_YEAR)} name={String(PREV_YEAR)} fill="rgba(124,58,237,.75)" radius={[3, 3, 0, 0]} />
              <Bar dataKey={String(LATEST_YEAR)} name={String(LATEST_YEAR)} fill="rgba(26,86,219,.85)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div style={{ ...panel, padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "14px 18px", borderBottom: `1px solid ${C.border}`, fontSize: 13, fontWeight: 700, color: C.navy }}>
          Comparație lunară {LATEST_YEAR} vs {PREV_YEAR} (mii EUR)
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: C.navy }}>
                {["Lună", String(PREV_YEAR), String(LATEST_YEAR), "Δ Absolut", "Δ %"].map((h, i) => (
                  <th key={h} style={{ padding: "9px 12px", color: "#fff", fontSize: 11, textAlign: i === 0 ? "left" : "right" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MONTHS_FULL.map((mn, i) => {
                const vp = dPrev[String(i + 1)], vn = dNow[String(i + 1)];
                const diff = vp != null && vn != null ? vn - vp : null;
                const dpct = vp != null && vp > 0 && vn != null ? ((vn - vp) / vp) * 100 : null;
                return (
                  <tr key={mn} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <td style={{ padding: "8px 12px", textAlign: "left" }}>{mn}</td>
                    <td style={{ padding: "8px 12px", textAlign: "right" }}>{fmt(vp)}</td>
                    <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: vn != null ? 600 : 400 }}>{fmt(vn)}</td>
                    <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: diff == null ? C.subtle : diff >= 0 ? C.green : C.red }}>{diff == null ? "—" : (diff >= 0 ? "+" : "") + fmt(diff)}</td>
                    <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: dpct == null ? C.subtle : dpct >= 0 ? C.green : C.red }}>{dpct == null ? "—" : (dpct >= 0 ? "+" : "") + dpct.toFixed(1) + "%"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* ═════════════ TAB 3 — JUDEȚE ═════════════ */
function Judete() {
  const jdSections = Object.keys(JD[JUDETE[0]] || {});
  const jdYears = useMemo(() => {
    const ys = new Set<string>();
    for (const c of Object.values(JD)) for (const sec of Object.values(c)) for (const y of Object.keys(sec)) ys.add(y);
    return Array.from(ys).sort();
  }, []);
  const defaultYear = jdYears[jdYears.length - 1] || String(LATEST_YEAR);

  const [section, setSection] = useState(jdSections[0] || "Total");
  const [year, setYear] = useState(defaultYear);
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<"judet" | "v" | "yoy">("v");
  const [sortDir, setSortDir] = useState(-1);

  const prevYear = String(Number(year) - 1);

  const rows = useMemo(() => {
    const list = JUDETE.map((j) => {
      const dNow = JD[j]?.[section]?.[year] || {};
      const dPrev = JD[j]?.[section]?.[prevYear] || {};
      const v = sum(dNow);
      const cmpMonths = Object.keys(dNow).filter((m) => dNow[m] != null).map(Number);
      const vNowC = cmpMonths.reduce((s, m) => s + (dNow[String(m)] || 0), 0);
      const vPrevC = cmpMonths.reduce((s, m) => s + (dPrev[String(m)] || 0), 0);
      const yoy = vPrevC > 0 ? ((vNowC - vPrevC) / vPrevC) * 100 : null;
      return { judet: j, v, yoy };
    });
    const q = asciiRo(search.trim());
    let filtered = list.filter((r) => !q || asciiRo(r.judet).includes(q));
    filtered.sort((a, b) => {
      if (sortCol === "judet") return sortDir * a.judet.localeCompare(b.judet, "ro");
      const x = (a[sortCol] as number) || 0, y = (b[sortCol] as number) || 0;
      return sortDir * (x - y);
    });
    return filtered;
  }, [section, year, prevYear, search, sortCol, sortDir]);

  const grand = rows.reduce((s, r) => s + r.v, 0);
  const top = [...rows].sort((a, b) => b.v - a.v)[0];
  const top15 = [...rows].sort((a, b) => b.v - a.v).slice(0, 15).map((r) => ({ judet: r.judet, v: r.v }));

  const setSort = (col: "judet" | "v" | "yoy") => {
    if (sortCol === col) setSortDir(-sortDir);
    else { setSortCol(col); setSortDir(col === "judet" ? 1 : -1); }
  };
  const arrow = (col: string) => (sortCol === col ? (sortDir < 0 ? " ↓" : " ↑") : "");

  return (
    <>
      <div style={ctrlBar}>
        <Select label="Secțiune" value={section} onChange={setSection} options={jdSections.map((s) => ({ v: s, t: s.length > 48 ? s.slice(0, 46) + "…" : s }))} />
        <Select label="An afișare" value={year} onChange={setYear} options={jdYears.map((y) => ({ v: y, t: `${y}${y === defaultYear ? " (recent)" : ""}` }))} />
        <div style={{ width: 1, alignSelf: "stretch", background: C.border }} />
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: C.muted, textTransform: "uppercase", letterSpacing: ".05em" }}>Caută județ</div>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="ex: Cluj, Timiș…"
            style={{ border: `1px solid ${C.border}`, borderRadius: 6, padding: "6px 10px", fontSize: 12, minWidth: 170 }} />
        </div>
      </div>
      <div style={kpiGrid}>
        <KPI label={`Total cumulat ${year}`} value={fmtMd(grand)} sub={`mld EUR — ${rows.length} județe`} />
        <KPI label={`Top județ ${year}`} value={top?.judet || "—"} sub={`${fmtMd(top?.v)} mld EUR`} big />
        <KPI label="Medie / județ" value={fmtMd(rows.length ? grand / rows.length : 0)} sub="mld EUR (mediu)" />
        <KPI label="Secțiune" value={section.length > 26 ? section.slice(0, 24) + "…" : section} sub={`${rows.length} județe selectate`} big />
      </div>
      <div style={panel}>
        <div style={panelTitle}>Top 15 județe după exporturi {year} — {section}</div>
        <div style={{ width: "100%", height: 360 }}>
          <ResponsiveContainer>
            <BarChart data={top15} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 70 }}>
              <CartesianGrid stroke="#f0f1f3" horizontal={false} />
              <XAxis type="number" tickFormatter={euroTick} tick={{ fontSize: 10, fill: C.muted }} />
              <YAxis type="category" dataKey="judet" tick={{ fontSize: 10, fill: C.text }} width={64} />
              <Tooltip content={<ChartTip />} />
              <Bar dataKey="v" name="Exporturi" fill={C.blue} radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div style={{ ...panel, padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: C.navy }}>
                <th onClick={() => setSort("judet")} style={{ padding: "9px 12px", color: "#fff", fontSize: 11, textAlign: "left", cursor: "pointer" }}>Județ{arrow("judet")}</th>
                <th onClick={() => setSort("v")} style={{ padding: "9px 12px", color: "#fff", fontSize: 11, textAlign: "right", cursor: "pointer" }}>Exporturi {year} (mii EUR){arrow("v")}</th>
                <th onClick={() => setSort("yoy")} style={{ padding: "9px 12px", color: "#fff", fontSize: 11, textAlign: "right", cursor: "pointer" }}>Δ % vs {prevYear}{arrow("yoy")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.judet} style={{ borderBottom: `1px solid ${C.border}` }}>
                  <td style={{ padding: "8px 12px", textAlign: "left" }}>{r.judet}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "'DM Mono', monospace" }}>{fmt(r.v)}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: r.yoy == null ? C.subtle : r.yoy >= 0 ? C.green : C.red }}>
                    {r.yoy == null ? "—" : (r.yoy >= 0 ? "+" : "") + r.yoy.toFixed(1) + "%"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

/* ═════════════ PAGINĂ ═════════════ */
const TABS = [
  { id: "evolutie", label: "📈 Evoluție în timp" },
  { id: "comparatie", label: `⇄ Comparație ${LATEST_YEAR} vs ${PREV_YEAR}` },
  { id: "judete", label: "📍 Județe" },
] as const;

export default function IndustriePage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("evolutie");

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "'DM Sans', system-ui, sans-serif", display: "flex", flexDirection: "column" }}>
      {/* Nav */}
      <nav style={{ background: C.navy, height: 56, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
        <Link href="/" style={{ color: "#fff", fontWeight: 700, fontSize: 16, textDecoration: "none", letterSpacing: "-0.3px" }}>24RECO</Link>
        <div style={{ display: "flex", gap: 18, fontSize: 13 }}>
          <Link href="/" style={{ color: "#9ca3af", textDecoration: "none" }}>Acasă</Link>
          <Link href="/industrii" style={{ color: "#fff", textDecoration: "none" }}>Industrii</Link>
          <Link href="/institutii" style={{ color: "#9ca3af", textDecoration: "none" }}>Instituții</Link>
        </div>
      </nav>

      {/* Header */}
      <div style={{ background: "#fff", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "14px 24px 0" }}>
          <div style={{ fontSize: 11, color: C.muted, marginBottom: 6 }}>
            <Link href="/industrii" style={{ color: C.muted, textDecoration: "none" }}>Industrii</Link>
            <span style={{ color: C.subtle }}> / Industrie</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 0 12px" }}>
            <div style={{ width: 40, height: 40, background: "#fce7f3", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>🏭</div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: C.navy }}>Industrie</div>
              <div style={{ fontSize: 11, color: C.muted }}>INS — Institutul Național de Statistică • Comerț exterior</div>
            </div>
            <a href="https://insse.ro" target="_blank" rel="noopener noreferrer" style={{ marginLeft: "auto", fontSize: 11, color: C.blue, textDecoration: "none", border: `1px solid ${C.blue}`, padding: "5px 12px", borderRadius: 6 }}>↗ Site oficial</a>
          </div>
          <div style={{ display: "flex", borderTop: `1px solid ${C.border}` }}>
            <div style={{ padding: "10px 16px", fontSize: 12, color: C.blue, fontWeight: 600, borderBottom: `2px solid ${C.blue}` }}>Exporturi</div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "20px 24px", flex: 1, width: "100%" }}>
        <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 8, padding: "12px 16px", marginBottom: 20, fontSize: 12, color: "#1d4ed8", lineHeight: 1.6 }}>
          Date INS — seria <strong>EXP101I</strong>: Exporturi FOB pe secțiuni CSCI Rev.4. Perioada: <strong>Ianuarie {ALL_YEARS[0] ?? 2013} → {DATA.ultima_luna ? `${MONTHS_FULL[Number(DATA.ultima_luna.split("-")[1]) - 1]} ${DATA.ultima_luna.split("-")[0]}` : `${LATEST_YEAR}`}</strong>. Date lunare la nivel național + defalcare pe județe. Valori în <strong>mii EUR</strong>. Actualizare automată lunară.
        </div>

        <div style={{ display: "flex", borderBottom: `1px solid ${C.border}`, marginBottom: 20 }}>
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{ padding: "10px 18px", fontSize: 12, fontWeight: tab === t.id ? 600 : 400, color: tab === t.id ? C.blue : C.muted, background: "none", border: "none", borderBottom: `2px solid ${tab === t.id ? C.blue : "transparent"}`, cursor: "pointer", marginBottom: -1 }}>
              {t.label}
            </button>
          ))}
        </div>

        {tab === "evolutie" && <Evolutie />}
        {tab === "comparatie" && <Comparatie />}
        {tab === "judete" && <Judete />}
      </div>

      {/* Footer */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "14px 24px", borderTop: `1px solid ${C.border}`, background: "#fff", fontSize: 11, color: C.muted, flexWrap: "wrap" }}>
        <span>Sursa: INS — seria EXP101I (Exporturi FOB pe secțiuni CSCI Rev.4)</span>
        <span style={{ color: C.subtle }}>•</span>
        <a href="http://statistici.insse.ro:8077/tempo-online/" target="_blank" rel="noopener noreferrer" style={{ color: C.blue, textDecoration: "none" }}>🔗 insse.ro — Tempo Online</a>
        <span style={{ marginLeft: "auto", color: C.subtle }}>Ultima actualizare: {DATA.ultima_actualizare ?? "—"} • Frecvență: lunar • Unitate: mii EUR</span>
      </div>
    </div>
  );
}
