#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 04 04 — Unde își plasează românii economiile: activele financiare ale gospodăriilor
Sursa: Eurostat, set `nasq_10_f_bs` (conturi financiare trimestriale, bilanțuri)
Frecvență: TRIMESTRIALĂ (nu există echivalent lunar pentru acest indicator).
"""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fetch, ro_luna, ro_num)

COD = "Financiara 04 04"
SECTIUNE = "04 Investiții financiare"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
DATASET = "nasq_10_f_bs"
BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
PAGINA = "https://ec.europa.eu/eurostat/databrowser/view/nasq_10_f_bs/default/table"
SECTOR = "S14_S15"   # gospodării + instituții fără scop lucrativ în serviciul gospodăriilor
START = "2000-Q1"

ACTIVE = {
    "F": "Total active financiare",
    "F2": "Numerar și depozite",
    "F21": "Numerar (bani cash)",
    "F22": "Depozite la vedere (conturi curente)",
    "F29": "Alte depozite (la termen, economii)",
    "F3": "Titluri de datorie (obligațiuni)",
    "F4": "Credite acordate de gospodării",
    "F51": "Acțiuni și participații",
    "F511": "Acțiuni listate la bursă",
    "F512_F519": "Acțiuni nelistate și alte participații",
    "F52": "Unități de fond de investiții",
    "F61_F66": "Rezerve tehnice de asigurări generale",
    "F62": "Asigurări de viață",
    "F63": "Drepturi de pensie (Pilon II și III)",
    "F64_F65": "Alte drepturi legate de pensii",
    "F7": "Instrumente financiare derivate",
    "F81": "Credite comerciale de încasat",
    "F89": "Alte creanțe",
}
# Componentele elementare care ÎNSUMATE dau exact totalul F (fără subtotaluri suprapuse:
# F5 = F51+F52, F6 = F61_F66+F62+F63+F64_F65, F8 = F81+F89). F1 (aur monetar și DST)
# nu este raportat pentru gospodăriile din România.
COMPONENTE = ["F2", "F3", "F4", "F51", "F52", "F61_F66", "F62", "F63", "F64_F65",
              "F7", "F81", "F89"]
# subsetul afișat în graficul de compoziție (restul este agregat în „Alte active")
GRAFIC = ["F2", "F51", "F63", "F89", "F52", "F3", "F62"]

PASIVE = {"F": "Total pasive financiare", "F4": "Credite (total)",
          "F41": "Credite pe termen scurt", "F42": "Credite pe termen lung"}

TARI = {"RO": "România", "BG": "Bulgaria", "CZ": "Cehia", "HU": "Ungaria",
        "PL": "Polonia", "EA20": "Zona euro"}
BENCH_ITEME = ["F", "F2", "F3", "F51", "F52", "F62", "F63"]


def _jsonstat(js: dict) -> pd.DataFrame:
    dims, sizes = js["id"], js["size"]
    inv = {d: {v: k for k, v in js["dimension"][d]["category"]["index"].items()} for d in dims}
    pasi = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        pasi[i] = pasi[i + 1] * sizes[i + 1]
    randuri = []
    for k, val in js["value"].items():
        if val is None:
            continue
        n = int(k)
        rec = {d: inv[d][(n // pasi[i]) % sizes[i]] for i, d in enumerate(dims)}
        rec["valoare"] = float(val)
        randuri.append(rec)
    return pd.DataFrame(randuri)


def _cerere(**kw) -> str:
    parti = []
    for k, v in kw.items():
        if isinstance(v, (list, tuple)):
            parti += [f"{k}={x}" for x in v]
        else:
            parti.append(f"{k}={v}")
    return f"{BASE}/{DATASET}?format=JSON&lang=EN&" + "&".join(parti) + f"&sinceTimePeriod={START}"


def descarca() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    a_ron = _jsonstat(fetch(_cerere(geo="RO", sector=SECTOR, finpos="ASS", unit="MIO_NAC",
                                    na_item=list(ACTIVE)), expect="json").json())
    fail_if_short(a_ron, 800, "Eurostat nasq_10_f_bs — active RO (lei)")

    a_eur = _jsonstat(fetch(_cerere(geo="RO", sector=SECTOR, finpos="ASS", unit="MIO_EUR",
                                    na_item=list(ACTIVE)), expect="json").json())
    fail_if_short(a_eur, 800, "Eurostat nasq_10_f_bs — active RO (euro)")

    p_ron = _jsonstat(fetch(_cerere(geo="RO", sector=SECTOR, finpos="LIAB", unit="MIO_NAC",
                                    na_item=list(PASIVE)), expect="json").json())
    fail_if_short(p_ron, 250, "Eurostat nasq_10_f_bs — pasive RO")

    bench = _jsonstat(fetch(_cerere(geo=list(TARI), sector=SECTOR, finpos="ASS", unit="MIO_EUR",
                                    na_item=BENCH_ITEME), expect="json").json())
    fail_if_short(bench, 2000, "Eurostat nasq_10_f_bs — benchmark regional")
    return a_ron, a_eur, p_ron, bench


def main() -> None:
    a_ron, a_eur, p_ron, bench = descarca()
    azi = dt.date.today().isoformat()

    A = a_ron.pivot(index="time", columns="na_item", values="valoare").sort_index()
    E = a_eur.pivot(index="time", columns="na_item", values="valoare").sort_index()
    P = p_ron.pivot(index="time", columns="na_item", values="valoare").sort_index()

    per_min, per_max = A.index.min(), A.index.max()
    if "F" not in A.columns or A["F"].notna().sum() < 60:
        raise SystemExit("EȘEC: seria de total active financiare lipsește sau e prea scurtă.")
    # verificare de prospețime adaptată frecvenței trimestriale (toleranță 3 trimestre)
    y, q = int(per_max[:4]), int(per_max[-1])
    azi_d = dt.date.today()
    vechime_t = (azi_d.year - y) * 4 + ((azi_d.month - 1) // 3 + 1 - q)
    if vechime_t > 4:
        raise SystemExit(f"EȘEC: nasq_10_f_bs se oprește la {per_max}, adică {vechime_t} "
                         "trimestre în urmă. Sursa pare înghețată.")

    # Verificare de integritate: componentele elementare trebuie să reconstituie totalul.
    comp_disp = [c for c in COMPONENTE if c in A.columns]
    suma_pc = (100 * A[comp_disp].sum(axis=1, min_count=1) / A["F"]).dropna()
    if not suma_pc.empty and (suma_pc.tail(40) < 99.0).any():
        raise SystemExit(
            f"EȘEC: componentele însumează doar {suma_pc.tail(40).min():.1f}% din total în "
            "ultimele trimestre — lipsește o poziție din lista na_item. Nu public o structură "
            "incompletă prezentată ca fiind totalul.")

    pond = pd.DataFrame({"Trimestru": A.index})
    for c in COMPONENTE:
        if c in A.columns:
            pond[f"{ACTIVE[c]} (%)"] = (100 * A[c] / A["F"]).round(2).values
    pond["Verificare — suma componentelor (%)"] = (
        100 * A[comp_disp].sum(axis=1, min_count=1) / A["F"]).round(2).values

    a_sume = A.rename(columns=ACTIVE).round(0).reset_index().rename(columns={"time": "Trimestru"})
    ord_a = ["Trimestru"] + [ACTIVE[k] for k in ACTIVE if ACTIVE[k] in a_sume.columns]
    a_sume = a_sume[ord_a]

    a_eur_s = E.rename(columns=ACTIVE).round(0).reset_index().rename(columns={"time": "Trimestru"})
    a_eur_s = a_eur_s[[c for c in ord_a if c in a_eur_s.columns]]

    a_din = pd.DataFrame({"Trimestru": A.index})
    for c in ["F"] + COMPONENTE:
        if c in A.columns:
            a_din[f"{ACTIVE[c]} — variație 4 trimestre (%)"] = (
                100 * (A[c] / A[c].shift(4) - 1)).round(1).values
    a_din = a_din.dropna(how="all", subset=[c for c in a_din.columns if c != "Trimestru"])

    a_net = pd.DataFrame({
        "Trimestru": A.index,
        "Active financiare (mil. lei)": A["F"].round(0).values,
        "Pasive financiare (mil. lei)": P["F"].reindex(A.index).round(0).values,
        "Avere financiară netă (mil. lei)": (A["F"] - P["F"].reindex(A.index)).round(0).values,
        "Credite totale (mil. lei)": P["F4"].reindex(A.index).round(0).values if "F4" in P else None,
        "Active / pasive (raport)": (A["F"] / P["F"].reindex(A.index)).round(2).values,
    })

    bench["Țara"] = bench["geo"].map(TARI)
    B = {}
    for it in BENCH_ITEME:
        B[it] = bench[bench.na_item == it].pivot(index="time", columns="Țara",
                                                 values="valoare").sort_index()
    ordine_b = [TARI[k] for k in TARI if TARI[k] in B["F"].columns]
    ult_b = B["F"].dropna(how="all").index.max()
    a_bench = pd.DataFrame({"Țara": ordine_b})
    for it in ["F2", "F3", "F51", "F52", "F62", "F63"]:
        a_bench[f"{ACTIVE[it]} (% din total)"] = [
            (100 * B[it][t].get(ult_b) / B["F"][t].get(ult_b))
            if t in B[it].columns and pd.notna(B[it][t].get(ult_b)) else None for t in ordine_b]
    a_bench = a_bench.round(1)
    a_bench.insert(1, f"Total active {ult_b} (mil. EUR)",
                   [round(B["F"][t].get(ult_b)) if pd.notna(B["F"][t].get(ult_b)) else None
                    for t in ordine_b])

    an = A.copy()
    an["An"] = an.index.str[:4]
    dec = an.groupby("An").last()
    a_anual = pd.DataFrame({"An": dec.index})
    for c in ["F"] + COMPONENTE:
        if c in dec.columns:
            a_anual[f"{ACTIVE[c]} (mil. lei)"] = dec[c].round(0).values
    a_anual["Variație anuală total (%)"] = (100 * dec["F"].pct_change()).round(1).values

    ult = pd.DataFrame({
        "Componentă": [ACTIVE[c] for c in ACTIVE if c in A.columns],
        f"{per_max} (mil. lei)": [A[c].iloc[-1] for c in ACTIVE if c in A.columns],
        f"{per_max} (mil. EUR)": [E[c].iloc[-1] if c in E.columns else None
                                  for c in ACTIVE if c in A.columns],
        "Pondere în total (%)": [100 * A[c].iloc[-1] / A["F"].iloc[-1] for c in ACTIVE if c in A.columns],
        "Acum 4 trimestre (mil. lei)": [A[c].iloc[-5] if len(A) > 5 else None
                                        for c in ACTIVE if c in A.columns],
    }).round(1)
    ult["Variație 4 trimestre (%)"] = (
        100 * (ult.iloc[:, 1] / ult["Acum 4 trimestre (mil. lei)"] - 1)).round(1)

    brut = pd.concat([
        a_ron.assign(sursa="Active RO, mil. lei"), a_eur.assign(sursa="Active RO, mil. EUR"),
        p_ron.assign(sursa="Pasive RO, mil. lei"), bench.assign(sursa="Benchmark, mil. EUR"),
    ], ignore_index=True)
    # Eticheta depinde de finpos: codul „F" înseamnă „total active financiare" pe linia
    # de activ și „total pasive financiare" pe linia de pasiv. O singură hartă comună ar
    # suprascrie una dintre semnificații (PASIVE["F"] peste ACTIVE["F"]).
    brut["Etichetă"] = [
        (PASIVE if fp == "LIAB" else ACTIVE).get(it, ACTIVE.get(it, PASIVE.get(it)))
        for it, fp in zip(brut["na_item"], brut["finpos"])]
    date_df = brut[["time", "geo", "sector", "finpos", "na_item", "Etichetă", "unit",
                    "valoare", "sursa"]].copy()
    date_df.columns = ["Trimestru", "Țara", "Sector", "Poziție", "Cod na_item", "Componentă",
                       "Unitate", "Valoare", "Set"]
    date_df = date_df.sort_values(["Trimestru", "Țara", "Cod na_item"]).reset_index(drop=True)

    meta = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": "Unde își plasează românii economiile: activele financiare ale gospodăriilor",
        "subtitlu": "Structura averii financiare a populației — depozite, numerar, acțiuni, "
                    "unități de fond, asigurări de viață și drepturi de pensie. Date trimestriale.",
        "sursa": "Eurostat — conturi financiare trimestriale (date raportate de BNR și INS)",
        "sursa_url": PAGINA,
        "cod_set": (f"{DATASET}; filtre: sector={SECTOR} (gospodării + IFSLSG), "
                    "finpos=ASS și LIAB, unit=MIO_NAC și MIO_EUR, geo=RO "
                    "(benchmark: " + "|".join(TARI) + "), na_item=" + "|".join(ACTIVE)),
        "frecventa": "TRIMESTRIALĂ",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "milioane lei (MIO_NAC) și milioane EUR (MIO_EUR); ponderile în procente",
        "descarcat": azi,
        "licenta": "Eurostat — reutilizare liberă cu menționarea sursei (Decizia 2011/833/UE).",
        "metodologie": (
            "Conturile financiare trimestriale din Sistemul European de Conturi (SEC 2010). "
            "Sectorul S14_S15 cuprinde gospodăriile populației și instituțiile fără scop "
            "lucrativ aflate în serviciul lor. Valorile sunt SOLDURI la sfârșitul "
            "trimestrului, evaluate la prețul pieței, nu fluxuri. Activele financiare NU "
            "includ locuințele, terenurile sau alte bunuri — doar instrumente financiare. "
            "Drepturile de pensie (F63) acoperă pensiile private obligatorii (Pilon II) și "
            "facultative (Pilon III), nu pensia publică de stat, care nu este un activ "
            "financiar în sensul SEC 2010."),
        "script": "scripts/financiara_04_04.py",
        "note": [
            "Acțiunile nelistate și alte participații (F512_F519) sunt, în România, în cea mai "
            "mare parte părți sociale în firme mici deținute de persoane fizice — nu sunt "
            "plasamente lichide de bursă.",
            "Numerarul (F21) include atât lei, cât și valută ținută efectiv „la saltea”; este "
            "estimat statistic, nu măsurat direct.",
            "Depozitele din acest set nu coincid perfect cu cele din statistica BCE folosită "
            "în setul „Financiara 04 02”: aici sunt incluse și depozitele la instituții "
            "nebancare și la bănci din străinătate.",
            "Pentru avere financiară netă se scad pasivele (în principal creditele bancare) "
            "din activele financiare.",
        ],
        "avertismente": [
            "ACEST SET ESTE TRIMESTRIAL. Nu există o serie lunară echivalentă pentru structura "
            "activelor financiare ale gospodăriilor; conturile financiare se compilează "
            "trimestrial prin regulament european.",
            "Datele apar cu aproximativ un trimestru și jumătate decalaj și se revizuiesc "
            "retroactiv, uneori pe serii lungi.",
            "Suma componentelor poate să nu dea exact totalul din cauza rotunjirilor și a "
            "unor poziții mici neincluse în lista descărcată.",
            "Comparația internațională se face în euro; pentru România, deprecierea leului "
            "reduce cifrele exprimate în euro fără o scădere reală a averii în lei. De aceea "
            "seriile principale sunt în lei, iar euro este folosit doar la benchmark.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta, date_df=date_df,
        analize={
            "Active financiare (lei)": a_sume,
            "Active financiare (euro)": a_eur_s,
            "Structura portofoliului": pond,
            "Dinamica anuală": a_din,
            "Avere financiară netă": a_net,
            "Comparație regională": a_bench,
            "Solduri la final de an": a_anual,
            "Sinteza ultimului trimestru": ult,
        },
        note_analize={
            "Active financiare (lei)": "Soldul fiecărei componente la finalul trimestrului, în milioane de lei.",
            "Active financiare (euro)": "Aceleași solduri, convertite în euro de Eurostat.",
            "Structura portofoliului": "Ponderea fiecărei componente în totalul activelor financiare (%).",
            "Dinamica anuală": "Variația față de același trimestru al anului precedent (%).",
            "Avere financiară netă": "Active minus pasive financiare — cât rămâne populației după datorii.",
            "Comparație regională": "Structura portofoliului în ultimul trimestru comun, România față de regiune.",
            "Solduri la final de an": "Soldul din ultimul trimestru al fiecărui an.",
            "Sinteza ultimului trimestru": "Fotografia ultimului trimestru, cu ponderi și variație anuală.",
        },
        numfmt="#,##0")

    # --- pagina HTML ------------------------------------------------------
    et = [ro_luna(p) for p in A.index]
    tot_now = float(A["F"].iloc[-1])
    dep_p = float(100 * A["F2"].iloc[-1] / tot_now)
    fond_p = float(100 * A["F52"].iloc[-1] / tot_now) if "F52" in A.columns else None
    pens_p = float(100 * A["F63"].iloc[-1] / tot_now) if "F63" in A.columns else None
    net_now = float(A["F"].iloc[-1] - P["F"].reindex(A.index).iloc[-1])
    # rest = total minus componentele arătate explicit în grafic, ca stiva să dea exact 100%
    rest = A["F"] - A[[c for c in GRAFIC if c in A.columns]].sum(axis=1, min_count=1)

    spec = {
        "cod": COD, "sectiune": SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Eurostat — nasq_10_f_bs (conturi financiare trimestriale, SEC 2010)",
        "sursa_url": PAGINA,
        "frecventa": "Trimestrial",
        "badge_extra": "Date trimestriale",
        "perioada": f"{per_min} – {per_max}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Active financiare ale populației, {per_max}",
             "valoare": f"{ro_num(tot_now / 1000, 1)} mld. lei",
             "nota": "depozite, numerar, acțiuni, fonduri, asigurări și pensii private"},
            {"eticheta": "Ținuți în numerar și depozite",
             "valoare": f"{ro_num(dep_p, 1)}%",
             "nota": "cea mai mare componentă a averii financiare"},
            {"eticheta": "În unități de fond de investiții",
             "valoare": f"{ro_num(fond_p, 1)}%" if fond_p is not None else "–",
             "nota": "plasamentul colectiv rămâne marginal în România"},
            {"eticheta": "Avere financiară netă",
             "valoare": f"{ro_num(net_now / 1000, 1)} mld. lei",
             "nota": "active financiare minus credite și alte datorii"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Averea financiară a gospodăriilor din România",
             "subtitlu": "Soldul activelor financiare la finalul fiecărui trimestru, în "
                         "miliarde de lei. Nu include locuințe, terenuri sau alte bunuri.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0, "stacked": True,
             "series": [{"name": ACTIVE[c], "data": clean(A[c] / 1000)}
                        for c in GRAFIC if c in A.columns]
                       + [{"name": "Alte active financiare", "data": clean(rest / 1000)}]},
            {"id": "c2", "type": "line",
             "titlu": "Cât din economii stă în bancă și cât este investit",
             "subtitlu": "Ponderea fiecărei componente în totalul activelor financiare. "
                         "Numerarul și depozitele rămân cea mai mare felie, iar plasamentele "
                         "de piață propriu-zise abia depășesc câteva procente.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0,
             "series": [{"name": ACTIVE[c], "data": clean(100 * A[c] / A["F"])}
                        for c in ["F2", "F51", "F63", "F52", "F62", "F3"] if c in A.columns]},
            {"id": "c3", "type": "line",
             "titlu": "Plasamentele de piață: fonduri, acțiuni listate, obligațiuni",
             "subtitlu": "Componentele care presupun asumarea unui risc de piață, în miliarde "
                         "de lei. Sunt de zeci de ori mai mici decât depozitele.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0,
             "series": [{"name": ACTIVE[c], "data": clean(A[c] / 1000)}
                        for c in ["F52", "F511", "F3", "F62"] if c in A.columns]},
            {"id": "c4", "type": "line",
             "titlu": "Active, datorii și avere financiară netă",
             "subtitlu": "Populația are de câteva ori mai multe active financiare decât "
                         "datorii — diferența este averea financiară netă.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0,
             "series": [
                 {"name": "Active financiare", "data": clean(A["F"] / 1000)},
                 {"name": "Pasive (credite și alte datorii)",
                  "data": clean(P["F"].reindex(A.index) / 1000)},
                 {"name": "Avere financiară netă",
                  "data": clean((A["F"] - P["F"].reindex(A.index)) / 1000)},
             ]},
            {"id": "c5", "type": "bar",
             "titlu": f"România față de regiune — structura portofoliului, {ult_b}",
             "subtitlu": "Ponderea fiecărei componente în activele financiare ale gospodăriilor. "
                         "Cu cât bara albastră este mai mare, cu atât economisirea e mai bancară.",
             "labels": list(a_bench["Țara"]), "unit": "%", "dec": 1, "ydec": 0,
             "stacked": True, "zero": True, "xticks": 12,
             "series": [{"name": ACTIVE[it], "data": clean(a_bench[f"{ACTIVE[it]} (% din total)"])}
                        for it in ["F2", "F51", "F52", "F63", "F62", "F3"]
                        if f"{ACTIVE[it]} (% din total)" in a_bench.columns]},
        ],
        "tabel": {
            "titlu": f"Structura activelor financiare — ultimele 36 de trimestre "
                     f"({len(A)} trimestre în fișierul Excel)",
            "columns": ["Trimestru", "Total (mil. lei)"] +
                       [ACTIVE[c] for c in ["F2", "F51", "F52", "F63", "F62", "F3"] if c in A.columns],
            "rows": [[ro_luna(i), ro_num(A["F"][i], 0)] +
                     [ro_num(A[c][i], 0) for c in ["F2", "F51", "F52", "F63", "F62", "F3"]
                      if c in A.columns]
                     for i in A.index[-36:][::-1]],
        },
        "note": [
            "<strong>Atenție: acest set este trimestrial, nu lunar.</strong> Conturile "
            "financiare ale sectoarelor instituționale se compilează trimestrial prin "
            "regulament european; nu există o serie lunară echivalentă pentru structura "
            "activelor financiare ale populației.",
            "Sursa: Eurostat, setul <code>nasq_10_f_bs</code> — conturi financiare trimestriale "
            "conform SEC 2010, compilate pentru România de BNR împreună cu INS.",
            "<strong>Ce măsoară.</strong> Totalul banilor pe care populația îi are în "
            "instrumente financiare: cash, conturi și depozite, obligațiuni, acțiuni și părți "
            "sociale, unități de fond, polițe de asigurare de viață și drepturi acumulate în "
            "pensiile private. NU include casele, terenurile sau mașinile.",
            "<strong>De ce contează.</strong> Structura arată cât de dezvoltată e cultura "
            "investițională a unei țări. În România, cea mai mare parte a averii financiare "
            "stă în numerar și depozite, iar aproape tot restul în acțiuni nelistate — adică "
            "părți sociale în firme proprii, nu plasamente lichide. Instrumentele de piață "
            "accesibile publicului (acțiuni listate, obligațiuni, unități de fond) însumează "
            "sub o zecime din total, ceea ce înseamnă că economiile românilor finanțează "
            "foarte puțin economia prin piața de capital.",
            "Drepturile de pensie cuprind Pilonul II (obligatoriu) și Pilonul III "
            "(facultativ). Pensia publică de stat nu apare aici: ea nu este un activ "
            "financiar în sensul SEC 2010, ci o promisiune bugetară.",
            "Acțiunile nelistate și părțile sociale reprezintă, în România, mai ales "
            "participații în firme mici deținute de persoane fizice — nu plasamente lichide.",
            "Datele au un decalaj de aproximativ un trimestru și jumătate și se revizuiesc "
            "retroactiv.",
            "Regenerare: <code>python3 scripts/financiara_04_04.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(date_df)} obs., {len(A)} trimestre, {per_min} → {per_max}, "
          f"total active = {tot_now:,.0f} mil. lei")


if __name__ == "__main__":
    main()
