#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 02 01 — Dobânzile la creditele noi acordate de băncile din România
Sursa: BCE (ECB Data Portal), setul MIR — MFI Interest Rate Statistics,
       date raportate de Banca Națională a României.
Frecvență: lunară. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.

Etichetele românești ale codurilor de dimensiune sunt preluate din codelist-urile
oficiale ECB (CL_BS_ITEM, CL_MATURITY_ORIG, CL_BS_COUNT_SECTOR, CL_AMOUNT_CAT,
CL_DATA_TYPE_MIR, CL_IR_BUS_COV) și traduse manual — vezi dicționarul ETICHETE.
"""
import datetime as dt
import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, fetch, ro_luna, ro_num)

COD = "Financiara 02 01"
SECTIUNE = "02 Bănci"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
API = "https://data-api.ecb.europa.eu/service/data/MIR"
PAGINA = "https://data.ecb.europa.eu/data/datasets/MIR"
START = "2007-01"

# ---------------------------------------------------------------------------
# Seriile folosite. Cheia SDMX are EXACT 10 puncte-separatoare (11 dimensiuni):
#   FREQ.REF_AREA.BS_REP_SECTOR.BS_ITEM.MATURITY_NOT_IRATE.DATA_TYPE_MIR.
#   AMOUNT_CAT.BS_COUNT_SECTOR.CURRENCY_TRANS.IR_BUS_COV
# ---------------------------------------------------------------------------
SERII = {
    # --- populație: credite pentru locuințe (A2C) ---------------------------
    "M.RO.B.A2C.F.R.A.2250.RON.N": ("Locuințe — dobândă fixată sub 1 an", "Populație"),
    "M.RO.B.A2C.I.R.A.2250.RON.N": ("Locuințe — dobândă fixată 1–5 ani", "Populație"),
    "M.RO.B.A2C.P.R.A.2250.RON.N": ("Locuințe — dobândă fixată peste 10 ani", "Populație"),
    # --- populație: credite de consum (A2B) ---------------------------------
    "M.RO.B.A2B.I.R.A.2250.RON.N": ("Consum — dobândă fixată 1–5 ani", "Populație"),
    "M.RO.B.A2B.J.R.A.2250.RON.N": ("Consum — dobândă fixată peste 5 ani", "Populație"),
    # --- populație: alte credite (A2D) --------------------------------------
    "M.RO.B.A2D.F.R.A.2250.RON.N": ("Alte credite — dobândă fixată sub 1 an", "Populație"),
    # --- populație: descoperit de cont și card de credit (A2Z) --------------
    "M.RO.B.A2Z.A.R.A.2250.RON.N": ("Descoperit de cont și card de credit", "Populație"),
    # --- firme nefinanciare (A2A / A2Z) -------------------------------------
    "M.RO.B.A2A.F.R.0.2240.RON.N": ("Firme — credite până la 1 mil. EUR, dobândă sub 1 an", "Firme"),
    "M.RO.B.A2A.F.R.1.2240.RON.N": ("Firme — credite peste 1 mil. EUR, dobândă sub 1 an", "Firme"),
    "M.RO.B.A2A.I.R.0.2240.RON.N": ("Firme — credite până la 1 mil. EUR, dobândă 1–5 ani", "Firme"),
    "M.RO.B.A2Z.A.R.A.2240.RON.N": ("Firme — descoperit de cont și card de credit", "Firme"),
    # --- DAE (costul total al creditului, inclusiv comisioane) --------------
    "M.RO.B.A2C.A.C.A.2250.RON.N": ("DAE credite locuințe în lei", "DAE"),
    "M.RO.B.A2C.A.C.A.2250.EUR.N": ("DAE credite locuințe în euro", "DAE"),
    "M.RO.B.A2B.A.C.A.2250.RON.N": ("DAE credite de consum în lei", "DAE"),
    # --- volume de creditare nouă (milioane lei) ----------------------------
    "M.RO.B.A2C.F.B.A.2250.RON.N": ("Volum credite locuințe, dobândă sub 1 an", "Volum"),
    "M.RO.B.A2C.I.B.A.2250.RON.N": ("Volum credite locuințe, dobândă 1–5 ani", "Volum"),
    "M.RO.B.A2C.P.B.A.2250.RON.N": ("Volum credite locuințe, dobândă peste 10 ani", "Volum"),
    "M.RO.B.A2B.I.B.A.2250.RON.N": ("Volum credite consum, dobândă 1–5 ani", "Volum"),
    "M.RO.B.A2A.F.B.0.2240.RON.N": ("Volum credite firme până la 1 mil. EUR", "Volum"),
    "M.RO.B.A2A.F.B.1.2240.RON.N": ("Volum credite firme peste 1 mil. EUR", "Volum"),
}

# Cereri grupate (codurile se combină cu „+" pe fiecare dimensiune).
CERERI = [
    "M.RO.B.A2B+A2C+A2D+A2Z.A+F+I+J+P.R+C.A.2250.RON+EUR.N",
    "M.RO.B.A2A+A2Z.A+F+I.R+B.0+1+A.2240.RON.N",
    "M.RO.B.A2B+A2C.A+F+I+J+P.B.A.2250.RON.N",
]

# Traducerea codurilor de dimensiune (verificate în codelist-urile ECB).
ETICHETE = {
    "BS_ITEM": {
        "A2A": "Credite către firme, exclusiv descoperit de cont și card de credit",
        "A2B": "Credite de consum, exclusiv descoperit de cont și card de credit",
        "A2C": "Credite pentru locuințe, exclusiv descoperit de cont și card de credit",
        "A2D": "Alte credite, exclusiv descoperit de cont și card de credit",
        "A2Z": "Descoperit de cont, card de credit (convenience și extended credit)",
    },
    "MATURITY_NOT_IRATE": {
        "A": "Total perioade de fixare a dobânzii", "F": "Până la 1 an",
        "I": "Peste 1 și până la 5 ani", "J": "Peste 5 ani",
        "P": "Peste 10 ani",
    },
    "DATA_TYPE_MIR": {
        "R": "Rată anualizată convenită (AAR/NDER)",
        "C": "Dobânda anuală efectivă (DAE)",
        "B": "Volum de afaceri (credite noi acordate)",
    },
    "AMOUNT_CAT": {"A": "Total", "0": "Până la 1 milion EUR", "1": "Peste 1 milion EUR"},
    "BS_COUNT_SECTOR": {
        "2240": "Societăți nefinanciare (firme, S.11)",
        "2250": "Gospodăriile populației și IFSLSGP (S.14 și S.15)",
    },
    "CURRENCY_TRANS": {"RON": "Leu românesc", "EUR": "Euro"},
    "IR_BUS_COV": {"N": "Credite noi (new business)"},
    "BS_REP_SECTOR": {"B": "Instituții care atrag depozite, exclusiv banca centrală (S.122)"},
}


def descarca_ecb(cereri, serii) -> pd.DataFrame:
    """Descarcă seriile MIR și întoarce un DataFrame lung (cheie, lună, valoare)."""
    bucati = []
    for c in cereri:
        url = f"{API}/{c}?format=csvdata&startPeriod={START}&detail=dataonly"
        r = fetch(url)
        txt = r.content.decode("utf-8")
        if txt.lstrip().startswith("<"):
            raise SystemExit(f"EȘEC: ECB a întors HTML (cheie invalidă?) pentru {c}")
        bucati.append(pd.read_csv(io.StringIO(txt), low_memory=False))
    d = pd.concat(bucati, ignore_index=True)
    d = d[d.OBS_VALUE.notna()].copy()
    d["cheie"] = d.KEY.str.replace("^MIR\\.", "", regex=True)
    d = d[d.cheie.isin(serii)].copy()

    lipsa = sorted(set(serii) - set(d.cheie.unique()))
    if lipsa:
        raise SystemExit("EȘEC: seriile următoare nu au întors nicio observație: "
                         + ", ".join(lipsa))
    d = d.rename(columns={"TIME_PERIOD": "luna", "OBS_VALUE": "valoare"})
    d["indicator"] = d.cheie.map(lambda k: serii[k][0])
    d["grup"] = d.cheie.map(lambda k: serii[k][1])
    return d[["luna", "cheie", "indicator", "grup", "valoare",
              "BS_ITEM", "MATURITY_NOT_IRATE", "DATA_TYPE_MIR", "AMOUNT_CAT",
              "BS_COUNT_SECTOR", "CURRENCY_TRANS", "IR_BUS_COV"]].sort_values(
        ["luna", "cheie"]).reset_index(drop=True)


def main() -> None:
    d = descarca_ecb(CERERI, SERII)
    fail_if_short(d, 3000, "ECB MIR — dobânzi la creditele noi, România")

    w = d.pivot_table(index="luna", columns="indicator", values="valoare",
                      aggfunc="first").sort_index()
    rate_pop = [SERII[k][0] for k in SERII if SERII[k][1] == "Populație"]
    rate_firme = [SERII[k][0] for k in SERII if SERII[k][1] == "Firme"]
    dae = [SERII[k][0] for k in SERII if SERII[k][1] == "DAE"]
    volume = [SERII[k][0] for k in SERII if SERII[k][1] == "Volum"]
    rate = rate_pop + rate_firme

    ultima = w[rate].dropna(how="all").index.max()
    fail_if_stale(ultima, 4, "ECB MIR România")
    prima = w.index.min()
    azi = dt.date.today().isoformat()

    # --- foi de analiză ----------------------------------------------------
    a_rate = w[rate].round(2).reset_index().rename(columns={"luna": "Luna"})
    a_dae = w[dae].round(2).reset_index().rename(columns={"luna": "Luna"})

    ref_loc = "Locuințe — dobândă fixată 1–5 ani"
    ref_cons = "Consum — dobândă fixată 1–5 ani"
    ref_firme = "Firme — credite până la 1 mil. EUR, dobândă sub 1 an"

    a_din = pd.DataFrame({"Luna": w.index})
    for et, col in (("Locuințe", ref_loc), ("Consum", ref_cons), ("Firme", ref_firme)):
        s = w[col]
        a_din[f"{et} (%)"] = s.round(2).values
        a_din[f"{et} — variație lunară (p.p.)"] = s.diff().round(2).values
        a_din[f"{et} — variație 12 luni (p.p.)"] = s.diff(12).round(2).values
        a_din[f"{et} — medie mobilă 12 luni (%)"] = s.rolling(12).mean().round(2).values

    a_cost = pd.DataFrame({
        "Luna": w.index,
        "DAE credite locuințe lei (%)": w["DAE credite locuințe în lei"].round(2).values,
        "Dobânda nominală locuințe 1–5 ani (%)": w[ref_loc].round(2).values,
        "Cost suplimentar din comisioane (p.p.)":
            (w["DAE credite locuințe în lei"] - w[ref_loc]).round(2).values,
        "DAE credite consum lei (%)": w["DAE credite de consum în lei"].round(2).values,
        "Dobânda nominală consum 1–5 ani (%)": w[ref_cons].round(2).values,
        "Diferență lei – euro, locuințe (p.p.)":
            (w["DAE credite locuințe în lei"] -
             w["DAE credite locuințe în euro"]).round(2).values,
    })

    a_dif = pd.DataFrame({
        "Luna": w.index,
        "Populație (locuințe 1–5 ani) (%)": w[ref_loc].round(2).values,
        "Firme (până la 1 mil. EUR) (%)": w[ref_firme].round(2).values,
        "Diferență populație – firme (p.p.)": (w[ref_loc] - w[ref_firme]).round(2).values,
        "Firme mici vs. firme mari (p.p.)":
            (w["Firme — credite până la 1 mil. EUR, dobândă sub 1 an"] -
             w["Firme — credite peste 1 mil. EUR, dobândă sub 1 an"]).round(2).values,
        "Descoperit de cont populație (%)":
            w["Descoperit de cont și card de credit"].round(2).values,
        "Descoperit de cont firme (%)":
            w["Firme — descoperit de cont și card de credit"].round(2).values,
    })

    an = w[rate + volume].groupby(w.index.str[:4])
    a_anual = an.mean().round(2)
    a_anual.insert(0, "Luni raportate", w[ref_loc].groupby(w.index.str[:4]).count())
    a_anual = a_anual.reset_index().rename(columns={"luna": "An"})

    vol = w[volume]
    a_vol = vol.round(0).reset_index().rename(columns={"luna": "Luna"})
    a_vol["Total volum urmărit (mil. lei)"] = vol.sum(axis=1, min_count=1).round(0).values

    rep = []
    for col in rate + dae:
        s = w[col].dropna()
        if s.empty:
            continue
        rep.append({
            "Indicator": col, "Minim (%)": round(s.min(), 2), "Luna minimului": s.idxmin(),
            "Maxim (%)": round(s.max(), 2), "Luna maximului": s.idxmax(),
            "Ultima valoare (%)": round(s.iloc[-1], 2), "Ultima lună": s.index[-1],
            "Medie 12 luni (%)": round(s.tail(12).mean(), 2),
            "Medie pe tot istoricul (%)": round(s.mean(), 2),
        })
    a_rep = pd.DataFrame(rep)

    a_dict = pd.DataFrame(
        [{"Dimensiune": dim, "Cod": cod, "Denumire în română": nume}
         for dim, m in ETICHETE.items() for cod, nume in m.items()])

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Dobânzile la creditele noi acordate de băncile din România",
        "subtitlu": "Cât costă un credit nou pentru o familie sau o firmă: rata anualizată "
                    "convenită și dobânda anuală efectivă (DAE), lună de lună, din 2007.",
        "sursa": "Banca Centrală Europeană — ECB Data Portal, setul MIR "
                 "(MFI Interest Rate Statistics); date raportate de Banca Națională a României",
        "sursa_url": PAGINA,
        "cod_set": "MIR (ECB_MIR1). Chei SDMX folosite (11 dimensiuni, 10 puncte): "
                   + "; ".join(sorted(SERII)),
        "frecventa": "Lunară",
        "perioada": f"{prima} → {ultima}",
        "unitate": "procente pe an (% p.a.); diferențele în puncte procentuale (p.p.); "
                   "volumele în milioane lei",
        "descarcat": azi,
        "licenta": "BCE — reutilizare permisă cu menționarea sursei "
                   "(ECB copyright / general terms of use for ECB statistics).",
        "metodologie": "Statistica MIR acoperă ratele dobânzii practicate de instituțiile care "
                       "atrag depozite, exclusiv banca centrală (sectorul S.122), pentru "
                       "contractele NOI încheiate în luna de referință cu rezidenți din zona "
                       "euro extinsă. „Rata anualizată convenită” (AAR/NDER) este dobânda "
                       "propriu-zisă, fără comisioane; „DAE” include și costurile conexe "
                       "(comisioane de analiză, de administrare, asigurări obligatorii). "
                       "Ratele sunt medii ponderate cu volumul creditelor noi din lună. "
                       "Categoriile de maturitate se referă la perioada de fixare inițială a "
                       "dobânzii, nu la durata creditului.",
        "script": "scripts/financiara_02_01.py",
        "note": [
            "Sectorul „populație” (cod 2250) include gospodăriile populației și instituțiile "
            "fără scop lucrativ în serviciul gospodăriilor.",
            "Sectorul „firme” (cod 2240) cuprinde societățile nefinanciare (S.11); pragul de "
            "1 milion EUR separă creditele acordate IMM-urilor de cele ale companiilor mari.",
            "„Perioada de fixare a dobânzii sub 1 an” înseamnă, în practică, credite cu "
            "dobândă variabilă (indexate la IRCC sau ROBOR).",
            "Volumele sunt sumele efectiv acordate în luna respectivă, nu soldurile rămase "
            "de rambursat.",
        ],
        "avertismente": [
            "Pentru România, setul MIR conține aproape exclusiv serii în lei (RON). Singura "
            "serie în euro disponibilă este DAE la creditele pentru locuință "
            "(M.RO.B.A2C.A.C.A.2250.EUR.N) — nu există serii AAR în euro.",
            "Seriile „totale” A2A.A / A2B.A / A2C.A (toate perioadele de fixare) încep abia "
            "în august 2017; pentru istoric lung din 2007 trebuie folosite seriile pe "
            "perioade de fixare (F, I, J, P).",
            "Unele chei apar în lista de serii (detail=serieskeysonly) fără să aibă vreo "
            "observație (ex. L23.D / L23.E pentru România) — existența cheii nu garantează date.",
            "Cheia SDMX pentru MIR trebuie să aibă exact 10 puncte; altfel API-ul întoarce "
            "HTTP 400 cu o pagină HTML în loc de CSV.",
            "Seria „Locuințe — dobândă fixată peste 10 ani” are întreruperi (nu în toate lunile "
            "s-au acordat astfel de credite); golurile rămân goale, nu se interpolează.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=d.rename(columns={
            "luna": "Luna", "cheie": "Cheie SDMX", "indicator": "Indicator",
            "grup": "Grup", "valoare": "Valoare",
            "BS_ITEM": "Cod produs (BS_ITEM)",
            "MATURITY_NOT_IRATE": "Cod fixare dobândă",
            "DATA_TYPE_MIR": "Cod tip de dată", "AMOUNT_CAT": "Cod categorie sumă",
            "BS_COUNT_SECTOR": "Cod sector client", "CURRENCY_TRANS": "Monedă",
            "IR_BUS_COV": "Cod acoperire"}),
        analize={
            "Rate lunare": a_rate,
            "DAE si costul total": a_dae,
            "Dinamica dobanzilor": a_din,
            "Comisioane si moneda": a_cost,
            "Populatie vs firme": a_dif,
            "Medii anuale": a_anual,
            "Volume credite noi": a_vol,
            "Repere istorice": a_rep,
            "Dictionar coduri": a_dict,
        },
        note_analize={
            "Rate lunare": "Ratele anualizate convenite (AAR/NDER) la creditele noi, în % pe an.",
            "DAE si costul total": "Dobânda anuală efectivă — include comisioanele, deci arată "
                                   "costul real al creditului.",
            "Dinamica dobanzilor": "Variații lunare, variații față de aceeași lună a anului "
                                   "trecut și medii mobile pe 12 luni.",
            "Comisioane si moneda": "Diferența dintre DAE și dobânda nominală arată cât "
                                    "adaugă comisioanele la costul creditului.",
            "Populatie vs firme": "Cât plătește în plus populația față de firme și firmele mici "
                                  "față de cele mari.",
            "Medii anuale": "Media lunilor raportate din fiecare an calendaristic.",
            "Volume credite noi": "Sumele efectiv acordate în fiecare lună, în milioane lei.",
            "Repere istorice": "Minime, maxime și medii pentru fiecare serie.",
            "Dictionar coduri": "Traducerea codurilor de dimensiune SDMX, conform "
                                "codelist-urilor oficiale ECB.",
        },
        numfmt="0.00")

    # --- pagina HTML -------------------------------------------------------
    et = [ro_luna(p) for p in w.index]
    v_loc = float(w[ref_loc].dropna().iloc[-1])
    v_cons = float(w[ref_cons].dropna().iloc[-1])
    v_firme = float(w[ref_firme].dropna().iloc[-1])
    s_loc = w[ref_loc].dropna()
    var12 = float(s_loc.iloc[-1] - s_loc.iloc[-13]) if len(s_loc) > 13 else None
    dae_loc = float(w["DAE credite locuințe în lei"].dropna().iloc[-1])

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "BCE — ECB Data Portal, setul MIR (raportări BNR)",
        "sursa_url": PAGINA, "frecventa": "Lunar",
        "perioada": f"{ro_luna(prima)} – {ro_luna(ultima)}", "actualizat": azi,
        "kpis": [
            {"eticheta": f"Credit pentru locuință, {ro_luna(ultima)}",
             "valoare": f"{ro_num(v_loc, 2)}%",
             "nota": "dobândă fixată 1–5 ani, credite noi în lei"},
            {"eticheta": "DAE la creditul pentru locuință",
             "valoare": f"{ro_num(dae_loc, 2)}%",
             "nota": "costul total, cu comisioane incluse"},
            {"eticheta": "Credit de consum",
             "valoare": f"{ro_num(v_cons, 2)}%", "nota": "dobândă fixată 1–5 ani"},
            {"eticheta": "Credit pentru firme mici",
             "valoare": f"{ro_num(v_firme, 2)}%",
             "nota": f"sub 1 mil. EUR · locuințe {'+' if (var12 or 0) >= 0 else ''}"
                     f"{ro_num(var12, 2)} p.p. în 12 luni"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Cât costă creditele populației",
             "subtitlu": "Rata anualizată convenită la creditele noi în lei, pe tipuri de credit.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "Locuințe (fixare 1–5 ani)", "data": clean(w[ref_loc])},
                 {"name": "Consum (fixare 1–5 ani)", "data": clean(w[ref_cons])},
                 {"name": "Alte credite (sub 1 an)",
                  "data": clean(w["Alte credite — dobândă fixată sub 1 an"])},
                 {"name": "Descoperit de cont / card",
                  "data": clean(w["Descoperit de cont și card de credit"])},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Creditele firmelor: mici vs. mari",
             "subtitlu": "Firmele care iau credite sub 1 milion de euro plătesc, de regulă, "
                         "mai mult decât companiile mari.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "Până la 1 mil. EUR", "data": clean(w[ref_firme])},
                 {"name": "Peste 1 mil. EUR",
                  "data": clean(w["Firme — credite peste 1 mil. EUR, dobândă sub 1 an"])},
                 {"name": "Descoperit de cont firme",
                  "data": clean(w["Firme — descoperit de cont și card de credit"])},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "Dobânda anunțată și costul real (DAE)",
             "subtitlu": "DAE include comisioanele și asigurările obligatorii; diferența față "
                         "de dobânda nominală arată cât adaugă acestea la factură.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "ylabel": "% pe an",
             "series": [
                 {"name": "DAE locuințe, lei",
                  "data": clean(w["DAE credite locuințe în lei"])},
                 {"name": "Dobândă nominală locuințe", "data": clean(w[ref_loc]),
                  "dashed": True},
                 {"name": "DAE locuințe, euro",
                  "data": clean(w["DAE credite locuințe în euro"])},
                 {"name": "DAE consum, lei",
                  "data": clean(w["DAE credite de consum în lei"])},
             ]},
            {"id": "c4", "type": "line",
             "titlu": "Cu cât plătește populația mai mult decât firmele",
             "subtitlu": "Diferența, în puncte procentuale, între dobânda la creditul pentru "
                         "locuință și cea la creditul pentru o firmă mică.",
             "labels": et, "unit": "p.p.", "dec": 2, "ydec": 0,
             "series": [
                 {"name": "Locuințe – firme mici", "data": clean(w[ref_loc] - w[ref_firme])},
                 {"name": "Consum – firme mici", "data": clean(w[ref_cons] - w[ref_firme])},
             ]},
            {"id": "c5", "type": "bar",
             "titlu": "Media anuală a dobânzilor",
             "subtitlu": "Ultimul an conține doar lunile raportate până acum.",
             "labels": list(a_anual["An"]), "unit": "%", "dec": 2, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Locuințe", "data": clean(a_anual[ref_loc])},
                 {"name": "Consum", "data": clean(a_anual[ref_cons])},
                 {"name": "Firme mici", "data": clean(a_anual[ref_firme])},
             ]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(w)} luni în fișierul Excel)",
            "columns": ["Luna", "Locuințe 1–5 ani (%)", "DAE locuințe (%)", "Consum 1–5 ani (%)",
                        "DAE consum (%)", "Firme sub 1 mil. EUR (%)", "Firme peste 1 mil. EUR (%)",
                        "Descoperit de cont populație (%)"],
            "rows": [[ro_luna(i),
                      ro_num(r[ref_loc], 2), ro_num(r["DAE credite locuințe în lei"], 2),
                      ro_num(r[ref_cons], 2), ro_num(r["DAE credite de consum în lei"], 2),
                      ro_num(r[ref_firme], 2),
                      ro_num(r["Firme — credite peste 1 mil. EUR, dobândă sub 1 an"], 2),
                      ro_num(r["Descoperit de cont și card de credit"], 2)]
                     for i, r in w.tail(36).iloc[::-1].iterrows()],
        },
        "note": [
            "Sursa: Banca Centrală Europeană, ECB Data Portal, setul <code>MIR</code> "
            "(MFI Interest Rate Statistics). Datele pentru România sunt raportate lunar de "
            "Banca Națională a României.",
            "<strong>Ce măsoară.</strong> Dobânzile de aici sunt cele la creditele "
            "<em>noi acordate</em> în luna respectivă, nu la creditele aflate deja în derulare. "
            "Sunt medii ponderate cu sumele împrumutate, pe toate băncile din România.",
            "<strong>Dobândă nominală vs. DAE.</strong> Rata anualizată convenită (AAR/NDER) "
            "este dobânda propriu-zisă. Dobânda anuală efectivă (DAE) adaugă comisioanele de "
            "analiză și administrare și asigurările obligatorii — este cifra care arată cât "
            "costă în realitate creditul.",
            "<strong>„Perioada de fixare a dobânzii”</strong> nu este durata creditului. Un "
            "credit ipotecar pe 30 de ani cu dobândă variabilă indexată la IRCC apare la "
            "categoria „fixare sub 1 an”; unul cu dobândă fixă în primii 5 ani apare la "
            "„fixare 1–5 ani”.",
            "Pragul de 1 milion de euro la creditele pentru firme este folosit de BCE ca "
            "aproximare pentru separarea IMM-urilor de companiile mari.",
            "Pentru România, setul MIR conține practic doar serii în lei; singura serie în euro "
            "este DAE la creditele pentru locuință.",
            "Regenerare: <code>python3 scripts/financiara_02_01.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(d)} obs., {len(SERII)} serii, {len(w)} luni, {prima} → {ultima}; "
          f"locuințe 1–5 ani = {v_loc:.2f}%, DAE = {dae_loc:.2f}%")


if __name__ == "__main__":
    main()
