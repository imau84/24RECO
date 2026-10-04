#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 02 02 — Dobânzile la depozite și marja bancară în România
Sursa: BCE (ECB Data Portal), setul MIR — MFI Interest Rate Statistics,
       date raportate de Banca Națională a României.
Frecvență: lunară. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.
"""
import datetime as dt
import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 02 02"
SECTIUNE = "02 Bănci"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
API = "https://data-api.ecb.europa.eu/service/data/MIR"
PAGINA = "https://data.ecb.europa.eu/data/datasets/MIR"
START = "2007-01"

# Cheie SDMX MIR = 11 dimensiuni / 10 puncte:
# FREQ.REF_AREA.BS_REP_SECTOR.BS_ITEM.MATURITY_NOT_IRATE.DATA_TYPE_MIR.
# AMOUNT_CAT.BS_COUNT_SECTOR.CURRENCY_TRANS.IR_BUS_COV
SERII = {
    # --- depozite NOI constituite în lună (IR_BUS_COV = N) ------------------
    "M.RO.B.L21.A.R.A.2250.RON.N": ("Cont curent populație", "Depozite noi"),
    "M.RO.B.L21.A.R.A.2240.RON.N": ("Cont curent firme", "Depozite noi"),
    "M.RO.B.L22.F.R.A.2250.RON.N": ("Depozit la termen până la 1 an — populație", "Depozite noi"),
    "M.RO.B.L22.F.R.A.2240.RON.N": ("Depozit la termen până la 1 an — firme", "Depozite noi"),
    "M.RO.B.L22.G.R.A.2250.RON.N": ("Depozit la termen 1–2 ani — populație", "Depozite noi"),
    "M.RO.B.L22.G.R.A.2240.RON.N": ("Depozit la termen 1–2 ani — firme", "Depozite noi"),
    "M.RO.B.L22.H.R.A.2240.RON.N": ("Depozit la termen peste 2 ani — firme", "Depozite noi"),
    "M.RO.B.L22.H.R.A.2250.RON.N": ("Depozit la termen peste 2 ani — populație", "Depozite noi"),
    # --- depozite EXISTENTE (solduri, IR_BUS_COV = O) -----------------------
    "M.RO.B.L22.L.R.A.2250.RON.O": ("Depozite existente până la 2 ani — populație", "Solduri depozite"),
    "M.RO.B.L22.L.R.A.2240.RON.O": ("Depozite existente până la 2 ani — firme", "Solduri depozite"),
    "M.RO.B.L22.H.R.A.2240.RON.O": ("Depozite existente peste 2 ani — firme", "Solduri depozite"),
    # --- credite NOI, pentru calculul marjei pe fluxuri ---------------------
    "M.RO.B.A2C.I.R.A.2250.RON.N": ("Credit nou pentru locuință (fixare 1–5 ani)", "Credite noi"),
    "M.RO.B.A2B.I.R.A.2250.RON.N": ("Credit nou de consum (fixare 1–5 ani)", "Credite noi"),
    "M.RO.B.A2A.F.R.0.2240.RON.N": ("Credit nou pentru firme sub 1 mil. EUR", "Credite noi"),
    # --- credite EXISTENTE (solduri), pentru marja pe stocuri ---------------
    "M.RO.B.A22.J.R.A.2250.RON.O": ("Credite pentru locuință existente, peste 5 ani", "Solduri credite"),
    "M.RO.B.A25.J.R.A.2250.RON.O": ("Credite de consum existente, peste 5 ani", "Solduri credite"),
    "M.RO.B.A25.I.R.A.2250.RON.O": ("Credite de consum existente, 1–5 ani", "Solduri credite"),
    "M.RO.B.A20.F.R.A.2240.RON.O": ("Credite existente firme, sub 1 an", "Solduri credite"),
    "M.RO.B.A20.J.R.A.2240.RON.O": ("Credite existente firme, peste 5 ani", "Solduri credite"),
    # --- volume de depozite nou constituite (milioane lei) ------------------
    "M.RO.B.L22.F.B.A.2250.RON.N": ("Volum depozite noi până la 1 an — populație", "Volum"),
    "M.RO.B.L22.F.B.A.2240.RON.N": ("Volum depozite noi până la 1 an — firme", "Volum"),
    "M.RO.B.L22.G.B.A.2250.RON.N": ("Volum depozite noi 1–2 ani — populație", "Volum"),
}

CERERI = [
    "M.RO.B.L21+L22.A+F+G+H+L.R+B.A.2240+2250.RON.N+O",
    "M.RO.B.A2A+A2B+A2C.F+I.R.0+A.2240+2250.RON.N",
    "M.RO.B.A20+A22+A25.F+I+J.R.A.2240+2250.RON.O",
]

ETICHETE = {
    "BS_ITEM": {
        "L21": "Depozite overnight (cont curent / la vedere)",
        "L22": "Depozite cu maturitate convenită (depozite la termen)",
        "A20": "Credite (total)",
        "A22": "Credite pentru achiziția de locuințe",
        "A25": "Credite de consum și alte credite",
        "A2A": "Credite către firme, exclusiv descoperit de cont și card de credit",
        "A2B": "Credite de consum, exclusiv descoperit de cont și card de credit",
        "A2C": "Credite pentru locuințe, exclusiv descoperit de cont și card de credit",
    },
    "MATURITY_NOT_IRATE": {
        "A": "Total", "F": "Până la 1 an", "G": "Peste 1 și până la 2 ani",
        "H": "Peste 2 ani", "I": "Peste 1 și până la 5 ani", "J": "Peste 5 ani",
        "L": "Până la 2 ani",
    },
    "DATA_TYPE_MIR": {
        "R": "Rată anualizată convenită (AAR/NDER)",
        "B": "Volum de afaceri (sume nou constituite / sold)",
    },
    "BS_COUNT_SECTOR": {
        "2240": "Societăți nefinanciare (firme, S.11)",
        "2250": "Gospodăriile populației și IFSLSGP (S.14 și S.15)",
    },
    "IR_BUS_COV": {"N": "Operațiuni noi (new business)",
                   "O": "Sold existent (outstanding amount)"},
    "CURRENCY_TRANS": {"RON": "Leu românesc"},
}


def descarca_ecb(cereri, serii) -> pd.DataFrame:
    bucati = []
    for c in cereri:
        url = f"{API}/{c}?format=csvdata&startPeriod={START}&detail=dataonly"
        txt = fetch(url).content.decode("utf-8")
        if txt.lstrip().startswith("<"):
            raise SystemExit(f"EȘEC: ECB a întors HTML (cheie invalidă?) pentru {c}")
        bucati.append(pd.read_csv(io.StringIO(txt), low_memory=False))
    d = pd.concat(bucati, ignore_index=True)
    d = d[d.OBS_VALUE.notna()].copy()
    d["cheie"] = d.KEY.str.replace("^MIR\\.", "", regex=True)
    d = d[d.cheie.isin(serii)].drop_duplicates(["cheie", "TIME_PERIOD"]).copy()
    lipsa = sorted(set(serii) - set(d.cheie.unique()))
    if lipsa:
        raise SystemExit("EȘEC: seriile următoare nu au întors nicio observație: "
                         + ", ".join(lipsa))
    d = d.rename(columns={"TIME_PERIOD": "luna", "OBS_VALUE": "valoare"})
    d["indicator"] = d.cheie.map(lambda k: serii[k][0])
    d["grup"] = d.cheie.map(lambda k: serii[k][1])
    return d[["luna", "cheie", "indicator", "grup", "valoare", "BS_ITEM",
              "MATURITY_NOT_IRATE", "DATA_TYPE_MIR", "BS_COUNT_SECTOR",
              "CURRENCY_TRANS", "IR_BUS_COV"]].sort_values(["luna", "cheie"]).reset_index(drop=True)


def main() -> None:
    d = descarca_ecb(CERERI, SERII)
    fail_if_short(d, 3500, "ECB MIR — depozite și marja bancară, România")

    w = d.pivot_table(index="luna", columns="indicator", values="valoare",
                      aggfunc="first").sort_index()
    grup = {g: [SERII[k][0] for k in SERII if SERII[k][1] == g]
            for g in ("Depozite noi", "Solduri depozite", "Credite noi",
                      "Solduri credite", "Volum")}

    D_POP = "Depozit la termen până la 1 an — populație"
    D_FIRME = "Depozit la termen până la 1 an — firme"
    D_CURENT = "Cont curent populație"
    C_LOC = "Credit nou pentru locuință (fixare 1–5 ani)"
    C_CONS = "Credit nou de consum (fixare 1–5 ani)"
    C_FIRME = "Credit nou pentru firme sub 1 mil. EUR"
    S_DEP_POP = "Depozite existente până la 2 ani — populație"
    S_CRE_LOC = "Credite pentru locuință existente, peste 5 ani"
    S_CRE_CONS = "Credite de consum existente, peste 5 ani"

    ultima = w[[D_POP, D_FIRME]].dropna(how="all").index.max()
    fail_if_stale(ultima, 4, "ECB MIR România — depozite")
    prima = w.index.min()
    azi = dt.date.today().isoformat()

    # --- marje -------------------------------------------------------------
    marje = pd.DataFrame({
        "Luna": w.index,
        "Marjă credit locuință – depozit populație (p.p.)": (w[C_LOC] - w[D_POP]).round(2).values,
        "Marjă credit consum – depozit populație (p.p.)": (w[C_CONS] - w[D_POP]).round(2).values,
        "Marjă credit firme – depozit firme (p.p.)": (w[C_FIRME] - w[D_FIRME]).round(2).values,
        "Marjă pe solduri, locuințe (p.p.)": (w[S_CRE_LOC] - w[S_DEP_POP]).round(2).values,
        "Marjă pe solduri, consum (p.p.)": (w[S_CRE_CONS] - w[S_DEP_POP]).round(2).values,
    })

    # --- foi de analiză ----------------------------------------------------
    a_dep = w[grup["Depozite noi"]].round(2).reset_index().rename(columns={"luna": "Luna"})
    a_sold = w[grup["Solduri depozite"] + grup["Solduri credite"]].round(2)\
        .reset_index().rename(columns={"luna": "Luna"})

    a_din = pd.DataFrame({"Luna": w.index})
    for et, col in (("Depozit populație 1 an", D_POP), ("Depozit firme 1 an", D_FIRME),
                    ("Cont curent populație", D_CURENT)):
        s = w[col]
        a_din[f"{et} (%)"] = s.round(2).values
        a_din[f"{et} — variație lunară (p.p.)"] = s.diff().round(2).values
        a_din[f"{et} — variație 12 luni (p.p.)"] = s.diff(12).round(2).values
        a_din[f"{et} — medie mobilă 12 luni (%)"] = s.rolling(12).mean().round(2).values

    a_scara = pd.DataFrame({
        "Luna": w.index,
        "Cont curent (%)": w[D_CURENT].round(2).values,
        "Termen până la 1 an (%)": w[D_POP].round(2).values,
        "Termen 1–2 ani (%)": w["Depozit la termen 1–2 ani — populație"].round(2).values,
        "Termen peste 2 ani (%)": w["Depozit la termen peste 2 ani — populație"].round(2).values,
        "Câștig față de contul curent, 1 an (p.p.)":
            (w[D_POP] - w[D_CURENT]).round(2).values,
    })

    a_pf = pd.DataFrame({
        "Luna": w.index,
        "Depozit populație până la 1 an (%)": w[D_POP].round(2).values,
        "Depozit firme până la 1 an (%)": w[D_FIRME].round(2).values,
        "Diferență populație – firme (p.p.)": (w[D_POP] - w[D_FIRME]).round(2).values,
        "Volum depozite noi populație (mil. lei)":
            w["Volum depozite noi până la 1 an — populație"].round(0).values,
        "Volum depozite noi firme (mil. lei)":
            w["Volum depozite noi până la 1 an — firme"].round(0).values,
    })

    cols_an = [D_CURENT, D_POP, D_FIRME, C_LOC, C_CONS, C_FIRME, S_DEP_POP, S_CRE_LOC]
    an = w[cols_an].groupby(w.index.str[:4])
    a_anual = an.mean().round(2)
    a_anual["Marjă solduri locuințe (p.p.)"] = (
        a_anual[S_CRE_LOC] - a_anual[S_DEP_POP]).round(2)
    a_anual.insert(0, "Luni raportate", w[D_POP].groupby(w.index.str[:4]).count())
    a_anual = a_anual.reset_index().rename(columns={"luna": "An"})

    rep = []
    for col in list(w.columns):
        if col in grup["Volum"]:
            continue
        s = w[col].dropna()
        if s.empty:
            continue
        rep.append({"Indicator": col, "Minim (%)": round(s.min(), 2),
                    "Luna minimului": s.idxmin(), "Maxim (%)": round(s.max(), 2),
                    "Luna maximului": s.idxmax(),
                    "Ultima valoare (%)": round(s.iloc[-1], 2), "Ultima lună": s.index[-1],
                    "Medie 12 luni (%)": round(s.tail(12).mean(), 2),
                    "Medie pe tot istoricul (%)": round(s.mean(), 2)})
    a_rep = pd.DataFrame(rep).sort_values("Indicator")

    a_dict = pd.DataFrame(
        [{"Dimensiune": dim, "Cod": cod, "Denumire în română": nume}
         for dim, m in ETICHETE.items() for cod, nume in m.items()])

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Dobânzile la depozite și marja bancară în România",
        "subtitlu": "Cât primește un deponent pentru banii ținuți la bancă și cât rămâne "
                    "băncii din diferența față de dobânda la credite.",
        "sursa": "Banca Centrală Europeană — ECB Data Portal, setul MIR "
                 "(MFI Interest Rate Statistics); date raportate de Banca Națională a României",
        "sursa_url": PAGINA,
        "cod_set": "MIR (ECB_MIR1). Chei SDMX folosite (11 dimensiuni, 10 puncte): "
                   + "; ".join(sorted(SERII)),
        "frecventa": "Lunară",
        "perioada": f"{prima} → {ultima}",
        "unitate": "procente pe an (% p.a.); marjele în puncte procentuale (p.p.); "
                   "volumele în milioane lei",
        "descarcat": azi,
        "licenta": "BCE — reutilizare permisă cu menționarea sursei.",
        "metodologie": "Ratele la depozite sunt mediile ponderate ale dobânzilor convenite de "
                       "instituțiile care atrag depozite (S.122) pentru depozitele nou "
                       "constituite în luna respectivă (IR_BUS_COV = N) sau pentru întregul "
                       "sold existent la finalul lunii (IR_BUS_COV = O). Marja bancară este "
                       "calculată în acest set ca diferență aritmetică între rata la credite "
                       "și rata la depozite, pentru aceeași categorie de clienți; nu este o "
                       "marjă de profit contabilă și nu ține cont de costurile operaționale, "
                       "de rezervele minime obligatorii sau de pierderile din credite neperformante.",
        "script": "scripts/financiara_02_02.py",
        "note": [
            "Depozitele „overnight” (cod L21) sunt banii din contul curent și din conturile de "
            "economii fără termen — se pot retrage oricând.",
            "Depozitele „cu maturitate convenită” (cod L22) sunt depozitele clasice la termen.",
            "Marja pe operațiuni noi reacționează rapid la deciziile de politică monetară; "
            "marja pe solduri se mișcă lent, pentru că include contracte vechi.",
            "Volumele de depozite noi includ și reînnoirile automate ale depozitelor la termen, "
            "deci sunt mult mai mari decât economiile nete adăugate într-o lună.",
        ],
        "avertismente": [
            "Seria depozitelor noi la termen peste 2 ani pentru populație "
            "(M.RO.B.L22.H.R.A.2250.RON.N) se oprește în octombrie 2023 — sunt luni în care "
            "nu s-au constituit astfel de depozite. Valorile lipsă rămân goale.",
            "Seriile L23 (depozite rambursabile după notificare) apar în lista de chei pentru "
            "România, dar nu conțin nicio observație.",
            "Marja calculată aici este o diferență de rate, nu profitul băncii. O marjă de 5 p.p. "
            "nu înseamnă 5% profit.",
            "Cheia SDMX pentru MIR trebuie să aibă exact 10 puncte; altfel API-ul întoarce "
            "HTTP 400 cu o pagină HTML în loc de CSV.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=d.rename(columns={
            "luna": "Luna", "cheie": "Cheie SDMX", "indicator": "Indicator", "grup": "Grup",
            "valoare": "Valoare", "BS_ITEM": "Cod produs (BS_ITEM)",
            "MATURITY_NOT_IRATE": "Cod maturitate", "DATA_TYPE_MIR": "Cod tip de dată",
            "BS_COUNT_SECTOR": "Cod sector client", "CURRENCY_TRANS": "Monedă",
            "IR_BUS_COV": "Cod acoperire"}),
        analize={
            "Dobanzi depozite noi": a_dep,
            "Marja bancara": marje,
            "Solduri credite si depozite": a_sold,
            "Dinamica depozitelor": a_din,
            "Scara maturitatilor": a_scara,
            "Populatie vs firme": a_pf,
            "Medii anuale": a_anual,
            "Repere istorice": a_rep,
            "Dictionar coduri": a_dict,
        },
        note_analize={
            "Dobanzi depozite noi": "Ratele convenite pentru depozitele constituite în luna "
                                    "respectivă, în % pe an.",
            "Marja bancara": "Diferența dintre dobânda la credite și dobânda la depozite, "
                             "pentru aceeași categorie de clienți.",
            "Solduri credite si depozite": "Ratele medii pentru toate contractele aflate în "
                                           "derulare la finalul lunii.",
            "Dinamica depozitelor": "Variații lunare, anuale și medii mobile pe 12 luni.",
            "Scara maturitatilor": "Cât câștigi în plus dacă blochezi banii pe termen mai lung.",
            "Populatie vs firme": "Comparație între ratele oferite populației și firmelor, "
                                  "plus volumele nou constituite.",
            "Medii anuale": "Media lunilor raportate din fiecare an calendaristic.",
            "Repere istorice": "Minime, maxime și medii pentru fiecare serie.",
            "Dictionar coduri": "Traducerea codurilor de dimensiune SDMX, conform "
                                "codelist-urilor oficiale ECB.",
        },
        numfmt="0.00")

    # --- pagina HTML -------------------------------------------------------
    et = [ro_luna(p) for p in w.index]
    v_dep = float(w[D_POP].dropna().iloc[-1])
    v_cur = float(w[D_CURENT].dropna().iloc[-1])
    s_dep = w[D_POP].dropna()
    var12 = float(s_dep.iloc[-1] - s_dep.iloc[-13]) if len(s_dep) > 13 else None
    m_loc = float((w[C_LOC] - w[D_POP]).dropna().iloc[-1])
    m_cons = float((w[C_CONS] - w[D_POP]).dropna().iloc[-1])
    m_sold = float((w[S_CRE_LOC] - w[S_DEP_POP]).dropna().iloc[-1])

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "BCE — ECB Data Portal, setul MIR (raportări BNR)",
        "sursa_url": PAGINA, "frecventa": "Lunar",
        "perioada": f"{ro_luna(prima)} – {ro_luna(ultima)}", "actualizat": azi,
        "kpis": [
            {"eticheta": f"Depozit la termen până la 1 an, {ro_luna(ultima)}",
             "valoare": f"{ro_num(v_dep, 2)}%", "nota": "depozite noi ale populației, în lei"},
            {"eticheta": "Variație față de anul trecut",
             "valoare": f"{'+' if (var12 or 0) >= 0 else ''}{ro_num(var12, 2)} p.p.",
             "nota": f"față de {ro_luna(s_dep.index[-13])}",
             "trend": "up" if (var12 or 0) > 0 else "down"},
            {"eticheta": "Marja la creditul de consum",
             "valoare": f"{ro_num(m_cons, 2)} p.p.",
             "nota": f"credit nou minus depozit nou · locuință {ro_num(m_loc, 2)} p.p."},
            {"eticheta": "Dobânda la contul curent",
             "valoare": f"{ro_num(v_cur, 2)}%",
             "nota": f"marja pe soldurile existente: {ro_num(m_sold, 2)} p.p."},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Cât primește un deponent",
             "subtitlu": "Dobânzile la depozitele noi în lei, pe termene. Contul curent este "
                         "aproape mereu cel mai prost plătit.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "Termen până la 1 an", "data": clean(w[D_POP])},
                 {"name": "Termen 1–2 ani",
                  "data": clean(w["Depozit la termen 1–2 ani — populație"])},
                 {"name": "Termen peste 2 ani",
                  "data": clean(w["Depozit la termen peste 2 ani — populație"])},
                 {"name": "Cont curent", "data": clean(w[D_CURENT])},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Marja bancară pe operațiuni noi",
             "subtitlu": "Diferența dintre dobânda cerută la un credit nou și dobânda plătită "
                         "la un depozit nou, în puncte procentuale.",
             "labels": et, "unit": "p.p.", "dec": 2, "ydec": 0,
             "series": [
                 {"name": "Consum – depozit populație", "data": clean(w[C_CONS] - w[D_POP])},
                 {"name": "Locuință – depozit populație", "data": clean(w[C_LOC] - w[D_POP])},
                 {"name": "Firme – depozit firme", "data": clean(w[C_FIRME] - w[D_FIRME])},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "Marja pe contractele aflate în derulare",
             "subtitlu": "Aceeași diferență, dar calculată pe soldul tuturor creditelor și "
                         "depozitelor existente — se mișcă mult mai lent.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "Credite locuință existente", "data": clean(w[S_CRE_LOC])},
                 {"name": "Credite consum existente", "data": clean(w[S_CRE_CONS])},
                 {"name": "Depozite existente populație", "data": clean(w[S_DEP_POP])},
                 {"name": "Marja (diferența)", "data": clean(w[S_CRE_LOC] - w[S_DEP_POP]),
                  "dashed": True},
             ]},
            {"id": "c4", "type": "line",
             "titlu": "Populația și firmele nu primesc aceeași dobândă",
             "subtitlu": "Depozite noi la termen până la 1 an, în lei.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "Populație", "data": clean(w[D_POP])},
                 {"name": "Firme", "data": clean(w[D_FIRME])},
                 {"name": "Diferența (populație – firme)", "data": clean(w[D_POP] - w[D_FIRME]),
                  "dashed": True},
             ]},
            {"id": "c5", "type": "bar",
             "titlu": "Media anuală: depozite, credite și marjă",
             "subtitlu": "Ultimul an conține doar lunile raportate până acum.",
             "labels": list(a_anual["An"]), "unit": "%", "dec": 2, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Depozit populație 1 an", "data": clean(a_anual[D_POP])},
                 {"name": "Credit consum nou", "data": clean(a_anual[C_CONS])},
                 {"name": "Marjă pe solduri, locuințe",
                  "data": clean(a_anual["Marjă solduri locuințe (p.p.)"])},
             ]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(w)} luni în fișierul Excel)",
            "columns": ["Luna", "Depozit ≤1 an populație (%)", "Depozit 1–2 ani (%)",
                        "Cont curent (%)", "Depozit ≤1 an firme (%)",
                        "Marjă consum (p.p.)", "Marjă firme (p.p.)",
                        "Marjă pe solduri, locuințe (p.p.)"],
            "rows": [[ro_luna(i), ro_num(r[D_POP], 2),
                      ro_num(r["Depozit la termen 1–2 ani — populație"], 2),
                      ro_num(r[D_CURENT], 2), ro_num(r[D_FIRME], 2),
                      ro_num(r[C_CONS] - r[D_POP], 2), ro_num(r[C_FIRME] - r[D_FIRME], 2),
                      ro_num(r[S_CRE_LOC] - r[S_DEP_POP], 2)]
                     for i, r in w.tail(36).iloc[::-1].iterrows()],
        },
        "note": [
            "Sursa: Banca Centrală Europeană, ECB Data Portal, setul <code>MIR</code>. Datele "
            "pentru România sunt raportate lunar de Banca Națională a României.",
            "<strong>Ce este marja bancară.</strong> Banca împrumută de la deponenți și dă mai "
            "departe cu dobândă mai mare. Diferența dintre cele două rate este marja. Din ea "
            "banca acoperă salariile, rețeaua de unități, IT-ul, rezervele impuse de BNR și "
            "pierderile din creditele nerambursate — deci marja nu este profit.",
            "<strong>De ce contează pentru tine.</strong> Când marja crește, înseamnă că "
            "dobânda la depozitul tău a scăzut mai repede (sau a crescut mai încet) decât cea "
            "la credite. Este cel mai simplu indicator al puterii de negociere a clientului.",
            "<strong>Două feluri de marjă.</strong> Marja pe „operațiuni noi” se referă la "
            "contractele semnate în luna respectivă și reacționează repede la deciziile BNR. "
            "Marja pe „solduri” acoperă toate contractele vechi și se mișcă lent.",
            "Depozitele overnight (cont curent, conturi de economii fără termen) sunt cele mai "
            "slab remunerate, dar banii sunt disponibili imediat.",
            "Regenerare: <code>python3 scripts/financiara_02_02.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(d)} obs., {len(SERII)} serii, {len(w)} luni, {prima} → {ultima}; "
          f"depozit ≤1 an = {v_dep:.2f}%, marjă credit locuință = {m_loc:.2f} p.p.")


if __name__ == "__main__":
    main()
