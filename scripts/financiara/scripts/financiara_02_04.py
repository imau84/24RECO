#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 02 04 — Cursul de schimb al leului și dobânzile de referință
Surse: BCE (ECB Data Portal, setul EXR) — cursuri de referință lunare;
       BIS (WS_CBPOL) — rata dobânzii de politică monetară a BNR;
       Eurostat (irt_st_m) — ratele dobânzii de pe piața monetară interbancară.
Frecvență: lunară. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.
"""
import datetime as dt
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 02 04"
SECTIUNE = "02 Bănci"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
START = "2007-01"

EXR_API = "https://data-api.ecb.europa.eu/service/data/EXR"
EXR_PAGINA = "https://data.ecb.europa.eu/data/datasets/EXR"
BIS_URL = "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.RO?format=csv"
BIS_PAGINA = "https://data.bis.org/topics/CBPOL"
EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/irt_st_m"
            "?format=JSON&lang=EN&geo=RO&sinceTimePeriod=" + START)
EUROSTAT_PAGINA = "https://ec.europa.eu/eurostat/databrowser/view/irt_st_m/default/table"

# Cheie SDMX EXR = 5 dimensiuni / 4 puncte:
# FREQ.CURRENCY.CURRENCY_DENOM.EXR_TYPE.EXR_SUFFIX
VALUTE = {"USD": "dolarul american", "CHF": "francul elvețian", "GBP": "lira sterlină"}
REGIUNE = {"PLN": "zlotul polonez", "HUF": "forintul maghiar", "CZK": "coroana cehă"}
EXR_CHEIE = "M." + "+".join(["RON"] + list(VALUTE) + list(REGIUNE)) + ".EUR.SP00.A"

ROBOR = {"IRT_DTD": "Rata overnight (o zi)", "IRT_M1": "Rata la 1 lună",
         "IRT_M3": "Rata la 3 luni", "IRT_M6": "Rata la 6 luni",
         "IRT_M12": "Rata la 12 luni"}


def descarca_exr() -> pd.DataFrame:
    url = f"{EXR_API}/{EXR_CHEIE}?format=csvdata&startPeriod={START}&detail=dataonly"
    txt = fetch(url).content.decode("utf-8")
    if txt.lstrip().startswith("<"):
        raise SystemExit("EȘEC: ECB EXR a întors HTML — cheia SDMX are un număr greșit de puncte.")
    d = pd.read_csv(io.StringIO(txt), low_memory=False)
    d = d[d.OBS_VALUE.notna()].copy()
    lipsa = sorted(set(["RON"] + list(VALUTE) + list(REGIUNE)) - set(d.CURRENCY.unique()))
    if lipsa:
        raise SystemExit("EȘEC: ECB EXR nu a întors date pentru: " + ", ".join(lipsa))
    return d.rename(columns={"TIME_PERIOD": "luna", "OBS_VALUE": "valoare",
                             "CURRENCY": "moneda"})[["luna", "moneda", "valoare"]]


def descarca_bis() -> pd.Series:
    txt = fetch(BIS_URL).content.decode("utf-8")
    if txt.lstrip().startswith("<"):
        raise SystemExit("EȘEC: BIS a întors HTML în loc de CSV.")
    d = pd.read_csv(io.StringIO(txt), low_memory=False)
    d = d[d.OBS_VALUE.notna()]
    d = d[d.TIME_PERIOD >= START]
    if d.empty:
        raise SystemExit("EȘEC: BIS WS_CBPOL nu a întors nicio observație pentru România.")
    return d.set_index("TIME_PERIOD").OBS_VALUE.astype(float).sort_index()


def descarca_eurostat() -> pd.DataFrame:
    js = json.loads(fetch(EUROSTAT, expect="json").content.decode("utf-8"))
    dims = js["id"]
    sizes = js["size"]
    idx = {d: {v: k for k, v in js["dimension"][d]["category"]["index"].items()} for d in dims}
    randuri = []
    for pos, val in js["value"].items():
        if val is None:
            continue
        p = int(pos)
        coord = []
        for s in reversed(sizes):
            coord.append(p % s)
            p //= s
        coord = list(reversed(coord))
        rec = {d: idx[d][c] for d, c in zip(dims, coord)}
        randuri.append({"luna": rec["time"], "cod": rec["int_rt"], "valoare": float(val)})
    d = pd.DataFrame(randuri)
    if d.empty or not set(ROBOR).issubset(set(d.cod.unique())):
        raise SystemExit("EȘEC: Eurostat irt_st_m nu a întors toate maturitățile pentru România.")
    d["indicator"] = d.cod.map(ROBOR)
    return d.sort_values(["luna", "cod"]).reset_index(drop=True)


def main() -> None:
    exr = descarca_exr()
    bis = descarca_bis()
    est = descarca_eurostat()
    fail_if_short(exr, 1200, "ECB EXR — cursuri lunare")
    fail_if_short(est, 900, "Eurostat irt_st_m — dobânzi piața monetară RO")

    e = exr.pivot(index="luna", columns="moneda", values="valoare").sort_index()
    ultima = e["RON"].dropna().index.max()
    fail_if_stale(ultima, 3, "ECB EXR RON/EUR")
    fail_if_stale(bis.index.max(), 3, "BIS — rata de politică monetară a BNR")
    prima = e.index.min()
    azi = dt.date.today().isoformat()

    # Cursuri directe: lei pentru o unitate de valută (cross-rate prin euro).
    curs = pd.DataFrame(index=e.index)
    curs["RON/EUR"] = e["RON"]
    for v in VALUTE:
        curs[f"RON/{v}"] = e["RON"] / e[v]

    # Deprecierea cumulată față de euro, bază = prima lună disponibilă.
    baza = e.loc[prima]
    idx_reg = pd.DataFrame(index=e.index)
    for m, nume in [("RON", "leul românesc")] + list(REGIUNE.items()):
        idx_reg[nume] = 100 * e[m] / baza[m]

    robor = est.pivot(index="luna", columns="indicator", values="valoare").sort_index()
    pol = bis.reindex(sorted(set(bis.index) | set(curs.index))).sort_index()

    # --- foi de analiză ----------------------------------------------------
    a_curs = curs.round(4).reset_index().rename(columns={"luna": "Luna"})

    a_var = pd.DataFrame({"Luna": curs.index})
    for c in curs.columns:
        s = curs[c]
        a_var[f"{c}"] = s.round(4).values
        a_var[f"{c} — variație lunară (%)"] = (100 * s.pct_change()).round(2).values
        a_var[f"{c} — variație 12 luni (%)"] = (100 * s.pct_change(12)).round(2).values

    ron = curs["RON/EUR"]
    var_l = ron.pct_change()
    a_vol = pd.DataFrame({
        "Luna": curs.index,
        "Curs RON/EUR": ron.round(4).values,
        "Variație lunară (%)": (100 * var_l).round(3).values,
        "Volatilitate 12 luni (%)": (100 * var_l.rolling(12).std()).round(3).values,
        "Volatilitate anualizată (%)": (100 * var_l.rolling(12).std() * np.sqrt(12)).round(3).values,
        "Medie mobilă 12 luni": ron.rolling(12).mean().round(4).values,
        "Abatere față de media pe 12 luni (%)":
            (100 * (ron / ron.rolling(12).mean() - 1)).round(2).values,
    })

    a_reg = idx_reg.round(1).reset_index().rename(columns={"luna": "Luna"})

    a_dob = pd.DataFrame({"Luna": curs.index})
    a_dob["Rata de politică monetară BNR (%)"] = pol.reindex(curs.index).round(2).values
    for c in [ROBOR[k] for k in ["IRT_DTD", "IRT_M1", "IRT_M3", "IRT_M6", "IRT_M12"]]:
        a_dob[f"{c} (%)"] = robor.reindex(curs.index)[c].round(2).values
    a_dob["Spread 3 luni – rata BNR (p.p.)"] = (
        robor.reindex(curs.index)[ROBOR["IRT_M3"]] - pol.reindex(curs.index)).round(2).values
    a_dob["Panta 12 luni – 3 luni (p.p.)"] = (
        robor.reindex(curs.index)[ROBOR["IRT_M12"]]
        - robor.reindex(curs.index)[ROBOR["IRT_M3"]]).round(2).values

    an_idx = curs.index.str[:4]
    a_anual = pd.DataFrame({"An": sorted(set(an_idx))})
    for c in curs.columns:
        g = curs[c].groupby(an_idx)
        a_anual[f"{c} — medie"] = g.mean().round(4).values
        a_anual[f"{c} — minim"] = g.min().round(4).values
        a_anual[f"{c} — maxim"] = g.max().round(4).values
    a_anual["Rata BNR — medie (%)"] = pol.reindex(curs.index).groupby(an_idx).mean().round(2).values
    a_anual["Rata 3 luni — medie (%)"] = \
        robor.reindex(curs.index)[ROBOR["IRT_M3"]].groupby(an_idx).mean().round(2).values
    a_anual["Luni raportate"] = ron.groupby(an_idx).count().values

    rep = []
    for c in list(curs.columns):
        s = curs[c].dropna()
        rep.append({"Indicator": c, "Minim": round(s.min(), 4), "Luna minimului": s.idxmin(),
                    "Maxim": round(s.max(), 4), "Luna maximului": s.idxmax(),
                    "Ultima valoare": round(s.iloc[-1], 4), "Ultima lună": s.index[-1],
                    "Variație de la începutul seriei (%)":
                        round(100 * (s.iloc[-1] / s.iloc[0] - 1), 1)})
    for nume, s in (("Rata de politică monetară BNR (%)", pol.dropna()),
                    ("Rata piața monetară 3 luni (%)", robor[ROBOR["IRT_M3"]].dropna())):
        rep.append({"Indicator": nume, "Minim": round(s.min(), 2), "Luna minimului": s.idxmin(),
                    "Maxim": round(s.max(), 2), "Luna maximului": s.idxmax(),
                    "Ultima valoare": round(s.iloc[-1], 2), "Ultima lună": s.index[-1],
                    "Variație de la începutul seriei (%)": None})
    a_rep = pd.DataFrame(rep)

    a_surse = pd.DataFrame([
        {"Indicator": "Curs RON/EUR, mediu lunar", "Sursă": "BCE — EXR",
         "Cheie / cod": "M.RON.EUR.SP00.A", "Observație":
             "Cursul de referință al BCE, media aritmetică a cotațiilor zilnice din lună."},
        {"Indicator": "Curs RON/USD, RON/CHF, RON/GBP", "Sursă": "BCE — EXR",
         "Cheie / cod": "M.RON.EUR.SP00.A ÷ M.{USD|CHF|GBP}.EUR.SP00.A",
         "Observație": "Cursuri încrucișate calculate prin euro; BCE nu publică direct "
                       "perechile RON/USD, RON/CHF sau RON/GBP."},
        {"Indicator": "Rata de politică monetară a BNR", "Sursă": "BIS — WS_CBPOL",
         "Cheie / cod": "M.RO", "Observație": "Valoarea de la sfârșitul lunii, preluată de BIS "
                                              "direct de la Banca Națională a României."},
        {"Indicator": "Dobânzile pieței monetare (tip ROBOR)", "Sursă": "Eurostat — irt_st_m",
         "Cheie / cod": "geo=RO, int_rt=IRT_DTD/M1/M3/M6/M12",
         "Observație": "Ratele interbancare pe piața monetară din România, medii lunare."},
    ])

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Cursul de schimb al leului și dobânzile de referință",
        "subtitlu": "Cât valorează leul față de euro, dolar, franc elvețian și liră, cât de "
                    "stabil este și la ce dobânzi se împrumută băncile între ele.",
        "sursa": "BCE (ECB Data Portal, setul EXR), BIS (WS_CBPOL) și Eurostat (irt_st_m)",
        "sursa_url": EXR_PAGINA,
        "cod_set": f"BCE EXR: {EXR_CHEIE} (5 dimensiuni, 4 puncte) · "
                   f"BIS: dataflow BIS/WS_CBPOL/1.0, cheie M.RO · "
                   f"Eurostat: irt_st_m, geo=RO, int_rt ∈ {{{', '.join(ROBOR)}}}",
        "frecventa": "Lunară",
        "perioada": f"{prima} → {ultima}",
        "unitate": "lei pentru o unitate de valută; dobânzile în procente pe an (% p.a.); "
                   "indicii au baza 100 în prima lună a seriei",
        "descarcat": azi,
        "licenta": "BCE și BIS — reutilizare cu menționarea sursei; Eurostat — reutilizare "
                   "liberă cu menționarea sursei (Decizia 2011/833/UE).",
        "metodologie": "Cursul RON/EUR este cursul de referință al BCE, calculat ca medie "
                       "aritmetică a cotațiilor zilnice din luna respectivă. Cursurile RON/USD, "
                       "RON/CHF și RON/GBP sunt cursuri încrucișate, obținute prin împărțirea "
                       "cursului RON/EUR la cursul valutei respective față de euro, din aceeași "
                       "sursă și aceeași lună. Volatilitatea este abaterea standard a "
                       "variațiilor lunare procentuale pe o fereastră mobilă de 12 luni, "
                       "prezentată și în formă anualizată (înmulțită cu radical din 12). "
                       "Rata de politică monetară este valoarea în vigoare la sfârșitul lunii.",
        "script": "scripts/financiara_02_04.py",
        "note": [
            "Un curs RON/EUR mai mare înseamnă un leu mai slab: e nevoie de mai mulți lei "
            "pentru un euro.",
            "Indicele regional compară deprecierea cumulată a leului cu cea a zlotului, "
            "forintului și coroanei cehe, toate raportate la euro și pornind de la 100.",
            "Rata de politică monetară a BNR este dobânda de referință pentru întreg sistemul "
            "bancar; dobânzile pieței monetare (ROBOR) urmează, de regulă, aceeași direcție.",
            "IRCC, indicele la care sunt indexate majoritatea creditelor noi în lei ale "
            "populației, se calculează din tranzacțiile efective de pe piața monetară și nu "
            "este disponibil în aceste surse internaționale.",
        ],
        "avertismente": [
            "BCE nu publică perechile RON/USD, RON/CHF, RON/GBP; ele sunt calculate aici ca "
            "raport între cursuri față de euro. Rezultatul poate diferi cu câteva zecimale de "
            "cursul publicat de BNR, care folosește altă convenție de mediere.",
            "Seria cursului EUR/BGN se oprește în decembrie 2025, odată cu intrarea Bulgariei "
            "în zona euro — leva a fost exclusă din comparația regională.",
            "Ratele Eurostat irt_st_m pentru România sunt ratele pieței monetare raportate de "
            "BNR; definiția lor nu coincide perfect cu ROBOR-ul afișat zilnic.",
            "Setul Eurostat prc_hicp_manr (inflația lunară) era, la data generării acestui "
            "fișier, actualizat doar până în decembrie 2025, deci nu a fost folosit pentru "
            "calculul dobânzilor reale.",
            "Cheia SDMX pentru EXR are exact 4 puncte; pentru BSI 11 și pentru MIR 10.",
        ],
    }

    date_df = pd.concat([
        curs.reset_index().melt(id_vars="luna", var_name="Indicator", value_name="Valoare")
        .assign(Sursa="BCE — EXR"),
        pol.dropna().rename("Valoare").reset_index()
        .rename(columns={"index": "luna", "TIME_PERIOD": "luna"})
        .assign(Indicator="Rata de politică monetară BNR (%)", Sursa="BIS — WS_CBPOL"),
        est.rename(columns={"valoare": "Valoare", "indicator": "Indicator"})[
            ["luna", "Indicator", "Valoare"]].assign(Sursa="Eurostat — irt_st_m"),
    ], ignore_index=True).rename(columns={"luna": "Luna"}).sort_values(["Luna", "Indicator"])

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=date_df.reset_index(drop=True),
        analize={
            "Cursuri lunare": a_curs,
            "Variatii curs": a_var,
            "Volatilitatea leului": a_vol,
            "Comparatie regionala": a_reg,
            "Dobanzi de referinta": a_dob,
            "Medii anuale": a_anual,
            "Repere istorice": a_rep,
            "Surse si chei": a_surse,
        },
        note_analize={
            "Cursuri lunare": "Lei pentru o unitate de valută, medii lunare.",
            "Variatii curs": "Variații lunare și față de aceeași lună a anului trecut.",
            "Volatilitatea leului": "Cât de mult se mișcă leul față de euro de la o lună la alta.",
            "Comparatie regionala": "Indice cu baza 100 în prima lună: valori peste 100 = "
                                    "moneda s-a depreciat față de euro.",
            "Dobanzi de referinta": "Rata BNR, ratele pieței monetare și diferențele dintre ele.",
            "Medii anuale": "Media, minimul și maximul fiecărui an calendaristic.",
            "Repere istorice": "Minime, maxime și variația totală de la începutul seriei.",
            "Surse si chei": "Sursa exactă și cheia SDMX pentru fiecare indicator.",
        },
        numfmt="#,##0.0000",
        numfmt_map={"Rata de politică monetară BNR (%)": "0.00"})

    # --- pagina HTML -------------------------------------------------------
    et = [ro_luna(p) for p in curs.index]
    v_eur = float(ron.iloc[-1])
    var12 = float(100 * (ron.iloc[-1] / ron.iloc[-13] - 1)) if len(ron) > 13 else None
    v_pol = float(pol.dropna().iloc[-1])
    v_m3 = float(robor[ROBOR["IRT_M3"]].dropna().iloc[-1])
    vol_a = float((100 * var_l.rolling(12).std() * np.sqrt(12)).dropna().iloc[-1])

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "BCE (EXR), BIS (WS_CBPOL) și Eurostat (irt_st_m)",
        "sursa_url": EXR_PAGINA, "frecventa": "Lunar",
        "perioada": f"{ro_luna(prima)} – {ro_luna(ultima)}", "actualizat": azi,
        "kpis": [
            {"eticheta": f"Curs RON/EUR, {ro_luna(ultima)}",
             "valoare": ro_num(v_eur, 4), "nota": "media cotațiilor zilnice din lună"},
            {"eticheta": "Deprecierea față de anul trecut",
             "valoare": f"{'+' if (var12 or 0) >= 0 else ''}{ro_num(var12, 2)}%",
             "nota": f"față de {ro_luna(ron.index[-13])}",
             "trend": "down" if (var12 or 0) > 0 else "up"},
            {"eticheta": "Rata de politică monetară a BNR",
             "valoare": f"{ro_num(v_pol, 2)}%",
             "nota": f"la finalul lunii {ro_luna(pol.dropna().index[-1])}"},
            {"eticheta": "Dobânda interbancară la 3 luni",
             "valoare": f"{ro_num(v_m3, 2)}%",
             "nota": f"volatilitatea leului: {ro_num(vol_a, 1)}% anualizat"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Cursul leului față de euro",
             "subtitlu": "Câți lei costă un euro. Linia care urcă înseamnă leu mai slab.",
             "labels": et, "unit": "lei", "dec": 4, "ydec": 2, "fill": True,
             "series": [{"name": "RON/EUR", "data": clean(ron)}]},
            {"id": "c2", "type": "line",
             "titlu": "Leul față de celelalte valute importante",
             "subtitlu": "Cursuri încrucișate calculate prin euro, din cotațiile BCE.",
             "labels": et, "unit": "lei", "dec": 4, "ydec": 1,
             "series": [{"name": f"RON/{v}", "data": clean(curs[f"RON/{v}"])} for v in VALUTE]},
            {"id": "c3", "type": "line",
             "titlu": "Leul în comparație cu monedele vecinilor",
             "subtitlu": f"Indice cu baza 100 în {ro_luna(prima)}. Valori mai mari = monedă "
                         "mai depreciată față de euro.",
             "labels": et, "unit": "", "dec": 1, "ydec": 0,
             "series": [{"name": n.capitalize(), "data": clean(idx_reg[n])}
                        for n in idx_reg.columns]},
            {"id": "c4", "type": "line",
             "titlu": "Dobânda BNR și dobânzile de pe piața interbancară",
             "subtitlu": "Rata de politică monetară stabilită de BNR și ratele la care băncile "
                         "își împrumută bani între ele.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "Rata de politică monetară BNR",
                  "data": clean(pol.reindex(curs.index))},
                 {"name": "Interbancar 3 luni",
                  "data": clean(robor.reindex(curs.index)[ROBOR["IRT_M3"]])},
                 {"name": "Interbancar 12 luni",
                  "data": clean(robor.reindex(curs.index)[ROBOR["IRT_M12"]])},
                 {"name": "Interbancar overnight",
                  "data": clean(robor.reindex(curs.index)[ROBOR["IRT_DTD"]])},
             ]},
            {"id": "c5", "type": "line",
             "titlu": "Cât de agitat este cursul leului",
             "subtitlu": "Abaterea standard a variațiilor lunare, pe o fereastră de 12 luni, "
                         "exprimată anualizat. Valori mici = curs previzibil.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "zero": True, "fill": True,
             "series": [{"name": "Volatilitate anualizată",
                         "data": clean(100 * var_l.rolling(12).std() * np.sqrt(12))}]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(curs)} luni în fișierul Excel)",
            "columns": ["Luna", "RON/EUR", "RON/USD", "RON/CHF", "RON/GBP",
                        "Variație lunară RON/EUR (%)", "Rata BNR (%)", "Interbancar 3 luni (%)"],
            "rows": [[ro_luna(i), ro_num(curs["RON/EUR"][i], 4), ro_num(curs["RON/USD"][i], 4),
                      ro_num(curs["RON/CHF"][i], 4), ro_num(curs["RON/GBP"][i], 4),
                      ro_num(100 * var_l[i], 2),
                      ro_num(pol.reindex(curs.index)[i], 2),
                      ro_num(robor.reindex(curs.index)[ROBOR["IRT_M3"]][i], 2)]
                     for i in curs.index[-36:][::-1]],
        },
        "note": [
            "Surse: <strong>BCE</strong> — ECB Data Portal, setul <code>EXR</code> (cursuri de "
            "referință); <strong>BIS</strong> — <code>WS_CBPOL</code> (rata de politică "
            "monetară, preluată de la BNR); <strong>Eurostat</strong> — <code>irt_st_m</code> "
            "(dobânzile pieței monetare).",
            "<strong>Cum se citește cursul.</strong> RON/EUR = câți lei trebuie dați pentru un "
            "euro. Când cifra crește, leul se depreciază: importurile, vacanțele în străinătate "
            "și ratele la creditele în valută devin mai scumpe.",
            "<strong>Cursurile față de dolar, franc și liră</strong> nu sunt publicate direct de "
            "BCE; ele sunt calculate aici prin euro, din aceleași cotații lunare. Pot diferi cu "
            "câteva zecimale față de cursul afișat de BNR.",
            "<strong>De ce contează dobânda BNR.</strong> Este prețul la care băncile se "
            "finanțează de la banca centrală. Când urcă, urcă și dobânzile interbancare, apoi "
            "cele la creditele și depozitele clienților — cu un decalaj de câteva luni.",
            "<strong>Volatilitatea</strong> arată cât de imprevizibil e cursul. În România a "
            "fost istoric scăzută, pentru că BNR intervine pe piață pentru a menține cursul "
            "într-un interval îngust.",
            "Regenerare: <code>python3 scripts/financiara_02_04.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(date_df)} obs., {len(curs)} luni, {prima} → {ultima}; "
          f"RON/EUR = {v_eur:.4f}, rata BNR = {v_pol:.2f}%, interbancar 3 luni = {v_m3:.2f}%")


if __name__ == "__main__":
    main()
