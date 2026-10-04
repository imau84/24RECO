"""
fin_common.py — utilitare partajate pentru pachetul "Financiara" (24reco.com).

Oferă:
  * build_excel(...)  -> .xlsx cu foaia `Sursa`, foaia `Date` și 4-6 foi de analiză
  * build_html(...)   -> pagină HTML standalone (Chart.js, date inline, zero fetch)
  * helpers           -> formatare RO, fetch cu retry, verificări "fail loud"

Convenții obligatorii pentru toate seturile din pachet:
  - numele fișierelor: "Financiara NN MM" (ex. "Financiara 02 01.xlsx" / ".html")
  - foaia `Sursa` documentează integral proveniența datelor
  - foaia `Date` conține datele brute, neagregate, exact cum au fost descărcate
  - foile de analiză conțin valori CALCULATE (pandas), nu formule Excel
  - pagina HTML nu face niciun `fetch()`: toate datele sunt inline în <script>
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import json as _json
import os as _os
import time as _time
from typing import Any, Iterable, Sequence

import pandas as pd
import requests
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Paletă validată (dataviz skill, instanță de referință) — aceleași hexuri
# în toate paginile pachetului. Ordinea sloturilor NU se schimbă.
# ---------------------------------------------------------------------------
SERIES_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
                "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500",
               "#d55181", "#008300", "#9085e9", "#e66767"]

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")

LUNI_RO = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
           "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


# ---------------------------------------------------------------------------
# Fetch cu "fail loud"
# ---------------------------------------------------------------------------
def fetch(url: str, *, tries: int = 4, timeout: int = 60, expect: str | None = None,
          session: requests.Session | None = None, **kw) -> requests.Response:
    """GET cu retry exponențial. Ridică excepție dacă răspunsul nu e valid.

    expect: 'json' | 'csv' | 'xlsx' | 'pdf' | None — verifică semnătura conținutului.
    """
    s = session or requests.Session()
    headers = {"User-Agent": UA, **kw.pop("headers", {})}
    last = None
    for i in range(tries):
        try:
            r = s.get(url, headers=headers, timeout=timeout, **kw)
            if r.status_code == 200 and len(r.content) > 64:
                if expect == "xlsx" and not r.content.startswith(b"PK"):
                    raise RuntimeError(f"nu este XLSX (semnătură {r.content[:4]!r}): {url}")
                if expect == "pdf" and not r.content.startswith(b"%PDF"):
                    raise RuntimeError(f"nu este PDF (semnătură {r.content[:4]!r}): {url}")
                if expect == "json":
                    r.json()
                return r
            last = RuntimeError(f"HTTP {r.status_code}, {len(r.content)} B: {url}")
        except Exception as e:  # noqa: BLE001
            last = e
        _time.sleep(2 ** i * 2)
    raise RuntimeError(f"Descărcare eșuată după {tries} încercări: {last}")


def fail_if_short(df: pd.DataFrame, minim: int, eticheta: str) -> None:
    """Oprește scriptul dacă sursa a întors mai puține rânduri decât minimul acceptat."""
    if len(df) < minim:
        raise SystemExit(
            f"EȘEC: {eticheta} a întors {len(df)} rânduri (<{minim}). "
            "Nu suprascriu datele bune. Verifică sursa.")


def fail_if_stale(ultima_perioada: str, luni_toleranta: int, eticheta: str) -> None:
    """Oprește scriptul dacă ultima perioadă e mai veche decât toleranța."""
    try:
        y, m = int(ultima_perioada[:4]), int(ultima_perioada[5:7])
    except Exception:  # noqa: BLE001
        return
    azi = _dt.date.today()
    vechime = (azi.year - y) * 12 + (azi.month - m)
    if vechime > luni_toleranta:
        raise SystemExit(
            f"EȘEC: {eticheta} se oprește la {ultima_perioada}, adică {vechime} luni "
            f"în urmă (toleranță {luni_toleranta}). Sursa pare înghețată.")


# ---------------------------------------------------------------------------
# Formatare numerică românească
# ---------------------------------------------------------------------------
def ro_num(x: Any, dec: int = 1) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "–"
    s = f"{float(x):,.{dec}f}"
    return s.replace(",", " ").replace(".", ",")


def ro_luna(per: str) -> str:
    """'2026-07' -> 'iulie 2026'; '2026-Q2' -> 'T2 2026'."""
    if "Q" in per:
        y, q = per.split("-Q")
        return f"T{q} {y}"
    y, m = per.split("-")[0], per.split("-")[1]
    return f"{LUNI_RO[int(m) - 1]} {y}"


# ---------------------------------------------------------------------------
# EXCEL
# ---------------------------------------------------------------------------
_HDR_FILL = PatternFill("solid", fgColor="1C5CAB")
_HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
_TITLE_FONT = Font(bold=True, size=13, color="0D366B")
_LABEL_FONT = Font(bold=True, size=10, color="0D366B")
_THIN = Side(style="thin", color="D6D6D2")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _autosize(ws, df: pd.DataFrame, start_row: int, max_w: int = 46) -> None:
    for j, col in enumerate(df.columns, start=1):
        vals = [str(col)] + [str(v) for v in df[col].head(300).tolist()]
        w = min(max(len(v) for v in vals) + 2, max_w)
        ws.column_dimensions[get_column_letter(j)].width = max(w, 10)


def _write_df(ws, df: pd.DataFrame, *, start_row: int = 1, numfmt: str | None = None,
              numfmt_map: dict[str, str] | None = None) -> None:
    for j, col in enumerate(df.columns, start=1):
        c = ws.cell(row=start_row, column=j, value=str(col))
        c.fill, c.font, c.border = _HDR_FILL, _HDR_FONT, _BORDER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, (_, row) in enumerate(df.iterrows(), start=start_row + 1):
        for j, col in enumerate(df.columns, start=1):
            v = row[col]
            if isinstance(v, (pd.Timestamp, _dt.date, _dt.datetime)):
                v = str(v)[:10]
            if pd.isna(v):
                v = None
            c = ws.cell(row=i, column=j, value=v)
            c.border = _BORDER
            fmt = (numfmt_map or {}).get(str(col), numfmt)
            if fmt and isinstance(v, (int, float)):
                c.number_format = fmt
    ws.freeze_panes = ws.cell(row=start_row + 1, column=2)
    _autosize(ws, df, start_row)


def build_excel(path: str, *, meta: dict, date_df: pd.DataFrame,
                analize: dict[str, pd.DataFrame],
                note_analize: dict[str, str] | None = None,
                numfmt: str | None = "#,##0.00",
                numfmt_map: dict[str, str] | None = None) -> str:
    """Scrie fișierul Excel standard al pachetului.

    meta: dict cu chei (toate string):
      cod, sectiune, titlu, subtitlu, sursa, sursa_url, cod_set, frecventa,
      perioada, unitate, descarcat, metodologie, licenta, note (listă), avertismente (listă)
    """
    from openpyxl import Workbook

    wb = Workbook()

    # --- Foaia Sursa -------------------------------------------------------
    ws = wb.active
    ws.title = "Sursa"
    ws["A1"] = meta.get("titlu", "")
    ws["A1"].font = _TITLE_FONT
    ws.merge_cells("A1:B1")
    ws["A2"] = meta.get("subtitlu", "")
    ws["A2"].font = Font(size=10, italic=True, color="52514E")
    ws.merge_cells("A2:B2")

    randuri = [
        ("Cod fișier", meta.get("cod", "")),
        ("Secțiune 24reco", meta.get("sectiune", "")),
        ("Sursa datelor", meta.get("sursa", "")),
        ("URL sursă", meta.get("sursa_url", "")),
        ("Cod / identificator set", meta.get("cod_set", "")),
        ("Frecvență", meta.get("frecventa", "")),
        ("Perioadă acoperită", meta.get("perioada", "")),
        ("Unitate de măsură", meta.get("unitate", "")),
        ("Data descărcării", meta.get("descarcat", _dt.date.today().isoformat())),
        ("Licență / condiții de reutilizare", meta.get("licenta", "")),
        ("Metodologie", meta.get("metodologie", "")),
        ("Script de re-descărcare", meta.get("script", "")),
    ]
    r = 4
    for k, v in randuri:
        ws.cell(row=r, column=1, value=k).font = _LABEL_FONT
        c = ws.cell(row=r, column=2, value=str(v))
        c.alignment = Alignment(wrap_text=True, vertical="top")
        r += 1

    for eticheta, cheie in (("Note", "note"), ("Avertismente / capcane", "avertismente")):
        lst = meta.get(cheie) or []
        if not lst:
            continue
        r += 1
        ws.cell(row=r, column=1, value=eticheta).font = _LABEL_FONT
        for n in lst:
            ws.cell(row=r, column=2, value=f"• {n}").alignment = Alignment(wrap_text=True, vertical="top")
            r += 1

    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 108

    # --- Foaia Date --------------------------------------------------------
    wsd = wb.create_sheet("Date")
    _write_df(wsd, date_df, numfmt=numfmt, numfmt_map=numfmt_map)

    # --- Foile de analiză --------------------------------------------------
    for nume, df in analize.items():
        w = wb.create_sheet(nume[:31])
        nota = (note_analize or {}).get(nume)
        start = 1
        if nota:
            w.cell(row=1, column=1, value=nota).font = Font(italic=True, size=9, color="52514E")
            w.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(2, len(df.columns)))
            start = 3
        _write_df(w, df, start_row=start, numfmt=numfmt, numfmt_map=numfmt_map)

    _os.makedirs(_os.path.dirname(path) or ".", exist_ok=True)
    wb.save(path)
    return path


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ | 24reco.com</title>
<meta name="description" content="__DESC__">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{
  color-scheme: light;
  --bg:#f7f7f5; --surface:#fcfcfb; --surface-2:#f0efec;
  --text-1:#0b0b0b; --text-2:#52514e; --text-3:#7a7873;
  --line:#e2e1dc; --accent:#1c5cab; --accent-soft:#e8f0fb;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100;
  --s5:#e87ba4; --s6:#008300; --s7:#4a3aa7; --s8:#e34948;
  --good:#1baf7a; --bad:#e34948;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  color-scheme: dark;
  --bg:#141413; --surface:#1a1a19; --surface-2:#242422;
  --text-1:#ffffff; --text-2:#c3c2b7; --text-3:#8f8e85;
  --line:#33332f; --accent:#6da7ec; --accent-soft:#1d2a3c;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  --good:#199e70; --bad:#e66767;
}}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#141413; --surface:#1a1a19; --surface-2:#242422;
  --text-1:#ffffff; --text-2:#c3c2b7; --text-3:#8f8e85;
  --line:#33332f; --accent:#6da7ec; --accent-soft:#1d2a3c;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500;
  --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  --good:#199e70; --bad:#e66767;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text-1);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  font-size:15px;line-height:1.55;-webkit-text-size-adjust:100%}
.wrap{max-width:1080px;margin:0 auto;padding:24px 16px 64px}
header.page{margin-bottom:22px}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.badge{font-size:11px;font-weight:600;letter-spacing:.03em;text-transform:uppercase;
  padding:3px 9px;border-radius:999px;background:var(--accent-soft);color:var(--accent);
  border:1px solid var(--line)}
.badge.alt{background:var(--surface-2);color:var(--text-2)}
h1{font-size:clamp(20px,4.6vw,29px);line-height:1.22;margin:0 0 8px;letter-spacing:-.01em}
.sub{color:var(--text-2);margin:0 0 12px;font-size:15px;max-width:66ch}
.srcline{font-size:13px;color:var(--text-3)}
.srcline a{color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:10px;margin:20px 0 26px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:13px 14px}
.kpi .k-l{font-size:12px;color:var(--text-2);margin-bottom:5px;line-height:1.3}
.kpi .k-v{font-size:clamp(19px,4.4vw,25px);font-weight:650;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;line-height:1.15}
.kpi .k-n{font-size:11.5px;color:var(--text-3);margin-top:4px;line-height:1.3}
.kpi .up{color:var(--good)} .kpi .down{color:var(--bad)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;
  padding:16px 16px 12px;margin-bottom:18px}
.card h2{font-size:16px;margin:0 0 3px;letter-spacing:-.005em}
.card .c-sub{font-size:12.5px;color:var(--text-2);margin:0 0 12px;max-width:70ch}
.chartbox{position:relative;width:100%;height:320px}
@media(max-width:560px){.chartbox{height:268px}}
.legend{display:flex;flex-wrap:wrap;gap:10px 16px;margin:10px 0 2px;font-size:12.5px;color:var(--text-2)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block;flex:none}
details.tbl{background:var(--surface);border:1px solid var(--line);border-radius:14px;
  padding:0 16px;margin-bottom:18px}
details.tbl summary{cursor:pointer;padding:14px 0;font-weight:600;font-size:14.5px;list-style:none}
details.tbl summary::-webkit-details-marker{display:none}
details.tbl summary::before{content:"▸ ";color:var(--text-3)}
details.tbl[open] summary::before{content:"▾ "}
.tscroll{overflow-x:auto;-webkit-overflow-scrolling:touch;padding-bottom:14px}
table{border-collapse:collapse;font-size:13px;min-width:100%}
th,td{padding:7px 11px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left;position:sticky;left:0;background:var(--surface)}
thead th{background:var(--surface-2);color:var(--text-2);font-weight:600;
  position:sticky;top:0;font-size:12px;text-transform:uppercase;letter-spacing:.02em}
td{font-variant-numeric:tabular-nums}
.notes{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.notes h2{font-size:14px;margin:0 0 8px}
.notes ul{margin:0;padding-left:18px;font-size:13px;color:var(--text-2)}
.notes li{margin-bottom:6px}
footer.page{margin-top:26px;font-size:12.5px;color:var(--text-3);border-top:1px solid var(--line);
  padding-top:14px}
footer.page a{color:var(--accent)}
</style>
</head>
<body>
<div class="wrap">
  <header class="page">
    <div class="badges">__BADGES__</div>
    <h1>__H1__</h1>
    <p class="sub">__SUB__</p>
    <p class="srcline">Sursa: __SRC__ · Perioadă: __PER__ · Actualizat: __UPD__</p>
  </header>
  <section class="kpis">__KPIS__</section>
  __CARDS__
  __TABLE__
  __NOTES__
  <footer class="page">
    <strong>__CODE__</strong> — set de date publicat pe
    <a href="https://24reco.com">24reco.com</a>.
    Date: __SRC__. Frecvență: __FREQ__. Generat: __UPD__.
    Valorile sunt preluate automat din sursa oficială și nu sunt modificate editorial.
  </footer>
</div>
<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
(function(){
  const D = JSON.parse(document.getElementById('payload').textContent);
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const SER = ['--s1','--s2','--s3','--s4','--s5','--s6','--s7','--s8'];
  const roFmt = (v, d) => (v===null||v===undefined||Number.isNaN(v)) ? '–' :
      new Intl.NumberFormat('ro-RO',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
  const charts = [];

  function build(){
    charts.forEach(c=>c.destroy()); charts.length = 0;
    const ink1 = css('--text-1'), ink2 = css('--text-2'), grid = css('--line'),
          surf = css('--surface');
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size = 12;
    Chart.defaults.color = ink2;

    D.charts.forEach((spec) => {
      const el = document.getElementById(spec.id);
      if(!el) return;
      const cols = SER.map(css);
      const ds = spec.series.map((s, i) => {
        const col = s.color ? css(s.color) || s.color : cols[i % cols.length];
        const base = {
          label: s.name, data: s.data, borderColor: col,
          backgroundColor: spec.type === 'line' ? col + '22' : col,
          borderWidth: spec.type === 'line' ? 2 : 0,
          borderRadius: spec.type === 'bar' ? 4 : 0,
          pointRadius: 0, pointHoverRadius: 5, pointHoverBorderWidth: 2,
          pointHoverBorderColor: surf, tension: 0.18,
          fill: !!(spec.fill && spec.series.length === 1),
          spanGaps: true, borderSkipped: false
        };
        if (s.dashed) base.borderDash = [5,4];
        if (spec.type === 'bar') { base.barPercentage = 0.92; base.categoryPercentage = 0.82; }
        return base;
      });
      const dec = spec.dec === undefined ? 1 : spec.dec;
      charts.push(new Chart(el, {
        type: spec.type === 'area' ? 'line' : spec.type,
        data: { labels: spec.labels, datasets: ds },
        options: {
          responsive: true, maintainAspectRatio: false,
          interaction: { mode: 'index', intersect: false },
          layout: { padding: { top: 4, right: 6 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: surf, titleColor: ink1, bodyColor: ink2,
              borderColor: grid, borderWidth: 1, padding: 10, cornerRadius: 8,
              titleFont: { weight: '600' }, displayColors: true, boxWidth: 9, boxHeight: 9,
              usePointStyle: false,
              callbacks: {
                label: (c) => ' ' + c.dataset.label + ': ' +
                    roFmt(c.parsed.y, dec) + (spec.unit ? ' ' + spec.unit : '')
              }
            }
          },
          scales: {
            x: { stacked: !!spec.stacked, grid: { display: false },
                 border: { color: grid },
                 ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: spec.xticks || 8 } },
            y: { stacked: !!spec.stacked, beginAtZero: !!spec.zero,
                 grid: { color: grid, drawTicks: false },
                 border: { display: false },
                 ticks: { padding: 8, callback: (v) => roFmt(v, spec.ydec === undefined ? 0 : spec.ydec) },
                 title: spec.ylabel ? { display: true, text: spec.ylabel, color: css('--text-3'),
                                        font: { size: 11 } } : undefined }
          }
        }
      }));
    });
  }
  build();
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  (mq.addEventListener ? mq.addEventListener('change', build) : mq.addListener(build));
})();
</script>
</body>
</html>
"""


def _legend_html(series: Sequence[dict]) -> str:
    if len(series) < 2:
        return ""
    out = []
    for i, s in enumerate(series):
        var = s.get("color") or f"--s{(i % 8) + 1}"
        out.append(f'<span><i style="background:var({var})"></i>{_html.escape(str(s["name"]))}</span>')
    return '<div class="legend">' + "".join(out) + "</div>"


def build_html(path: str, spec: dict) -> str:
    """Generează pagina HTML standalone.

    spec: {
      cod, sectiune, titlu, subtitlu, sursa, sursa_url, frecventa, perioada, actualizat,
      kpis: [{eticheta, valoare, nota, trend: 'up'|'down'|None}],
      charts: [{id, type: 'line'|'bar', titlu, subtitlu, labels: [...],
                series: [{name, data, color?, dashed?}],
                unit?, dec?, ydec?, ylabel?, stacked?, zero?, fill?, xticks?}],
      tabel: {titlu, columns: [...], rows: [[...]]} | None,
      note: [str],
    }
    """
    badges = [f'<span class="badge">{_html.escape(spec["sectiune"])}</span>',
              f'<span class="badge alt">{_html.escape(spec.get("frecventa", "Lunar"))}</span>',
              f'<span class="badge alt">{_html.escape(spec["cod"])}</span>']
    if spec.get("badge_extra"):
        badges.append(f'<span class="badge alt">{_html.escape(spec["badge_extra"])}</span>')

    kpis = []
    for k in spec.get("kpis", []):
        cls = " " + k["trend"] if k.get("trend") in ("up", "down") else ""
        kpis.append(
            f'<div class="kpi"><div class="k-l">{_html.escape(k["eticheta"])}</div>'
            f'<div class="k-v{cls}">{_html.escape(str(k["valoare"]))}</div>'
            f'<div class="k-n">{_html.escape(k.get("nota", ""))}</div></div>')

    cards = []
    for c in spec.get("charts", []):
        cards.append(
            f'<section class="card"><h2>{_html.escape(c["titlu"])}</h2>'
            f'<p class="c-sub">{_html.escape(c.get("subtitlu", ""))}</p>'
            f'{_legend_html(c["series"])}'
            f'<div class="chartbox"><canvas id="{c["id"]}"></canvas></div></section>')

    tbl = ""
    t = spec.get("tabel")
    if t:
        head = "".join(f"<th>{_html.escape(str(x))}</th>" for x in t["columns"])
        body = "".join(
            "<tr>" + "".join(f"<td>{_html.escape(str(v))}</td>" for v in row) + "</tr>"
            for row in t["rows"])
        tbl = (f'<details class="tbl"><summary>{_html.escape(t.get("titlu", "Tabel de date"))}'
               f'</summary><div class="tscroll"><table><thead><tr>{head}</tr></thead>'
               f'<tbody>{body}</tbody></table></div></details>')

    notes = ""
    if spec.get("note"):
        li = "".join(f"<li>{n}</li>" for n in spec["note"])
        notes = f'<section class="notes"><h2>Note metodologice și sursa datelor</h2><ul>{li}</ul></section>'

    payload = _json.dumps({"charts": spec.get("charts", [])}, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False, default=lambda o: None)

    src = spec.get("sursa", "")
    if spec.get("sursa_url"):
        src = f'<a href="{_html.escape(spec["sursa_url"])}" rel="noopener">{_html.escape(src)}</a>'
    else:
        src = _html.escape(src)

    out = (_HTML_TEMPLATE
           .replace("__TITLE__", _html.escape(spec["titlu"]))
           .replace("__DESC__", _html.escape(spec.get("subtitlu", ""))[:190])
           .replace("__BADGES__", "".join(badges))
           .replace("__H1__", _html.escape(spec["titlu"]))
           .replace("__SUB__", _html.escape(spec.get("subtitlu", "")))
           .replace("__SRC__", src)
           .replace("__PER__", _html.escape(spec.get("perioada", "")))
           .replace("__UPD__", _html.escape(spec.get("actualizat", _dt.date.today().isoformat())))
           .replace("__FREQ__", _html.escape(spec.get("frecventa", "Lunar")))
           .replace("__CODE__", _html.escape(spec["cod"]))
           .replace("__KPIS__", "".join(kpis))
           .replace("__CARDS__", "".join(cards))
           .replace("__TABLE__", tbl)
           .replace("__NOTES__", notes)
           .replace("__PAYLOAD__", payload.replace("</", "<\\/")))

    _os.makedirs(_os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)
    return path


def clean(seq: Iterable) -> list:
    """NaN/inf -> None, pentru serializare JSON validă."""
    out = []
    for v in seq:
        if v is None:
            out.append(None)
        elif isinstance(v, (int,)):
            out.append(v)
        else:
            try:
                fv = float(v)
                out.append(None if (pd.isna(fv) or fv in (float("inf"), float("-inf"))) else round(fv, 6))
            except (TypeError, ValueError):
                out.append(None)
    return out
