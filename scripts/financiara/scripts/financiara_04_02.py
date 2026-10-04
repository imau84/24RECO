#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 04 02 — Unde își țin banii românii: depozitele la bănci, pe maturități și sectoare
Sursa: BCE, Data Portal, setul BSI (bilanțul instituțiilor financiare monetare)
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

COD = "Financiara 04 02"
SECTIUNE = "04 Investiții financiare"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
API = "https://data-api.ecb.europa.eu/service/data/BSI"
PAGINA = "https://data.ecb.europa.eu/data/datasets/BSI"
START = "2007-01"

# BSI are 11 dimensiuni:
# FREQ.REF_AREA.ADJUSTMENT.BS_REP_SECTOR.BS_ITEM.MATURITY_ORIG.DATA_TYPE.
# COUNT_AREA.BS_COUNT_SECTOR.CURRENCY_TRANS.BS_SUFFIX
# Numărul de puncte din cheie trebuie să fie EXACT 10 (11 câmpuri), altfel HTTP 400.
ITEME = {"L20": "Depozite — total", "L21": "Depozite la vedere",
         "L22": "Depozite la termen", "L23": "Depozite rambursabile după notificare",
         "L24": "Operațiuni repo"}
MATURITATI = {"A": "toate maturitățile", "F": "sub 1 an",
              "G": "1–2 ani", "H": "peste 2 ani",
              "D": "notificare sub 3 luni", "E": "notificare peste 3 luni",
              "L": "sub 2 ani (agregat)"}
SECTOARE = {"2250": "Populație (gospodării)",
            "2240": "Firme nefinanciare",
            "2210": "Instituții financiare nebancare",
            "2220": "Asigurări și fonduri de pensii",
            "2300": "Total deponenți (exclusiv administrația centrală)"}
TIP_DATE = {"1": "Solduri (stocuri)", "4": "Tranzacții (flux net lunar)",
            "I": "Ritm anual de creștere (%)"}


def _get(cheie: str, eticheta: str, minim: int) -> pd.DataFrame:
    u = f"{API}/{cheie}?format=csvdata&startPeriod={START}"
    r = fetch(u, timeout=240)
    if not r.text.lstrip().startswith("KEY"):
        raise SystemExit(f"EȘEC: {eticheta} nu a întors CSV (probabil cheie cu număr greșit "
                         f"de puncte). Primele 200 de caractere: {r.text[:200]!r}")
    df = pd.read_csv(io.StringIO(r.text), dtype={"BS_COUNT_SECTOR": str})
    fail_if_short(df, minim, eticheta)
    return df


def descarca() -> pd.DataFrame:
    sect = "2250+2240+2210+2220+2300"
    parti = [
        _get(f"M.RO.N.A.L20+L21.A.1.U6.{sect}.Z01.E", "BSI solduri total/la vedere", 2200),
        _get(f"M.RO.N.A.L22.F+G+H.1.U6.{sect}.Z01.E", "BSI solduri la termen pe maturități", 3300),
        _get(f"M.RO.N.A.L23+L24.A+D+E.1.U6.{sect}.Z01.E", "BSI solduri notificare/repo", 3300),
        _get(f"M.RO.N.A.L20+L21.A.4.U6.{sect}.Z01.E", "BSI tranzacții", 2200),
        _get(f"M.RO.N.A.L22.F+G+H.4.U6.{sect}.Z01.E", "BSI tranzacții la termen", 3300),
        _get(f"M.RO.N.A.L20+L21.A.I.U6.{sect}.Z01.A", "BSI ritm de creștere", 2200),
        _get(f"M.RO.N.A.L22.F+G+H.I.U6.{sect}.Z01.A", "BSI ritm de creștere la termen", 3300),
    ]
    cols = ["KEY", "BS_ITEM", "MATURITY_ORIG", "DATA_TYPE", "BS_COUNT_SECTOR",
            "TIME_PERIOD", "OBS_VALUE", "UNIT"]
    df = pd.concat([p[cols] for p in parti], ignore_index=True)
    df["DATA_TYPE"] = df["DATA_TYPE"].astype(str)
    df = df.dropna(subset=["OBS_VALUE"])
    fail_if_short(df, 19000, "BSI România — set complet")
    return df


def _piv(df, dt_code, item, mat, col="BS_COUNT_SECTOR"):
    s = df[(df.DATA_TYPE == dt_code) & (df.BS_ITEM == item) & (df.MATURITY_ORIG == mat)]
    return s.pivot_table(index="TIME_PERIOD", columns=col, values="OBS_VALUE").sort_index()


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()

    tot = _piv(df, "1", "L20", "A")          # depozite totale, pe sectoare
    ved = _piv(df, "1", "L21", "A")          # la vedere
    t_f = _piv(df, "1", "L22", "F")          # termen sub 1 an
    t_g = _piv(df, "1", "L22", "G")          # termen 1–2 ani
    t_h = _piv(df, "1", "L22", "H")          # termen peste 2 ani
    term = (t_f.fillna(0) + t_g.fillna(0) + t_h.fillna(0)).where(t_f.notna())

    fl_tot = _piv(df, "4", "L20", "A")       # tranzacții lunare nete
    gr_tot = _piv(df, "I", "L20", "A")       # ritm anual de creștere

    per_min, per_max = tot.index.min(), tot.index.max()
    fail_if_stale(per_max, 4, "BCE BSI România")
    for s in ("2250", "2240", "2300"):
        if s not in tot.columns:
            raise SystemExit(f"EȘEC: sectorul {s} lipsește din BSI — structura setului s-a schimbat.")

    pop, fir, tot_all = "2250", "2240", "2300"

    # --- foile de analiză --------------------------------------------------
    a_sold = tot.rename(columns=SECTOARE).round(0).reset_index().rename(
        columns={"TIME_PERIOD": "Luna"})
    ord_sect = ["Luna"] + [SECTOARE[k] for k in SECTOARE if SECTOARE[k] in a_sold.columns]
    a_sold = a_sold[ord_sect]

    a_pop = pd.DataFrame({
        "Luna": tot.index,
        "Depozite totale (mil. EUR)": tot[pop].round(0).values,
        "La vedere (mil. EUR)": ved[pop].round(0).values,
        "La termen sub 1 an (mil. EUR)": t_f[pop].round(0).values,
        "La termen 1–2 ani (mil. EUR)": t_g[pop].round(0).values,
        "La termen peste 2 ani (mil. EUR)": t_h[pop].round(0).values,
        "Pondere la vedere (%)": (100 * ved[pop] / tot[pop]).round(1).values,
        "Pondere la termen (%)": (100 * term[pop] / tot[pop]).round(1).values,
    })

    a_fir = pd.DataFrame({
        "Luna": tot.index,
        "Depozite totale (mil. EUR)": tot[fir].round(0).values,
        "La vedere (mil. EUR)": ved[fir].round(0).values,
        "La termen sub 1 an (mil. EUR)": t_f[fir].round(0).values,
        "La termen 1–2 ani (mil. EUR)": t_g[fir].round(0).values,
        "La termen peste 2 ani (mil. EUR)": t_h[fir].round(0).values,
        "Pondere la vedere (%)": (100 * ved[fir] / tot[fir]).round(1).values,
    })

    a_flux = pd.DataFrame({"Luna": fl_tot.index})
    for s in (pop, fir, tot_all):
        if s in fl_tot.columns:
            a_flux[f"{SECTOARE[s]} — flux net lunar (mil. EUR)"] = fl_tot[s].round(0).values
            a_flux[f"{SECTOARE[s]} — cumulat 12 luni"] = fl_tot[s].rolling(12).sum().round(0).values
    a_flux = a_flux.dropna(how="all", subset=[c for c in a_flux.columns if c != "Luna"])

    a_ritm = gr_tot.rename(columns=SECTOARE).round(1).dropna(how="all").reset_index().rename(
        columns={"TIME_PERIOD": "Luna"})
    a_ritm = a_ritm[[c for c in ord_sect if c in a_ritm.columns]]

    struct = pd.DataFrame({
        "Luna": tot.index,
        "Populație — pondere la vedere (%)": (100 * ved[pop] / tot[pop]).round(1).values,
        "Populație — pondere termen sub 1 an (%)": (100 * t_f[pop] / tot[pop]).round(1).values,
        "Populație — pondere termen peste 1 an (%)":
            (100 * (t_g.fillna(0) + t_h.fillna(0))[pop] / tot[pop]).round(1).values,
        "Firme — pondere la vedere (%)": (100 * ved[fir] / tot[fir]).round(1).values,
        "Populație / firme (raport solduri)": (tot[pop] / tot[fir]).round(2).values,
    })

    an = tot.copy()
    an["An"] = an.index.str[:4]
    dec = an.groupby("An").last()
    a_anual = pd.DataFrame({"An": dec.index})
    for s in SECTOARE:
        if s in dec.columns:
            a_anual[f"{SECTOARE[s]} — sold la final de an (mil. EUR)"] = dec[s].round(0).values
    a_anual[f"{SECTOARE[pop]} — variație anuală (%)"] = (100 * dec[pop].pct_change()).round(1).values

    ult = pd.DataFrame({
        "Categorie": ["Depozite totale", "La vedere", "La termen sub 1 an",
                      "La termen 1–2 ani", "La termen peste 2 ani"],
        f"Populație, {ro_luna(per_max)} (mil. EUR)": [
            tot[pop].iloc[-1], ved[pop].iloc[-1], t_f[pop].iloc[-1],
            t_g[pop].iloc[-1], t_h[pop].iloc[-1]],
        f"Firme nefinanciare, {ro_luna(per_max)} (mil. EUR)": [
            tot[fir].iloc[-1], ved[fir].iloc[-1], t_f[fir].iloc[-1],
            t_g[fir].iloc[-1], t_h[fir].iloc[-1]],
        "Populație — acum 12 luni (mil. EUR)": [
            tot[pop].iloc[-13], ved[pop].iloc[-13], t_f[pop].iloc[-13],
            t_g[pop].iloc[-13], t_h[pop].iloc[-13]] if len(tot) > 13 else [None] * 5,
    }).round(0)
    ult["Populație — variație 12 luni (%)"] = (
        100 * (ult.iloc[:, 1] / ult["Populație — acum 12 luni (mil. EUR)"] - 1)).round(1)

    date_df = df.copy()
    date_df["Instrument"] = date_df["BS_ITEM"].map(ITEME)
    date_df["Maturitate"] = date_df["MATURITY_ORIG"].map(MATURITATI)
    date_df["Sector deponent"] = date_df["BS_COUNT_SECTOR"].map(SECTOARE)
    date_df["Tip serie"] = date_df["DATA_TYPE"].map(TIP_DATE)
    date_df = date_df[["TIME_PERIOD", "KEY", "Instrument", "Maturitate", "Sector deponent",
                       "Tip serie", "OBS_VALUE", "UNIT"]]
    date_df.columns = ["Luna", "Cheie SDMX", "Instrument", "Maturitate", "Sector deponent",
                       "Tip serie", "Valoare", "Unitate"]
    date_df = date_df.sort_values(["Luna", "Cheie SDMX"]).reset_index(drop=True)

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Unde își țin banii românii: depozitele la bănci, pe maturități și sectoare",
        "subtitlu": "Economisirea populației și a firmelor în sistemul bancar românesc — "
                    "cât stă în conturi curente, cât în depozite la termen și cum se schimbă "
                    "raportul, lună de lună.",
        "sursa": "Banca Centrală Europeană — Data Portal, setul BSI (bilanțul IFM)",
        "sursa_url": PAGINA,
        "cod_set": (
            "BSI, 11 dimensiuni: FREQ.REF_AREA.ADJUSTMENT.BS_REP_SECTOR.BS_ITEM."
            "MATURITY_ORIG.DATA_TYPE.COUNT_AREA.BS_COUNT_SECTOR.CURRENCY_TRANS.BS_SUFFIX. "
            "Chei folosite: M.RO.N.A.L20+L21.A.{1|4|I}.U6.2210+2220+2240+2250+2300.Z01.{E|A} "
            "și M.RO.N.A.L22.F+G+H.{1|4|I}.U6.<sectoare>.Z01.{E|A}, plus "
            "M.RO.N.A.L23+L24.A+D+E.1.U6.<sectoare>.Z01.E"),
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "milioane EUR pentru solduri și tranzacții; procente pentru ritmul de creștere",
        "descarcat": azi,
        "licenta": "BCE — reutilizare permisă cu menționarea sursei "
                   "(https://www.ecb.europa.eu/services/disclaimer/html/index.en.html).",
        "metodologie": (
            "Setul BSI cuprinde bilanțul agregat al instituțiilor financiare monetare (băncile "
            "comerciale, fără banca centrală) raportat de fiecare bancă centrală națională la "
            "BCE, conform Regulamentului BCE/2021/2. Depozitele sunt pasive ale băncilor față "
            "de clienți. „Solduri” = stocul la sfârșitul lunii. „Tranzacții” = variația lunară "
            "curățată de reclasificări, reevaluări și efecte de curs valutar. „Ritm anual de "
            "creștere” este calculat de BCE pe baza tranzacțiilor, nu a soldurilor, deci nu "
            "conține efectul aprecierii sau deprecierii leului."),
        "script": "scripts/financiara_04_02.py",
        "note": [
            "Sectorul 2250 este populația (gospodăriile, inclusiv instituțiile fără scop "
            "lucrativ în serviciul lor), 2240 sunt firmele nefinanciare.",
            "Depozitele rambursabile după notificare (L23) și operațiunile repo (L24) sunt "
            "practic zero în România — au fost descărcate pentru completitudine.",
            "Maturitatea se referă la durata inițial convenită, nu la durata rămasă.",
            "„Total deponenți” (2300) exclude administrația centrală, dar include "
            "administrațiile locale și fondurile de asigurări sociale.",
            "Agentul secțiunii 02 Bănci folosește același set BSI pentru creditare și pentru "
            "soldurile agregate; setul de față acoperă exclusiv latura de economisire.",
        ],
        "avertismente": [
            "Cheia SDMX trebuie să aibă exact 10 puncte (11 câmpuri). Un punct în minus "
            "întoarce HTTP 400 cu o pagină HTML, nu cu JSON de eroare.",
            "BCE publică soldurile pentru România convertite în EURO la cursul de la finalul "
            "lunii. O bună parte din depozitele românești sunt în lei, deci variația exprimată "
            "în euro amestecă evoluția reală cu efectul de curs. Pentru dinamică reală "
            "folosiți seriile de tranzacții (DATA_TYPE=4) și ritmul de creștere (DATA_TYPE=I), "
            "care sunt curățate de efectul valutar.",
            "Defalcarea pe monedă (RON vs. valută) NU este disponibilă în BSI pentru România — "
            "dimensiunea CURRENCY_TRANS are doar valoarea Z01 („toate monedele”) pentru "
            "depozitele românești.",
            "Pentru sectoarele 2240 și 2250 nu există serie L22 cu maturitate „A” (total); "
            "totalul depozitelor la termen se obține însumând maturitățile F, G și H.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta, date_df=date_df,
        analize={
            "Solduri pe sectoare": a_sold,
            "Depozitele populației": a_pop,
            "Depozitele firmelor": a_fir,
            "Fluxuri lunare nete": a_flux,
            "Ritm anual de creștere": a_ritm,
            "Structura economisirii": struct,
            "Solduri la final de an": a_anual,
            "Sinteza ultimei luni": ult,
        },
        note_analize={
            "Solduri pe sectoare": "Soldul depozitelor la sfârșitul fiecărei luni, pe sectorul deponentului (mil. EUR).",
            "Depozitele populației": "Defalcarea depozitelor gospodăriilor pe tip și maturitate, cu ponderile calculate.",
            "Depozitele firmelor": "Aceeași defalcare pentru firmele nefinanciare.",
            "Fluxuri lunare nete": "Tranzacții BCE — banii efectiv depuși minus cei retrași, fără efecte de curs sau reevaluare.",
            "Ritm anual de creștere": "Creșterea față de aceeași lună a anului precedent, calculată de BCE pe tranzacții (%).",
            "Structura economisirii": "Cât din bani stă în cont curent și cât la termen — indicatorul preferinței pentru lichiditate.",
            "Solduri la final de an": "Soldul din decembrie al fiecărui an; ultimul an conține ultima lună raportată.",
            "Sinteza ultimei luni": "Fotografia ultimei luni, cu comparația față de aceeași lună a anului trecut.",
        },
        numfmt="#,##0")

    # --- pagina HTML ------------------------------------------------------
    et = [ro_luna(p) for p in tot.index]
    pop_now = float(tot[pop].iloc[-1])
    pop_12 = float(tot[pop].iloc[-13]) if len(tot) > 13 else None
    pond_ved = float(100 * ved[pop].iloc[-1] / tot[pop].iloc[-1])
    ritm = float(gr_tot[pop].dropna().iloc[-1]) if pop in gr_tot.columns and gr_tot[pop].notna().any() else None
    flux12 = float(fl_tot[pop].rolling(12).sum().iloc[-1])

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "BCE — Data Portal, setul BSI (bilanțul instituțiilor financiare monetare)",
        "sursa_url": PAGINA,
        "frecventa": "Lunar",
        "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Depozitele populației, {ro_luna(per_max)}",
             "valoare": f"{ro_num(pop_now / 1000, 1)} mld. EUR",
             "nota": (f"{'+' if pop_now >= pop_12 else '−'}"
                      f"{ro_num(abs(100 * (pop_now / pop_12 - 1)), 1)}% față de acum un an")
                     if pop_12 else "sold la sfârșit de lună"},
            {"eticheta": "Ritm anual de creștere (curățat de curs)",
             "valoare": f"{ro_num(ritm, 1)}%" if ritm is not None else "–",
             "nota": "calculat de BCE pe tranzacții, nu pe solduri",
             "trend": "up" if (ritm or 0) > 0 else "down"},
            {"eticheta": "Bani ținuți în cont curent",
             "valoare": f"{ro_num(pond_ved, 1)}%",
             "nota": "din depozitele populației, restul fiind la termen"},
            {"eticheta": "Bani depuși net în ultimele 12 luni",
             "valoare": f"{'+' if flux12 >= 0 else '−'}{ro_num(abs(flux12) / 1000, 1)} mld. EUR",
             "nota": "depuneri minus retrageri, populație"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Depozitele populației și ale firmelor la băncile din România",
             "subtitlu": "Sold la sfârșitul fiecărei luni, în miliarde de euro. Valorile sunt "
                         "convertite de BCE în euro la cursul de la finalul lunii.",
             "labels": et, "unit": "mld. EUR", "dec": 1, "ydec": 0,
             "series": [
                 {"name": SECTOARE[pop], "data": clean(tot[pop] / 1000)},
                 {"name": SECTOARE[fir], "data": clean(tot[fir] / 1000)},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Banii la vedere față de banii puși deoparte — populație",
             "subtitlu": "Cont curent și economii la vedere, față de depozitele la termen. "
                         "Când dobânzile cresc, banii migrează spre termen.",
             "labels": et, "unit": "mld. EUR", "dec": 1, "ydec": 0, "stacked": True,
             "series": [
                 {"name": "La vedere (cont curent / economii)", "data": clean(ved[pop] / 1000)},
                 {"name": "La termen sub 1 an", "data": clean(t_f[pop] / 1000)},
                 {"name": "La termen 1–2 ani", "data": clean(t_g[pop] / 1000)},
                 {"name": "La termen peste 2 ani", "data": clean(t_h[pop] / 1000)},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "Cât la sută din banii populației stă în cont curent",
             "subtitlu": "Ponderea depozitelor la vedere în total. O pondere în creștere arată "
                         "preferință pentru lichiditate — banii rămân la îndemână, nu blocați.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0,
             "series": [
                 {"name": "Populație", "data": clean(100 * ved[pop] / tot[pop])},
                 {"name": "Firme nefinanciare", "data": clean(100 * ved[fir] / tot[fir])},
             ]},
            {"id": "c4", "type": "bar",
             "titlu": "Bani depuși net de populație, cumulat pe 12 luni",
             "subtitlu": "Depuneri minus retrageri, curățate de efectul cursului valutar și de "
                         "reevaluări. Peste zero înseamnă că populația economisește net.",
             "labels": [ro_luna(p) for p in fl_tot[pop].rolling(12).sum().dropna().index],
             "unit": "mil. EUR", "dec": 0, "ydec": 0,
             "series": [{"name": "Flux net cumulat 12 luni",
                         "data": clean(fl_tot[pop].rolling(12).sum().dropna())}]},
            {"id": "c5", "type": "line",
             "titlu": "Ritmul anual de creștere a depozitelor",
             "subtitlu": "Variație față de aceeași lună a anului precedent, calculată de BCE pe "
                         "baza tranzacțiilor — fără influența cursului leu/euro.",
             "labels": [ro_luna(p) for p in gr_tot.dropna(how="all").index],
             "unit": "%", "dec": 1, "ydec": 0,
             "series": [{"name": SECTOARE[s], "data": clean(gr_tot.dropna(how="all")[s])}
                        for s in (pop, fir, tot_all) if s in gr_tot.columns]},
        ],
        "tabel": {
            "titlu": f"Depozitele populației — ultimele 36 de luni ({len(tot)} luni în fișierul Excel)",
            "columns": ["Luna", "Total (mil. EUR)", "La vedere", "Termen sub 1 an",
                        "Termen 1–2 ani", "Termen peste 2 ani", "Pondere la vedere (%)"],
            "rows": [[ro_luna(i), ro_num(tot[pop][i], 0), ro_num(ved[pop][i], 0),
                      ro_num(t_f[pop][i], 0), ro_num(t_g[pop][i], 0), ro_num(t_h[pop][i], 0),
                      ro_num(100 * ved[pop][i] / tot[pop][i], 1)]
                     for i in tot.index[-36:][::-1]],
        },
        "note": [
            "Sursa: Banca Centrală Europeană, setul <code>BSI</code> — bilanțul agregat al "
            "instituțiilor financiare monetare din România, raportat lunar de BNR către BCE.",
            "<strong>Ce măsoară.</strong> Soldul depozitelor este banul pe care populația și "
            "firmele îl țin la bănci: conturi curente, conturi de economii și depozite la "
            "termen. Este cea mai mare formă de economisire din România — de câteva ori mai "
            "mare decât toate fondurile de investiții și acțiunile la un loc.",
            "<strong>De ce contează raportul vedere / termen.</strong> Când dobânzile la "
            "depozite sunt mici sau când inflația e mare și oamenii nu vor să-și blocheze "
            "banii, ponderea contului curent crește. Când dobânzile urcă, banii se mută la "
            "termen. Este un barometru simplu al încrederii și al costului de oportunitate "
            "al economisirii.",
            "<strong>Atenție la efectul de curs.</strong> BCE publică sumele în euro, deși "
            "majoritatea depozitelor sunt în lei. O depreciere a leului reduce automat soldul "
            "exprimat în euro, fără ca cineva să fi retras bani. De aceea graficul cu fluxuri "
            "nete și cel cu ritmul anual folosesc seriile de tranzacții, curățate de acest efect.",
            "Defalcarea pe monedă (lei față de valută) nu este publicată de BCE pentru "
            "România — dimensiunea de monedă are o singură valoare, „toate monedele”.",
            "Depozitele sunt garantate de Fondul de Garantare a Depozitelor Bancare în limita "
            "a 100.000 EUR per deponent și per bancă.",
            "Regenerare: <code>python3 scripts/financiara_04_02.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(df)} obs., {len(tot)} luni, {per_min} → {per_max}, "
          f"depozite populație = {pop_now:,.0f} mil. EUR")


if __name__ == "__main__":
    main()
