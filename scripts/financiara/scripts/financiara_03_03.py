#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 03 03 — Cât de solizi sunt asigurătorii din România (Solvency II)
Sursa: EIOPA — Insurance statistics, „Solo quarterly": SQ_Own_Funds.csv
       (fonduri proprii, SCR, MCR) și SQ_Balance_Sheet.csv (bilanț, formularul S.02.01).
Frecvență: TRIMESTRIALĂ.

CAPCANE CONFIRMATE LIVE (2026-09-17):
  * SQ_Balance_Sheet.csv NU este codat UTF-8 (conține octetul 0x96) — pandas
    aruncă UnicodeDecodeError; se citește cu encoding='latin-1'.
  * În SQ_Balance_Sheet.csv nu există linia „All undertaking types"; totalul de
    piață se obține prin însumarea tipurilor de societăți. Unele țări au și
    categoria „Undertaking type not published" (România NU are).
  * Rata de solvabilitate este publicată ca RAPORT (1,62), nu ca procent (162%).
  * Fișierele sunt servite de pe bucket-ul S3 nexteuropa-multisites...amazonaws.com.
"""
import datetime as dt
import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fetch, ro_luna, ro_num)

COD = "Financiara 03 03"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
S3 = ("https://nexteuropa-multisites.s3.eu-west-1.amazonaws.com/"
      "www.eiopa.europa.eu/assets/insurance-statistics")
URL_OF = f"{S3}/SQ_Own_Funds.csv"
URL_BS = f"{S3}/SQ_Balance_Sheet.csv"
PAGINA = "https://www.eiopa.europa.eu/tools-and-data/insurance-statistics_en"

TARI = {"ROMANIA": "România", "BULGARIA": "Bulgaria", "CZECHIA": "Cehia",
        "HUNGARY": "Ungaria", "POLAND": "Polonia", "EEA": "Spațiul Economic European"}
TOT = "All undertaking types"
TIPURI = {"Life undertakings": "Societăți de asigurări de viață",
          "Non-Life undertakings": "Societăți de asigurări generale",
          "Other undertakings": "Societăți compozite și altele"}

BS_ITEMS = {"R0500": "Total active",
            "R0070": "Plasamente (fără unit-linked)",
            "R0140": "din care titluri de stat",
            "R0220": "Active unit-linked și index-linked",
            "R0410": "Numerar și echivalente",
            "R0510": "Provizioane tehnice — asigurări generale",
            "R0600": "Provizioane tehnice — viață (fără unit-linked)",
            "R0690": "Provizioane tehnice — unit-linked și index-linked",
            "R0900": "Total datorii",
            "R1000": "Excedentul activelor față de datorii"}


def per_sort(p: str) -> tuple[int, int]:
    y, q = p.split(" Q")
    return int(y), int(q)


def per_iso(p: str) -> str:
    y, q = p.split(" Q")
    return f"{y}-Q{q}"


def descarca() -> tuple[pd.DataFrame, pd.DataFrame]:
    r = fetch(URL_OF, timeout=300)
    of = pd.read_csv(io.BytesIO(r.content), encoding="utf-8")
    # Fișierul de bilanț NU este UTF-8 (capcană confirmată).
    r = fetch(URL_BS, timeout=600)
    try:
        bs = pd.read_csv(io.BytesIO(r.content), encoding="utf-8")
    except UnicodeDecodeError:
        bs = pd.read_csv(io.BytesIO(r.content), encoding="latin-1")

    for df, nume, cols in ((of, "SQ_Own_Funds", {"Reporting country", "Reference period",
                                                 "Item code", "Value", "Undertaking type"}),
                           (bs, "SQ_Balance_Sheet", {"Reporting country", "Reference period",
                                                     "Item code", "Value",
                                                     "Undertaking type"})):
        lipsa = cols - set(df.columns)
        if lipsa:
            raise SystemExit(f"EȘEC: {nume} nu mai are coloanele {sorted(lipsa)}. "
                             "Structura sursei s-a schimbat — nu suprascriu datele bune.")

    of = of[of["Reporting country"].isin(TARI)].copy()
    bs = bs[bs["Reporting country"] == "ROMANIA"].copy()
    fail_if_short(of, 5000, "EIOPA SQ_Own_Funds")
    fail_if_short(bs, 3000, "EIOPA SQ_Balance_Sheet (România)")

    ro = of[(of["Reporting country"] == "ROMANIA") & of["Value"].notna()]
    if ro.empty:
        raise SystemExit("EȘEC: EIOPA nu a întors fonduri proprii pentru România.")
    ultim = max(ro["Reference period"], key=per_sort)
    y, q = per_sort(ultim)
    azi = dt.date.today()
    vechime = (azi.year - y) * 4 + ((azi.month - 1) // 3 + 1 - q)
    if vechime > 4:
        raise SystemExit(f"EȘEC: EIOPA se oprește la {ultim} ({vechime} trimestre în "
                         "urmă, toleranță 4). Sursa pare înghețată.")
    return of, bs


def main() -> None:
    of, bs = descarca()
    azi = dt.date.today().isoformat()

    ro_of = of[of["Reporting country"] == "ROMANIA"]
    perioade = sorted(set(ro_of["Reference period"]), key=per_sort)
    per_max, per_min = perioade[-1], perioade[0]
    et = [ro_luna(per_iso(p)) for p in perioade]

    def s_of(cod: str, tip: str = TOT, tara: str = "ROMANIA") -> pd.Series:
        d = of[(of["Reporting country"] == tara) & (of["Item code"] == cod)
               & (of["Undertaking type"] == tip)]
        s = d.set_index("Reference period")["Value"]
        return s[~s.index.duplicated()].reindex(perioade)

    def s_of_sum(cod: str, tara: str = "ROMANIA") -> pd.Series:
        """Sumele absolute NU sunt publicate pe linia 'All undertaking types' —
        se obțin însumând categoriile de societăți (inclusiv 'not published',
        folosită de unele țări în locul defalcării)."""
        d = of[(of["Reporting country"] == tara) & (of["Item code"] == cod)
               & (of["Undertaking type"] != TOT)]
        s = d.groupby("Reference period")["Value"].sum(min_count=1)
        return s.reindex(perioade)

    def s_bs(cod: str) -> pd.Series:
        d = bs[bs["Item code"] == cod]
        s = d.groupby("Reference period")["Value"].sum(min_count=1)
        return s.reindex(perioade)

    scr_ratio = s_of("R0620") * 100
    mcr_ratio = s_of("R0640") * 100
    of_scr = s_of_sum("R0540")     # fonduri proprii eligibile pentru SCR
    scr = s_of_sum("R0580")
    mcr = s_of_sum("R0600")

    # ================= FOI DE ANALIZĂ =====================================
    a1 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    a1["Rata de solvabilitate — total piață (%)"] = scr_ratio.round(1).values
    for et_p, pc in (("P10", "R0620_P10"), ("P25", "R0620_P25"), ("P50", "R0620_P50"),
                     ("P75", "R0620_P75"), ("P90", "R0620_P90")):
        a1[f"Percentila {et_p} (%)"] = (s_of(pc) * 100).round(1).values
    a1["Rata MCR — total piață (%)"] = mcr_ratio.round(1).values

    a2 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    a2["Fonduri proprii eligibile pentru SCR (mil. EUR)"] = of_scr.round(1).values
    a2["Cerința de capital de solvabilitate SCR (mil. EUR)"] = scr.round(1).values
    a2["Surplus de capital (mil. EUR)"] = (of_scr - scr).round(1).values
    a2["Cerința minimă de capital MCR (mil. EUR)"] = mcr.round(1).values
    a2["Rata de solvabilitate (%)"] = scr_ratio.round(1).values

    a3 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    for cod, nume in TIPURI.items():
        a3[f"{nume} — rata de solvabilitate (%)"] = (
            s_of("R0620", cod) * 100).round(1).values

    a4 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    tiers = {"R0540 - C0020": "Nivel 1 nerestricționat (mil. EUR)",
             "R0540 - C0030": "Nivel 1 restricționat (mil. EUR)",
             "R0540 - C0040": "Nivel 2 (mil. EUR)",
             "R0540 - C0050": "Nivel 3 (mil. EUR)"}
    for cod, nume in tiers.items():
        a4[nume] = s_of_sum(cod).round(1).values
    sum_t = a4[list(tiers.values())].sum(axis=1, min_count=1)
    a4["Pondere Nivel 1 nerestricționat (%)"] = (
        a4["Nivel 1 nerestricționat (mil. EUR)"] / sum_t * 100).round(1)

    a5 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    for cod, nume in BS_ITEMS.items():
        a5[f"{nume} (mil. EUR)"] = s_bs(cod).round(1).values
    a5["Ponderea titlurilor de stat în plasamente (%)"] = (
        s_bs("R0140") / s_bs("R0070") * 100).round(1).values

    reg_rows = []
    for t_cod, t_num in TARI.items():
        r = s_of("R0620", TOT, t_cod) * 100
        eo = s_of_sum("R0540", t_cod)
        c = s_of_sum("R0580", t_cod)
        reg_rows.append({
            "Țara": t_num,
            f"Rata de solvabilitate {per_iso(per_max)} (%)":
                round(float(r[per_max]), 1) if pd.notna(r.get(per_max)) else None,
            "Acum 4 trimestre (%)": (round(float(r.dropna().iloc[-5]), 1)
                                     if len(r.dropna()) > 5 else None),
            "Fonduri proprii eligibile (mil. EUR)":
                round(float(eo[per_max]), 0) if pd.notna(eo.get(per_max)) else None,
            "Cerința SCR (mil. EUR)":
                round(float(c[per_max]), 0) if pd.notna(c.get(per_max)) else None,
        })
    a6 = pd.DataFrame(reg_rows)
    col_r = f"Rata de solvabilitate {per_iso(per_max)} (%)"
    a6["Variație (p.p.)"] = (a6[col_r] - a6["Acum 4 trimestre (%)"]).round(1)

    ro_raw = (ro_of[["Reference period", "Undertaking type", "Item code", "Item name",
                     "Value", "Number of submissions (per reporting country, reference "
                     "date and undertaking type)"]]
              .rename(columns={
                  "Reference period": "Trimestru",
                  "Undertaking type": "Tip de societate",
                  "Item code": "Cod S.23.01",
                  "Item name": "Indicator (EIOPA)",
                  "Value": "Valoare (mil. EUR sau raport)",
                  "Number of submissions (per reporting country, reference date and "
                  "undertaking type)": "Număr de raportări"})
              .assign(Trimestru=lambda d: d["Trimestru"].map(per_iso))
              .sort_values(["Trimestru", "Tip de societate", "Cod S.23.01"])
              .reset_index(drop=True))

    nr = ro_of[(ro_of["Undertaking type"] == TOT)][
        "Number of submissions (per reporting country, reference date and "
        "undertaking type)"].dropna()
    nr_soc = int(nr.iloc[-1]) if len(nr) else None

    meta = {
        "cod": COD, "sectiune": "03 Asigurări",
        "titlu": "Cât de solizi sunt asigurătorii din România",
        "subtitlu": "Rata de solvabilitate, capitalul disponibil și bilanțul societăților "
                    "de asigurare din România, din raportările Solvency II centralizate "
                    "de EIOPA — cu reperul european alături.",
        "sursa": "EIOPA — Insurance statistics, raportare solo trimestrială "
                 "(Solvency II, formularele S.23.01 și S.02.01)",
        "sursa_url": PAGINA,
        "cod_set": "SQ_Own_Funds.csv (R0540, R0580, R0600, R0620, R0640 și percentilele "
                   "R0620_P10…P90) și SQ_Balance_Sheet.csv (R0070, R0140, R0220, R0410, "
                   "R0500, R0510, R0600, R0690, R0900, R1000)",
        "frecventa": "TRIMESTRIALĂ — nu există serie lunară publică",
        "perioada": f"{per_iso(per_min)} → {per_iso(per_max)}",
        "unitate": "milioane EUR; ratele în procente (%); percentilele în procente",
        "descarcat": azi,
        "licenta": "EIOPA — reutilizare permisă cu menționarea sursei.",
        "metodologie": "În regimul Solvency II fiecare asigurător trebuie să dețină "
                       "fonduri proprii cel puțin egale cu cerința de capital de "
                       "solvabilitate (SCR) — nivelul de capital calibrat astfel încât "
                       "societatea să reziste unui șoc care apare o dată la 200 de ani. "
                       "Rata de solvabilitate este raportul dintre fondurile proprii "
                       "eligibile și SCR: 100% înseamnă exact minimul legal, iar valorile "
                       "mari înseamnă rezerve suplimentare. Sub 100% autoritatea de "
                       "supraveghere (ASF) intervine; sub cerința minimă MCR se poate "
                       "retrage autorizația. Percentilele arată distribuția între "
                       "societăți: P10 este pragul sub care se află cele mai slab "
                       "capitalizate 10% dintre societăți.",
        "script": "scripts/financiara_03_03.py",
        "note": [
            f"Agregatul pentru România acoperă {nr_soc} societăți raportoare în ultimul "
            "trimestru disponibil." if nr_soc else
            "Numărul de societăți raportoare este publicat de EIOPA pe fiecare trimestru.",
            "Media de piață este ponderată (suma fondurilor proprii împărțită la suma "
            "cerințelor de capital), deci o societate mare o poate ridica peste nivelul "
            "tipic al societăților mici. De aceea sunt incluse și percentilele.",
            "Valorile de bilanț sunt însumate din categoriile de societăți: viață, "
            "generale și compozite/altele.",
            "Datele trimestriale sunt neauditate și pot fi revizuite ulterior.",
            "Spre deosebire de setul Financiara 03 02 (prime și daune, unde EIOPA "
            "publică valori cumulate de la începutul anului), toate valorile din "
            "acest set sunt solduri la sfârșitul trimestrului: bilanț, fonduri "
            "proprii, cerințe de capital și rate. Ele se compară direct de la un "
            "trimestru la altul, fără de-cumulare.",
            "Asigurătorii cu sediul în alt stat membru care operează în România sunt "
            "raportați în țara de origine.",
            "Pentru agregatul Spațiului Economic European, EIOPA publică doar ratele, nu "
            "și sumele absolute de fonduri proprii și de cerințe de capital.",
        ],
        "avertismente": [
            "SQ_Balance_Sheet.csv NU este codat UTF-8 (conține octetul 0x96) — citirea "
            "directă cu pandas aruncă UnicodeDecodeError. Scriptul reîncearcă cu latin-1.",
            "Fișierul de bilanț nu conține linia „All undertaking types\"; totalul se "
            "obține prin însumare. Unele țări au și categoria „Undertaking type not "
            "published\" (România nu are) — o însumare oarbă pe alte țări poate dubla "
            "valorile.",
            "Rata de solvabilitate este publicată ca raport (1,62), nu ca procent — "
            "trebuie înmulțită cu 100.",
            "Fișierele nu sunt servite de pe eiopa.europa.eu, ci de pe bucket-ul S3 "
            "nexteuropa-multisites.s3.eu-west-1.amazonaws.com (SQ_Balance_Sheet.csv are "
            "peste 20 MB).",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta, date_df=ro_raw,
        analize={
            "Rata de solvabilitate": a1,
            "Capital și cerințe": a2,
            "Pe tipuri de societăți": a3,
            "Calitatea capitalului": a4,
            "Bilanțul pieței": a5,
            "România în regiune": a6,
        },
        note_analize={
            "Rata de solvabilitate": "Media de piață și distribuția între societăți "
                                     "(percentile). 100% = minimul legal.",
            "Capital și cerințe": "Fondurile proprii eligibile, cerințele de capital SCR "
                                  "și MCR și surplusul, în milioane euro.",
            "Pe tipuri de societăți": "Rata de solvabilitate separat pentru societățile "
                                      "de viață, generale și compozite.",
            "Calitatea capitalului": "Structura pe niveluri a fondurilor proprii. Nivelul "
                                     "1 nerestricționat este capitalul cel mai solid.",
            "Bilanțul pieței": "Activele, plasamentele și provizioanele tehnice ale "
                               "societăților din România, însumate pe tipuri.",
            "România în regiune": "Rata de solvabilitate comparată cu vecinii și cu media "
                                  "Spațiului Economic European. Pentru agregatul SEE "
                                  "EIOPA publică doar rate, nu și sumele absolute de "
                                  "fonduri proprii și SCR — celulele rămân goale.",
        },
        numfmt="#,##0.0")

    # ================= PAGINA HTML ========================================
    scr_v = float(scr_ratio.dropna().iloc[-1])
    surplus = float((of_scr - scr).dropna().iloc[-1])
    p10 = float((s_of("R0620_P10") * 100).dropna().iloc[-1])
    eea_v = a6.loc[a6["Țara"] == "Spațiul Economic European", col_r]
    eea_v = float(eea_v.iloc[0]) if len(eea_v) and pd.notna(eea_v.iloc[0]) else None
    active = float(s_bs("R0500").dropna().iloc[-1])

    spec = {
        "cod": COD, "sectiune": "03 Asigurări",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "EIOPA — Insurance statistics (Solo quarterly, S.23.01 și S.02.01)",
        "sursa_url": PAGINA,
        "frecventa": "Trimestrial", "badge_extra": "Date trimestriale",
        "perioada": f"{ro_luna(per_iso(per_min))} – {ro_luna(per_iso(per_max))}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Rata de solvabilitate, {ro_luna(per_iso(per_max))}",
             "valoare": f"{ro_num(scr_v, 0)}%",
             "nota": "100% = minimul cerut de lege",
             "trend": "up" if scr_v >= 150 else "down"},
            {"eticheta": "Media Spațiului Economic European",
             "valoare": (f"{ro_num(eea_v, 0)}%" if eea_v else "–"),
             "nota": (f"România este cu {ro_num(eea_v - scr_v, 0)} p.p. sub medie"
                      if eea_v else "")},
            {"eticheta": "Capital peste cerința minimă",
             "valoare": f"{ro_num(surplus, 0)} mil. EUR",
             "nota": "fonduri proprii eligibile minus SCR"},
            {"eticheta": "Cele mai slab capitalizate 10%",
             "valoare": f"{ro_num(p10, 0)}%",
             "nota": "percentila 10 a ratei de solvabilitate",
             "trend": "up" if p10 >= 120 else "down"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Rata de solvabilitate a pieței românești",
             "subtitlu": "Media de piață și distribuția între societăți. Sub 100% "
                         "societatea nu mai respectă cerința legală de capital.",
             "labels": et, "unit": "%", "dec": 0, "ydec": 0, "xticks": 8,
             "series": [
                 {"name": "Media de piață", "data": clean(scr_ratio)},
                 {"name": "Percentila 90 (cele mai capitalizate)",
                  "data": clean(s_of("R0620_P90") * 100), "dashed": True},
                 {"name": "Percentila 50 (mediana)",
                  "data": clean(s_of("R0620_P50") * 100)},
                 {"name": "Percentila 10 (cele mai slabe)",
                  "data": clean(s_of("R0620_P10") * 100), "dashed": True},
             ]},
            {"id": "c2", "type": "bar",
             "titlu": "Capital disponibil față de capital cerut",
             "subtitlu": "Fondurile proprii eligibile și cerința de capital de "
                         "solvabilitate (SCR), în milioane euro.",
             "labels": et, "unit": "mil. EUR", "dec": 0, "ydec": 0, "zero": True,
             "xticks": 8,
             "series": [
                 {"name": "Fonduri proprii eligibile", "data": clean(of_scr)},
                 {"name": "Cerința SCR", "data": clean(scr)},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "Diferențe între tipurile de societăți",
             "subtitlu": "Rata de solvabilitate separat pentru asigurările de viață, "
                         "asigurările generale și societățile compozite.",
             "labels": et, "unit": "%", "dec": 0, "ydec": 0, "xticks": 8,
             "series": [{"name": nume, "data": clean(s_of("R0620", cod) * 100)}
                        for cod, nume in TIPURI.items()]},
            {"id": "c4", "type": "bar",
             "titlu": "România față de vecini și de media europeană",
             "subtitlu": f"Rata de solvabilitate în {ro_luna(per_iso(per_max))}.",
             "labels": list(a6["Țara"]), "unit": "%", "dec": 0, "ydec": 0, "zero": True,
             "series": [{"name": "Rata de solvabilitate", "data": clean(a6[col_r])}]},
            {"id": "c5", "type": "line",
             "titlu": "Bilanțul pieței: active și obligații față de asigurați",
             "subtitlu": "Totalul activelor și provizioanele tehnice — banii puși "
                         "deoparte pentru despăgubirile viitoare, în milioane euro.",
             "labels": et, "unit": "mil. EUR", "dec": 0, "ydec": 0, "xticks": 8,
             "series": [
                 {"name": "Total active", "data": clean(s_bs("R0500"))},
                 {"name": "Plasamente", "data": clean(s_bs("R0070"))},
                 {"name": "Provizioane tehnice — generale", "data": clean(s_bs("R0510"))},
                 {"name": "Excedentul activelor față de datorii",
                  "data": clean(s_bs("R1000"))},
             ]},
        ],
        "tabel": {
            "titlu": f"Date trimestriale ({len(perioade)} trimestre)",
            "columns": ["Trimestru", "Rata de solvabilitate (%)", "Percentila 10 (%)",
                        "Mediana (%)", "Fonduri proprii (mil. EUR)", "SCR (mil. EUR)",
                        "Total active (mil. EUR)"],
            "rows": [[per_iso(p).replace("-Q", " T"),
                      ro_num(scr_ratio.get(p), 1),
                      ro_num((s_of("R0620_P10") * 100).get(p), 1),
                      ro_num((s_of("R0620_P50") * 100).get(p), 1),
                      ro_num(of_scr.get(p), 1), ro_num(scr.get(p), 1),
                      ro_num(s_bs("R0500").get(p), 1)]
                     for p in perioade[::-1]],
        },
        "note": [
            "Sursa: EIOPA, statistici de asigurări — raportarea „solo\" trimestrială din "
            "regimul Solvency II: formularul S.23.01 (fonduri proprii) și S.02.01 "
            "(bilanț).",
            "<strong>Ce măsoară.</strong> Rata de solvabilitate compară capitalul pe care "
            "îl are efectiv un asigurător cu capitalul pe care legea i-l cere. Cerința "
            "(SCR) este calibrată astfel încât societatea să poată absorbi pierderi care "
            "apar o dată la 200 de ani. 100% înseamnă exact minimul; 250% înseamnă de "
            "două ori și jumătate minimul.",
            "<strong>De ce contează.</strong> Când un asigurător rămâne fără capital, "
            "clienții rămân fără despăgubiri. În România acest lucru s-a întâmplat de "
            "două ori într-un interval scurt — City Insurance (2021) și Euroins (2023) — "
            "iar despăgubirile au fost preluate de Fondul de Garantare a Asiguraților, cu "
            "plafon și cu întârzieri. Rata de solvabilitate este semnalul de avarie care "
            "se vede din timp.",
            "<strong>De ce contează percentilele.</strong> Media de piață este ponderată "
            "cu mărimea societăților: o singură societate mare și bine capitalizată poate "
            "ridica media, în timp ce societăți mici stau aproape de prag. Percentila 10 "
            "arată exact acea margine a pieței.",
            "<strong>Frecvență.</strong> Setul este TRIMESTRIAL; raportarea prudențială "
            "Solvency II nu are componentă lunară publică.",
            "Regenerare: <code>python3 scripts/financiara_03_03.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(ro_raw)} obs. RO, {len(perioade)} trimestre, "
          f"{per_iso(per_min)} → {per_iso(per_max)}, SCR RO = {scr_v:.1f}%, "
          f"active = {active:.0f} mil. EUR")


if __name__ == "__main__":
    main()
