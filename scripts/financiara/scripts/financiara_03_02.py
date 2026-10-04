#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 03 02 — Piața asigurărilor din România: prime, daune, cheltuieli
Sursa: EIOPA — Insurance statistics, „Solo quarterly" (raportarea Solvency II,
       formularul S.05.01), fișierul SQ_Premiums_Claims_Expenses.csv.
Frecvență: TRIMESTRIALĂ (nu există echivalent lunar public — vezi nota din Sursa).

CAPCANE CONFIRMATE LIVE (2026-09-17):
  * Valorile publicate sunt CUMULATE de la începutul anului (year-to-date):
    T1 < T2 < T3 < T4, iar în T1 al anului următor seria repornește. Scriptul
    calculează separat fluxul trimestrial prin diferență.
  * Fișierele nu sunt pe eiopa.europa.eu, ci pe bucket-ul S3
    nexteuropa-multisites.s3.eu-west-1.amazonaws.com; linkurile se descoperă din
    pagina „Insurance statistics".
  * SQ_Balance_Sheet.csv NU este UTF-8 (are octeți 0x96) — se citește cu latin-1.
    Fișierul de față este UTF-8, dar validarea rămâne explicită.
"""
import datetime as dt
import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fetch, ro_luna, ro_num)

COD = "Financiara 03 02"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
S3 = ("https://nexteuropa-multisites.s3.eu-west-1.amazonaws.com/"
      "www.eiopa.europa.eu/assets/insurance-statistics")
URL = f"{S3}/SQ_Premiums_Claims_Expenses.csv"
PAGINA = "https://www.eiopa.europa.eu/tools-and-data/insurance-statistics_en"

TARI = {"ROMANIA": "România", "BULGARIA": "Bulgaria", "CZECHIA": "Cehia",
        "HUNGARY": "Ungaria", "POLAND": "Polonia", "EEA": "Spațiul Economic European"}

# Coduri din formularul S.05.01 (Solvency II)
NV = {"R0110": "Prime brute subscrise — afacere directă",
      "R0140": "Prime subscrise — partea reasigurătorilor",
      "R0200": "Prime subscrise — net",
      "R0210": "Prime brute câștigate — afacere directă",
      "R0300": "Prime câștigate — net",
      "R0310": "Daune brute — afacere directă",
      "R0400": "Daune — net",
      "R0550": "Cheltuieli de exploatare"}
VI = {"R1410": "Prime brute subscrise",
      "R1420": "Prime subscrise — partea reasigurătorilor",
      "R1500": "Prime subscrise — net",
      "R1510": "Prime brute câștigate",
      "R1600": "Prime câștigate — net",
      "R1610": "Daune brute",
      "R1700": "Daune — net",
      "R1900": "Cheltuieli de exploatare"}


def per_sort(p: str) -> tuple[int, int]:
    y, q = p.split(" Q")
    return int(y), int(q)


def per_iso(p: str) -> str:
    y, q = p.split(" Q")
    return f"{y}-Q{q}"


def descarca() -> pd.DataFrame:
    r = fetch(URL, timeout=300)
    df = pd.read_csv(io.BytesIO(r.content), encoding="utf-8")
    cerute = {"Reporting country", "Reference period", "Item", "Business type",
              "Item code", "Value"}
    lipsa = cerute - set(df.columns)
    if lipsa:
        raise SystemExit(f"EȘEC: fișierul EIOPA nu mai are coloanele {sorted(lipsa)}. "
                         "Structura sursei s-a schimbat — nu suprascriu datele bune.")
    df = df[df["Reporting country"].isin(TARI)].copy()
    fail_if_short(df, 8000, "EIOPA SQ_Premiums_Claims_Expenses")
    ro = df[(df["Reporting country"] == "ROMANIA") & df["Value"].notna()]
    if ro.empty:
        raise SystemExit("EȘEC: EIOPA nu a întors nicio valoare pentru România.")
    ultim = max(ro["Reference period"], key=per_sort)
    y, q = per_sort(ultim)
    azi = dt.date.today()
    vechime = (azi.year - y) * 4 + ((azi.month - 1) // 3 + 1 - q)
    if vechime > 4:
        raise SystemExit(
            f"EȘEC: EIOPA se oprește la {ultim}, adică {vechime} trimestre în urmă "
            "(toleranță 4). Sursa pare înghețată.")
    return df


def decumuleaza(s: pd.Series) -> pd.Series:
    """YTD cumulat -> flux trimestrial. Index = 'AAAA Qn', sortat cronologic."""
    out = {}
    for p, v in s.items():
        y, q = per_sort(p)
        if pd.isna(v):
            out[p] = None
            continue
        if q == 1:
            out[p] = float(v)
        else:
            prev = s.get(f"{y} Q{q - 1}")
            out[p] = (float(v) - float(prev)) if pd.notna(prev) else None
    return pd.Series(out)


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()

    ro = df[df["Reporting country"] == "ROMANIA"].copy()
    perioade = sorted(set(ro["Reference period"]), key=per_sort)
    per_max, per_min = perioade[-1], perioade[0]

    def serie(cod: str, tip: str, tara: str = "ROMANIA") -> pd.Series:
        d = df[(df["Reporting country"] == tara) & (df["Item code"] == cod)
               & (df["Business type"] == tip)]
        s = d.set_index("Reference period")["Value"]
        s = s[~s.index.duplicated()]
        return s.reindex(perioade)

    ytd_nv = pd.DataFrame({NV[c]: serie(c, "Non-Life") for c in NV})
    ytd_vi = pd.DataFrame({VI[c]: serie(c, "Life") for c in VI})

    fl_nv = pd.DataFrame({c: decumuleaza(ytd_nv[c]) for c in ytd_nv.columns})
    fl_vi = pd.DataFrame({c: decumuleaza(ytd_vi[c]) for c in ytd_vi.columns})

    gwp_nv = fl_nv["Prime brute subscrise — afacere directă"]
    gwp_vi = fl_vi["Prime brute subscrise"]
    gwp_tot = gwp_nv.add(gwp_vi, fill_value=None)

    # ================= FOI DE ANALIZĂ =====================================
    a1 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    a1["Prime brute generale (mil. EUR)"] = gwp_nv.round(1).values
    a1["Prime brute viață (mil. EUR)"] = gwp_vi.round(1).values
    a1["Total prime brute (mil. EUR)"] = gwp_tot.round(1).values
    a1["Pondere asigurări generale (%)"] = (gwp_nv / gwp_tot * 100).round(1).values
    a1["Variație față de același trimestru al anului trecut (%)"] = (
        (gwp_tot / gwp_tot.shift(4) - 1) * 100).round(1).values

    a2 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    a2["Daune brute generale (mil. EUR)"] = fl_nv["Daune brute — afacere directă"].round(1).values
    a2["Daune brute viață (mil. EUR)"] = fl_vi["Daune brute"].round(1).values
    a2["Cheltuieli de exploatare generale (mil. EUR)"] = fl_nv["Cheltuieli de exploatare"].round(1).values
    a2["Cheltuieli de exploatare viață (mil. EUR)"] = fl_vi["Cheltuieli de exploatare"].round(1).values
    a2["Rata daunei brute — generale, flux trimestrial (%)"] = (
        fl_nv["Daune brute — afacere directă"]
        / fl_nv["Prime brute câștigate — afacere directă"] * 100).round(1).values

    ani = sorted({per_sort(p)[0] for p in perioade})
    rows = []
    for y in ani:
        q4 = f"{y} Q4"
        ultim_an = max([p for p in perioade if per_sort(p)[0] == y], key=per_sort)
        complet = q4 in perioade and pd.notna(ytd_nv["Prime brute subscrise — afacere directă"].get(q4))
        rows.append({
            "An": y,
            "Prime brute generale (mil. EUR)":
                ytd_nv["Prime brute subscrise — afacere directă"].get(ultim_an),
            "Prime brute viață (mil. EUR)": ytd_vi["Prime brute subscrise"].get(ultim_an),
            "Daune brute generale (mil. EUR)":
                ytd_nv["Daune brute — afacere directă"].get(ultim_an),
            "Daune brute viață (mil. EUR)": ytd_vi["Daune brute"].get(ultim_an),
            "An complet": "da" if complet else f"parțial (până la {per_iso(ultim_an)})",
        })
    a3 = pd.DataFrame(rows)
    a3["Total prime brute (mil. EUR)"] = (a3["Prime brute generale (mil. EUR)"]
                                          + a3["Prime brute viață (mil. EUR)"])
    plin = a3[a3["An complet"] == "da"].copy()
    a3["Creștere anuală a primelor (%)"] = None
    if len(plin) > 1:
        cr = (plin["Total prime brute (mil. EUR)"]
              / plin["Total prime brute (mil. EUR)"].shift(1) - 1) * 100
        a3.loc[plin.index, "Creștere anuală a primelor (%)"] = cr.round(1)
    for c in a3.columns:
        if "mil. EUR" in c:
            a3[c] = a3[c].round(1)

    # ATENȚIE: ratele Z0001/Z0002 sunt calculate de EIOPA pe valori CUMULATE de la
    # începutul anului, exact ca restul formularului S.05.01. T1 acoperă doar
    # ianuarie–martie, T4 acoperă întregul an. Nu sunt rate trimestriale.
    ACOPERIRE = {1: "ianuarie–martie", 2: "ianuarie–iunie",
                 3: "ianuarie–septembrie", 4: "anul întreg"}
    cr_comb = serie("Z0001", "Non-Life")
    cr_chelt = serie("Z0002", "Non-Life")
    a4 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    a4["Perioada acoperită (cumulat)"] = [ACOPERIRE[per_sort(p)[1]] for p in perioade]
    a4["Rata combinată netă, cumulat de la 1 ianuarie (%)"] = (cr_comb * 100).round(1).values
    a4["Rata cheltuielilor nete, cumulat (%)"] = (cr_chelt * 100).round(1).values
    a4["Rata daunei nete, cumulat (%)"] = ((cr_comb - cr_chelt) * 100).round(1).values
    a4["Profitabilitate tehnică"] = [
        "profit tehnic" if pd.notna(v) and v < 100 else
        ("pierdere tehnică" if pd.notna(v) else "—")
        for v in a4["Rata combinată netă, cumulat de la 1 ianuarie (%)"]]

    # Referință comparabilă: rata la sfârșitul fiecărui an complet (T4 = anul întreg).
    ani_complet = [int(y) for y, c in zip(a3["An"], a3["An complet"]) if c == "da"
                   and pd.notna(cr_comb.get(f"{y} Q4"))]
    ultim_an_plin = max(ani_complet) if ani_complet else None
    comb_an = (float(cr_comb[f"{ultim_an_plin} Q4"]) * 100
               if ultim_an_plin is not None else None)

    a5 = pd.DataFrame({"Trimestru": [per_iso(p) for p in perioade]})
    a5["Prime cedate în reasigurare — generale (mil. EUR)"] = \
        fl_nv["Prime subscrise — partea reasigurătorilor"].round(1).values
    a5["Grad de cedare — generale (%)"] = (
        fl_nv["Prime subscrise — partea reasigurătorilor"]
        / fl_nv["Prime brute subscrise — afacere directă"] * 100).round(1).values
    a5["Prime cedate în reasigurare — viață (mil. EUR)"] = \
        fl_vi["Prime subscrise — partea reasigurătorilor"].round(1).values
    a5["Grad de cedare — viață (%)"] = (
        fl_vi["Prime subscrise — partea reasigurătorilor"]
        / fl_vi["Prime brute subscrise"] * 100).round(1).values

    # Comparație regională: ultimele 4 trimestre cumulate (flux)
    reg_rows = []
    for t_cod, t_num in TARI.items():
        nv = decumuleaza(serie("R0110", "Non-Life", t_cod))
        vi = decumuleaza(serie("R1410", "Life", t_cod))
        tot = nv.add(vi, fill_value=None)
        u4 = tot.dropna().tail(4)
        u4_prec = tot.dropna().iloc[-8:-4]
        reg_rows.append({
            "Țara": t_num,
            "Prime brute, ultimele 4 trimestre (mil. EUR)":
                round(float(u4.sum()), 1) if len(u4) == 4 else None,
            "din care asigurări generale (mil. EUR)":
                round(float(nv.dropna().tail(4).sum()), 1) if len(u4) == 4 else None,
            "din care asigurări de viață (mil. EUR)":
                round(float(vi.dropna().tail(4).sum()), 1) if len(u4) == 4 else None,
            "Variație față de cele 4 trimestre anterioare (%)":
                round((float(u4.sum()) / float(u4_prec.sum()) - 1) * 100, 1)
                if len(u4) == 4 and len(u4_prec) == 4 and float(u4_prec.sum()) else None,
        })
    a6 = pd.DataFrame(reg_rows)
    eea = a6.loc[a6["Țara"] == "Spațiul Economic European",
                 "Prime brute, ultimele 4 trimestre (mil. EUR)"]
    if len(eea) and pd.notna(eea.iloc[0]) and eea.iloc[0]:
        a6["Cotă din piața SEE (%)"] = (
            a6["Prime brute, ultimele 4 trimestre (mil. EUR)"] / float(eea.iloc[0]) * 100
        ).round(2)

    ro_raw = (ro[["Reference period", "Business type", "Item", "Item code", "Value",
                  "Number of submissions (per reporting country, reference date and "
                  "undertaking type)"]]
              .rename(columns={
                  "Reference period": "Trimestru",
                  "Business type": "Tip de activitate",
                  "Item": "Indicator (EIOPA)",
                  "Item code": "Cod S.05.01",
                  "Value": "Valoare YTD (mil. EUR)",
                  "Number of submissions (per reporting country, reference date and "
                  "undertaking type)": "Număr de raportări"})
              .assign(Trimestru=lambda d: d["Trimestru"].map(per_iso))
              .sort_values(["Trimestru", "Tip de activitate", "Cod S.05.01"])
              .reset_index(drop=True))

    nr_soc = ro["Number of submissions (per reporting country, reference date and "
                "undertaking type)"].dropna()
    nr_soc = int(nr_soc.iloc[-1]) if len(nr_soc) else None

    # Cât de mult contează excluderea reasigurării acceptate (R0120 + R0130) din
    # agregatul „prime brute" — calculat pe ultimul an complet disponibil.
    ref_an = f"{ultim_an_plin} Q4" if ultim_an_plin is not None else per_max
    r_dir = serie("R0110", "Non-Life").get(ref_an)
    r_acc = sum(float(serie(c, "Non-Life").get(ref_an) or 0) for c in ("R0120", "R0130"))
    pct_acc = (r_acc / (float(r_dir) + r_acc) * 100
               if pd.notna(r_dir) and (float(r_dir) + r_acc) else None)

    meta = {
        "cod": COD, "sectiune": "03 Asigurări",
        "titlu": "Piața asigurărilor din România: prime, daune, cheltuieli",
        "subtitlu": "Cât încasează asigurătorii din România din polițe, cât plătesc în "
                    "despăgubiri și dacă activitatea de asigurare este profitabilă — "
                    "din raportările Solvency II centralizate de EIOPA.",
        "sursa": "EIOPA — Insurance statistics, raportare solo trimestrială "
                 "(Solvency II, formularul S.05.01)",
        "sursa_url": PAGINA,
        "cod_set": "SQ_Premiums_Claims_Expenses.csv (Solo Quarterly); coduri S.05.01: "
                   "R0110, R0140, R0200, R0210, R0300, R0310, R0400, R0550 (generale); "
                   "R1410–R1900 (viață); Z0001/Z0002 (rate calculate de EIOPA)",
        "frecventa": "TRIMESTRIALĂ — nu există serie lunară publică pentru piața "
                     "asigurărilor din România",
        "perioada": f"{per_iso(per_min)} → {per_iso(per_max)}",
        "unitate": "milioane EUR; ratele în procente (%)",
        "descarcat": azi,
        "licenta": "EIOPA — reutilizare permisă cu menționarea sursei.",
        "metodologie": "Datele provin din raportările prudențiale trimestriale pe care "
                       "societățile de asigurare din Spațiul Economic European le trimit "
                       "autorităților naționale de supraveghere (în România, ASF) în "
                       "regimul Solvency II. EIOPA le agregă la nivel de țară. "
                       "„Afacere directă\" înseamnă polițele vândute clienților, fără "
                       "reasigurarea acceptată de la alte societăți. Rata combinată netă "
                       "este suma dintre rata daunei și rata cheltuielilor: sub 100% "
                       "activitatea de asigurare aduce profit tehnic, peste 100% aduce "
                       "pierdere tehnică acoperită din veniturile financiare.",
        "script": "scripts/financiara_03_02.py",
        "note": [
            f"Agregatul pentru România acoperă {nr_soc} societăți raportoare în ultimul "
            "trimestru disponibil." if nr_soc else
            "Numărul de societăți raportoare este publicat de EIOPA pe fiecare trimestru.",
            "Valorile sunt exprimate în euro; o parte din variația de la un an la altul "
            "vine din cursul de schimb RON/EUR, nu doar din volumul de afaceri.",
            "Foaia „Date\" păstrează valorile exact cum le publică EIOPA (cumulate de la "
            "începutul anului). Foile de analiză cu SUME conțin fluxul trimestrial "
            "recalculat; foaia „Indicatori tehnici\" rămâne cumulată (vezi avertismente).",
            "„Prime brute subscrise\" înseamnă aici afacerea directă (R0110 la asigurări "
            "generale, R1410 la viață) — polițele vândute clienților. Reasigurarea "
            "acceptată de la alte societăți (R0120 proporțională și R0130 "
            "neproporțională) este exclusă din agregat.",
            "Asigurătorii care își au sediul în alt stat membru și operează în România pe "
            "baza libertății de a presta servicii sunt raportați în țara de origine, nu "
            "în România.",
            "Datele trimestriale sunt neauditate și pot fi revizuite la publicările "
            "ulterioare.",
        ],
        "avertismente": [
            "Valorile publicate sunt CUMULATE de la începutul anului calendaristic "
            "(year-to-date): T4 conține întregul an. Fără de-cumulare, o comparație "
            "directă între trimestre este greșită.",
            "Ratele Z0001 (rata combinată netă) și Z0002 (rata cheltuielilor nete) sunt "
            "calculate de EIOPA tot pe valori cumulate și NU au fost de-cumulate în acest "
            "set, pentru că sunt preluate exact cum le publică sursa. Valoarea unui "
            "trimestru 1 acoperă doar ianuarie–martie, cea a unui trimestru 4 acoperă anul "
            "întreg. Comparați T1 cu T1, nu T1 cu T4. Foaia „Indicatori tehnici\" are o "
            "coloană „Perioada acoperită\" care indică explicit intervalul fiecărui rând.",
            "Agregatul „prime brute\" din acest set este afacerea directă (R0110 / R1410) "
            "și EXCLUDE reasigurarea acceptată de la alte societăți: R0120 (proporțională) "
            "și R0130 (neproporțională). "
            + (f"Efectul este mic: în {ultim_an_plin} reasigurarea acceptată a reprezentat "
               f"{ro_num(pct_acc, 3)}% din primele brute la asigurările generale."
               if pct_acc is not None else
               "Ponderea reasigurării acceptate este publicată separat în foaia „Date\"."),
            "Fișierele nu sunt servite de pe eiopa.europa.eu, ci de pe bucket-ul S3 "
            "nexteuropa-multisites.s3.eu-west-1.amazonaws.com; adresele se descoperă din "
            "pagina „Insurance statistics\".",
            "SQ_Balance_Sheet.csv de pe același bucket NU este codat UTF-8 (conține "
            "octetul 0x96) și trebuie citit cu latin-1.",
            "Nu există echivalent lunar. ASF România publică rapoarte trimestriale în "
            "PDF cu nume de fișier opace, iar paginile de navigare asfromania.ro sunt "
            "protejate de un WAF — nu pot fi automatizate.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta, date_df=ro_raw,
        analize={
            "Prime trimestriale": a1,
            "Daune și cheltuieli": a2,
            "Totaluri anuale": a3,
            "Indicatori tehnici": a4,
            "Cedare în reasigurare": a5,
            "România în regiune": a6,
        },
        note_analize={
            "Prime trimestriale": "Prime brute subscrise, flux pe trimestru (recalculat "
                                  "din valorile cumulate publicate de EIOPA), în mil. EUR.",
            "Daune și cheltuieli": "Despăgubirile plătite și cheltuielile de exploatare, "
                                   "flux trimestrial, plus rata daunei brute.",
            "Totaluri anuale": "Valoarea cumulată la sfârșitul fiecărui an; ultimul an "
                               "este parțial dacă nu s-a publicat încă trimestrul 4.",
            "Indicatori tehnici": "Ratele calculate de EIOPA pentru asigurările generale. "
                                  "ATENȚIE: sunt cumulate de la începutul anului, ca tot "
                                  "formularul S.05.01 — T1 acoperă doar ianuarie–martie, "
                                  "T4 acoperă anul întreg. Nu compara direct un T1 cu un "
                                  "T4; compară T1 cu T1. Rata combinată sub 100% = profit "
                                  "tehnic.",
            "Cedare în reasigurare": "Cât din primele încasate este transferat "
                                     "reasigurătorilor, în valoare și în procente.",
            "România în regiune": "Primele brute din ultimele patru trimestre, comparate "
                                  "cu vecinii și cu totalul Spațiului Economic European.",
        },
        numfmt="#,##0.0")

    # ================= PAGINA HTML ========================================
    et = [ro_luna(per_iso(p)) for p in perioade]
    tot_4q = float(gwp_tot.dropna().tail(4).sum())
    tot_4q_prec = float(gwp_tot.dropna().iloc[-8:-4].sum())
    crestere = (tot_4q / tot_4q_prec - 1) * 100 if tot_4q_prec else None
    nv_share = float(gwp_nv.dropna().tail(4).sum()) / tot_4q * 100 if tot_4q else None
    comb = a4["Rata combinată netă, cumulat de la 1 ianuarie (%)"].dropna()
    comb_v = float(comb.iloc[-1]) if len(comb) else None
    acop_max = ACOPERIRE[per_sort(per_max)[1]]
    cota = a6.loc[a6["Țara"] == "România", "Cotă din piața SEE (%)"]
    cota_v = float(cota.iloc[0]) if len(cota) and pd.notna(cota.iloc[0]) else None

    a3_plin = a3[a3["An complet"] == "da"]

    spec = {
        "cod": COD, "sectiune": "03 Asigurări",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "EIOPA — Insurance statistics (Solo quarterly, S.05.01)",
        "sursa_url": PAGINA,
        "frecventa": "Trimestrial",
        "badge_extra": "Date trimestriale",
        "perioada": f"{ro_luna(per_iso(per_min))} – {ro_luna(per_iso(per_max))}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": "Prime brute, ultimele 4 trimestre",
             "valoare": f"{ro_num(tot_4q, 0)} mil. EUR",
             "nota": f"până la {ro_luna(per_iso(per_max))}"},
            {"eticheta": "Creștere față de anul anterior",
             "valoare": (f"{'+' if (crestere or 0) >= 0 else ''}{ro_num(crestere, 1)}%"
                         if crestere is not None else "–"),
             "nota": "cele 4 trimestre precedente, în euro",
             "trend": "up" if (crestere or 0) >= 0 else "down"},
            {"eticheta": "Ponderea asigurărilor generale",
             "valoare": (f"{ro_num(nv_share, 1)}%" if nv_share else "–"),
             "nota": "restul sunt asigurări de viață"},
            {"eticheta": f"Rata combinată netă, {ro_luna(per_iso(per_max))} "
                         f"(cumulat {acop_max})",
             "valoare": (f"{ro_num(comb_v, 1)}%" if comb_v else "–"),
             "nota": ((f"ultimul an complet ({ultim_an_plin}): {ro_num(comb_an, 1)}% · "
                       if comb_an is not None else "")
                      + ("sub 100% = profit tehnic" if comb_v and comb_v < 100
                         else "peste 100% = pierdere tehnică")),
             "trend": "up" if comb_v and comb_v < 100 else "down"},
        ],
        "charts": [
            {"id": "c1", "type": "bar",
             "titlu": "Prime brute subscrise, pe trimestru",
             "subtitlu": "Cât au încasat asigurătorii din polițele vândute în fiecare "
                         "trimestru. Valorile au fost recalculate din datele cumulate "
                         "publicate de EIOPA.",
             "labels": et, "unit": "mil. EUR", "dec": 0, "ydec": 0, "zero": True,
             "stacked": True, "xticks": 8,
             "series": [
                 {"name": "Asigurări generale", "data": clean(gwp_nv)},
                 {"name": "Asigurări de viață", "data": clean(gwp_vi)},
             ]},
            {"id": "c2", "type": "line",
             "titlu": "Prime încasate față de despăgubiri plătite",
             "subtitlu": "Asigurări generale, flux trimestrial. Distanța dintre linii "
                         "arată cât rămâne pentru cheltuieli și profit.",
             "labels": et, "unit": "mil. EUR", "dec": 0, "ydec": 0, "xticks": 8,
             "series": [
                 {"name": "Prime brute câștigate",
                  "data": clean(fl_nv["Prime brute câștigate — afacere directă"])},
                 {"name": "Daune brute",
                  "data": clean(fl_nv["Daune brute — afacere directă"])},
             ]},
            {"id": "c3", "type": "line",
             "titlu": "Este profitabilă activitatea de asigurare?",
             "subtitlu": "Rata combinată netă la asigurările generale. Peste 100% "
                         "înseamnă că despăgubirile și cheltuielile depășesc primele "
                         "încasate. Atenție: ratele sunt cumulate de la începutul "
                         "fiecărui an — T1 acoperă doar trei luni, T4 acoperă anul "
                         "întreg, iar seria repornește în fiecare ianuarie. Comparați T1 "
                         "cu T1, nu T1 cu T4.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "xticks": 8,
             "series": [
                 {"name": "Rata combinată netă (cumulat)", "data": clean(cr_comb * 100)},
                 {"name": "Rata daunei nete (cumulat)",
                  "data": clean((cr_comb - cr_chelt) * 100)},
                 {"name": "Rata cheltuielilor nete (cumulat)", "data": clean(cr_chelt * 100)},
             ]},
            {"id": "c4", "type": "bar",
             "titlu": "Piața, an de an",
             "subtitlu": "Prime brute subscrise pe an calendaristic, în milioane de euro. "
                         "Ultimul an poate fi parțial.",
             "labels": [str(x) for x in a3["An"]], "unit": "mil. EUR",
             "dec": 0, "ydec": 0, "zero": True, "stacked": True,
             "series": [
                 {"name": "Asigurări generale",
                  "data": clean(a3["Prime brute generale (mil. EUR)"])},
                 {"name": "Asigurări de viață",
                  "data": clean(a3["Prime brute viață (mil. EUR)"])},
             ]},
            {"id": "c5", "type": "bar",
             "titlu": "România față de vecini",
             "subtitlu": "Prime brute subscrise în ultimele patru trimestre, milioane "
                         "euro. Spațiul Economic European este exclus din grafic pentru "
                         "lizibilitate (vezi tabelul din Excel).",
             "labels": [t for t in a6["Țara"] if t != "Spațiul Economic European"],
             "unit": "mil. EUR", "dec": 0, "ydec": 0, "zero": True,
             "series": [{"name": "Prime brute (4 trimestre)",
                         "data": clean(a6.loc[a6["Țara"] != "Spațiul Economic European",
                                              "Prime brute, ultimele 4 trimestre (mil. EUR)"])}]},
        ],
        "tabel": {
            "titlu": f"Date trimestriale — sume în flux trimestrial, rata combinată "
                     f"cumulată de la 1 ianuarie ({len(perioade)} trimestre)",
            "columns": ["Trimestru", "Prime generale (mil. EUR)",
                        "Prime viață (mil. EUR)", "Total (mil. EUR)",
                        "Daune generale (mil. EUR)",
                        "Rata combinată netă — cumulat de la 1 ianuarie (%)"],
            "rows": [[a1["Trimestru"].iloc[i].replace("-Q", " T"),
                      ro_num(a1["Prime brute generale (mil. EUR)"].iloc[i], 1),
                      ro_num(a1["Prime brute viață (mil. EUR)"].iloc[i], 1),
                      ro_num(a1["Total prime brute (mil. EUR)"].iloc[i], 1),
                      ro_num(a2["Daune brute generale (mil. EUR)"].iloc[i], 1),
                      ro_num(a4["Rata combinată netă, cumulat de la 1 ianuarie (%)"]
                             .iloc[i], 1)]
                     for i in range(len(a1) - 1, -1, -1)],
        },
        "note": [
            "Sursa: EIOPA, statistici de asigurări — raportarea „solo\" trimestrială din "
            "regimul Solvency II, formularul S.05.01 (prime, daune și cheltuieli).",
            "<strong>Ce măsoară.</strong> „Primele brute subscrise\" sunt banii pe care "
            "asigurătorii i-au încasat sau i-au facturat pentru polițele vândute în "
            "perioada respectivă. „Daunele\" sunt despăgubirile plătite sau rezervate "
            "pentru evenimente deja produse.",
            "<strong>De ce contează.</strong> Dimensiunea pieței și raportul dintre prime "
            "și daune arată dacă asigurătorii își pot onora obligațiile din activitatea "
            "curentă. În România, falimentele City Insurance (2021) și Euroins (2023) au "
            "lăsat sute de mii de șoferi fără RCA valabil, așa că echilibrul tehnic al "
            "sectorului nu este o chestiune pur contabilă.",
            "<strong>Rata combinată netă</strong> adună despăgubirile și cheltuielile și "
            "le raportează la primele câștigate. Sub 100% activitatea de asigurare aduce "
            "profit; peste 100% pierderea trebuie acoperită din plasamentele financiare "
            "sau din capitalul acționarilor.",
            "<strong>Cum se citește rata combinată.</strong> Spre deosebire de sumele din "
            "grafice, rata combinată NU a fost de-cumulată: EIOPA o publică așa cum o "
            "calculează, pe valori cumulate de la începutul anului. Valoarea afișată "
            "pentru un trimestru 1 acoperă doar ianuarie–martie, cea pentru un trimestru "
            "4 acoperă anul întreg, iar seria repornește în fiecare ianuarie. O comparație "
            "corectă se face între același trimestru din ani diferiți sau între ani "
            "încheiați.",
            "<strong>Frecvență.</strong> Setul este TRIMESTRIAL. Nu există o statistică "
            "lunară publică pentru piața asigurărilor din România: ASF publică date "
            "trimestriale, iar EIOPA agregă tot trimestrial.",
            "Valorile publicate de EIOPA sunt cumulate de la începutul anului; graficele "
            "și tabelul de mai sus folosesc fluxul trimestrial recalculat prin diferență.",
            "Regenerare: <code>python3 scripts/financiara_03_02.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(ro_raw)} obs. RO, {len(perioade)} trimestre, "
          f"{per_iso(per_min)} → {per_iso(per_max)}, prime 4T = {tot_4q:.0f} mil. EUR")


if __name__ == "__main__":
    main()
