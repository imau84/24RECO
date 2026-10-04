#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 04 03 — Fondurile de investiții din România: active, tipuri de fonduri și bani noi
Sursa: BCE, Data Portal, setul IVF (Investment Funds Balance Sheet Statistics)
Frecvență: LUNARĂ. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.
"""
import datetime as dt
import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 04 03"
SECTIUNE = "04 Investiții financiare"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
API = "https://data-api.ecb.europa.eu/service/data/IVF"
PAGINA = "https://data.ecb.europa.eu/data/datasets/IVF"
START = "2008-01"

# IVF are 11 dimensiuni, ca și BSI:
# FREQ.REF_AREA.ADJUSTMENT.IVF_REP_SECTOR.IVF_ITEM.MATURITY_ORIG.DATA_TYPE.
# COUNT_AREA.BS_COUNT_SECTOR.CURRENCY_TRANS.BS_SUFFIX
# ATENȚIE: BS_COUNT_SECTOR se scrie „0000”, nu „0” — altfel HTTP 404.
TIPURI = {"T0": "Toate fondurile", "10": "Fonduri de acțiuni", "20": "Fonduri de obligațiuni",
          "30": "Fonduri mixte", "40": "Fonduri imobiliare", "50": "Fonduri de hedging",
          "60": "Alte fonduri", "TA": "Fonduri deschise", "TB": "Fonduri închise"}
TIPURI_GRAFIC = ["10", "20", "30", "40", "50", "60"]

POZITII = {
    "T00": "Total active", "L30": "Unități de fond emise (activ net al investitorilor)",
    "A20": "Depozite și credite acordate", "A30": "Titluri de datorie deținute",
    "A52": "Unități ale altor fonduri deținute", "A5A": "Acțiuni și participații deținute",
    "A60": "Active nefinanciare (imobiliare)", "AT1": "Alte active (inclusiv derivate)",
    "L20": "Împrumuturi și depozite primite", "LT1": "Alte pasive (inclusiv derivate)",
}
ACTIVE_GRAFIC = ["A5A", "A30", "A20", "A52", "A60", "AT1"]

MONEDE = {"RON": "Lei (RON)", "EUR": "Euro", "Z07": "Alte monede", "Z01": "Toate monedele"}
MATURITATI = {"F": "sub 1 an", "G": "1–2 ani", "H": "peste 2 ani"}
TIP_DATE = {"1": "Solduri (stocuri)", "4": "Tranzacții (flux net lunar)"}


def _get(cheie: str, eticheta: str, minim: int) -> pd.DataFrame:
    r = fetch(f"{API}/{cheie}?format=csvdata&startPeriod={START}", timeout=240)
    if not r.text.lstrip().startswith("KEY"):
        raise SystemExit(f"EȘEC: {eticheta} nu a întors CSV. Verifică numărul de puncte din "
                         f"cheie și codul BS_COUNT_SECTOR. Răspuns: {r.text[:200]!r}")
    df = pd.read_csv(io.StringIO(r.text),
                     dtype={"BS_COUNT_SECTOR": str, "IVF_REP_SECTOR": str})
    fail_if_short(df, minim, eticheta)
    return df


def descarca() -> dict[str, pd.DataFrame]:
    tip = "+".join(TIPURI)
    d = {
        "solduri": _get(f"M.RO.N.{tip}.T00+L30.A.1.Z5.0000.Z01.E",
                        "IVF solduri pe tipuri de fonduri", 3000),
        "compozitie": _get("M.RO.N.T0.A20+A30+A52+A5A+A60+AT1+L20+LT1.A.1.Z5.0000.Z01.E",
                           "IVF compoziția portofoliului", 1500),
        "tranzactii": _get(f"M.RO.N.{tip}.T00+L30.A.4.Z5.0000.Z01.E",
                           "IVF tranzacții", 3000),
        # ATENȚIE: defalcarea pe monedă și maturitate EXISTĂ DOAR pentru titlurile emise
        # de instituții financiare monetare (BS_COUNT_SECTOR=1000) din România (U6) și din
        # zona euro (U2). Este un SUBSET îngust al portofoliului total de titluri de datorie
        # (A30.A.1.Z5.0000), nu același agregat — vezi nota din foaia de analiză.
        "datorie": _get("M.RO.N.T0.A30.F+G+H.1.U6+U2.1000.RON+EUR+Z01.E",
                        "IVF titluri de datorie bancare pe monedă și maturitate", 3500),
    }
    return d


def main() -> None:
    d = descarca()
    azi = dt.date.today().isoformat()

    s = d["solduri"]
    tot = s[s.IVF_ITEM == "T00"].pivot_table(index="TIME_PERIOD", columns="IVF_REP_SECTOR",
                                             values="OBS_VALUE").sort_index()
    nav = s[s.IVF_ITEM == "L30"].pivot_table(index="TIME_PERIOD", columns="IVF_REP_SECTOR",
                                             values="OBS_VALUE").sort_index()
    comp = d["compozitie"].pivot_table(index="TIME_PERIOD", columns="IVF_ITEM",
                                       values="OBS_VALUE").sort_index()
    tr = d["tranzactii"]
    tr_nav = tr[tr.IVF_ITEM == "L30"].pivot_table(index="TIME_PERIOD", columns="IVF_REP_SECTOR",
                                                  values="OBS_VALUE").sort_index()

    per_min, per_max = tot.index.min(), tot.index.max()
    fail_if_stale(per_max, 4, "BCE IVF România")
    if "T0" not in tot.columns:
        raise SystemExit("EȘEC: seria agregată T0 lipsește din IVF — structura setului s-a schimbat.")

    # Titluri de datorie emise de INSTITUȚII FINANCIARE MONETARE din România și zona euro,
    # pe monedă și maturitate. Acesta este singurul nivel la care BCE publică defalcarea pe
    # monedă; el NU este egal cu portofoliul total de titluri de datorie al fondurilor
    # (comp["A30"]), ci un subset al lui. Cele două agregate sunt denumite distinct peste tot.
    dd = d["datorie"]
    dat_mon = dd.groupby(["TIME_PERIOD", "CURRENCY_TRANS"]).OBS_VALUE.sum().unstack().sort_index()
    dat_mat = dd[dd.CURRENCY_TRANS == "Z01"].groupby(
        ["TIME_PERIOD", "MATURITY_ORIG"]).OBS_VALUE.sum().unstack().sort_index()
    # ponderea subsetului bancar în portofoliul total de titluri de datorie
    dat_pond = (100 * dat_mon["Z01"] / comp["A30"].reindex(dat_mon.index)).dropna()

    # Defalcarea pe tipuri de fonduri este raportată doar din momentul în care componentele
    # acoperă practic tot agregatul; înainte, lipsa lor ar sugera fals că fondurile mixte
    # dominau piața. Reținem doar lunile în care suma tipurilor acoperă cel puțin 95% din total.
    tip_sum = tot[[k for k in TIPURI_GRAFIC if k in tot.columns]].sum(axis=1, min_count=1)
    acoperire = (100 * tip_sum / tot["T0"]).fillna(0)
    luni_tip = tot.index[acoperire >= 95]
    if len(luni_tip) < 3:
        raise SystemExit("EȘEC: defalcarea pe tipuri de fonduri nu acoperă nicio lună "
                         "completă — structura setului IVF s-a schimbat.")

    # --- foile de analiză --------------------------------------------------
    a_tot = tot.rename(columns=TIPURI).round(1).reset_index().rename(columns={"TIME_PERIOD": "Luna"})
    ord_tip = ["Luna"] + [TIPURI[k] for k in TIPURI if TIPURI[k] in a_tot.columns]
    a_tot = a_tot[ord_tip]

    a_nav = nav.rename(columns=TIPURI).round(1).reset_index().rename(columns={"TIME_PERIOD": "Luna"})
    a_nav = a_nav[[c for c in ord_tip if c in a_nav.columns]]

    a_comp = comp.rename(columns=POZITII).round(1).reset_index().rename(columns={"TIME_PERIOD": "Luna"})
    a_pond = pd.DataFrame({"Luna": comp.index})
    for c in ACTIVE_GRAFIC:
        if c in comp.columns:
            a_pond[f"{POZITII[c]} (% din total active)"] = (
                100 * comp[c] / tot["T0"]).round(1).values

    a_flux = pd.DataFrame({"Luna": tr_nav.index})
    for k in ("T0", "10", "20", "30", "40"):
        if k in tr_nav.columns:
            a_flux[f"{TIPURI[k]} — flux net lunar (mil. EUR)"] = tr_nav[k].round(1).values
            a_flux[f"{TIPURI[k]} — cumulat 12 luni"] = tr_nav[k].rolling(12).sum().round(1).values
    a_flux = a_flux.dropna(how="all", subset=[c for c in a_flux.columns if c != "Luna"])

    struct = pd.DataFrame({"Luna": tot.index})
    for k in TIPURI_GRAFIC:
        if k in tot.columns:
            struct[f"{TIPURI[k]} (% din total)"] = (100 * tot[k] / tot["T0"]).round(1).values
    for k in ("TA", "TB"):
        if k in tot.columns:
            struct[f"{TIPURI[k]} (% din total)"] = (100 * tot[k] / tot["T0"]).round(1).values

    a_dat = pd.DataFrame({"Luna": dat_mon.index})
    a_dat["Titluri de datorie — TOTAL portofoliu (mil. EUR)"] = (
        comp["A30"].reindex(dat_mon.index).round(1).values)
    for m in ("Z01", "RON", "EUR"):
        if m in dat_mon.columns:
            a_dat[f"Din care, emise de bănci RO+zona euro — {MONEDE[m]} (mil. EUR)"] = \
                dat_mon[m].round(1).values
    a_dat["Subsetul bancar ca % din titlurile de datorie"] = (
        dat_pond.reindex(dat_mon.index).round(1).values)
    if {"RON", "Z01"} <= set(dat_mon.columns):
        a_dat["Pondere lei ÎN SUBSETUL bancar (%)"] = (
            100 * dat_mon["RON"] / dat_mon["Z01"]).round(1).values
        a_dat["Titluri în lei ca % din TOTALUL titlurilor de datorie"] = (
            100 * dat_mon["RON"] / comp["A30"].reindex(dat_mon.index)).round(1).values
    for m in ("F", "G", "H"):
        if m in dat_mat.columns:
            a_dat[f"Subset bancar, maturitate {MATURITATI[m]} (mil. EUR)"] = dat_mat[m].round(1).values

    an = tot.copy()
    an["An"] = an.index.str[:4]
    dec = an.groupby("An").last()
    a_anual = pd.DataFrame({"An": dec.index})
    for k in TIPURI:
        if k in dec.columns:
            a_anual[f"{TIPURI[k]} (mil. EUR)"] = dec[k].round(0).values
    a_anual["Variație anuală total (%)"] = (100 * dec["T0"].pct_change()).round(1).values

    ult = pd.DataFrame({
        "Tip de fond": [TIPURI[k] for k in TIPURI if k in tot.columns],
        f"Active totale {ro_luna(per_max)} (mil. EUR)": [tot[k].iloc[-1] for k in TIPURI if k in tot.columns],
        "Acum 12 luni (mil. EUR)": [tot[k].iloc[-13] if len(tot) > 13 else None
                                    for k in TIPURI if k in tot.columns],
        "Pondere în total (%)": [100 * tot[k].iloc[-1] / tot["T0"].iloc[-1]
                                 for k in TIPURI if k in tot.columns],
        "Flux net 12 luni (mil. EUR)": [tr_nav[k].rolling(12).sum().iloc[-1] if k in tr_nav.columns else None
                                        for k in TIPURI if k in tot.columns],
    }).round(1)
    ult["Variație 12 luni (%)"] = (
        100 * (ult.iloc[:, 1] / ult["Acum 12 luni (mil. EUR)"] - 1)).round(1)

    brut = pd.concat([v for v in d.values()], ignore_index=True)
    brut["Tip de fond"] = brut["IVF_REP_SECTOR"].map(TIPURI)
    brut["Poziție bilanțieră"] = brut["IVF_ITEM"].map(POZITII)
    brut["Tip serie"] = brut["DATA_TYPE"].astype(str).map(TIP_DATE)
    brut["Monedă"] = brut["CURRENCY_TRANS"].map(MONEDE)
    date_df = brut[["TIME_PERIOD", "KEY", "Tip de fond", "Poziție bilanțieră", "MATURITY_ORIG",
                    "Monedă", "Tip serie", "OBS_VALUE", "UNIT"]].copy()
    date_df.columns = ["Luna", "Cheie SDMX", "Tip de fond", "Poziție bilanțieră", "Cod maturitate",
                       "Monedă", "Tip serie", "Valoare (mil. EUR)", "Unitate"]
    date_df = date_df.sort_values(["Luna", "Cheie SDMX"]).reset_index(drop=True)

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Fondurile de investiții din România: active, tipuri de fonduri și bani noi",
        "subtitlu": "Cât administrează fondurile de investiții românești, în ce își plasează "
                    "banii și cât capital nou atrag sau pierd în fiecare lună.",
        "sursa": "Banca Centrală Europeană — Data Portal, setul IVF "
                 "(statistica bilanțieră a fondurilor de investiții)",
        "sursa_url": PAGINA,
        "cod_set": (
            "IVF, 11 dimensiuni: FREQ.REF_AREA.ADJUSTMENT.IVF_REP_SECTOR.IVF_ITEM."
            "MATURITY_ORIG.DATA_TYPE.COUNT_AREA.BS_COUNT_SECTOR.CURRENCY_TRANS.BS_SUFFIX. "
            "Chei folosite: M.RO.N.{T0|TA|TB|10|20|30|40|50|60}.T00+L30.A.{1|4}.Z5.0000.Z01.E; "
            "M.RO.N.T0.A20+A30+A52+A5A+A60+AT1+L20+LT1.A.1.Z5.0000.Z01.E; "
            "M.RO.N.T0.A30.F+G+H.1.U6+U2.1000.RON+EUR+Z01.E"),
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "milioane EUR",
        "descarcat": azi,
        "licenta": "BCE — reutilizare permisă cu menționarea sursei "
                   "(https://www.ecb.europa.eu/services/disclaimer/html/index.en.html).",
        "metodologie": (
            "Setul IVF cuprinde bilanțul agregat al fondurilor de investiții rezidente "
            "(exclusiv fondurile de piață monetară, care sunt raportate în setul BSI), "
            "conform Regulamentului BCE/2013/38. Datele sunt colectate de BNR de la "
            "administratorii de fonduri și transmise BCE. „Total active” este valoarea "
            "întregului portofoliu; „unități de fond emise” este contravaloarea deținerilor "
            "investitorilor, adică activul net. „Tranzacții” reprezintă subscrierile minus "
            "răscumpărările, curățate de variația prețurilor activelor și de efectele de curs."),
        "script": "scripts/financiara_04_03.py",
        "note": [
            "Clasificarea pe tipuri urmează politica de investiții declarată: fonduri de "
            "acțiuni, de obligațiuni, mixte, imobiliare, de hedging și alte fonduri.",
            "Fondurile deschise (open-end) permit răscumpărarea oricând; cele închise "
            "(closed-end) au un număr fix de unități.",
            "Fondurile de piață monetară NU sunt incluse aici — ele apar în statistica "
            "instituțiilor financiare monetare (setul BSI).",
            "Diferența dintre „total active” și „unități de fond emise” este dată de "
            "împrumuturile primite și de alte pasive ale fondurilor.",
            "Asociația Administratorilor de Fonduri din România (aaf.ro) publica statistici "
            "proprii, dar site-ul este nefuncțional; ASF nu expune un fișier public "
            "echivalent pe subdomeniul de date. BCE este singura sursă lunară stabilă.",
        ],
        "avertismente": [
            "Cheia SDMX trebuie să aibă exact 10 puncte (11 câmpuri). În plus, codul "
            "BS_COUNT_SECTOR se scrie „0000”; forma „0” întoarce HTTP 404.",
            "O interogare cu wildcard pe mai puține dimensiuni (ex. M.RO......) întoarce "
            "HTTP 400 cu o pagină HTML, nu cu JSON de eroare.",
            "Valorile sunt exprimate în euro, deși majoritatea activelor fondurilor românești "
            "sunt denominate în lei. Variația soldului în euro amestecă performanța "
            "portofoliului cu efectul cursului; pentru fluxuri reale folosiți seriile de "
            "tranzacții (DATA_TYPE=4).",
            "Seria de tranzacții începe cu o lună mai târziu decât cea de solduri "
            "(prima lună nu are termen de comparație).",
            "Fondurile de hedging și cele imobiliare au valori foarte mici sau zero în "
            "România; ponderile lor nu sunt semnificative statistic.",
            "Defalcarea pe monedă și maturitate a titlurilor de datorie NU este disponibilă "
            "pentru întregul portofoliu. BCE o publică doar pentru titlurile emise de "
            "instituții financiare monetare din România și din zona euro "
            "(BS_COUNT_SECTOR=1000, COUNT_AREA=U6+U2) — sub o zecime din obligațiunile "
            "deținute. Raportarea unei „ponderi a leului” calculate pe acest subset ca și cum "
            "ar descrie tot portofoliul este o eroare: cele două agregate sunt denumite "
            "distinct în foaia de analiză și în pagină.",
            "Defalcarea pe tipuri de fonduri (acțiuni, obligațiuni, alte fonduri) este "
            "raportată de BCE pentru România abia din decembrie 2025; anterior există doar "
            "agregatul total, fondurile mixte și cele imobiliare. Graficul pe tipuri este "
            "restrâns la lunile în care componentele acoperă cel puțin 95% din total, ca să "
            "nu sugereze fals că fondurile mixte dominau piața în trecut.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta, date_df=date_df,
        analize={
            "Active pe tipuri de fonduri": a_tot,
            "Activ net al investitorilor": a_nav,
            "Compoziția portofoliului": a_comp,
            "Ponderi în portofoliu": a_pond,
            "Bani noi în fonduri": a_flux,
            "Structura pieței": struct,
            "Titluri de datorie (total + subset)": a_dat,
            "Solduri la final de an": a_anual,
            "Sinteza ultimei luni": ult,
        },
        note_analize={
            "Active pe tipuri de fonduri": "Valoarea totală a activelor administrate, pe categorii de fonduri (mil. EUR).",
            "Activ net al investitorilor": "Contravaloarea unităților de fond deținute de investitori (mil. EUR).",
            "Compoziția portofoliului": "În ce sunt plasați banii tuturor fondurilor: acțiuni, obligațiuni, depozite etc.",
            "Ponderi în portofoliu": "Aceeași compoziție, exprimată ca procent din activele totale.",
            "Bani noi în fonduri": "Subscrieri minus răscumpărări, fără efectul variației prețurilor sau al cursului.",
            "Structura pieței": "Ponderea fiecărui tip de fond în activele totale ale industriei.",
            "Titluri de datorie (total + subset)":
                "ATENȚIE, două agregate diferite în aceeași foaie. Prima coloană este TOTALUL "
                "titlurilor de datorie din portofoliul fondurilor (cheia A30.A.1.Z5.0000.Z01.E, "
                "aceeași valoare ca în foaia „Compoziția portofoliului”). Coloanele următoare "
                "acoperă DOAR titlurile emise de instituții financiare monetare din România și "
                "din zona euro (BS_COUNT_SECTOR=1000, COUNT_AREA=U6+U2) — singurul nivel la care "
                "BCE publică defalcarea pe monedă și maturitate. Acest subset reprezintă sub o "
                "zecime din portofoliul de obligațiuni, deci ponderea „lei” calculată în "
                "interiorul lui NU este ponderea leului în obligațiunile fondurilor.",
            "Solduri la final de an": "Activele din decembrie al fiecărui an; ultimul an conține ultima lună raportată.",
            "Sinteza ultimei luni": "Fotografia ultimei luni, cu ponderea, variația anuală și fluxul net pe 12 luni.",
        },
        numfmt="#,##0.0")

    # --- pagina HTML ------------------------------------------------------
    et = [ro_luna(p) for p in tot.index]
    act_now = float(tot["T0"].iloc[-1])
    act_12 = float(tot["T0"].iloc[-13]) if len(tot) > 13 else None
    flux12 = float(tr_nav["T0"].rolling(12).sum().iloc[-1])
    p_act = float(100 * comp["A5A"].iloc[-1] / act_now) if "A5A" in comp.columns else None
    p_dat = float(100 * comp["A30"].iloc[-1] / act_now) if "A30" in comp.columns else None
    # ponderea subsetului bancar în portofoliul total de obligațiuni (pentru subtitlul c5)
    p_sub = float(dat_pond.iloc[-1]) if len(dat_pond) else None
    p_10 = float(100 * tot.loc[luni_tip[-1], "10"] / tot.loc[luni_tip[-1], "T0"])
    p_20 = float(100 * tot.loc[luni_tip[-1], "20"] / tot.loc[luni_tip[-1], "T0"])

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "BCE — Data Portal, setul IVF (bilanțul fondurilor de investiții)",
        "sursa_url": PAGINA,
        "frecventa": "Lunar",
        "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Active administrate, {ro_luna(per_max)}",
             "valoare": f"{ro_num(act_now / 1000, 2)} mld. EUR",
             "nota": (f"{'+' if act_now >= act_12 else '−'}"
                      f"{ro_num(abs(100 * (act_now / act_12 - 1)), 1)}% față de acum un an")
                     if act_12 else "toate fondurile de investiții rezidente"},
            {"eticheta": "Bani noi atrași în ultimele 12 luni",
             "valoare": f"{'+' if flux12 >= 0 else '−'}{ro_num(abs(flux12), 0)} mil. EUR",
             "nota": "subscrieri minus răscumpărări",
             "trend": "up" if flux12 >= 0 else "down"},
            {"eticheta": "Pondere acțiuni în portofoliu",
             "valoare": f"{ro_num(p_act, 1)}%" if p_act is not None else "–",
             "nota": "restul: obligațiuni, depozite și unități ale altor fonduri"},
            {"eticheta": "Pondere obligațiuni în portofoliu",
             "valoare": f"{ro_num(p_dat, 1)}%" if p_dat is not None else "–",
             "nota": "titluri de datorie, din activele totale ale fondurilor"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Activele administrate de fondurile de investiții din România",
             "subtitlu": "Valoarea totală a portofoliilor, în miliarde de euro, la finalul "
                         "fiecărei luni. Include toate fondurile rezidente, mai puțin cele "
                         "de piață monetară.",
             "labels": et, "unit": "mld. EUR", "dec": 2, "ydec": 0, "fill": True,
             "series": [{"name": "Total active", "data": clean(tot["T0"] / 1000)}]},
            {"id": "c2", "type": "bar",
             "titlu": "Ce tipuri de fonduri administrează banii",
             "subtitlu": f"Activele fiecărei categorii, în miliarde de euro. Fondurile de "
                         f"acțiuni sunt de departe cele mai mari — {ro_num(p_10, 1)}% din piață "
                         f"în {ro_luna(luni_tip[-1])}, față de {ro_num(p_20, 1)}% cât dețin "
                         f"fondurile de obligațiuni. BCE publică această defalcare doar "
                         f"începând cu {ro_luna(luni_tip[0])}.",
             "labels": [ro_luna(p) for p in luni_tip], "unit": "mld. EUR", "dec": 2,
             "ydec": 1, "stacked": True, "xticks": 12,
             "series": [{"name": TIPURI[k], "data": clean(tot.loc[luni_tip, k] / 1000)}
                        for k in TIPURI_GRAFIC if k in tot.columns]},
            {"id": "c3", "type": "line",
             "titlu": "În ce sunt plasați banii fondurilor",
             "subtitlu": "Compoziția portofoliului agregat, în miliarde de euro.",
             "labels": [ro_luna(p) for p in comp.index], "unit": "mld. EUR", "dec": 2,
             "ydec": 1, "stacked": True,
             "series": [{"name": POZITII[c], "data": clean(comp[c] / 1000)}
                        for c in ACTIVE_GRAFIC if c in comp.columns]},
            {"id": "c4", "type": "bar",
             "titlu": "Bani noi intrați în fonduri, cumulat pe 12 luni",
             "subtitlu": "Subscrieri minus răscumpărări, curățate de variația prețurilor și de "
                         "efectul cursului. Sub zero înseamnă că investitorii retrag bani.",
             "labels": [ro_luna(p) for p in tr_nav["T0"].rolling(12).sum().dropna().index],
             "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "series": [{"name": "Flux net cumulat 12 luni",
                         "data": clean(tr_nav["T0"].rolling(12).sum().dropna())}]},
            {"id": "c5", "type": "line",
             "titlu": "Obligațiunile bancare din portofoliu, pe monedă",
             "subtitlu": f"Doar titlurile emise de bănci din România și din zona euro — "
                         f"singurul segment pentru care BCE publică moneda. Este un colț mic "
                         f"al portofoliului de obligațiuni: {ro_num(p_sub, 1)}% din el în "
                         f"{ro_luna(per_max)}. Valori în milioane de euro.",
             "labels": [ro_luna(p) for p in dat_mon.index], "unit": "mil. EUR", "dec": 1, "ydec": 0,
             "series": [{"name": MONEDE[m], "data": clean(dat_mon[m])}
                        for m in ("RON", "EUR") if m in dat_mon.columns]},
        ],
        "tabel": {
            "titlu": f"Active pe tipuri de fonduri — ultimele 36 de luni "
                     f"({len(tot)} luni în fișierul Excel; defalcarea pe tipuri începe în "
                     f"{ro_luna(luni_tip[0])}, înainte celulele sunt goale)",
            "columns": ["Luna", "Total (mil. EUR)"] +
                       [TIPURI[k] for k in TIPURI_GRAFIC if k in tot.columns] +
                       ["Flux net lunar"],
            "rows": [[ro_luna(i), ro_num(tot["T0"][i], 0)] +
                     [ro_num(tot[k][i], 0) for k in TIPURI_GRAFIC if k in tot.columns] +
                     [ro_num(tr_nav["T0"].get(i), 0)]
                     for i in tot.index[-36:][::-1]],
        },
        "note": [
            "Sursa: Banca Centrală Europeană, setul <code>IVF</code> — bilanțul agregat al "
            "fondurilor de investiții rezidente în România, colectat de BNR de la "
            "administratorii de fonduri și transmis lunar la BCE.",
            "<strong>Ce este un fond de investiții.</strong> Un fond adună banii mai multor "
            "investitori și îi plasează, după o strategie declarată, în acțiuni, obligațiuni "
            "sau depozite. Investitorul primește unități de fond; valoarea lor urcă sau coboară "
            "odată cu portofoliul. Este forma de investiție colectivă cea mai accesibilă "
            "publicului larg din România.",
            "<strong>De ce contează fluxul net.</strong> Activele unui fond pot crește din două "
            "motive: pentru că titlurile din portofoliu s-au scumpit sau pentru că au intrat "
            "bani noi. Seria de tranzacții separă cele două — arată exact câți bani au subscris "
            "investitorii minus câți au răscumpărat. O ieșire netă susținută semnalează "
            "pierdere de încredere, chiar dacă activele totale par stabile.",
            "<strong>Cât de mică e piața.</strong> Pentru comparație, depozitele populației la "
            "băncile din România depășesc 80 de miliarde de euro. Industria fondurilor "
            "administrează o fracțiune din această sumă — economisirea românească rămâne "
            "covârșitor bancară.",
            "<strong>Două agregate diferite pentru obligațiuni.</strong> Graficul „În ce sunt "
            "plasați banii fondurilor” arată TOT portofoliul de titluri de datorie. Graficul "
            "pe monede arată doar obligațiunile emise de bănci din România și din zona euro — "
            "singurul segment pentru care BCE publică moneda, adică "
            f"{ro_num(p_sub, 1)}% din obligațiunile deținute. Cele două nu sunt comparabile "
            "și nu trebuie citite ca aceeași mărime.",
            "Defalcarea pe tipuri de fonduri este publicată de BCE pentru România abia din "
            f"{ro_luna(luni_tip[0])}; graficul pe tipuri acoperă doar acele luni.",
            "Fondurile de piață monetară nu sunt incluse în acest set; ele sunt raportate "
            "împreună cu instituțiile de credit.",
            "Valorile sunt publicate de BCE în euro, deși cea mai mare parte a activelor sunt "
            "în lei: o depreciere a leului reduce automat cifrele exprimate în euro.",
            "Regenerare: <code>python3 scripts/financiara_04_03.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(date_df)} obs., {len(tot)} luni, {per_min} → {per_max}, "
          f"active totale = {act_now:,.0f} mil. EUR")


if __name__ == "__main__":
    main()
