#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 03 01 — Prețul asigurărilor în inflație (IAPC)
Sursa: Eurostat, setul `prc_hicp_minr` (IAPC — ECOICOP ver.2, indici și rate de
       variație, date lunare) plus `prc_hicp_iw` (ponderile din coșul de consum).
Frecvență: LUNARĂ (ponderile: anuale).

Grupa ECOICOP ver.2 nr. 12 „Asigurări și servicii financiare", cu clasele
raportate de România:
  CP121   – asigurări, total
  CP1213  – asigurări legate de locuință
  CP1214  – asigurări legate de transport
  CP12141 – asigurarea mijloacelor de transport personale (RCA, CASCO)
România NU raportează CP1211 (viață și accidente), CP1212 (sănătate),
CP1219 (alte asigurări) — celulele rămân goale, nu sunt estimate.

CAPCANE CONFIRMATE LIVE (2026-09-17):
  * `prc_hicp_midx` / `prc_hicp_manr` / `prc_hicp_inw` sunt seturile ECOICOP ver.1
    și sunt ÎNGHEȚATE la 2025-12. Setul viu este `prc_hicp_minr`.
  * În `prc_hicp_minr` dimensiunea se numește `coicop18` (nu `coicop`), iar codul
    agregatului total este `TOTAL`. Codul `CP00` întoarce HTTP 400.
  * În ECOICOP ver.2 asigurările au urcat de la CP125 la CP121.
"""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 03 01"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
PAGINA = "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table"

TARI = {"RO": "România", "PL": "Polonia", "HU": "Ungaria", "CZ": "Cehia",
        "BG": "Bulgaria", "EA": "Zona euro", "EU27_2020": "Uniunea Europeană"}
GRUPE = {"TOTAL": "Total coș de consum",
         "CP121": "Asigurări — total",
         "CP1213": "Asigurări de locuință",
         "CP1214": "Asigurări de transport",
         "CP12141": "Asigurarea autoturismului (RCA, CASCO)"}
START = "2005-01"


def jsonstat(js: dict) -> pd.DataFrame:
    """Parser generic JSON-stat 2.0 (Eurostat) -> DataFrame lung."""
    dims, sizes = js["id"], js["size"]
    cats = [{v: k for k, v in js["dimension"][d]["category"]["index"].items()}
            for d in dims]
    randuri = []
    for idx, val in js["value"].items():
        if val is None:
            continue
        rest = int(idx)
        chei = [None] * len(dims)
        for p in range(len(dims) - 1, -1, -1):
            chei[p] = cats[p][rest % sizes[p]]
            rest //= sizes[p]
        r = dict(zip(dims, chei))
        r["value"] = float(val)
        randuri.append(r)
    return pd.DataFrame(randuri)


def descarca() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    q_geo = "".join(f"&geo={g}" for g in TARI)
    q_cp = "".join(f"&coicop18={c}" for c in GRUPE)

    js = fetch(f"{BASE}/prc_hicp_minr?format=JSON&lang=EN&unit=I15{q_cp}{q_geo}"
               f"&sinceTimePeriod={START}", expect="json").json()
    idx = jsonstat(js).rename(columns={"time": "perioada", "value": "indice",
                                       "coicop18": "coicop"})
    fail_if_short(idx, 5000, "Eurostat prc_hicp_minr (unit=I15)")

    js = fetch(f"{BASE}/prc_hicp_minr?format=JSON&lang=EN&unit=RCH_A{q_cp}{q_geo}"
               f"&sinceTimePeriod={START}", expect="json").json()
    anr = jsonstat(js).rename(columns={"time": "perioada", "value": "var_anuala",
                                       "coicop18": "coicop"})
    fail_if_short(anr, 5000, "Eurostat prc_hicp_minr (unit=RCH_A)")

    js = fetch(f"{BASE}/prc_hicp_iw?format=JSON&lang=EN&geo=RO{q_cp}"
               "&sinceTimePeriod=2015", expect="json").json()
    inw = jsonstat(js).rename(columns={"time": "an", "value": "pondere_promile",
                                       "coicop18": "coicop"})
    fail_if_short(inw, 30, "Eurostat prc_hicp_iw")

    ro = anr[(anr.geo == "RO") & (anr.coicop == "CP121")]
    if ro.empty:
        raise SystemExit("EȘEC: Eurostat nu a întors seria CP121 pentru România.")
    fail_if_stale(ro.perioada.max(), 3, "IAPC asigurări România")
    return idx, anr, inw


def main() -> None:
    idx, anr, inw = descarca()
    azi = dt.date.today().isoformat()

    date_df = (idx.merge(anr, on=["perioada", "geo", "coicop", "freq", "unit"],
                         how="outer", suffixes=("", "_a"))
               if False else
               idx[["perioada", "geo", "coicop", "indice"]].merge(
                   anr[["perioada", "geo", "coicop", "var_anuala"]],
                   on=["perioada", "geo", "coicop"], how="outer"))
    date_df = (date_df.assign(tara=lambda d: d.geo.map(TARI),
                              grupa=lambda d: d.coicop.map(GRUPE))
               .sort_values(["perioada", "geo", "coicop"])
               [["perioada", "geo", "tara", "coicop", "grupa", "indice", "var_anuala"]]
               .reset_index(drop=True))

    ro_idx = (idx[idx.geo == "RO"].pivot(index="perioada", columns="coicop",
                                         values="indice").sort_index())
    ro_anr = (anr[anr.geo == "RO"].pivot(index="perioada", columns="coicop",
                                         values="var_anuala").sort_index())
    for c in GRUPE:
        if c not in ro_idx.columns:
            ro_idx[c] = None
        if c not in ro_anr.columns:
            ro_anr[c] = None
    ro_idx, ro_anr = ro_idx[list(GRUPE)], ro_anr[list(GRUPE)]

    reg = (anr[anr.coicop == "CP121"].pivot(index="perioada", columns="geo",
                                            values="var_anuala").sort_index())
    reg = reg[[g for g in TARI if g in reg.columns]]
    reg.columns = [TARI[g] for g in reg.columns]

    ro_cp = ro_anr["CP121"].dropna()
    per_max, per_min = ro_cp.index.max(), ro_idx.index.min()

    # ================= FOI DE ANALIZĂ =====================================
    a1 = ro_idx.round(2).rename(columns=GRUPE).reset_index().rename(
        columns={"perioada": "Luna"})

    a2 = ro_anr.round(2).rename(columns=GRUPE).reset_index().rename(
        columns={"perioada": "Luna"})
    a2["Diferență asigurări – total (p.p.)"] = (
        a2["Asigurări — total"] - a2["Total coș de consum"]).round(2)

    a3 = reg.round(2).reset_index().rename(columns={"perioada": "Luna"})

    an = ro_cp.groupby(ro_cp.index.str[:4])
    ro_tot = ro_anr["TOTAL"].dropna()
    an_tot = ro_tot.groupby(ro_tot.index.str[:4]).mean()
    a4 = pd.DataFrame({
        "An": an.mean().index,
        "Asigurări — medie anuală (%)": an.mean().round(2).values,
        "Asigurări — minim (%)": an.min().round(2).values,
        "Asigurări — maxim (%)": an.max().round(2).values,
        "Luni raportate": an.count().values,
    })
    a4["Inflație totală — medie anuală (%)"] = [
        round(float(an_tot[y]), 2) if y in an_tot.index else None for y in a4["An"]]
    a4["Diferență (p.p.)"] = (a4["Asigurări — medie anuală (%)"]
                              - a4["Inflație totală — medie anuală (%)"]).round(2)

    a5 = (inw.assign(Grupa=lambda d: d.coicop.map(GRUPE))
          .pivot(index="an", columns="Grupa", values="pondere_promile")
          .sort_index().reset_index().rename(columns={"an": "An"}))
    a5 = a5[["An"] + [GRUPE[c] for c in GRUPE if GRUPE[c] in a5.columns]]
    if "Asigurări — total" in a5.columns:
        a5["Asigurări — % din coșul de consum"] = (a5["Asigurări — total"] / 10).round(3)

    ultim = []
    for g, num in GRUPE.items():
        r = {"Grupa ECOICOP": num, "Cod": g}
        for t_cod, t_num in TARI.items():
            s = anr[(anr.geo == t_cod) & (anr.coicop == g) & (anr.perioada == per_max)]
            r[t_num] = round(float(s.var_anuala.iloc[0]), 2) if len(s) else None
        ultim.append(r)
    a6 = pd.DataFrame(ultim)

    a7_rows = []
    for g, num in GRUPE.items():
        s = pd.to_numeric(ro_idx[g], errors="coerce").dropna()
        if s.empty:
            continue
        a7_rows.append({
            "Grupa ECOICOP": num,
            "Indice curent (2015 = 100)": round(float(s.iloc[-1]), 2),
            "Creștere cumulată față de 2015 (%)": round(float(s.iloc[-1]) - 100, 2),
            "Creștere în ultimii 5 ani (%)": (
                round((float(s.iloc[-1]) / float(s.iloc[-61]) - 1) * 100, 2)
                if len(s) > 61 else None),
            "Maxim istoric (indice)": round(float(s.max()), 2),
            "Luna maximului": ro_luna(str(s.idxmax())),
            "Luni cu date": int(s.count()),
        })
    a7 = pd.DataFrame(a7_rows)

    meta = {
        "cod": COD, "sectiune": "03 Asigurări",
        "titlu": "Prețul asigurărilor în inflație (IAPC)",
        "subtitlu": "Cât de repede se scumpesc asigurările în România față de restul "
                    "coșului de consum și față de țările din regiune — grupa ECOICOP 12 "
                    "din indicele armonizat al prețurilor de consum.",
        "sursa": "Eurostat — Indicele armonizat al prețurilor de consum (IAPC/HICP), "
                 "ECOICOP ver.2",
        "sursa_url": PAGINA,
        "cod_set": "prc_hicp_minr (unit = I15 și RCH_A; dimensiunea coicop18 = TOTAL, "
                   "CP121, CP1213, CP1214, CP12141) și prc_hicp_iw (ponderi anuale)",
        "frecventa": "LUNARĂ (ponderile din coșul de consum: anuale)",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "indice 2015 = 100; rata anuală de variație în procente (%); "
                   "diferențele în puncte procentuale (p.p.); ponderile în ‰ din 1000",
        "descarcat": azi,
        "licenta": "Eurostat — reutilizare liberă cu menționarea sursei "
                   "(Decizia 2011/833/UE).",
        "metodologie": "IAPC este indicele de prețuri calculat după o metodologie unică "
                       "în toată Uniunea Europeană, ceea ce face comparațiile între țări "
                       "valide. Clasa ECOICOP 12.1 „Asigurări\" acoperă primele plătite de "
                       "gospodării, măsurate ca „serviciu de asigurare\": pentru "
                       "asigurările generale se urmărește partea din primă care rămâne "
                       "asigurătorului după plata despăgubirilor (prima brută minus "
                       "daunele), nu prima încasată integral. De aceea indicele poate "
                       "diferi de evoluția tarifelor afișate la vânzare. Subclasa CP12141 "
                       "(asigurarea mijloacelor de transport personale) conține în "
                       "principal RCA și CASCO.",
        "script": "scripts/financiara_03_01.py",
        "note": [
            "România raportează clasele CP121 (total), CP1213 (locuință), CP1214 "
            "(transport) și CP12141 (autoturisme). CP1211 (viață și accidente), CP1212 "
            "(sănătate) și CP1219 (alte asigurări) nu au valori pentru România — "
            "celulele rămân goale, nu sunt estimate.",
            "Ponderea grupei se recalculează anual și arată cât din cheltuiala unei "
            "gospodării medii merge către asigurări.",
            "Zona euro (EA) și UE27 sunt agregate ponderate, folosite ca reper.",
            "Valorile ultimelor luni pot fi revizuite de institutele naționale de "
            "statistică.",
        ],
        "avertismente": [
            "Seturile vechi prc_hicp_midx / prc_hicp_manr / prc_hicp_inw (ECOICOP ver.1) "
            "sunt ÎNGHEȚATE la 2025-12. Verificat live la 2026-09-17: întorc HTTP 200 dar "
            "nu mai primesc luni noi. Setul viu este prc_hicp_minr.",
            "În prc_hicp_minr dimensiunea COICOP se numește `coicop18`, iar agregatul "
            "total se cere cu codul `TOTAL`; `CP00` întoarce HTTP 400.",
            "În ECOICOP ver.2 asigurările au fost renumerotate: CP125 (ver.1) a devenit "
            "CP121 (ver.2), iar CP1254 a devenit CP1214.",
            "Unitatea trebuie cerută explicit (I15 sau RCH_A); altfel răspunsul amestecă "
            "cinci unități diferite (I25, I15, RCH_M, RCH_A, RCH_MV12MAVR).",
            "Eurostat răspunde cu HTTP 413 dacă cererea nu este filtrată strâns.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=date_df.rename(columns={
            "perioada": "Luna", "geo": "Cod țară", "tara": "Țara",
            "coicop": "Cod ECOICOP", "grupa": "Grupa",
            "indice": "Indice (2015=100)", "var_anuala": "Variație anuală (%)"}),
        analize={
            "Indici lunari RO": a1,
            "Inflația anuală RO": a2,
            "Comparație regională": a3,
            "Medii anuale RO": a4,
            "Ponderi în coșul de consum": a5,
            "Situația ultimei luni": a6,
            "Repere cumulate RO": a7,
        },
        note_analize={
            "Indici lunari RO": "Nivelul indicelui de prețuri (2015 = 100) pentru "
                                "România, pe asigurări și pe total coș de consum.",
            "Inflația anuală RO": "Variația față de aceeași lună a anului anterior (%), "
                                  "plus diferența dintre asigurări și inflația totală.",
            "Comparație regională": "Rata anuală de variație a prețurilor asigurărilor "
                                    "(CP121), o coloană per țară.",
            "Medii anuale RO": "Media, minimul și maximul ratei anuale pe fiecare an "
                               "calendaristic, comparate cu inflația totală.",
            "Ponderi în coșul de consum": "Ponderea (‰ din 1000) alocată asigurărilor în "
                                          "coșul IAPC al României, revizuită anual.",
            "Situația ultimei luni": "Fotografia ultimei luni disponibile: rata anuală pe "
                                     "fiecare clasă și fiecare țară.",
            "Repere cumulate RO": "Creșterea cumulată a prețurilor față de baza 2015 și "
                                  "în ultimii cinci ani.",
        },
        numfmt="0.00")

    # ================= PAGINA HTML ========================================
    et = [ro_luna(p) for p in ro_anr.index]
    et_idx = [ro_luna(p) for p in ro_idx.index]
    v121 = float(ro_cp.iloc[-1])
    v_tot = float(ro_anr["TOTAL"].dropna().iloc[-1])
    s_auto = pd.to_numeric(ro_anr["CP12141"], errors="coerce").dropna()
    v_auto = float(s_auto.iloc[-1]) if len(s_auto) else None
    pond = a5["Asigurări — % din coșul de consum"].dropna() \
        if "Asigurări — % din coșul de consum" in a5.columns else pd.Series(dtype=float)
    pond_v = float(pond.iloc[-1]) if len(pond) else None
    pond_an = str(a5["An"].iloc[-1]) if len(a5) else ""

    spec = {
        "cod": COD, "sectiune": "03 Asigurări",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Eurostat — IAPC, setul prc_hicp_minr", "sursa_url": PAGINA,
        "frecventa": "Lunar", "badge_extra": "Date lunare",
        "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Scumpirea asigurărilor, {ro_luna(per_max)}",
             "valoare": f"{ro_num(v121, 1)}%",
             "nota": "variație față de aceeași lună a anului trecut",
             "trend": "down" if v121 > v_tot else "up"},
            {"eticheta": "Inflația totală, aceeași lună",
             "valoare": f"{ro_num(v_tot, 1)}%",
             "nota": f"diferență: {ro_num(v121 - v_tot, 1)} p.p."},
            {"eticheta": "Asigurarea autoturismului (RCA, CASCO)",
             "valoare": (f"{ro_num(v_auto, 1)}%" if v_auto is not None else "–"),
             "nota": "clasa CP12141, variație anuală"},
            {"eticheta": "Cât din coșul de consum",
             "valoare": (f"{ro_num(pond_v, 2)}%" if pond_v is not None else "–"),
             "nota": f"ponderea asigurărilor în coșul IAPC ({pond_an})"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Asigurările față de restul coșului de consum",
             "subtitlu": "Rata anuală de variație a prețurilor în România. Când linia "
                         "asigurărilor e deasupra liniei totale, asigurările se scumpesc "
                         "mai repede decât restul cheltuielilor.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "xticks": 9,
             "series": [
                 {"name": "Asigurări", "data": clean(ro_anr["CP121"])},
                 {"name": "Inflație totală", "data": clean(ro_anr["TOTAL"])},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Ce tipuri de asigurări s-au scumpit",
             "subtitlu": "Rata anuală de variație pe clasele raportate de România: "
                         "locuință, transport și, separat, asigurarea autoturismului "
                         "(RCA și CASCO).",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "xticks": 9,
             "series": [
                 {"name": "Asigurări de locuință", "data": clean(ro_anr["CP1213"])},
                 {"name": "Asigurarea autoturismului (RCA, CASCO)",
                  "data": clean(ro_anr["CP12141"])},
                 {"name": "Asigurări — total", "data": clean(ro_anr["CP121"]),
                  "dashed": True},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "România în comparație cu regiunea",
             "subtitlu": "Rata anuală de variație a prețului asigurărilor în țările "
                         "vecine, în zona euro și în UE.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "xticks": 9,
             "series": [{"name": t, "data": clean(reg[t])} for t in reg.columns]},
            {"id": "c4", "type": "line",
             "titlu": "Nivelul prețurilor, cu 2015 ca punct de plecare",
             "subtitlu": "Indice 2015 = 100. Arată cât s-au scumpit cumulat asigurările "
                         "față de coșul total de consum.",
             "labels": et_idx, "unit": "puncte", "dec": 1, "ydec": 0, "xticks": 9,
             "series": [
                 {"name": "Asigurări", "data": clean(ro_idx["CP121"])},
                 {"name": "Asigurarea autoturismului", "data": clean(ro_idx["CP12141"])},
                 {"name": "Asigurări de locuință", "data": clean(ro_idx["CP1213"])},
                 {"name": "Total coș de consum", "data": clean(ro_idx["TOTAL"]),
                  "dashed": True},
             ]},
            {"id": "c5", "type": "bar",
             "titlu": "Media anuală: asigurări vs. inflația totală",
             "subtitlu": "Media ratelor lunare din fiecare an calendaristic. Ultimul an "
                         "conține doar lunile deja raportate.",
             "labels": list(a4["An"]), "unit": "%", "dec": 1, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Asigurări", "data": clean(a4["Asigurări — medie anuală (%)"])},
                 {"name": "Inflație totală",
                  "data": clean(a4["Inflație totală — medie anuală (%)"])},
             ]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni "
                     f"({len(ro_anr)} luni în fișierul Excel)",
            "columns": ["Luna", "Asigurări (%)", "Locuință (%)", "Transport (%)",
                        "Autoturism – RCA/CASCO (%)", "Inflație totală (%)",
                        "Diferență (p.p.)"],
            "rows": [[ro_luna(i), ro_num(r["CP121"], 1), ro_num(r["CP1213"], 1),
                      ro_num(r["CP1214"], 1), ro_num(r["CP12141"], 1),
                      ro_num(r["TOTAL"], 1),
                      ro_num((r["CP121"] - r["TOTAL"])
                             if pd.notna(r["CP121"]) and pd.notna(r["TOTAL"]) else None, 1)]
                     for i, r in ro_anr.tail(36).iloc[::-1].iterrows()],
        },
        "note": [
            "Sursa: Eurostat, setul <code>prc_hicp_minr</code> — IAPC în clasificarea "
            "ECOICOP ver.2, indici lunari (2015 = 100) și rate anuale de variație; "
            "ponderile provin din <code>prc_hicp_iw</code>.",
            "<strong>Ce măsoară.</strong> IAPC este indicele de prețuri calculat identic "
            "în toate statele membre, tocmai ca să poată fi comparat între țări. Grupa "
            "12.1 „Asigurări\" urmărește cât plătesc gospodăriile pentru polițe.",
            "<strong>De ce contează.</strong> RCA este obligatoriu prin lege pentru orice "
            "autovehicul înmatriculat, iar asigurarea obligatorie a locuinței (PAD) este "
            "și ea impusă de lege. O scumpire a acestor polițe nu poate fi evitată prin "
            "renunțare, așa că intră direct în bugetul gospodăriei și, prin ponderea din "
            "coș, în rata oficială a inflației.",
            "<strong>Atenție la interpretare.</strong> Pentru asigurările generale IAPC nu "
            "măsoară prima brută, ci „serviciul de asigurare\": prima încasată minus "
            "despăgubirile plătite. Dacă într-un an daunele cresc puternic, indicele poate "
            "scădea chiar dacă tarifele afișate cresc. De aceea seria are salturi mai mari "
            "decât ar sugera tarifele din piață.",
            "România nu raportează clasele CP1211 (asigurări de viață și de accidente), "
            "CP1212 (sănătate) și CP1219 (alte asigurări); pentru acestea nu există date, "
            "iar tabelele le lasă necompletate în loc să le estimeze.",
            "Regenerare: <code>python3 scripts/financiara_03_01.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(date_df)} obs., {len(ro_anr)} luni, {per_min} → {per_max}, "
          f"asigurări RO = {v121:.1f}%, total = {v_tot:.1f}%")


if __name__ == "__main__":
    main()
