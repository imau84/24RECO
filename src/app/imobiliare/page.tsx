"use client";
import { useEffect, useRef, useState } from "react";
import Script from "next/script";

// ─── types ───────────────────────────────────────────────────────────────────
interface JudetData {
  extrav_agr: number;
  extrav_neagr: number;
  intrav_constr: number;
  intrav_fara: number;
  unitati_indiv: number;
  total: number;
  uat?: string;
}
interface ImobData {
  RAW: Record<string, Record<string, JudetData>>;
  RES: Record<string, Record<string, JudetData>>;
  SECT: Record<string, Record<string, JudetData>>;
}
type CatKey = "total" | "extrav_agr" | "extrav_neagr" | "intrav_constr" | "intrav_fara" | "unitati_indiv";
type ViewMode = "tabel" | "comparatie";

// ─── constants ───────────────────────────────────────────────────────────────
const MONTHS_RO: Record<string, string> = {
  "01":"Ian","02":"Feb","03":"Mar","04":"Apr","05":"Mai","06":"Iun",
  "07":"Iul","08":"Aug","09":"Sep","10":"Oct","11":"Nov","12":"Dec"
};
const MONTHS_FULL: Record<string, string> = {
  "01":"Ianuarie","02":"Februarie","03":"Martie","04":"Aprilie","05":"Mai","06":"Iunie",
  "07":"Iulie","08":"August","09":"Septembrie","10":"Octombrie","11":"Noiembrie","12":"Decembrie"
};
const CAT_LABELS: Record<CatKey, string> = {
  total:"Total Imobile", extrav_agr:"Extravilan Agricol", extrav_neagr:"Extravilan Neagricol",
  intrav_constr:"Intravilan cu Construcții", intrav_fara:"Intravilan fără Construcții",
  unitati_indiv:"Unități Individuale"
};
const fmt = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US");
const toAscii = (s: string) =>
  s.toLowerCase().replace(/ă/g,"a").replace(/â/g,"a").replace(/î/g,"i").replace(/ș/g,"s").replace(/ț/g,"t");

function aggregateData(
  keys: string[],
  dict: Record<string, Record<string, JudetData>>,
  items: string[],
  includeUat = false
): Record<string, JudetData> {
  const result: Record<string, JudetData> = {};
  items.forEach(item => {
    let total=0, ea=0, en=0, ic=0, ifv=0, ui=0, uat="";
    keys.forEach(k => {
      const d = dict[k]?.[item];
      if (!d) return;
      total += d.total; ea += d.extrav_agr; en += d.extrav_neagr;
      ic += d.intrav_constr; ifv += d.intrav_fara; ui += d.unitati_indiv;
      if (includeUat && !uat && d.uat) uat = d.uat;
    });
    result[item] = { total, extrav_agr:ea, extrav_neagr:en, intrav_constr:ic, intrav_fara:ifv, unitati_indiv:ui };
    if (includeUat) result[item].uat = uat;
  });
  return result;
}

// ─── sub-components ──────────────────────────────────────────────────────────
function KpiGrid({ data, keys, judete, cat, state, dict }: {
  data: Record<string, JudetData>;
  keys: string[];
  judete: string[];
  cat: CatKey;
  state: { year: string; month: string };
  dict: Record<string, Record<string, JudetData>>;
}) {
  const vals = judete.map(j => data[j][cat]);
  const grandTotal = vals.reduce((a,b)=>a+b,0);
  const avg = Math.round(grandTotal / judete.length);
  const maxIdx = vals.indexOf(Math.max(...vals));
  const topJudet = judete[maxIdx];
  const topVal = data[topJudet]?.[cat] ?? 0;
  const topUat = data[topJudet]?.uat;

  let period = "";
  if (state.month !== "all") {
    const [y,m] = state.month.split("_");
    period = `${MONTHS_FULL[m]} ${y}`;
  } else if (state.year !== "all") {
    period = `Cumulat ${state.year} (${keys.length} luni)`;
  } else {
    period = `Cumulat 2025-2026 (${keys.length} luni)`;
  }

  let yoyDelta: number | null = null;
  if (state.year === "2026") {
    const k25 = Object.keys(dict).filter(k=>k.startsWith("2025")).sort();
    const k26 = Object.keys(dict).filter(k=>k.startsWith("2026")).sort();
    const compM = k26.map(k=>k.split("_")[1]);
    const k25c = k25.filter(k=>compM.includes(k.split("_")[1]));
    const d25 = aggregateData(k25c, dict, judete, !!topUat);
    const d26 = aggregateData(k26, dict, judete, !!topUat);
    const t25 = judete.reduce((s,j)=>s+(d25[j]?.[cat]||0),0);
    const t26 = judete.reduce((s,j)=>s+(d26[j]?.[cat]||0),0);
    if (t25 > 0) yoyDelta = ((t26-t25)/t25*100);
  }

  return (
    <div className="kpi-grid">
      <div className="kpi-card">
        <div className="kpi-label">Total Tranzacții</div>
        <div className="kpi-value">{fmt(grandTotal)}</div>
        <div className="kpi-sub">{period}</div>
        {yoyDelta !== null && (
          <div className={`kpi-delta ${yoyDelta>=0?"up":"down"}`}>
            {yoyDelta>=0?"▲":"▼"} {Math.abs(yoyDelta).toFixed(1)}% vs aceleași luni 2025
          </div>
        )}
      </div>
      <div className="kpi-card">
        <div className="kpi-label">Medie / {topUat ? "Oraș" : "Județ"}</div>
        <div className="kpi-value">{fmt(avg)}</div>
        <div className="kpi-sub">{judete.length} {topUat ? "orașe reședință" : "județe"}</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">Top {topUat ? "Oraș" : "Județ"}</div>
        <div className="kpi-value" style={{fontSize:16}}>{topUat || topJudet}</div>
        <div className="kpi-sub">{fmt(topVal)} tranzacții</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">Luni analizate</div>
        <div className="kpi-value">{keys.length}</div>
        <div className="kpi-sub">
          {keys.length > 0
            ? `${MONTHS_RO[keys[0].split("_")[1]]} ${keys[0].split("_")[0]} – ${MONTHS_RO[keys[keys.length-1].split("_")[1]]} ${keys[keys.length-1].split("_")[0]}`
            : "—"}
        </div>
      </div>
    </div>
  );
}

function LineChart({ chartId, dict, judete, cat, color2026 }: {
  chartId: string;
  dict: Record<string, Record<string, JudetData>>;
  judete: string[];
  cat: CatKey;
  color2026: string;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartRef = useRef<any>(null);

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Chart = (window as any).Chart;
    if (!Chart) return;
    const labels = ["Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec"];
    const d2025 = labels.map((_,i) => {
      const k = `2025_${String(i+1).padStart(2,"0")}`;
      if (!dict[k]) return null;
      return judete.reduce((s,j)=>(dict[k][j]?s+dict[k][j][cat]:s),0);
    });
    const d2026 = labels.map((_,i) => {
      const k = `2026_${String(i+1).padStart(2,"0")}`;
      if (!dict[k]) return null;
      return judete.reduce((s,j)=>(dict[k][j]?s+dict[k][j][cat]:s),0);
    });
    const existing = Chart.getChart?.(chartId);
    if (existing) existing.destroy();
    const ctx = document.getElementById(chartId) as HTMLCanvasElement;
    if (!ctx) return;
    chartRef.current = new Chart(ctx, {
      type:"line",
      data:{
        labels,
        datasets:[
          {label:"2025", data:d2025, borderColor:"#7c3aed", backgroundColor:"rgba(124,58,237,.1)", borderWidth:2, tension:.35, pointRadius:3, pointBackgroundColor:"#7c3aed", fill:false, spanGaps:false},
          {label:"2026", data:d2026, borderColor:color2026, backgroundColor:`${color2026}26`, borderWidth:2.5, tension:.35, pointRadius:4, pointBackgroundColor:color2026, fill:true, spanGaps:false},
        ]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{
          legend:{display:true,position:"bottom",labels:{font:{size:11,family:"'DM Sans'"},color:"#5f6368",usePointStyle:true,padding:14}},
          tooltip:{callbacks:{label:(c: {dataset:{label:string},parsed:{y:number|null}})=>`${c.dataset.label}: ${c.parsed.y==null?"—":c.parsed.y.toLocaleString("en-US")} tranzacții`}}
        },
        scales:{
          x:{ticks:{font:{size:11},color:"#5f6368"},grid:{display:false}},
          y:{ticks:{font:{size:11},color:"#5f6368",callback:(v: number)=>`${(v/1000).toFixed(0)}k`},grid:{color:"#f4f5f7"}}
        }
      }
    });
    return () => {
      if (chartRef.current) chartRef.current.destroy();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dict, judete, cat]);

  return (
    <div className="panel">
      <div className="panel-title">Evoluție lunară — {CAT_LABELS[cat]}</div>
      <div className="chart-wrap">
        <canvas id={chartId}></canvas>
      </div>
    </div>
  );
}

function Tabel({ data, cat, judete, includeUat }: {
  data: Record<string, JudetData>;
  cat: CatKey;
  judete: string[];
  includeUat: boolean;
}) {
  const [sortCol, setSortCol] = useState<string>("total");
  const [sortDir, setSortDir] = useState<number>(-1);

  const handleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d * -1);
    else { setSortCol(col); setSortDir(-1); }
  };
  const si = (col: string) =>
    sortCol !== col ? <span className="sort-icon">↕</span>
    : sortDir > 0 ? <span className="sort-icon">↑</span>
    : <span className="sort-icon">↓</span>;
  const sorted = [...judete].sort((a,b) => {
    if (sortCol === "judet") return sortDir * a.localeCompare(b,"ro");
    if (sortCol === "uat") return sortDir * ((data[a].uat||"").localeCompare(data[b].uat||"","ro"));
    return sortDir * ((data[a][sortCol as CatKey] as number) - (data[b][sortCol as CatKey] as number));
  });
  const maxVal = Math.max(...judete.map(j=>data[j][cat]),1);
  const gt: Record<string,number> = {};
  (["total","extrav_agr","extrav_neagr","intrav_constr","intrav_fara","unitati_indiv"] as CatKey[]).forEach(c => {
    gt[c] = judete.reduce((s,j)=>s+(data[j][c]||0),0);
  });

  return (
    <div className="panel" style={{padding:0,overflow:"hidden"}}>
      <div style={{padding:"14px 18px",display:"flex",justifyContent:"space-between",alignItems:"center",borderBottom:"1px solid #e8eaed"}}>
        <div style={{fontSize:13,fontWeight:700,color:"#0f2044"}}>
          {includeUat ? "Tranzacții pe orașe reședință" : "Tranzacții pe județ"} — {CAT_LABELS[cat]}
        </div>
        <div style={{fontSize:11,color:"#9aa0a6"}}>{sorted.length} {includeUat?"orașe":"județe"} afișate</div>
      </div>
      <div className="table-scroll" style={{border:"none",borderRadius:0}}>
        <table>
          <thead>
            <tr>
              <th className="text-left">#</th>
              <th className="text-left" onClick={()=>handleSort("judet")} style={{cursor:"pointer"}} data-sorted={sortCol==="judet"}>Județ {si("judet")}</th>
              {includeUat && <th className="text-left" onClick={()=>handleSort("uat")} style={{cursor:"pointer"}}>Oraș Reședință {si("uat")}</th>}
              {(["extrav_agr","extrav_neagr","intrav_constr","intrav_fara","unitati_indiv","total"] as CatKey[]).map(c => (
                <th key={c} onClick={()=>handleSort(c)} style={{cursor:"pointer"}} data-sorted={sortCol===c}>
                  {c==="extrav_agr"?"Ext. Agr.":c==="extrav_neagr"?"Ext. Neagr.":c==="intrav_constr"?"Intr. c/Constr.":c==="intrav_fara"?"Intr. f/Constr.":c==="unitati_indiv"?"Unit. Indiv.":"Total"} {si(c)}
                </th>
              ))}
              <th className="bar-cell">Pondere</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((j,i) => {
              const d = data[j];
              const pct = ((d[cat]/maxVal)*100).toFixed(0);
              return (
                <tr key={j}>
                  <td className="rank">{i+1}</td>
                  <td className="text-left">{j}</td>
                  {includeUat && <td className="text-left" style={{color:"#5f6368"}}>{d.uat||""}</td>}
                  <td>{fmt(d.extrav_agr)}</td>
                  <td>{fmt(d.extrav_neagr)}</td>
                  <td>{fmt(d.intrav_constr)}</td>
                  <td>{fmt(d.intrav_fara)}</td>
                  <td>{fmt(d.unitati_indiv)}</td>
                  <td className="total-col">{fmt(d.total)}</td>
                  <td className="bar-cell">
                    <div className="mini-bar-bg"><div className="mini-bar-fill" style={{width:`${pct}%`}}></div></div>
                  </td>
                </tr>
              );
            })}
            <tr className="total-row">
              <td className="rank">—</td>
              <td className="text-left">TOTAL</td>
              {includeUat && <td></td>}
              <td>{fmt(gt.extrav_agr)}</td>
              <td>{fmt(gt.extrav_neagr)}</td>
              <td>{fmt(gt.intrav_constr)}</td>
              <td>{fmt(gt.intrav_fara)}</td>
              <td>{fmt(gt.unitati_indiv)}</td>
              <td>{fmt(gt.total)}</td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ComparatieYoY({ dict, keys, judete, cat, includeUat }: {
  dict: Record<string, Record<string, JudetData>>;
  keys: string[];
  judete: string[];
  cat: CatKey;
  includeUat: boolean;
}) {
  const k2025 = keys.filter(k=>k.startsWith("2025"));
  const k2026 = keys.filter(k=>k.startsWith("2026"));
  const compM = k2026.map(k=>k.split("_")[1]);
  const k2025c = k2025.filter(k=>compM.includes(k.split("_")[1]));
  const d25 = aggregateData(k2025c, dict, judete, includeUat);
  const d26 = aggregateData(k2026, dict, judete, includeUat);
  const t25 = judete.reduce((s,j)=>s+(d25[j]?.[cat]||0),0);
  const t26 = judete.reduce((s,j)=>s+(d26[j]?.[cat]||0),0);
  const dPct = t25>0 ? ((t26-t25)/t25*100) : 0;
  const dAbs = t26-t25;
  const mLabel = compM.map(m=>MONTHS_RO[m]).join(", ");
  const rows = [...judete].sort((a,b)=>(d26[b]?.[cat]||0)-(d26[a]?.[cat]||0));

  return (
    <>
      <div className="panel">
        <div className="panel-title">Comparație Anul Curent vs. Anul Precedent — {CAT_LABELS[cat]}</div>
        <div style={{fontSize:11,color:"#9aa0a6",marginBottom:14}}>Compară aceleași luni: <strong>{mLabel}</strong></div>
        <div className="compare-grid">
          <div className="compare-card">
            <div className="compare-label">{mLabel} 2025</div>
            <div className="compare-val">{fmt(t25)}</div>
            <div className="compare-delta">tranzacții cumulate</div>
          </div>
          <div className="compare-card">
            <div className="compare-label">{mLabel} 2026</div>
            <div className="compare-val">{fmt(t26)}</div>
            <div className={`compare-delta ${dPct>=0?"up":"down"}`}>
              {dPct>=0?"▲":"▼"} {Math.abs(dPct).toFixed(1)}% ({dAbs>=0?"+":""}{fmt(dAbs)})
            </div>
          </div>
        </div>
      </div>
      <div className="panel" style={{padding:0,overflow:"hidden"}}>
        <div style={{padding:"14px 18px",borderBottom:"1px solid #e8eaed"}}>
          <div style={{fontSize:13,fontWeight:700,color:"#0f2044"}}>Comparație YoY pe {includeUat?"oraș reședință":"județ"}</div>
          <div style={{fontSize:11,color:"#9aa0a6",marginTop:2}}>Sortare după 2026 descrescător</div>
        </div>
        <div className="table-scroll" style={{border:"none",borderRadius:0}}>
          <table>
            <thead>
              <tr>
                <th className="text-left">#</th>
                <th className="text-left">Județ</th>
                {includeUat && <th className="text-left">Oraș</th>}
                <th>2025</th>
                <th>2026</th>
                <th>Δ Absolut</th>
                <th>Δ %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((j,i) => {
                const v25 = d25[j]?.[cat]||0, v26 = d26[j]?.[cat]||0;
                const diff = v26-v25;
                const pct = v25>0 ? ((v26-v25)/v25*100) : (v26>0?100:0);
                return (
                  <tr key={j}>
                    <td className="rank">{i+1}</td>
                    <td className="text-left">{j}</td>
                    {includeUat && <td className="text-left" style={{color:"#5f6368"}}>{d26[j]?.uat||d25[j]?.uat||""}</td>}
                    <td>{fmt(v25)}</td>
                    <td className="total-col">{fmt(v26)}</td>
                    <td style={{color:diff>=0?"#0e7245":"#b91c1c",fontWeight:600}}>{diff>=0?"+":""}{fmt(diff)}</td>
                    <td style={{color:pct>=0?"#0e7245":"#b91c1c",fontWeight:600}}>{pct>=0?"+":""}{pct.toFixed(1)}%</td>
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

// ─── SubPanel ────────────────────────────────────────────────────────────────
function SubPanel({ dict, allKeys, allJudete, chartId, color2026, includeUat }: {
  dict: Record<string, Record<string, JudetData>>;
  allKeys: string[];
  allJudete: string[];
  chartId: string;
  color2026: string;
  includeUat: boolean;
}) {
  const [year, setYear] = useState("2025");
  const [month, setMonth] = useState("all");
  const [cat, setCat] = useState<CatKey>("total");
  const [search, setSearch] = useState("");
  const [view, setView] = useState<ViewMode>("tabel");

  const filteredKeys = month !== "all"
    ? [month]
    : allKeys.filter(k => year === "all" || k.startsWith(year));

  const filteredJudete = search
    ? allJudete.filter(j =>
        toAscii(j).includes(toAscii(search)) ||
        (includeUat && aggregateData(filteredKeys, dict, [j], true)[j]?.uat &&
          toAscii(aggregateData(filteredKeys, dict, [j], true)[j].uat!).includes(toAscii(search)))
      )
    : allJudete;

  const data = aggregateData(filteredKeys, dict, allJudete, includeUat);
  const filteredData = aggregateData(filteredKeys, dict, filteredJudete, includeUat);

  const monthOpts = allKeys
    .filter(k => year === "all" || k.startsWith(year))
    .map(k => { const [y,m] = k.split("_"); return { value:k, label:`${MONTHS_FULL[m]} ${y}` }; });

  return (
    <>
      {/* Controls */}
      <div className="controls">
        <div className="ctrl-group">
          <div className="ctrl-label">An</div>
          <select value={year} onChange={e=>{setYear(e.target.value);setMonth("all");}}>
            <option value="all">Toți anii</option>
            <option value="2025">2025</option>
            <option value="2026">2026</option>
          </select>
        </div>
        <div className="ctrl-group">
          <div className="ctrl-label">Lună</div>
          <select value={month} onChange={e=>setMonth(e.target.value)}>
            <option value="all">Toate lunile (cumulat)</option>
            {monthOpts.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="ctrl-group">
          <div className="ctrl-label">Categorie</div>
          <select value={cat} onChange={e=>setCat(e.target.value as CatKey)}>
            {(Object.entries(CAT_LABELS) as [CatKey,string][]).map(([k,v])=>(
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <div className="ctrl-sep"></div>
        <div className="ctrl-group">
          <div className="ctrl-label">Caută {includeUat?"oraș/județ":"județ"}</div>
          <input className="search-input" type="text" value={search}
            onChange={e=>setSearch(e.target.value)}
            placeholder={includeUat?"ex: Cluj-Napoca, Timișoara...":"ex: Cluj, Timiș..."} />
        </div>
        <div className="ctrl-sep"></div>
        <div className="ctrl-group">
          <div className="ctrl-label">Vizualizare</div>
          <div className="view-toggle">
            <button className={`view-btn ${view==="tabel"?"active":""}`} onClick={()=>setView("tabel")}>⊞ Tabel</button>
            <button className={`view-btn ${view==="comparatie"?"active":""}`} onClick={()=>setView("comparatie")}>⇄ Comparație YoY</button>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <KpiGrid data={data} keys={filteredKeys} judete={allJudete} cat={cat} state={{year,month}} dict={dict} />

      {/* Chart */}
      <LineChart chartId={chartId} dict={dict} judete={filteredJudete} cat={cat} color2026={color2026} />

      {/* Main view */}
      {view === "tabel"
        ? <Tabel data={filteredData} cat={cat} judete={filteredJudete} includeUat={includeUat} />
        : <ComparatieYoY dict={dict} keys={allKeys} judete={filteredJudete} cat={cat} includeUat={includeUat} />
      }
    </>
  );
}

// ─── main page ───────────────────────────────────────────────────────────────
export default function ImobiliarePage() {
  const [data, setData] = useState<ImobData | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"vanzari"|"resedinta">("vanzari");
  const [chartJsReady, setChartJsReady] = useState(false);

  useEffect(() => {
    fetch("/imobiliare_data.json")
      .then(r => r.json())
      .then(d => setData(d))
      .catch(e => setError(String(e)));
  }, []);

  const vKeys = data ? Object.keys(data.RAW).sort() : [];
  const rKeys = data ? Object.keys(data.RES).sort() : [];
  const vJudete = data && vKeys[0] ? Object.keys(data.RAW[vKeys[0]]).sort() : [];
  const rJudete = data && rKeys[0] ? Object.keys(data.RES[rKeys[0]]).sort() : [];
  const lastUpdate = vKeys.length ? (() => {
    const last = vKeys[vKeys.length-1];
    const [y,m] = last.split("_");
    return `${MONTHS_FULL[m]} ${y}`;
  })() : "";

  return (
    <>
      <Script
        src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"
        onLoad={() => setChartJsReady(true)}
        strategy="afterInteractive"
      />
      <style>{`
        *, *::before, *::after { box-sizing: border-box; }
        .kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin-bottom:16px; }
        .kpi-card { background:#fff; border:1px solid #e8eaed; border-radius:10px; padding:14px 18px; }
        .kpi-label { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:.05em; color:#5f6368; margin-bottom:6px; }
        .kpi-value { font-size:22px; font-weight:700; color:#0f2044; line-height:1; font-family:'DM Mono',monospace; }
        .kpi-sub { font-size:11px; color:#9aa0a6; margin-top:4px; }
        .kpi-delta { font-size:11px; font-weight:600; margin-top:6px; }
        .kpi-delta.up { color:#0e7245; }
        .kpi-delta.down { color:#b91c1c; }
        .controls { display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; background:#fff; border:1px solid #e8eaed; border-radius:10px; padding:14px 16px; margin-bottom:16px; }
        .ctrl-group { display:flex; flex-direction:column; gap:5px; }
        .ctrl-label { font-size:10px; font-weight:600; color:#5f6368; text-transform:uppercase; letter-spacing:.05em; }
        select, .search-input { border:1px solid #e8eaed; border-radius:6px; padding:6px 10px; font-size:12px; color:#1a1f2e; background:#fff; outline:none; min-width:140px; font-family:inherit; }
        select:focus, .search-input:focus { border-color:#1a56db; box-shadow:0 0 0 2px rgba(26,86,219,.15); }
        .ctrl-sep { width:1px; align-self:stretch; background:#e8eaed; }
        .view-toggle { display:flex; gap:4px; }
        .view-btn { padding:6px 12px; font-size:11px; font-weight:500; cursor:pointer; color:#5f6368; background:#fff; border:1px solid #e8eaed; border-radius:5px; font-family:inherit; }
        .view-btn.active { background:#0f2044; color:#fff; border-color:#0f2044; }
        .panel { background:#fff; border:1px solid #e8eaed; border-radius:10px; padding:18px; margin-bottom:16px; }
        .panel-title { font-size:13px; font-weight:700; color:#0f2044; margin-bottom:14px; }
        .chart-wrap { position:relative; width:100%; height:280px; }
        .compare-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:14px; }
        .compare-card { background:#fafafa; border:1px solid #e8eaed; border-radius:8px; padding:12px 14px; }
        .compare-label { font-size:10px; font-weight:600; color:#5f6368; text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }
        .compare-val { font-size:18px; font-weight:700; color:#0f2044; font-family:'DM Mono',monospace; }
        .compare-delta { font-size:11px; margin-top:4px; font-weight:600; }
        .compare-delta.up { color:#0e7245; }
        .compare-delta.down { color:#b91c1c; }
        .table-scroll { overflow-x:auto; border:1px solid #e8eaed; border-radius:8px; }
        table { width:100%; border-collapse:collapse; font-size:12px; }
        thead tr { background:#0f2044; }
        th { padding:9px 12px; font-weight:600; color:#fff; text-align:right; white-space:nowrap; font-size:11px; cursor:pointer; user-select:none; }
        th.text-left { text-align:left; }
        th:hover { background:#1a2d56; }
        .sort-icon { opacity:.5; margin-left:3px; }
        td { padding:7px 12px; text-align:right; color:#1a1f2e; border-bottom:1px solid #f4f5f7; font-family:'DM Mono',monospace; }
        td.text-left { text-align:left; font-weight:500; font-family:'DM Sans',sans-serif; }
        td.total-col { color:#0f2044; font-weight:700; }
        td.rank { color:#9aa0a6; text-align:center; }
        tbody tr:nth-child(odd) { background:#fafafa; }
        tbody tr:hover { background:#f0f7ff; }
        .total-row td { background:#fef9c3 !important; border-top:2px solid #f59e0b; font-weight:700; color:#0f2044; }
        .bar-cell { min-width:80px; }
        .mini-bar-bg { background:#e8eaed; border-radius:2px; height:5px; overflow:hidden; }
        .mini-bar-fill { height:100%; border-radius:2px; background:linear-gradient(90deg,#7c3aed,#1a56db); transition:width .4s ease; }
        .subtabs-bar { display:flex; gap:0; border-bottom:1px solid #e8eaed; margin-bottom:20px; }
        .subtab-btn { padding:10px 18px; font-size:12px; font-weight:400; color:#5f6368; background:none; border:none; border-bottom:2px solid transparent; cursor:pointer; margin-bottom:-1px; font-family:inherit; }
        .subtab-btn:hover { color:#1a1f2e; }
        .subtab-btn.active { color:#1a56db; font-weight:600; border-bottom-color:#1a56db; }
      `}</style>

      <main style={{minHeight:"100vh", background:"#f4f5f7", fontFamily:"'DM Sans',system-ui,sans-serif", fontSize:14, color:"#1a1f2e"}}>
        {/* Header */}
        <div style={{background:"#fff", borderBottom:"1px solid #e8eaed"}}>
          <div style={{maxWidth:1200,margin:"0 auto",padding:"14px 24px 0"}}>
            <div style={{fontSize:11,color:"#5f6368",marginBottom:6}}>
              <span style={{color:"#9aa0a6"}}>Acasă › Industrii › </span>
              <span style={{color:"#1a1f2e",fontWeight:500}}>Imobiliare</span>
            </div>
            <div style={{display:"flex",alignItems:"center",gap:14,padding:"10px 0 12px"}}>
              <div style={{width:40,height:40,background:"#fef9c3",borderRadius:8,display:"flex",alignItems:"center",justifyContent:"center",fontSize:20}}>🏠</div>
              <div>
                <div style={{fontSize:18,fontWeight:700,color:"#0f2044"}}>Imobiliare</div>
                <div style={{fontSize:11,color:"#5f6368"}}>ANCPI — Agenția Națională de Cadastru și Publicitate Imobiliară</div>
              </div>
              <a href="https://www.ancpi.ro" target="_blank" rel="noopener noreferrer"
                style={{marginLeft:"auto",fontSize:11,color:"#1a56db",textDecoration:"none",border:"1px solid #1a56db",padding:"5px 12px",borderRadius:6}}>
                ↗ Site oficial
              </a>
            </div>
            <div style={{display:"flex",gap:0,borderTop:"1px solid #e8eaed"}}>
              <div style={{padding:"10px 16px",fontSize:12,fontWeight:600,borderBottom:"2px solid #1a56db",color:"#1a56db"}}>ANCPI</div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div style={{maxWidth:1200,margin:"0 auto",padding:"20px 24px"}}>
          {error && (
            <div style={{padding:30,color:"#b91c1c",background:"#fff",border:"1px solid #fca5a5",borderRadius:10}}>
              Eroare la încărcarea datelor: {error}
            </div>
          )}
          {!data && !error && (
            <div style={{padding:60,textAlign:"center",color:"#9aa0a6",fontSize:13}}>Se încarcă datele...</div>
          )}
          {data && chartJsReady && (
            <>
              {/* Info banner */}
              <div style={{background:"#eff6ff",border:"1px solid #bfdbfe",borderRadius:8,padding:"12px 16px",display:"flex",gap:10,alignItems:"flex-start",marginBottom:20}}>
                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#1a56db" strokeWidth="2" style={{flexShrink:0,marginTop:1}}>
                  <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
                </svg>
                <p style={{fontSize:12,color:"#1d4ed8",lineHeight:1.6,margin:0}}>
                  Date <strong>ANCPI</strong> — tranzacții imobiliare lunare.{" "}
                  <strong>Vânzări Județ</strong>: agregare la nivel de județ (Ian 2025 → {lastUpdate}).{" "}
                  <strong>Reședință Județ</strong>: tranzacții în orașele reședință de județ.
                </p>
              </div>

              {/* Sub-tabs */}
              <div className="subtabs-bar">
                <button className={`subtab-btn ${tab==="vanzari"?"active":""}`} onClick={()=>setTab("vanzari")}>
                  Vânzări Județ
                </button>
                <button className={`subtab-btn ${tab==="resedinta"?"active":""}`} onClick={()=>setTab("resedinta")}>
                  Reședință Județ
                </button>
              </div>

              {tab === "vanzari" && (
                <SubPanel
                  dict={data.RAW}
                  allKeys={vKeys}
                  allJudete={vJudete}
                  chartId="vEvoChart"
                  color2026="#1a56db"
                  includeUat={false}
                />
              )}
              {tab === "resedinta" && (
                <SubPanel
                  dict={data.RES}
                  allKeys={rKeys}
                  allJudete={rJudete}
                  chartId="rEvoChart"
                  color2026="#0e7245"
                  includeUat={true}
                />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{borderTop:"1px solid #e8eaed",background:"#fff",padding:"10px 24px",display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
          <div style={{width:7,height:7,borderRadius:"50%",background:"#22c55e"}}></div>
          <div style={{fontSize:11,color:"#5f6368"}}>Sursa: ANCPI — Date lunare oficiale tranzacții imobiliare</div>
          <span style={{color:"#e8eaed"}}>•</span>
          <a href="https://www.ancpi.ro" target="_blank" rel="noopener noreferrer" style={{fontSize:11,color:"#1a56db",textDecoration:"none"}}>🔗 ancpi.ro</a>
          <div style={{flex:1}}></div>
          <div style={{fontSize:11,color:"#9aa0a6"}}>
            Ultima actualizare: {lastUpdate} • Frecvență: lunar
          </div>
        </div>
      </main>
    </>
  );
}
