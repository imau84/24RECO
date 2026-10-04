#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 01 04 — Ratele dobânzii de pe piața monetară (ROBOR) și comparația regională
Sursa: Eurostat, set `irt_st_m` (Money market interest rates — monthly data).
Pentru România, seriile corespund cotațiilor ROBOR (overnight, 1, 3, 6 și 12 luni).
Frecvență: lunară, ianuarie 2007 – prezent.
"""
import datetime as dt
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 01 04"
OUT = os.path.join(HERE, "..", "out")
DATASET = "irt_st_m"
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
PAGINA = "https://ec.europa.eu/eurostat/databrowser/view/irt_st_m/default/table"

MATURITATI = {
    "IRT_DTD": "Overnight (ON)",
    "IRT_M1": "1 lună",
    "IRT_M3": "3 luni",
    "IRT_M6": "6 luni",
    "IRT_M12": "12 luni",
}
TARI = {"RO": "România", "PL": "Polonia", "HU": "Ungaria", "CZ": "Cehia", "EA": "Zona euro"}
START = "2007-01"
REF = "IRT_M3"  # maturitatea de referință: ROBOR 3M


def descarca() -> pd.DataFrame:
    url = (f"{BASE}/{DATASET}?format=JSON&lang=EN"
           + "".join(f"&geo={g}" for g in TARI)
           + "".join(f"&int_rt={m}" for m in MATURITATI)
           + f"&sinceTimePeriod={START}")
    js = fetch(url, expect="json").json()
    ids, size = js["id"], js["size"]
    invers = {k: {v: kk for kk, v in js["dimension"][k]["category"]["index"].items()}
              for k in ids}
    randuri = []
    for s, val in js["value"].items():
        if val is None:
            continue
        i = int(s)
        coord = []
        for n in reversed(size):
            coord.append(i % n)
            i //= n
        coord.reverse()
        d = {k: invers[k][c] for k, c in zip(ids, coord)}
        randuri.append({
            "perioada": d["time"], "geo": d["geo"], "tara": TARI[d["geo"]],
            "cod_maturitate": d["int_rt"], "maturitate": MATURITATI[d["int_rt"]],
            "rata_pct": float(val),
        })
    df = (pd.DataFrame(randuri)
          .sort_values(["perioada", "geo", "cod_maturitate"]).reset_index(drop=True))
    fail_if_short(df, 3000, "Eurostat irt_st_m")
    ro = df[(df.geo == "RO") & (df.cod_maturitate == REF)]
    fail_if_short(ro, 150, "Eurostat irt_st_m — România, 3 luni")
    fail_if_stale(ro.perioada.max(), 3, "rata pieței monetare RO")
    return df


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()

    ro = (df[df.geo == "RO"].pivot(index="perioada", columns="cod_maturitate",
                                   values="rata_pct").sort_index())
    ro = ro[[m for m in MATURITATI if m in ro.columns]]
    ro.columns = [MATURITATI[c] for c in ro.columns]
    reg = (df[df.cod_maturitate == REF].pivot(index="perioada", columns="tara",
                                              values="rata_pct").sort_index())
    reg = reg[[TARI[k] for k in TARI if TARI[k] in reg.columns]]

    r3 = ro["3 luni"].dropna()

    # Serii care nu mai sunt publicate (ex. overnight pentru zona euro, după EONIA).
    ultima_globala = df.perioada.max()
    incheiate = []
    for (tara, mat), g_ in df.groupby(["tara", "maturitate"]):
        ultim = g_.perioada.max()
        if ultim != ultima_globala:
            incheiate.append((f"{tara}, {mat}", ultim))
    incheiate.sort(key=lambda x: x[1], reverse=True)
    per_min, per_max = ro.index.min(), r3.index[-1]

    # ---------------- foi de analiză ----------------
    a_serii = ro.round(2).reset_index().rename(columns={"perioada": "Luna"})

    a_dinamica = pd.DataFrame({
        "Luna": r3.index,
        "Rata 3 luni (%)": r3.round(2).values,
        "Variație lunară (p.p.)": r3.diff().round(2).values,
        "Variație 12 luni (p.p.)": r3.diff(12).round(2).values,
        "Medie mobilă 12 luni (%)": r3.rolling(12).mean().round(2).values,
        "Minim ultimele 12 luni (%)": r3.rolling(12).min().round(2).values,
        "Maxim ultimele 12 luni (%)": r3.rolling(12).max().round(2).values,
    })

    a_curba = pd.DataFrame({"Luna": ro.index})
    if "12 luni" in ro and "1 lună" in ro:
        a_curba["Panta 12 luni – 1 lună (p.p.)"] = (ro["12 luni"] - ro["1 lună"]).round(2).values
    if "12 luni" in ro and "Overnight (ON)" in ro:
        a_curba["Panta 12 luni – overnight (p.p.)"] = (
            ro["12 luni"] - ro["Overnight (ON)"]).round(2).values
    if "3 luni" in ro and "Overnight (ON)" in ro:
        a_curba["Tensiune 3 luni – overnight (p.p.)"] = (
            ro["3 luni"] - ro["Overnight (ON)"]).round(2).values
    a_curba["Rata 3 luni (%)"] = ro["3 luni"].round(2).values

    a_reg = reg.round(2).reset_index().rename(columns={"perioada": "Luna"})
    for t in reg.columns:
        if t != "România":
            a_reg[f"RO – {t} (p.p.)"] = (reg["România"] - reg[t]).round(2).values

    an = r3.groupby(r3.index.str[:4])
    a_anual = pd.DataFrame({
        "An": an.mean().index,
        "Medie anuală 3 luni (%)": an.mean().round(2).values,
        "Minim (%)": an.min().round(2).values,
        "Maxim (%)": an.max().round(2).values,
        "Amplitudine (p.p.)": (an.max() - an.min()).round(2).values,
        "Variație în cursul anului (p.p.)": (an.last() - an.first()).round(2).values,
        "Luni raportate": an.count().values,
    })

    ultim = pd.DataFrame({
        "Țara": list(reg.columns),
        f"Rata 3 luni, {ro_luna(per_max)} (%)": [
            reg[t].dropna().iloc[-1] if reg[t].notna().any() else None for t in reg.columns],
        "Acum 12 luni (%)": [
            reg[t].iloc[-13] if len(reg) > 13 else None for t in reg.columns],
    })
    ultim["Variație 12 luni (p.p.)"] = (
        ultim.iloc[:, 1] - ultim["Acum 12 luni (%)"]).round(2)
    ultim["Diferență față de România (p.p.)"] = (
        ultim.iloc[:, 1] - float(r3.iloc[-1])).round(2)
    ultim = ultim.round(2)

    a_repere = pd.DataFrame({
        "Indicator": ["Maxim istoric (3 luni)", "Minim istoric (3 luni)",
                      "Ultima valoare (3 luni)", "Medie 2007–prezent",
                      "Medie ultimele 12 luni", "Medie ultimele 36 luni",
                      "Ultima valoare overnight", "Ultima valoare 12 luni"],
        "Valoare (%)": [
            r3.max(), r3.min(), r3.iloc[-1], r3.mean(), r3.tail(12).mean(), r3.tail(36).mean(),
            ro["Overnight (ON)"].dropna().iloc[-1] if "Overnight (ON)" in ro else None,
            ro["12 luni"].dropna().iloc[-1] if "12 luni" in ro else None],
        "Luna": [ro_luna(r3.idxmax()), ro_luna(r3.idxmin()), ro_luna(r3.index[-1]),
                 "—", "—", "—", ro_luna(per_max), ro_luna(per_max)],
    }).round(2)

    txt_incheiate = "; ".join(f"{k} (ultima lună {ro_luna(p_)})" for k, p_ in incheiate)

    meta = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": "Ratele dobânzii de pe piața monetară (ROBOR) și comparația regională",
        "subtitlu": "La ce dobândă își împrumută băncile banii între ele pe termen scurt — "
                    "reperul care determină costul creditelor cu dobândă variabilă și randamentul "
                    "depozitelor.",
        "sursa": "Eurostat — rate ale dobânzii pe piața monetară (date raportate de băncile "
                 "centrale naționale; pentru România, cotațiile ROBOR ale BNR)",
        "sursa_url": PAGINA,
        "cod_set": f"{DATASET}; dimensiunea int_rt: "
                   + ", ".join(f"{k} = {v}" for k, v in MATURITATI.items()),
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max} ({len(ro)} luni). Setul cuprinde "
                    f"{len(MATURITATI)} maturități pentru România (toate completate în "
                    f"ultima lună) și {len(TARI)} economii comparate pe maturitatea de "
                    f"3 luni." + (f" Serii încheiate: {txt_incheiate}." if incheiate else ""),
        "unitate": "procente pe an (% p.a.); diferențele în puncte procentuale (p.p.)",
        "descarcat": azi,
        "licenta": "Eurostat — reutilizare liberă cu menționarea sursei (Decizia 2011/833/UE).",
        "metodologie": "Media lunară a cotațiilor zilnice de pe piața interbancară, pentru fiecare "
                       "maturitate. Pentru România seriile corespund ROBOR (Romanian Interbank "
                       "Offer Rate), rata la care băncile declară că sunt dispuse să se împrumute "
                       "reciproc. Pentru zona euro, seriile corespund EURIBOR (și €STR pentru "
                       "overnight, după 2022). Pantele curbei și mediile anuale sunt calculate "
                       "în acest set.",
        "script": "scripts/financiara_01_04.py",
        "note": [
            "ROBOR 3M este reperul folosit istoric pentru creditele ipotecare cu dobândă variabilă "
            "din România. Pentru creditele de consum acordate după mai 2019, referința legală este "
            "IRCC, calculat pe tranzacții efective, nu pe cotații.",
            "Diferența dintre rata pe 12 luni și cea pe 1 lună („panta curbei”) arată ce așteaptă "
            "piața de la dobânzi: pozitivă = se anticipează creșteri, negativă = se anticipează scăderi.",
            "Diferența dintre rata pe 3 luni și cea overnight crește când apar tensiuni de "
            "lichiditate pe piața interbancară.",
            ("Unele serii nu mai sunt publicate: " + txt_incheiate + ". Cea overnight a zonei "
             "euro s-a oprit odată cu înlocuirea EONIA; celelalte maturități continuă.")
            if incheiate else
            "Toate seriile din set sunt încă publicate în ultima lună disponibilă.",
        ],
        "avertismente": [
            "Ungaria nu raportează continuu maturitățile de 6 și 12 luni — lunile lipsă rămân goale.",
            "Valorile sunt medii lunare ale cotațiilor, nu cotații de sfârșit de lună; nu sunt "
            "direct comparabile cu ROBOR-ul afișat zilnic de BNR.",
            "Codurile corecte pentru dimensiunea int_rt sunt IRT_DTD / IRT_M1 / IRT_M3 / IRT_M6 / "
            "IRT_M12. Codurile de tip TOTAL sau MCBY nu există pe acest set.",
            "Nu se folosesc valori estimate: lunile fără raportare rămân goale.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=df.rename(columns={"perioada": "Luna", "geo": "Cod țară", "tara": "Țara",
                                   "cod_maturitate": "Cod maturitate",
                                   "maturitate": "Maturitate", "rata_pct": "Rata (%)"}),
        analize={
            "Maturități România": a_serii,
            "Dinamica ratei 3 luni": a_dinamica,
            "Panta curbei": a_curba,
            "Comparație regională": a_reg,
            "Medii anuale RO": a_anual,
            "Situația ultimei luni": ultim,
            "Repere istorice RO": a_repere,
        },
        note_analize={
            "Maturități România": "Ratele lunare pentru fiecare maturitate, în procente pe an.",
            "Dinamica ratei 3 luni": "Variații, medie mobilă și intervalul ultimelor 12 luni.",
            "Panta curbei": "Diferențele dintre maturități — indicatorul așteptărilor pieței.",
            "Comparație regională": "Rata pe 3 luni în fiecare țară și diferența față de România.",
            "Medii anuale RO": "Agregare anuală a seriei lunare pe 3 luni.",
            "Situația ultimei luni": "Fotografia ultimei luni raportate, cu variația față de anul trecut.",
            "Repere istorice RO": "Maxime, minime și medii pe diverse ferestre.",
        },
        numfmt="0.00")

    # ---------------- pagina HTML ----------------
    et = [ro_luna(p) for p in ro.index]
    r3_now = float(r3.iloc[-1])
    var12 = float(r3.iloc[-1] - r3.iloc[-13]) if len(r3) > 13 else None
    on_now = float(ro["Overnight (ON)"].dropna().iloc[-1])
    m12_now = float(ro["12 luni"].dropna().iloc[-1])
    panta = m12_now - float(ro["1 lună"].dropna().iloc[-1])
    ea_now = float(reg["Zona euro"].dropna().iloc[-1])

    spec = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Eurostat — irt_st_m", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Rata pe 3 luni (ROBOR 3M), {ro_luna(per_max)}",
             "valoare": f"{ro_num(r3_now, 2)}%", "nota": "media lunară a cotațiilor"},
            {"eticheta": "Variație față de anul trecut",
             "valoare": f"{'+' if (var12 or 0) >= 0 else ''}{ro_num(var12, 2)} p.p.",
             "nota": f"față de {ro_luna(r3.index[-13])}",
             "trend": "down" if (var12 or 0) > 0 else "up"},
            {"eticheta": "Panta curbei (12 luni – 1 lună)",
             "valoare": f"{'+' if panta >= 0 else ''}{ro_num(panta, 2)} p.p.",
             "nota": "pozitivă = piața așteaptă dobânzi mai mari"},
            {"eticheta": "Diferență față de zona euro",
             "valoare": f"{ro_num(r3_now - ea_now, 2)} p.p.",
             "nota": f"zona euro: {ro_num(ea_now, 2)}% pe 3 luni"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Dobânzile interbancare din România, pe maturități",
             "subtitlu": "Cu cât maturitatea e mai lungă, cu atât rata reflectă mai mult "
                         "așteptările pieței despre viitor.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0,
             "series": [{"name": c, "data": clean(ro[c])} for c in ro.columns]},
            {"id": "c2", "type": "line",
             "titlu": "România față de regiune, la trei luni",
             "subtitlu": "Rata pe care o plătesc băncile pentru împrumuturi interbancare "
                         "pe trei luni, în fiecare țară.",
             "labels": [ro_luna(p) for p in reg.index], "unit": "%", "dec": 2, "ydec": 0,
             "series": [{"name": t, "data": clean(reg[t])} for t in reg.columns]},
            {"id": "c3", "type": "line",
             "titlu": "Ce așteaptă piața de la dobânzi",
             "subtitlu": "Diferența dintre rata pe 12 luni și cea pe 1 lună. Peste zero, "
                         "piața anticipează scumpirea banilor; sub zero, ieftinirea lor.",
             "labels": et, "unit": "p.p.", "dec": 2, "ydec": 1, "fill": True,
             "series": [{"name": "12 luni – 1 lună",
                         "data": clean(ro["12 luni"] - ro["1 lună"])}]},
            {"id": "c4", "type": "line",
             "titlu": "Tensiunea de lichiditate pe piața interbancară",
             "subtitlu": "Diferența dintre rata pe 3 luni și cea overnight. Salturile mari "
                         "apar când băncile se feresc să se împrumute reciproc.",
             "labels": et, "unit": "p.p.", "dec": 2, "ydec": 1,
             "series": [{"name": "3 luni – overnight",
                         "data": clean(ro["3 luni"] - ro["Overnight (ON)"])}]},
            {"id": "c5", "type": "bar",
             "titlu": "Media anuală a ratei pe 3 luni în România",
             "subtitlu": "Agregarea seriei lunare. Ultimul an conține doar lunile raportate.",
             "labels": list(a_anual["An"]), "unit": "%", "dec": 2, "ydec": 0, "zero": True,
             "series": [{"name": "Medie anuală",
                         "data": clean(a_anual["Medie anuală 3 luni (%)"])}]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(ro)} luni în fișierul Excel)",
            "columns": ["Luna"] + list(ro.columns) + ["Zona euro, 3 luni (%)"],
            "rows": [[ro_luna(p)] + [ro_num(ro[c][p], 2) for c in ro.columns]
                     + [ro_num(reg["Zona euro"].get(p), 2)]
                     for p in list(ro.index[-36:])[::-1]],
        },
        "note": [
            "Sursa: <strong>Eurostat</strong>, setul <code>irt_st_m</code> — ratele dobânzii de pe "
            "piața monetară, raportate de băncile centrale naționale. Pentru România, seriile "
            "corespund cotațiilor <strong>ROBOR</strong> publicate de BNR.",
            "ROBOR este rata la care băncile declară că sunt dispuse să se împrumute între ele. "
            "Când crește, se scumpesc creditele cu dobândă variabilă legate de el, dar cresc și "
            "dobânzile la depozite.",
            "Pentru creditele de consum acordate după mai 2019, referința legală în România nu mai "
            "este ROBOR, ci <strong>IRCC</strong>, calculat pe tranzacții efectiv încheiate. "
            "ROBOR rămâne însă reperul pentru creditele mai vechi și pentru piața interbancară.",
            "Valorile sunt <strong>medii lunare</strong> ale cotațiilor zilnice, nu valori de "
            "sfârșit de lună — nu coincid cu ROBOR-ul afișat într-o zi anume de BNR.",
            ("Unele serii s-au încheiat și nu mai sunt actualizate: " + txt_incheiate +
             " — cea overnight a zonei euro s-a oprit odată cu retragerea EONIA. "
             "Ungaria nu raportează continuu maturitățile lungi.")
            if incheiate else
            "Ungaria nu raportează continuu maturitățile lungi.",
            "Regenerare: <code>python3 scripts/financiara_01_04.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(df)} obs., {len(ro)} luni, {per_min} → {per_max}, "
          f"RO 3M = {r3_now:.2f}%")


if __name__ == "__main__":
    main()
