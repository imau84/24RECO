#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 01 01 — Randamentul titlurilor de stat pe 10 ani (criteriul Maastricht)
Sursa: Eurostat, set `irt_lt_mcby_m` (EMU convergence criterion series - monthly data)
Frecvență: lunară. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.
"""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 01 01"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
DATASET = "irt_lt_mcby_m"
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
PAGINA = "https://ec.europa.eu/eurostat/databrowser/view/irt_lt_mcby_m/default/table"

TARI = {"RO": "România", "PL": "Polonia", "HU": "Ungaria", "CZ": "Cehia",
        "BG": "Bulgaria", "DE": "Germania", "EA": "Zona euro"}
START = "2005-01"


def descarca() -> pd.DataFrame:
    url = (f"{BASE}/{DATASET}?format=JSON&lang=EN&int_rt=MCBY"
           + "".join(f"&geo={g}" for g in TARI) + f"&sinceTimePeriod={START}")
    js = fetch(url, expect="json").json()
    per = js["dimension"]["time"]["category"]["index"]
    geo = js["dimension"]["geo"]["category"]["index"]
    inv_per = {v: k for k, v in per.items()}
    inv_geo = {v: k for k, v in geo.items()}
    n_per = len(per)
    randuri = []
    for idx, val in js["value"].items():
        i = int(idx)
        g = inv_geo[i // n_per]
        t = inv_per[i % n_per]
        if val is None:
            continue
        randuri.append({"perioada": t, "geo": g, "tara": TARI[g], "randament_pct": float(val)})
    df = pd.DataFrame(randuri).sort_values(["perioada", "geo"]).reset_index(drop=True)
    fail_if_short(df, 1000, "Eurostat irt_lt_mcby_m")
    fail_if_stale(df[df.geo == "RO"].perioada.max(), 3, "randament RO")
    return df


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()
    wide = df.pivot(index="perioada", columns="tara", values="randament_pct").sort_index()
    ordine = [TARI[k] for k in TARI if TARI[k] in wide.columns]
    wide = wide[ordine]
    ro = wide["România"].dropna()
    per_min, per_max = wide.index.min(), ro.index.max()

    # --- analize ----------------------------------------------------------
    a_serii = wide.round(2).reset_index().rename(columns={"perioada": "Luna"})

    a_var = pd.DataFrame({
        "Luna": ro.index,
        "Randament RO (%)": ro.round(2).values,
        "Variație lunară (p.p.)": ro.diff().round(2).values,
        "Variație 12 luni (p.p.)": ro.diff(12).round(2).values,
        "Medie mobilă 12 luni (%)": ro.rolling(12).mean().round(2).values,
    })

    spread = pd.DataFrame({"Luna": wide.index})
    for t in ordine:
        if t != "România":
            spread[f"RO – {t} (p.p.)"] = (wide["România"] - wide[t]).round(2).values
    spread = spread.dropna(how="all", subset=[c for c in spread.columns if c != "Luna"])

    an = ro.groupby(ro.index.str[:4])
    a_anual = pd.DataFrame({
        "An": an.mean().index,
        "Medie anuală (%)": an.mean().round(2).values,
        "Minim (%)": an.min().round(2).values,
        "Maxim (%)": an.max().round(2).values,
        "Amplitudine (p.p.)": (an.max() - an.min()).round(2).values,
        "Luni raportate": an.count().values,
    })

    ultim = wide.tail(1).T.reset_index()
    ultim.columns = ["Țara", f"Randament {ro_luna(per_max)} (%)"]
    ultim["Acum 12 luni (%)"] = [wide[t].iloc[-13] if len(wide) > 13 else None for t in ultim["Țara"]]
    ultim["Variație (p.p.)"] = (ultim.iloc[:, 1] - ultim["Acum 12 luni (%)"]).round(2)
    ultim["Diferență față de România (p.p.)"] = (
        ultim.iloc[:, 1] - float(ro.iloc[-1])).round(2)
    ultim = ultim.round(2)

    a_extreme = pd.DataFrame({
        "Indicator": ["Maxim istoric RO", "Minim istoric RO", "Ultima valoare RO",
                      "Medie 2005–prezent", "Medie ultimele 12 luni",
                      "Medie ultimele 36 luni"],
        "Valoare (%)": [ro.max(), ro.min(), ro.iloc[-1], ro.mean(),
                        ro.tail(12).mean(), ro.tail(36).mean()],
        "Luna": [ro.idxmax(), ro.idxmin(), ro.index[-1], "—", "—", "—"],
    }).round(2)

    meta = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": "Randamentul titlurilor de stat pe 10 ani (criteriul Maastricht)",
        "subtitlu": "Rata dobânzii pe termen lung folosită la evaluarea convergenței, "
                    "România în comparație cu economiile din regiune și zona euro.",
        "sursa": "Eurostat (date raportate de BNR / Ministerul Finanțelor)",
        "sursa_url": PAGINA,
        "cod_set": f"{DATASET}, dimensiune int_rt=MCBY",
        "frecventa": "Lunară",
        "perioada": (f"{ro.index.min()} → {per_max} pentru România ({len(ro)} luni raportate); "
                     f"setul acoperă {per_min} → {wide.index.max()} pe ansamblul țărilor "
                     f"({len(wide)} luni). Seria românească începe în {ro.index.min()}."),
        "unitate": "procente pe an (% p.a.); diferențele sunt în puncte procentuale (p.p.)",
        "descarcat": azi,
        "licenta": "Eurostat — reutilizare liberă cu menționarea sursei "
                   "(Decizia 2011/833/UE).",
        "metodologie": "Randamentul mediu lunar al obligațiunilor de stat pe termen lung "
                       "(aprox. 10 ani), pe piața secundară, brut de impozit, conform "
                       "definiției criteriului de convergență Maastricht. Valorile sunt "
                       "medii ale cotațiilor zilnice din luna respectivă.",
        "script": "scripts/financiara_01_01.py",
        "note": [
            "Zona euro (EA) este agregatul ponderat al randamentelor din statele membre.",
            "Diferența (spread-ul) față de Germania este indicatorul uzual de risc suveran.",
            "Valorile lipsă apar când o țară nu are emisiuni lichide pe maturitatea de referință.",
        ],
        "avertismente": [
            "Eurostat listează uneori eticheta lunii curente fără valori — filtrarea se face "
            "după valoare, nu după etichetă.",
            "Nu folosi codul CP00 / coduri de tip 'TOTAL' pe acest set; dimensiunea corectă "
            "este int_rt=MCBY.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=df.rename(columns={"perioada": "Luna", "geo": "Cod țară",
                                   "tara": "Țara", "randament_pct": "Randament (%)"}),
        analize={
            "Serii lunare": a_serii,
            "Dinamica României": a_var,
            "Spread vs. regiune": spread,
            "Medii anuale RO": a_anual,
            "Situația ultimei luni": ultim,
            "Repere istorice RO": a_extreme,
        },
        note_analize={
            "Serii lunare": "Randamentele lunare, o coloană per țară (%).",
            "Dinamica României": "Variații lunare, anuale și medie mobilă pe 12 luni.",
            "Spread vs. regiune": "Diferența dintre randamentul României și fiecare comparabil, "
                                  "în puncte procentuale. Valori pozitive = România se împrumută mai scump.",
            "Medii anuale RO": "Agregare anuală a seriei lunare pentru România.",
            "Situația ultimei luni": "Fotografia ultimei luni disponibile, cu variația față de anul trecut.",
            "Repere istorice RO": "Maxime, minime și medii pe diverse ferestre.",
        },
        numfmt="0.00")

    # --- pagina HTML ------------------------------------------------------
    et = [ro_luna(p) for p in wide.index]
    ultim_ro = float(ro.iloc[-1])
    var12 = float(ro.iloc[-1] - ro.iloc[-13]) if len(ro) > 13 else None
    sp_de = float(wide["România"].iloc[-1] - wide["Germania"].iloc[-1])

    spec = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Eurostat — irt_lt_mcby_m", "sursa_url": PAGINA,
        "frecventa": "Lunar",
        "perioada": f"{ro_luna(ro.index.min())} – {ro_luna(per_max)} (România)",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Randament România, {ro_luna(per_max)}",
             "valoare": f"{ro_num(ultim_ro, 2)}%", "nota": "obligațiuni de stat pe 10 ani"},
            {"eticheta": "Variație față de anul trecut",
             "valoare": f"{'+' if (var12 or 0) >= 0 else ''}{ro_num(var12, 2)} p.p.",
             "nota": f"față de {ro_luna(ro.index[-13])}",
             "trend": "down" if (var12 or 0) > 0 else "up"},
            {"eticheta": "Diferență față de Germania",
             "valoare": f"{ro_num(sp_de, 2)} p.p.", "nota": "prima de risc suveran"},
            {"eticheta": "Medie ultimele 12 luni",
             "valoare": f"{ro_num(ro.tail(12).mean(), 2)}%",
             "nota": f"maxim istoric {ro_num(ro.max(), 2)}% ({ro_luna(ro.idxmax())})"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Randamentul titlurilor de stat românești pe 10 ani",
             "subtitlu": "Media lunară a cotațiilor de pe piața secundară, în procente pe an.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 1, "fill": True,
             "series": [{"name": "România", "data": clean(wide["România"])}]},
            {"id": "c2", "type": "line",
             "titlu": "România în comparație cu regiunea",
             "subtitlu": "Cu cât randamentul e mai mare, cu atât statul se împrumută mai scump.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 1,
             "series": [{"name": t, "data": clean(wide[t])} for t in ordine]},
            {"id": "c3", "type": "line",
             "titlu": "Prima de risc față de Germania și zona euro",
             "subtitlu": "Diferența de randament, în puncte procentuale.",
             "labels": et, "unit": "p.p.", "dec": 2, "ydec": 1,
             "series": [
                 {"name": "RO – Germania", "data": clean(wide["România"] - wide["Germania"])},
                 {"name": "RO – Zona euro", "data": clean(wide["România"] - wide["Zona euro"])},
                 {"name": "RO – Polonia", "data": clean(wide["România"] - wide["Polonia"])},
             ]},
            {"id": "c4", "type": "bar",
             "titlu": "Media anuală a randamentului în România",
             "subtitlu": "Agregare a seriei lunare; ultimul an conține doar lunile raportate.",
             "labels": list(a_anual["An"]), "unit": "%", "dec": 2, "ydec": 0, "zero": True,
             "series": [{"name": "Medie anuală", "data": clean(a_anual["Medie anuală (%)"])}]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(wide)} luni în fișierul Excel)",
            "columns": ["Luna"] + ordine,
            "rows": [[ro_luna(idx)] + [ro_num(r[t], 2) for t in ordine]
                     for idx, r in wide.tail(36).iloc[::-1].iterrows()],
        },
        "note": [
            "Sursa: Eurostat, setul <code>irt_lt_mcby_m</code> — seria criteriului de convergență "
            "Maastricht pentru ratele dobânzii pe termen lung, raportată de băncile centrale naționale.",
            "Indicatorul este randamentul mediu lunar al obligațiunilor de stat cu maturitate reziduală "
            "de aproximativ 10 ani, tranzacționate pe piața secundară, brut de impozit.",
            "Diferența față de Germania (spread) este cel mai folosit indicator de risc suveran: "
            "arată cât plătește în plus România față de emitentul de referință din zona euro.",
            "Datele se actualizează lunar, cu un decalaj de câteva zile față de încheierea lunii. "
            "Seria pentru România începe în aprilie 2005, când a devenit disponibilă o cotație de "
            "referință pe maturitatea de 10 ani; lunile anterioare din set aparțin celorlalte țări.",
            "Regenerare: <code>python3 scripts/financiara_01_01.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(df)} obs., {len(wide)} luni, {per_min} → {per_max}, "
          f"RO ultim = {ultim_ro:.2f}%")


if __name__ == "__main__":
    main()
