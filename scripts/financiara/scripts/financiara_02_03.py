#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 02 03 — Creditele și depozitele din bilanțul băncilor din România
Sursa: BCE (ECB Data Portal), setul BSI — Balance Sheet Items,
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

COD = "Financiara 02 03"
SECTIUNE = "02 Bănci"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
API = "https://data-api.ecb.europa.eu/service/data/BSI"
PAGINA = "https://data.ecb.europa.eu/data/datasets/BSI"
START = "2007-01"

# Cheie SDMX BSI = 12 dimensiuni / 11 puncte:
# FREQ.REF_AREA.ADJUSTMENT.BS_REP_SECTOR.BS_ITEM.MATURITY_ORIG.DATA_TYPE.
# COUNT_AREA.BS_COUNT_SECTOR.CURRENCY_TRANS.BS_SUFFIX
SOLDURI = {
    "M.RO.N.A.A20.A.1.U6.2250.Z01.E": "Credite acordate populației",
    "M.RO.N.A.A20.A.1.U6.2240.Z01.E": "Credite acordate firmelor nefinanciare",
    "M.RO.N.A.A20.A.1.U6.2100.Z01.E": "Credite acordate administrației publice",
    "M.RO.N.A.A20.A.1.U6.2250.Z41.E": "Credite în valută — populație",
    "M.RO.N.A.A20.A.1.U6.2240.Z41.E": "Credite în valută — firme",
    "M.RO.N.A.A22.A.1.U6.2250.Z01.E": "Credite pentru locuințe",
    "M.RO.N.A.A21.A.1.U6.2250.Z01.E": "Credite de consum",
    "M.RO.N.A.A23.A.1.U6.2250.Z01.E": "Alte credite acordate populației",
    "M.RO.N.A.A20.F.1.U6.2240.Z01.E": "Credite firme — scadență până la 1 an",
    "M.RO.N.A.A20.I.1.U6.2240.Z01.E": "Credite firme — scadență 1–5 ani",
    "M.RO.N.A.A20.J.1.U6.2240.Z01.E": "Credite firme — scadență peste 5 ani",
    "M.RO.N.A.L20.A.1.U6.2250.Z01.E": "Depozite ale populației",
    "M.RO.N.A.L20.A.1.U6.2240.Z01.E": "Depozite ale firmelor nefinanciare",
    "M.RO.N.A.L21.A.1.U6.2250.Z01.E": "Depozite la vedere — populație",
    "M.RO.N.A.L21.A.1.U6.2240.Z01.E": "Depozite la vedere — firme",
    "M.RO.N.A.L22.F.1.U6.2250.Z01.E": "Depozite la termen până la 1 an — populație",
    "M.RO.N.A.L22.G.1.U6.2250.Z01.E": "Depozite la termen 1–2 ani — populație",
    "M.RO.N.A.L22.H.1.U6.2250.Z01.E": "Depozite la termen peste 2 ani — populație",
    "M.RO.N.A.L22.F.1.U6.2240.Z01.E": "Depozite la termen până la 1 an — firme",
    "M.RO.N.A.A30.A.1.U6.2100.Z01.E": "Titluri de stat românești deținute de bănci",
    "M.RO.N.A.T00.A.1.Z5.0000.Z01.E": "Total activ bilanțier al sistemului bancar",
}
RITMURI = {
    "M.RO.N.A.A20.A.I.U6.2250.Z01.A": "Ritm anual de creștere — credite populație",
    "M.RO.N.A.A20.A.I.U6.2240.Z01.A": "Ritm anual de creștere — credite firme",
    "M.RO.N.A.A20.A.I.U6.2200.Z01.A": "Ritm anual de creștere — credite sector privat",
}
PONDERI = {
    "M.RO.N.A.A20.A.1.U6.2200.Z41.P10": "Ponderea creditelor în valută (sector privat)",
}
SERII = {**SOLDURI, **RITMURI, **PONDERI}

CERERI = [
    "M.RO.N.A.A20+A21+A22+A23.A+F+I+J.1.U6.2100+2240+2250.Z01+Z41.E",
    "M.RO.N.A.L20+L21+L22.A+F+G+H.1.U6.2240+2250.Z01.E",
    "M.RO.N.A.A30.A.1.U6.2100.Z01.E",
    "M.RO.N.A.T00.A.1.Z5.0000.Z01.E",
    "M.RO.N.A.A20.A.I.U6.2200+2240+2250.Z01.A",
    "M.RO.N.A.A20.A.1.U6.2200.Z41.P10",
]

ETICHETE = {
    "BS_ITEM": {
        "A20": "Credite (total)", "A21": "Credite de consum",
        "A22": "Credite pentru achiziția de locuințe", "A23": "Alte credite",
        "A30": "Titluri de datorie deținute",
        "L20": "Depozite atrase (total)", "L21": "Depozite overnight (la vedere)",
        "L22": "Depozite cu maturitate convenită (la termen)",
        "T00": "Total activ / pasiv bilanțier",
    },
    "MATURITY_ORIG": {
        "A": "Total maturități", "F": "Până la 1 an",
        "G": "Peste 1 și până la 2 ani", "H": "Peste 2 ani",
        "I": "Peste 1 și până la 5 ani", "J": "Peste 5 ani",
    },
    "DATA_TYPE": {
        "1": "Solduri la sfârșitul perioadei (stocuri)",
        "I": "Indice al stocurilor noționale (bază pentru ritmul de creștere)",
    },
    "COUNT_AREA": {"U6": "Intern (România)", "Z5": "Nealocat geografic"},
    "BS_COUNT_SECTOR": {
        "0000": "Toate sectoarele (total bilanț)",
        "2100": "Administrația publică",
        "2200": "Sectorul privat (non-IFM, exclusiv administrația publică)",
        "2240": "Societăți nefinanciare (firme, S.11)",
        "2250": "Gospodăriile populației și IFSLSGP (S.14 și S.15)",
    },
    "CURRENCY_TRANS": {"Z01": "Toate monedele", "Z41": "Toate monedele, mai puțin leul"},
    "BS_SUFFIX": {"E": "Valori exprimate în euro", "A": "Ritm anual de creștere (%)",
                  "P10": "Pondere în total (%)"},
    "ADJUSTMENT": {"N": "Neajustat sezonier și cu numărul de zile lucrătoare"},
    "BS_REP_SECTOR": {"A": "Instituții financiare monetare, exclusiv SEBC"},
}


def descarca_ecb(cereri, serii) -> pd.DataFrame:
    bucati = []
    for c in cereri:
        url = f"{API}/{c}?format=csvdata&startPeriod={START}&detail=dataonly"
        txt = fetch(url).content.decode("utf-8")
        if txt.lstrip().startswith("<"):
            raise SystemExit(f"EȘEC: ECB a întors HTML (cheie invalidă?) pentru {c}")
        bucati.append(pd.read_csv(io.StringIO(txt), low_memory=False, dtype=str))
    d = pd.concat(bucati, ignore_index=True)
    d["OBS_VALUE"] = pd.to_numeric(d.OBS_VALUE, errors="coerce")
    d = d[d.OBS_VALUE.notna()].copy()
    d["cheie"] = d.KEY.str.replace("^BSI\\.", "", regex=True)
    d = d[d.cheie.isin(serii)].drop_duplicates(["cheie", "TIME_PERIOD"]).copy()
    lipsa = sorted(set(serii) - set(d.cheie.unique()))
    if lipsa:
        raise SystemExit("EȘEC: seriile următoare nu au întors nicio observație: "
                         + ", ".join(lipsa))
    d = d.rename(columns={"TIME_PERIOD": "luna", "OBS_VALUE": "valoare"})
    d["indicator"] = d.cheie.map(serii)
    return d[["luna", "cheie", "indicator", "valoare", "BS_ITEM", "MATURITY_ORIG",
              "DATA_TYPE", "COUNT_AREA", "BS_COUNT_SECTOR", "CURRENCY_TRANS",
              "BS_SUFFIX"]].sort_values(["luna", "cheie"]).reset_index(drop=True)


def main() -> None:
    d = descarca_ecb(CERERI, SERII)
    fail_if_short(d, 4500, "ECB BSI — bilanțul băncilor din România")

    w = d.pivot_table(index="luna", columns="indicator", values="valoare",
                      aggfunc="first").sort_index()
    ultima = w.dropna(how="all").index.max()
    fail_if_stale(ultima, 4, "ECB BSI România")
    prima = w.index.min()
    azi = dt.date.today().isoformat()

    CP, CF = "Credite acordate populației", "Credite acordate firmelor nefinanciare"
    DP, DF = "Depozite ale populației", "Depozite ale firmelor nefinanciare"

    # Solduri în miliarde EUR (sursa le publică în milioane EUR).
    mld = (w[list(SOLDURI.values())] / 1000.0).round(3)

    # --- foi de analiză ----------------------------------------------------
    a_sold = mld.reset_index().rename(columns={"luna": "Luna"})

    credite_tot = w[CP] + w[CF]
    depozite_tot = w[DP] + w[DF]
    a_raport = pd.DataFrame({
        "Luna": w.index,
        "Credite populație + firme (mld. EUR)": (credite_tot / 1000).round(3).values,
        "Depozite populație + firme (mld. EUR)": (depozite_tot / 1000).round(3).values,
        "Raport credite / depozite (%)": (100 * credite_tot / depozite_tot).round(1).values,
        "Raport credite / depozite — populație (%)": (100 * w[CP] / w[DP]).round(1).values,
        "Raport credite / depozite — firme (%)": (100 * w[CF] / w[DF]).round(1).values,
        "Excedent depozite peste credite (mld. EUR)":
            ((depozite_tot - credite_tot) / 1000).round(3).values,
    })

    a_ritm = pd.DataFrame({"Luna": w.index})
    for nume in RITMURI.values():
        a_ritm[f"{nume} (%)"] = w[nume].round(1).values
    a_ritm["Ponderea creditelor în valută (%)"] = \
        w["Ponderea creditelor în valută (sector privat)"].round(1).values
    a_ritm["Pondere credite în valută — populație (%)"] = \
        (100 * w["Credite în valută — populație"] / w[CP]).round(1).values
    a_ritm["Pondere credite în valută — firme (%)"] = \
        (100 * w["Credite în valută — firme"] / w[CF]).round(1).values

    struct_pop = w[["Credite pentru locuințe", "Credite de consum",
                    "Alte credite acordate populației"]]
    a_struct = pd.DataFrame({"Luna": w.index})
    for c in struct_pop.columns:
        a_struct[f"{c} (mld. EUR)"] = (struct_pop[c] / 1000).round(3).values
    tot_pop = struct_pop.sum(axis=1, min_count=1)
    for c in struct_pop.columns:
        a_struct[f"{c} (% din creditele populației)"] = \
            (100 * struct_pop[c] / tot_pop).round(1).values

    dep_pop = w[["Depozite la vedere — populație",
                 "Depozite la termen până la 1 an — populație",
                 "Depozite la termen 1–2 ani — populație",
                 "Depozite la termen peste 2 ani — populație"]]
    tot_dep = dep_pop.sum(axis=1, min_count=1)
    a_dep = pd.DataFrame({"Luna": w.index})
    for c in dep_pop.columns:
        a_dep[f"{c} (mld. EUR)"] = (dep_pop[c] / 1000).round(3).values
    a_dep["Pondere depozite la vedere (%)"] = \
        (100 * dep_pop["Depozite la vedere — populație"] / tot_dep).round(1).values

    a_bilant = pd.DataFrame({
        "Luna": w.index,
        "Total activ (mld. EUR)": (w["Total activ bilanțier al sistemului bancar"] / 1000).round(3).values,
        "Credite sector privat (mld. EUR)": (credite_tot / 1000).round(3).values,
        "Titluri de stat deținute (mld. EUR)":
            (w["Titluri de stat românești deținute de bănci"] / 1000).round(3).values,
        "Credite private în total activ (%)":
            (100 * credite_tot / w["Total activ bilanțier al sistemului bancar"]).round(1).values,
        "Titluri de stat în total activ (%)":
            (100 * w["Titluri de stat românești deținute de bănci"]
             / w["Total activ bilanțier al sistemului bancar"]).round(1).values,
    })

    an_idx = w.index.str[:4]
    a_anual = pd.DataFrame({
        "An": sorted(set(an_idx)),
        "Credite populație, medie (mld. EUR)": (w[CP].groupby(an_idx).mean() / 1000).round(3).values,
        "Credite firme, medie (mld. EUR)": (w[CF].groupby(an_idx).mean() / 1000).round(3).values,
        "Depozite populație, medie (mld. EUR)": (w[DP].groupby(an_idx).mean() / 1000).round(3).values,
        "Depozite firme, medie (mld. EUR)": (w[DF].groupby(an_idx).mean() / 1000).round(3).values,
        "Raport credite/depozite, medie (%)":
            (100 * credite_tot / depozite_tot).groupby(an_idx).mean().round(1).values,
        "Ritm credite sector privat, medie (%)":
            w["Ritm anual de creștere — credite sector privat"].groupby(an_idx).mean().round(1).values,
        "Luni raportate": w[CP].groupby(an_idx).count().values,
    })

    rep = []
    for col in list(SOLDURI.values()):
        s = (w[col] / 1000).dropna()
        if s.empty:
            continue
        rep.append({"Indicator": col, "Minim (mld. EUR)": round(s.min(), 3),
                    "Luna minimului": s.idxmin(), "Maxim (mld. EUR)": round(s.max(), 3),
                    "Luna maximului": s.idxmax(),
                    "Ultima valoare (mld. EUR)": round(s.iloc[-1], 3),
                    "Ultima lună": s.index[-1],
                    "Creștere față de acum 12 luni (%)":
                        round(100 * (s.iloc[-1] / s.iloc[-13] - 1), 1) if len(s) > 13 else None})
    a_rep = pd.DataFrame(rep)

    a_dict = pd.DataFrame(
        [{"Dimensiune": dim, "Cod": cod, "Denumire în română": nume}
         for dim, m in ETICHETE.items() for cod, nume in m.items()])

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Creditele și depozitele din bilanțul băncilor din România",
        "subtitlu": "Câți bani au împrumutat băncile populației și firmelor, câți bani au "
                    "primit ca depozite și cum s-a schimbat raportul dintre cele două.",
        "sursa": "Banca Centrală Europeană — ECB Data Portal, setul BSI "
                 "(Balance Sheet Items); date raportate de Banca Națională a României",
        "sursa_url": PAGINA,
        "cod_set": "BSI (ECB_BSI1). Chei SDMX folosite (12 dimensiuni, 11 puncte): "
                   + "; ".join(sorted(SERII)),
        "frecventa": "Lunară",
        "perioada": f"{prima} → {ultima}",
        "unitate": "solduri în milioane EUR în foaia `Date`, convertite în miliarde EUR în "
                   "foile de analiză; ritmurile și ponderile în procente",
        "descarcat": azi,
        "licenta": "BCE — reutilizare permisă cu menționarea sursei.",
        "metodologie": "Setul BSI conține bilanțul agregat al instituțiilor financiare monetare "
                       "(băncile comerciale și băncile de economisire-creditare, exclusiv banca "
                       "centrală). Soldurile sunt cele de la finalul lunii, neajustate sezonier. "
                       "BCE publică datele naționale convertite în euro la cursul de referință "
                       "de la finalul lunii, deci variațiile în euro conțin și efectul cursului "
                       "de schimb. Din acest motiv, ritmurile de creștere folosite aici sunt "
                       "ritmurile oficiale calculate de BCE pe baza indicelui stocurilor "
                       "noționale (DATA_TYPE = I, BS_SUFFIX = A), care elimină efectele de curs, "
                       "reclasificările și scoaterile de active din bilanț.",
        "script": "scripts/financiara_02_03.py",
        "note": [
            "Raportul credite/depozite arată cât din banii atrași de la clienți sunt dați mai "
            "departe sub formă de credite. Sub 100% înseamnă că băncile au mai multe depozite "
            "decât credite — situație tipică pentru România de după 2012.",
            "Creditele pentru locuințe includ atât creditele ipotecare standard, cât și cele "
            "din programul „Noua Casă” / „Prima Casă”.",
            "Ponderea creditelor în valută arată expunerea clienților la riscul de curs valutar.",
            "„Alte credite acordate populației” cuprinde în principal creditele acordate "
            "persoanelor fizice autorizate și întreprinderilor familiale.",
        ],
        "avertismente": [
            "Soldurile sunt exprimate în EURO, nu în lei — BCE convertește raportările BNR la "
            "cursul de referință de la finalul lunii. O scădere a soldului în euro poate "
            "însemna doar o depreciere a leului, nu o scădere reală a creditării.",
            "Pentru creșteri corecte folosiți coloanele de ritm anual publicate de BCE, nu "
            "diferențele calculate din soldurile în euro.",
            "În cheia SDMX, sectorul contrapartidei pentru totalul bilanțier se scrie `0000` "
            "(patru zerouri), nu `0`; cheia BSI are exact 11 puncte.",
            "COUNT_AREA = U6 înseamnă „intern” (contrapartide rezidente în România), nu "
            "„zona euro”; U2 este zona euro, iar Z5 este agregatul nealocat geografic.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=d.rename(columns={
            "luna": "Luna", "cheie": "Cheie SDMX", "indicator": "Indicator",
            "valoare": "Valoare", "BS_ITEM": "Cod poziție bilanțieră",
            "MATURITY_ORIG": "Cod maturitate", "DATA_TYPE": "Cod tip de dată",
            "COUNT_AREA": "Cod zonă contrapartidă",
            "BS_COUNT_SECTOR": "Cod sector contrapartidă", "CURRENCY_TRANS": "Cod monedă",
            "BS_SUFFIX": "Cod sufix"}),
        analize={
            "Solduri lunare": a_sold,
            "Credite vs depozite": a_raport,
            "Ritm si valuta": a_ritm,
            "Structura creditelor": a_struct,
            "Structura depozitelor": a_dep,
            "Bilantul bancar": a_bilant,
            "Medii anuale": a_anual,
            "Repere istorice": a_rep,
            "Dictionar coduri": a_dict,
        },
        note_analize={
            "Solduri lunare": "Soldurile de la finalul fiecărei luni, în miliarde EUR.",
            "Credite vs depozite": "Raportul credite/depozite și excedentul de depozite.",
            "Ritm si valuta": "Ritmurile oficiale de creștere publicate de BCE și ponderea "
                              "creditelor în valută.",
            "Structura creditelor": "Cum se împart creditele populației între locuințe, consum "
                                    "și alte destinații.",
            "Structura depozitelor": "Cât din economiile populației stau la vedere și cât la termen.",
            "Bilantul bancar": "Ce pondere au creditele private și titlurile de stat în activul "
                               "total al sistemului bancar.",
            "Medii anuale": "Media lunilor raportate din fiecare an calendaristic.",
            "Repere istorice": "Minime, maxime, ultima valoare și creșterea pe 12 luni.",
            "Dictionar coduri": "Traducerea codurilor de dimensiune SDMX, conform "
                                "codelist-urilor oficiale ECB.",
        },
        numfmt="#,##0.000")

    # --- pagina HTML -------------------------------------------------------
    et = [ro_luna(p) for p in w.index]
    cp = float(w[CP].iloc[-1] / 1000)
    cf = float(w[CF].iloc[-1] / 1000)
    ld = float(100 * credite_tot.iloc[-1] / depozite_tot.iloc[-1])
    ritm = float(w["Ritm anual de creștere — credite sector privat"].dropna().iloc[-1])
    fx = float(w["Ponderea creditelor în valută (sector privat)"].dropna().iloc[-1])

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "BCE — ECB Data Portal, setul BSI (raportări BNR)",
        "sursa_url": PAGINA, "frecventa": "Lunar",
        "perioada": f"{ro_luna(prima)} – {ro_luna(ultima)}", "actualizat": azi,
        "badge_extra": "Valori în euro",
        "kpis": [
            {"eticheta": f"Credite acordate populației, {ro_luna(ultima)}",
             "valoare": f"{ro_num(cp, 1)} mld. EUR", "nota": "sold la finalul lunii"},
            {"eticheta": "Credite acordate firmelor",
             "valoare": f"{ro_num(cf, 1)} mld. EUR", "nota": "societăți nefinanciare"},
            {"eticheta": "Raport credite / depozite",
             "valoare": f"{ro_num(ld, 1)}%",
             "nota": "sub 100% = băncile au mai multe depozite decât credite"},
            {"eticheta": "Ritm anual al creditării private",
             "valoare": f"{'+' if ritm >= 0 else ''}{ro_num(ritm, 1)}%",
             "nota": f"credite în valută: {ro_num(fx, 1)}% din total",
             "trend": "up" if ritm > 0 else "down"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Cât au împrumutat băncile și câți bani au primit",
             "subtitlu": "Solduri la finalul lunii, în miliarde de euro.",
             "labels": et, "unit": "mld. EUR", "dec": 1, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Depozite populație", "data": clean(w[DP] / 1000)},
                 {"name": "Credite populație", "data": clean(w[CP] / 1000)},
                 {"name": "Depozite firme", "data": clean(w[DF] / 1000)},
                 {"name": "Credite firme", "data": clean(w[CF] / 1000)},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Raportul credite / depozite",
             "subtitlu": "Cât din banii atrași de la clienți se întorc în economie sub formă "
                         "de credite. Peste 100% înseamnă că băncile se finanțează și din alte "
                         "surse decât depozitele.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0,
             "series": [
                 {"name": "Total (populație + firme)",
                  "data": clean(100 * credite_tot / depozite_tot)},
                 {"name": "Populație", "data": clean(100 * w[CP] / w[DP])},
                 {"name": "Firme", "data": clean(100 * w[CF] / w[DF])},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "Ritmul anual de creștere a creditării",
             "subtitlu": "Ritmurile oficiale calculate de BCE, curățate de efectele cursului "
                         "de schimb și ale reclasificărilor.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0,
             "series": [{"name": n, "data": clean(w[n])} for n in RITMURI.values()]},
            {"id": "c4", "type": "line",
             "titlu": "Creditele populației, pe destinații",
             "subtitlu": "Soldurile creditelor pentru locuințe, de consum și alte credite.",
             "labels": et, "unit": "mld. EUR", "dec": 1, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Locuințe", "data": clean(w["Credite pentru locuințe"] / 1000)},
                 {"name": "Consum", "data": clean(w["Credite de consum"] / 1000)},
                 {"name": "Alte credite",
                  "data": clean(w["Alte credite acordate populației"] / 1000)},
             ]},
            {"id": "c5", "type": "line",
             "titlu": "Cât din credite sunt în valută",
             "subtitlu": "Ponderea creditelor acordate în altă monedă decât leul. O pondere "
                         "mare înseamnă că o depreciere a leului scumpește ratele.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Sector privat (total)",
                  "data": clean(w["Ponderea creditelor în valută (sector privat)"])},
                 {"name": "Populație", "data": clean(100 * w["Credite în valută — populație"] / w[CP])},
                 {"name": "Firme", "data": clean(100 * w["Credite în valută — firme"] / w[CF])},
             ]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(w)} luni în fișierul Excel)",
            "columns": ["Luna", "Credite populație (mld. EUR)", "Credite firme (mld. EUR)",
                        "Depozite populație (mld. EUR)", "Depozite firme (mld. EUR)",
                        "Credite / depozite (%)", "Ritm credite private (%)",
                        "Credite în valută (%)"],
            "rows": [[ro_luna(i), ro_num(r[CP] / 1000, 1), ro_num(r[CF] / 1000, 1),
                      ro_num(r[DP] / 1000, 1), ro_num(r[DF] / 1000, 1),
                      ro_num(100 * (r[CP] + r[CF]) / (r[DP] + r[DF]), 1),
                      ro_num(r["Ritm anual de creștere — credite sector privat"], 1),
                      ro_num(r["Ponderea creditelor în valută (sector privat)"], 1)]
                     for i, r in w.tail(36).iloc[::-1].iterrows()],
        },
        "note": [
            "Sursa: Banca Centrală Europeană, ECB Data Portal, setul <code>BSI</code> "
            "(Balance Sheet Items). Datele pentru România sunt raportate lunar de Banca "
            "Națională a României.",
            "<strong>Atenție la monedă.</strong> BCE publică bilanțul băncilor românești "
            "convertit în euro, la cursul de referință de la finalul fiecărei luni. O scădere "
            "a soldului exprimat în euro poate veni doar din deprecierea leului. Pentru "
            "creșteri reale folosiți graficul cu ritmurile oficiale, care elimină acest efect.",
            "<strong>Ce este raportul credite/depozite.</strong> Arată câți lei împrumută "
            "băncile pentru fiecare leu primit ca depozit. În 2008 depășea 130% — băncile se "
            "finanțau masiv de la băncile-mamă din străinătate. De la mijlocul anilor 2010 "
            "stă sub 100%, semn că sistemul bancar românesc se finanțează din economiile "
            "locale.",
            "<strong>Creditele în valută</strong> au fost o problemă majoră după 2008, când "
            "deprecierea leului și a francului elvețian a scumpit brusc ratele. Ponderea lor "
            "a scăzut constant de atunci.",
            "Soldurile sunt cele de la finalul lunii și nu sunt ajustate sezonier.",
            "Regenerare: <code>python3 scripts/financiara_02_03.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(d)} obs., {len(SERII)} serii, {len(w)} luni, {prima} → {ultima}; "
          f"credite populație = {cp:.1f} mld. EUR, credite/depozite = {ld:.1f}%")


if __name__ == "__main__":
    main()
