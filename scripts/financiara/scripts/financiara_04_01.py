#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 04 01 — Fluxurile de investiții financiare ale României cu restul lumii
Sursa: Eurostat, set `bop_c6_m` (Balance of payments by country — monthly data, BPM6)
Frecvență: LUNARĂ. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.
"""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 04 01"
SECTIUNE = "04 Investiții financiare"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
DATASET = "bop_c6_m"
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
PAGINA = "https://ec.europa.eu/eurostat/databrowser/view/bop_c6_m/default/table"
START = "2005-01"

# Componentele contului financiar (BPM6). Cheile sunt codurile `bop_item` Eurostat.
ITEME = {
    "FA": "Contul financiar (total)",
    "FA__D__F": "Investiții directe",
    "FA__P__F": "Investiții de portofoliu",
    "FA__P__F5": "Portofoliu — acțiuni și unități de fond",
    "FA__P__F3": "Portofoliu — titluri de datorie",
    "FA__F__F7": "Instrumente financiare derivate",
    "FA__O__F": "Alte investiții (credite, depozite, numerar)",
    "FA__R__F": "Active de rezervă (BNR)",
}
# Componentele „mari" folosite în grafice și în structura fluxurilor.
MARI = ["FA__D__F", "FA__P__F", "FA__O__F", "FA__F__F7", "FA__R__F"]

FLUXURI = {"NET": "Net", "ASS": "Active (ieșiri de capital)", "LIAB": "Pasive (intrări de capital)"}

TARI_BENCH = {"RO": "România", "BG": "Bulgaria", "CZ": "Cehia",
              "HU": "Ungaria", "PL": "Polonia"}


# ---------------------------------------------------------------------------
# Decodor JSON-stat 2.0 generic (Eurostat)
# ---------------------------------------------------------------------------
def _jsonstat(js: dict) -> pd.DataFrame:
    dims = js["id"]
    sizes = js["size"]
    inv = {}
    for d in dims:
        idx = js["dimension"][d]["category"]["index"]
        inv[d] = {v: k for k, v in idx.items()}
    # pași pentru indexarea liniarizată (row-major)
    pasi = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        pasi[i] = pasi[i + 1] * sizes[i + 1]
    randuri = []
    for k, val in js["value"].items():
        if val is None:
            continue
        n = int(k)
        rec = {}
        for i, d in enumerate(dims):
            rec[d] = inv[d][(n // pasi[i]) % sizes[i]]
        rec["valoare"] = float(val)
        randuri.append(rec)
    return pd.DataFrame(randuri)


def descarca_ro() -> pd.DataFrame:
    """Contul financiar al României, pe componente și pe sens (net / active / pasive).

    CAPCANĂ: o cerere fără filtre pe `bop_c6_m` întoarce HTTP 413
    (EXTRACTION_TOO_BIG sau ASYNCHRONOUS_RESPONSE). Filtrăm strâns pe
    geo, partner, currency, sector10, sectpart, stk_flow și bop_item.
    """
    u = (f"{BASE}/{DATASET}?format=JSON&lang=EN&geo=RO&partner=WRL_REST"
         "&currency=MIO_EUR&sector10=S1&sectpart=S1"
         "&stk_flow=NET&stk_flow=ASS&stk_flow=LIAB"
         + "".join(f"&bop_item={i}" for i in ITEME)
         + f"&sinceTimePeriod={START}")
    df = _jsonstat(fetch(u, expect="json").json())
    fail_if_short(df, 3000, "Eurostat bop_c6_m (România)")
    return df


def descarca_bench() -> pd.DataFrame:
    """Benchmark regional: doar fluxul NET pentru investiții directe și de portofoliu."""
    u = (f"{BASE}/{DATASET}?format=JSON&lang=EN&partner=WRL_REST"
         "&currency=MIO_EUR&sector10=S1&sectpart=S1&stk_flow=NET"
         "&bop_item=FA__D__F&bop_item=FA__P__F"
         + "".join(f"&geo={g}" for g in TARI_BENCH)
         + f"&sinceTimePeriod={START}")
    df = _jsonstat(fetch(u, expect="json").json())
    fail_if_short(df, 1500, "Eurostat bop_c6_m (benchmark regional)")
    return df


def main() -> None:
    raw = descarca_ro()
    bench = descarca_bench()
    azi = dt.date.today().isoformat()

    raw["Componentă"] = raw["bop_item"].map(ITEME)
    raw["Sens"] = raw["stk_flow"].map(FLUXURI)

    net = raw[raw.stk_flow == "NET"].pivot(index="time", columns="bop_item",
                                           values="valoare").sort_index()
    ass = raw[raw.stk_flow == "ASS"].pivot(index="time", columns="bop_item",
                                           values="valoare").sort_index()
    lia = raw[raw.stk_flow == "LIAB"].pivot(index="time", columns="bop_item",
                                            values="valoare").sort_index()

    per_min, per_max = net.index.min(), net.index.max()
    fail_if_stale(per_max, 5, "Eurostat bop_c6_m RO")

    # cumulat pe 12 luni — elimină sezonalitatea foarte pronunțată a fluxurilor lunare
    net12 = net.rolling(12).sum()
    ass12 = ass.rolling(12).sum()
    lia12 = lia.rolling(12).sum()

    # --- foile de analiză --------------------------------------------------
    a_net = net.rename(columns=ITEME).round(1).reset_index().rename(columns={"time": "Luna"})
    ordine_net = ["Luna"] + [ITEME[k] for k in ITEME if ITEME[k] in a_net.columns]
    a_net = a_net[ordine_net]

    a_12 = net12.rename(columns=ITEME).round(1).dropna(how="all").reset_index()
    a_12 = a_12.rename(columns={"time": "Luna"})
    a_12 = a_12[[c for c in ordine_net if c in a_12.columns]]

    a_al = pd.DataFrame({"Luna": ass.index})
    for cod, et in (("FA__D__F", "Investiții directe"), ("FA__P__F", "Investiții de portofoliu"),
                    ("FA__O__F", "Alte investiții")):
        a_al[f"{et} — active (mil. EUR)"] = ass[cod].round(1).values if cod in ass else None
        a_al[f"{et} — pasive (mil. EUR)"] = lia[cod].round(1).values if cod in lia else None
        a_al[f"{et} — net (mil. EUR)"] = net[cod].round(1).values if cod in net else None

    an = net.copy()
    an["An"] = an.index.str[:4]
    a_anual = an.groupby("An").agg(["sum", "count"])
    a_anual_flat = pd.DataFrame({"An": a_anual.index})
    for cod in ITEME:
        if cod in net.columns:
            a_anual_flat[ITEME[cod] + " (mil. EUR)"] = a_anual[(cod, "sum")].round(0).values
    a_anual_flat["Luni raportate"] = a_anual[(net.columns[0], "count")].values

    # structura investițiilor de portofoliu: acțiuni vs. titluri de datorie
    a_port = pd.DataFrame({
        "Luna": net.index,
        "Portofoliu total — net (mil. EUR)": net.get("FA__P__F", pd.Series(dtype=float)).round(1).values,
        "Acțiuni și unități de fond — net": net.get("FA__P__F5", pd.Series(dtype=float)).round(1).values,
        "Titluri de datorie — net": net.get("FA__P__F3", pd.Series(dtype=float)).round(1).values,
        "Portofoliu — active (cumulat 12 luni)": ass12.get("FA__P__F", pd.Series(dtype=float)).round(0).values,
        "Portofoliu — pasive (cumulat 12 luni)": lia12.get("FA__P__F", pd.Series(dtype=float)).round(0).values,
    })

    bench["Țara"] = bench["geo"].map(TARI_BENCH)
    b_port = bench[bench.bop_item == "FA__P__F"].pivot(
        index="time", columns="Țara", values="valoare").sort_index()
    b_dir = bench[bench.bop_item == "FA__D__F"].pivot(
        index="time", columns="Țara", values="valoare").sort_index()
    b_port12 = b_port.rolling(12).sum()
    b_dir12 = b_dir.rolling(12).sum()
    ordine_b = [TARI_BENCH[k] for k in TARI_BENCH if TARI_BENCH[k] in b_port12.columns]
    a_bench = pd.DataFrame({"Luna": b_port12.index})
    for t in ordine_b:
        a_bench[f"{t} — portofoliu, 12 luni"] = b_port12[t].round(0).values
        if t in b_dir12.columns:
            a_bench[f"{t} — investiții directe, 12 luni"] = b_dir12[t].round(0).values
    a_bench = a_bench.dropna(how="all", subset=[c for c in a_bench.columns if c != "Luna"])

    u12 = net12.iloc[-1]
    a_rez = pd.DataFrame({
        "Componentă": [ITEME[c] for c in ITEME if c in net.columns],
        f"Ultima lună ({ro_luna(per_max)}), mil. EUR": [net[c].iloc[-1] for c in ITEME if c in net.columns],
        "Cumulat 12 luni, mil. EUR": [u12.get(c) for c in ITEME if c in net.columns],
        "Cumulat 12 luni anterioare, mil. EUR": [net12[c].iloc[-13] if len(net12) > 13 else None
                                                 for c in ITEME if c in net.columns],
        "Medie lunară 2005–prezent, mil. EUR": [net[c].mean() for c in ITEME if c in net.columns],
    }).round(1)
    a_rez["Variație 12 luni, mil. EUR"] = (
        a_rez["Cumulat 12 luni, mil. EUR"] - a_rez["Cumulat 12 luni anterioare, mil. EUR"]).round(1)

    date_df = raw[["time", "bop_item", "Componentă", "stk_flow", "Sens", "geo", "valoare"]].copy()
    date_df.columns = ["Luna", "Cod bop_item", "Componentă", "Cod stk_flow", "Sens",
                       "Țara", "Valoare (mil. EUR)"]
    date_df = date_df.sort_values(["Luna", "Cod bop_item", "Cod stk_flow"]).reset_index(drop=True)

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Fluxurile de investiții financiare ale României cu restul lumii",
        "subtitlu": "Contul financiar al balanței de plăți, lunar: investiții directe, "
                    "investiții de portofoliu, alte investiții și active de rezervă.",
        "sursa": "Eurostat — balanța de plăți lunară (date raportate de BNR)",
        "sursa_url": PAGINA,
        "cod_set": (f"{DATASET}; filtre: geo=RO, partner=WRL_REST (restul lumii), "
                    "currency=MIO_EUR, sector10=S1, sectpart=S1, "
                    "stk_flow=NET|ASS|LIAB, bop_item=" + "|".join(ITEME) +
                    "; benchmark: geo=" + "|".join(TARI_BENCH)),
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "milioane EUR, fluxuri lunare (nu solduri)",
        "descarcat": azi,
        "licenta": "Eurostat — reutilizare liberă cu menționarea sursei (Decizia 2011/833/UE).",
        "metodologie": (
            "Manualul FMI privind balanța de plăți, ediția a 6-a (BPM6). Contul financiar "
            "înregistrează tranzacțiile cu active și pasive financiare între rezidenți și "
            "nerezidenți. „Active” = achiziția netă de active financiare de către rezidenți "
            "(bani care ies din țară ca investiție în străinătate). „Pasive” = asumarea netă "
            "de obligații față de nerezidenți (bani care intră în țară ca investiție străină). "
            "„Net” = Active − Pasive; un net negativ înseamnă că România a atras mai mult "
            "capital decât a plasat în afară. Datele sunt fluxuri lunare, nu solduri."),
        "script": "scripts/financiara_04_01.py",
        "note": [
            "Investițiile directe presupun o participație de cel puțin 10% și o relație "
            "durabilă între investitor și firma-țintă; investițiile de portofoliu sunt "
            "plasamente financiare fără control (acțiuni listate, obligațiuni).",
            "„Alte investiții” cuprind credite, depozite, numerar și credite comerciale — "
            "componenta cea mai volatilă de la o lună la alta.",
            "Activele de rezervă sunt gestionate de BNR; o valoare pozitivă înseamnă "
            "acumulare de rezerve valutare.",
            "Partenerul este „restul lumii” (WRL_REST), adică toate țările, nu doar UE.",
            "Fluxurile lunare sunt foarte volatile; foaia „Cumulat 12 luni” oferă imaginea "
            "de tendință.",
        ],
        "avertismente": [
            "O cerere largă pe bop_c6_m întoarce HTTP 413 (EXTRACTION_TOO_BIG / "
            "ASYNCHRONOUS_RESPONSE). Este obligatoriu să filtrezi simultan geo, partner, "
            "currency, sector10, sectpart, stk_flow și bop_item.",
            "Codurile bop_item folosesc dublu underscore (FA__P__F3), nu underscore simplu; "
            "un cod greșit întoarce un răspuns 200 cu `value` gol, nu o eroare.",
            "Ultimele 1-2 luni sunt date preliminare și se revizuiesc; revizuirile pot fi "
            "de ordinul sutelor de milioane de euro.",
            "Semnul din BPM6 diferă de convenția BPM5: în BPM6 o intrare de capital apare "
            "ca pasiv pozitiv, nu ca flux negativ.",
            "Eurostat NU publică seria lunară a activelor de rezervă (bop_item=FA__R__F) "
            "pentru România — codul este acceptat de API, dar întoarce doar valori goale. "
            "Scriptul îl cere oricum și tratează absența ca atare, fără să inventeze valori. "
            "Rezervele valutare oficiale se urmăresc separat, din statistica BNR.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta, date_df=date_df,
        analize={
            "Fluxuri nete lunare": a_net,
            "Cumulat 12 luni": a_12,
            "Active vs pasive": a_al.round(1),
            "Structura portofoliului": a_port,
            "Agregat anual": a_anual_flat,
            "Comparație regională": a_bench,
            "Sinteza ultimei luni": a_rez,
        },
        note_analize={
            "Fluxuri nete lunare": "Fluxul net (active − pasive) pe fiecare componentă a contului financiar, mil. EUR.",
            "Cumulat 12 luni": "Suma mobilă pe 12 luni a fluxurilor nete — elimină sezonalitatea lunară.",
            "Active vs pasive": "Separat: câți bani au plasat rezidenții în afară (active) și cât capital "
                                "străin a intrat (pasive), pe cele trei categorii mari.",
            "Structura portofoliului": "Investițiile de portofoliu descompuse în acțiuni/unități de fond și "
                                       "titluri de datorie (obligațiuni).",
            "Agregat anual": "Suma fluxurilor lunare pe an calendaristic. Ultimul an conține doar lunile raportate.",
            "Comparație regională": "Fluxuri nete cumulate pe 12 luni, România față de patru economii din regiune.",
            "Sinteza ultimei luni": "Fotografia ultimei luni disponibile, cu cumulatul anual și media istorică.",
        },
        numfmt="#,##0")

    # --- pagina HTML ------------------------------------------------------
    et = [ro_luna(p) for p in net.index]
    et12 = [ro_luna(p) for p in net12.dropna(how="all").index]
    n12 = net12.dropna(how="all")

    fa_net_12 = float(u12.get("FA", float("nan")))
    dir_12 = float(u12.get("FA__D__F", float("nan")))
    port_12 = float(u12.get("FA__P__F", float("nan")))
    rez_12 = float(u12.get("FA__R__F", float("nan")))
    alt_12 = float(u12.get("FA__O__F", float("nan")))
    # Componentele efectiv disponibile nu reconstituie totalul: Eurostat nu publică lunar
    # activele de rezervă pentru România, iar ele intră în agregatul FA. Calculăm și
    # declarăm explicit reziduul, în loc să pretindem că sunt afișate „toate componentele".
    comp_disp = [c for c in MARI if c in net12.columns and net12[c].notna().any()]
    rezidual_12 = float(fa_net_12 - sum(float(u12.get(c, 0) or 0) for c in comp_disp))
    port_12_prec = float(net12["FA__P__F"].iloc[-13]) if len(net12) > 13 else None

    def semn(v, dec=0):
        return ("+" if v >= 0 else "−") + ro_num(abs(v), dec)

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Eurostat — bop_c6_m (balanța de plăți lunară, BPM6)",
        "sursa_url": PAGINA,
        "frecventa": "Lunar",
        "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": "Investiții directe, net — ultimele 12 luni",
             "valoare": f"{semn(dir_12)} mil. EUR",
             "nota": "valoare negativă = România a atras capital direct din afară",
             "trend": "up" if dir_12 < 0 else "down"},
            {"eticheta": "Investiții de portofoliu, net — ultimele 12 luni",
             "valoare": f"{semn(port_12)} mil. EUR",
             "nota": ("față de " + semn(port_12_prec) + " în anul precedent")
                     if port_12_prec is not None else "cumulat pe 12 luni",
             "trend": "up" if port_12 < 0 else "down"},
            {"eticheta": "Contul financiar total, net — 12 luni",
             "valoare": f"{semn(fa_net_12)} mil. EUR",
             "nota": ("agregatul publicat de Eurostat; cu "
                      f"{semn(rezidual_12)} mil. EUR peste componentele afișate, "
                      "diferență dată de activele de rezervă"
                      if pd.notna(rezidual_12) and abs(rezidual_12) > 1
                      else "active minus pasive")},
            ({"eticheta": "Active de rezervă (BNR) — 12 luni",
              "valoare": f"{semn(rez_12)} mil. EUR",
              "nota": f"ultima lună raportată: {ro_luna(per_max)}"}
             if pd.notna(rez_12) else
             {"eticheta": "Alte investiții, net — ultimele 12 luni",
              "valoare": f"{semn(alt_12)} mil. EUR",
              "nota": "credite, depozite și numerar — cea mai volatilă componentă"}),
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Investiții directe și de portofoliu — flux net cumulat pe 12 luni",
             "subtitlu": "Valorile negative arată capital care intră în România; cele pozitive, "
                         "capital care iese. Cumularea pe 12 luni elimină zgomotul lunar.",
             "labels": et12, "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "series": [
                 {"name": "Investiții directe", "data": clean(n12["FA__D__F"])},
                 {"name": "Investiții de portofoliu", "data": clean(n12["FA__P__F"])},
                 {"name": "Alte investiții", "data": clean(n12["FA__O__F"])},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Investițiile de portofoliu: cine cumpără și cine vinde",
             "subtitlu": "Active = plasamentele românilor în titluri străine. Pasive = titluri "
                         "românești cumpărate de nerezidenți. Ambele cumulate pe 12 luni.",
             "labels": et12, "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "series": [
                 {"name": "Pasive — capital străin intrat", "data": clean(lia12["FA__P__F"].loc[n12.index])},
                 {"name": "Active — capital plasat în afară", "data": clean(ass12["FA__P__F"].loc[n12.index])},
                 {"name": "Net (active − pasive)", "data": clean(n12["FA__P__F"])},
             ]},
            {"id": "c3", "type": "bar",
             "titlu": "Componentele contului financiar, pe ani",
             "subtitlu": "Suma fluxurilor nete lunare din fiecare an calendaristic. Ultimul an "
                         "cuprinde doar lunile raportate. Barele nu reconstituie totalul "
                         "contului financiar: activele de rezervă nu sunt publicate lunar "
                         "pentru România.",
             "labels": list(a_anual_flat["An"]), "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "stacked": True,
             "series": [{"name": ITEME[c], "data": clean(a_anual_flat[ITEME[c] + " (mil. EUR)"])}
                        for c in MARI if ITEME[c] + " (mil. EUR)" in a_anual_flat.columns]},
            {"id": "c4", "type": "line",
             "titlu": "Portofoliu: acțiuni față de titluri de datorie",
             "subtitlu": "Aproape tot fluxul de portofoliu al României trece prin obligațiuni "
                         "de stat, nu prin acțiuni. Cumulat pe 12 luni.",
             "labels": et12, "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "series": [
                 {"name": "Titluri de datorie", "data": clean(net12["FA__P__F3"].loc[n12.index])},
                 {"name": "Acțiuni și unități de fond", "data": clean(net12["FA__P__F5"].loc[n12.index])},
             ]},
            {"id": "c5", "type": "line",
             "titlu": "România față de regiune — investiții de portofoliu, net",
             "subtitlu": "Flux net cumulat pe 12 luni, în milioane de euro. Sub zero înseamnă "
                         "că țara a atras mai mult capital de portofoliu decât a plasat în afară.",
             "labels": [ro_luna(p) for p in b_port12.dropna(how="all").index],
             "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "series": [{"name": t, "data": clean(b_port12.dropna(how="all")[t])}
                        for t in ordine_b]},
        ],
        "tabel": {
            "titlu": f"Fluxuri nete lunare — ultimele 36 de luni ({len(net)} luni în fișierul Excel)",
            "columns": ["Luna"] + [ITEME[c] for c in MARI if c in net.columns] + ["Total cont financiar"],
            "rows": [[ro_luna(idx)] + [ro_num(r[c], 0) for c in MARI if c in net.columns]
                     + [ro_num(r.get("FA"), 0)]
                     for idx, r in net.tail(36).iloc[::-1].iterrows()],
        },
        "note": [
            "Sursa: Eurostat, setul <code>bop_c6_m</code> — balanța de plăți lunară a României, "
            "compilată de BNR după metodologia BPM6 a FMI și transmisă Eurostat.",
            "<strong>Cum se citesc semnele.</strong> „Active” sunt banii pe care rezidenții "
            "români îi plasează în active financiare din străinătate. „Pasive” sunt banii pe "
            "care nerezidenții îi plasează în România. „Net” = active − pasive. Un net negativ "
            "înseamnă intrare netă de capital: România primește mai mult decât trimite.",
            "<strong>De ce contează.</strong> O ieșire netă susținută de investiții de portofoliu "
            "arată că investitorii străini își retrag banii din obligațiunile și acțiunile "
            "românești — de obicei un semnal de neîncredere în finanțele publice sau în moneda "
            "națională, care pune presiune pe curs și pe costul împrumutului de stat. O intrare "
            "netă mare, în schimb, finanțează deficitul de cont curent, dar o face cu bani "
            "„fierbinți”, care pot pleca rapid.",
            "Investițiile directe (participații de peste 10%, fabrici, achiziții de firme) sunt "
            "considerabil mai stabile decât cele de portofoliu și sunt forma preferată de "
            "finanțare externă.",
            "Fluxurile lunare sunt extrem de volatile — o singură emisiune de eurobonduri poate "
            "muta cifra lunii cu miliarde de euro. De aceea graficele folosesc cumulat pe 12 luni.",
            "<strong>De ce nu se adună componentele la total.</strong> Eurostat nu publică "
            "lunar activele de rezervă ale BNR pentru România, deși ele fac parte din contul "
            "financiar. Diferența dintre totalul publicat și suma componentelor afișate "
            f"({semn(rezidual_12)} mil. EUR în ultimele 12 luni) corespunde tocmai acestei "
            "poziții lipsă. Nu am completat-o prin deducere în serii, ci o semnalăm ca atare.",
            "Ultimele luni sunt preliminare și se revizuiesc. Datele se actualizează lunar, "
            "cu aproximativ 6-8 săptămâni decalaj.",
            "Regenerare: <code>python3 scripts/financiara_04_01.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(raw)} obs. RO + {len(bench)} benchmark, {per_min} → {per_max}")


if __name__ == "__main__":
    main()
