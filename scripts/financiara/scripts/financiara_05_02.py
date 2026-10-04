#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 05 02 — Pilonul II: unde sunt investiți banii (structura portofoliului)
Sursa: ASF, `p2-date_statistice.xlsx`, foaia `Table 6.` (Structura investiţii)
Frecvență: lunară. Rulează scriptul ca să regenerezi Excel-ul și pagina HTML.
"""
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, ro_luna, ro_num)
import pensii_asf as P  # noqa: E402

COD = "Financiara 05 02"
PAGINA = "https://data.asfromania.ro/pensii/p2-date_statistice.xlsx"

# Coloanele cu VALORI (lei) din Table 6.; coloanele "% in TOTAL activ" din sursă
# sunt ignorate, procentele fiind recalculate aici din valorile absolute.
COLOANE = {
    3: "Activ total",
    4: "Total investiții",
    5: "Depozite bancare",
    7: "Titluri de stat / obligațiuni municipale (raportare combinată, 2008)",
    9: "Titluri de stat",
    11: "Obligațiuni municipale",
    13: "Obligațiuni corporative",
    15: "Obligațiuni ale organismelor străine neguvernamentale (BERD, BEI, BM)",
    17: "Acțiuni",
    19: "Titluri de participare — OPCVM",
    21: "Alte organisme de plasament colectiv (AOPC)",
    23: "Mărfuri și metale prețioase",
    25: "Fonduri de mărfuri și metale prețioase",
    27: "Instrumente de acoperire a riscului",
    29: "Acțiuni private equity",
    31: "Infrastructură",
    33: "Alte instrumente financiare",
    35: "Alte sume, inclusiv sume în curs de decontare",
}
GRUPE = {
    "Titluri de stat": ["Titluri de stat",
                        "Titluri de stat / obligațiuni municipale (raportare combinată, 2008)"],
    "Acțiuni": ["Acțiuni"],
    "Fonduri de investiții (OPCVM și AOPC)": ["Titluri de participare — OPCVM",
                                              "Alte organisme de plasament colectiv (AOPC)"],
    "Obligațiuni corporative": ["Obligațiuni corporative"],
    "Depozite bancare": ["Depozite bancare"],
    "Obligațiuni municipale": ["Obligațiuni municipale"],
    "Obligațiuni supranaționale": [
        "Obligațiuni ale organismelor străine neguvernamentale (BERD, BEI, BM)"],
    "Alte plasamente (private equity, mărfuri, acoperirea riscului)": [
        "Mărfuri și metale prețioase", "Fonduri de mărfuri și metale prețioase",
        "Instrumente de acoperire a riscului", "Acțiuni private equity", "Infrastructură",
        "Alte instrumente financiare"],
    "Alte sume, inclusiv în curs de decontare": ["Alte sume, inclusiv sume în curs de decontare"],
}
ORDINE = list(GRUPE)


def curata_nume(s: str) -> str:
    return s.strip().rstrip("*").strip().upper()


def culege() -> pd.DataFrame:
    d = P.foaie("p2", "Table 6.")
    lung = P.lung_din_matrice(d, rand_antet=2, col_data=1, col_nume=2, col_valori=COLOANE)
    lung["entitate"] = lung["entitate"].map(curata_nume)
    lung = lung.groupby(["perioada", "entitate", "indicator"], as_index=False)["valoare"].last()
    fail_if_short(lung, 25000, "ASF Pilon II — Table 6. (structura investiţii)")
    fail_if_stale(lung.perioada.max(), 4, "ASF Pilon II structura investiții")
    return lung


def grupeaza(pv: pd.DataFrame) -> pd.DataFrame:
    """Coloane pe instrument -> coloane pe grupă (sume)."""
    out = pd.DataFrame(index=pv.index)
    for g, membri in GRUPE.items():
        cols = [c for c in membri if c in pv.columns]
        out[g] = pv[cols].sum(axis=1, min_count=1) if cols else None
    return out


def main() -> None:
    lung = culege()
    azi = dt.date.today().isoformat()

    tot = lung[lung.entitate == "TOTAL"].pivot_table(
        index="perioada", columns="indicator", values="valoare", aggfunc="last").sort_index()
    activ = tot["Activ total"]
    per_min, per_max = tot.index.min(), tot.index.max()

    g_val = grupeaza(tot)                      # lei
    g_pct = g_val.div(activ, axis=0) * 100     # % din activul total

    # ---------------- foi de analiză ---------------------------------------
    a_pct = (g_pct.round(2).reset_index().rename(columns={"perioada": "Luna"}))
    a_pct.insert(1, "Activ total (mil. lei)", (activ / 1e6).round(1).values)

    a_val = (g_val / 1e6).round(1).reset_index().rename(columns={"perioada": "Luna"})
    a_val.insert(1, "Activ total (mil. lei)", (activ / 1e6).round(1).values)

    dec = g_pct[g_pct.index.str.endswith("-12")]
    a_anual = dec.round(2).reset_index()
    a_anual["perioada"] = [p[:4] for p in dec.index]
    a_anual = a_anual.rename(columns={"perioada": "An (31 decembrie)"})

    fonduri = sorted(x for x in lung[lung.perioada == per_max].entitate.unique() if x != "TOTAL")
    pv_ult = lung[(lung.perioada == per_max) & (lung.entitate != "TOTAL")].pivot_table(
        index="entitate", columns="indicator", values="valoare", aggfunc="last")
    pv_ult = pv_ult.reindex(fonduri).dropna(how="all")
    fonduri = list(pv_ult.index)
    gf_val = grupeaza(pv_ult)
    gf_pct = gf_val.div(pv_ult["Activ total"], axis=0) * 100

    a_fond_pct = gf_pct.round(2).reset_index().rename(columns={"entitate": "Fond de pensii"})
    a_fond_pct.insert(1, "Activ total (mil. lei)", (pv_ult["Activ total"] / 1e6).round(1).values)
    a_fond_val = (gf_val / 1e6).round(1).reset_index().rename(columns={"entitate": "Fond de pensii"})
    a_fond_val.insert(1, "Activ total (mil. lei)", (pv_ult["Activ total"] / 1e6).round(1).values)

    idx12 = -13 if len(g_pct) > 13 else 0
    a_dinamica = pd.DataFrame({
        "Clasă de active": ORDINE,
        f"Pondere {ro_luna(per_max)} (%)": [g_pct[c].iloc[-1] for c in ORDINE],
        "Pondere acum 12 luni (%)": [g_pct[c].iloc[idx12] for c in ORDINE],
        "Variație 12 luni (p.p.)": [g_pct[c].iloc[-1] - g_pct[c].iloc[idx12] for c in ORDINE],
        f"Valoare {ro_luna(per_max)} (mil. lei)": [g_val[c].iloc[-1] / 1e6 for c in ORDINE],
        "Valoare acum 12 luni (mil. lei)": [g_val[c].iloc[idx12] / 1e6 for c in ORDINE],
        "Variație valoare 12 luni (%)": [
            (g_val[c].iloc[-1] / g_val[c].iloc[idx12] - 1) * 100
            if g_val[c].iloc[idx12] not in (0, None) and pd.notna(g_val[c].iloc[idx12]) else None
            for c in ORDINE],
    }).round(2)

    instr = tot.drop(columns=[c for c in ("Activ total", "Total investiții") if c in tot.columns])
    a_instr = (instr.tail(60) / 1e6).round(2).reset_index().rename(columns={"perioada": "Luna"})

    meta = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": "Pilonul II: unde sunt investiți banii din pensia privată obligatorie",
        "subtitlu": "Structura portofoliului celor peste 240 de miliarde de lei administrați: "
                    "cât merge în titluri de stat, cât în acțiuni, cât în depozite.",
        "sursa": "Autoritatea de Supraveghere Financiară (ASF) — date statistice pensii private, Pilon II",
        "sursa_url": PAGINA,
        "cod_set": "p2-date_statistice.xlsx — Table 6. (Structura investiţii, lei și % din active totale)",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "valori în lei (foaia Date) și milioane lei (foile de analiză); "
                   "ponderi în % din activul total",
        "descarcat": azi,
        "licenta": P.LICENTA,
        "metodologie": "Foaia Table 6. este deja în format lung: o linie per lună și per fond, cu "
                       "valoarea plasată în fiecare clasă de instrumente financiare, la data ultimei "
                       "zile lucrătoare a lunii. Aici sunt preluate exclusiv coloanele cu VALORI "
                       "(lei); ponderile sunt recalculate de 24reco ca valoare / activ total × 100, "
                       "ca să fie coerente cu agregările pe grupe. Instrumentele individuale sunt "
                       "apoi grupate în 9 clase de active, pentru lizibilitate; foaia `Date` "
                       "păstrează detaliul pe fiecare instrument raportat.",
        "script": "scripts/financiara_05_02.py",
        "note": [
            "Suma plasamentelor poate depăși ușor 100% din activul total, pentru că «alte sume, "
            "inclusiv sume în curs de decontare» este frecvent o valoare negativă (obligații ale "
            "fondului), iar totalul investițiilor raportat este brut.",
            "Coloana «Titluri de stat / obligațiuni municipale» a fost raportată combinat doar în "
            "2008; este inclusă în grupa «Titluri de stat» și marcată ca atare în foaia Date.",
            "Clasele «Infrastructură» și «AOPC» apar în formularul de raportare, dar nu au avut "
            "valori nenule în perioada acoperită — coloanele rămân în set pentru completitudine.",
            "Investițiile în acțiuni includ atât acțiuni listate la Bursa de Valori București, cât "
            "și acțiuni străine; sursa nu separă cele două categorii în această foaie.",
        ],
        "avertismente": [
            "Fișierul ASF se actualizează in-place: istoricul stă în rânduri suplimentare adăugate "
            "lunar la finalul foii Table 6.",
            "Numele fondurilor apar inconsecvent în această foaie (ex. «VITAL» și «Vital»); aici "
            "sunt normalizate la majuscule, fără alte modificări.",
            "Rapoartele rectificative pot schimba retroactiv valori deja publicate.",
            "Instrumentele de acoperire a riscului pot avea valori negative (poziții de hedging cu "
            "valoare de piață negativă) — nu sunt erori de date.",
        ],
    }

    build_excel(
        os.path.join(P.OUT, f"{COD}.xlsx"), meta=meta,
        date_df=lung.rename(columns={"perioada": "Luna", "entitate": "Fond de pensii",
                                     "indicator": "Instrument financiar", "valoare": "Valoare (lei)"}),
        analize={
            "Structura sistem (%)": a_pct,
            "Structura sistem (mil. lei)": a_val,
            "Structura la 31 decembrie (%)": a_anual,
            "Structura pe fond (%)": a_fond_pct,
            "Structura pe fond (mil. lei)": a_fond_val,
            "Dinamica pe 12 luni": a_dinamica,
            "Instrumente detaliate (60 luni)": a_instr,
        },
        note_analize={
            "Structura sistem (%)": "Ponderea fiecărei clase de active în activul total al Pilonului II.",
            "Structura sistem (mil. lei)": "Aceleași clase, în valori absolute.",
            "Structura la 31 decembrie (%)": "Serie anuală comparabilă, măsurată în aceeași lună.",
            "Structura pe fond (%)": f"Politica de investiții a fiecărui fond în {ro_luna(per_max)}.",
            "Structura pe fond (mil. lei)": "Expunerea absolută a fiecărui fond, pe clase de active.",
            "Dinamica pe 12 luni": "Cum s-a mutat portofoliul sistemului față de aceeași lună a anului trecut.",
            "Instrumente detaliate (60 luni)": "Detaliul pe fiecare instrument raportat, exact ca în sursă.",
        },
        numfmt="#,##0.00")

    # ---------------- pagina HTML ------------------------------------------
    et = [ro_luna(p) for p in g_pct.index]
    princ = ["Titluri de stat", "Acțiuni", "Fonduri de investiții (OPCVM și AOPC)",
             "Obligațiuni corporative", "Depozite bancare"]
    ts, ac = g_pct["Titluri de stat"], g_pct["Acțiuni"]
    d_ts = float(ts.iloc[-1] - ts.iloc[idx12])

    spec = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "ASF — date statistice Pilon II, Table 6.", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"În titluri de stat, {ro_luna(per_max)}",
             "valoare": f"{ro_num(ts.iloc[-1], 1)}%",
             "nota": f"{ro_num(g_val['Titluri de stat'].iloc[-1] / 1e9, 1)} mld. lei "
                     f"împrumutați statului român"},
            {"eticheta": "În acțiuni",
             "valoare": f"{ro_num(ac.iloc[-1], 1)}%",
             "nota": f"{ro_num(g_val['Acțiuni'].iloc[-1] / 1e9, 1)} mld. lei"},
            {"eticheta": "În depozite bancare",
             "valoare": f"{ro_num(g_pct['Depozite bancare'].iloc[-1], 1)}%",
             "nota": "partea ținută lichid, la bănci"},
            {"eticheta": "Variația ponderii titlurilor de stat, 12 luni",
             "valoare": f"{'+' if d_ts >= 0 else ''}{ro_num(d_ts, 1)} p.p.",
             "nota": f"față de {ro_luna(g_pct.index[idx12])}",
             "trend": "up" if d_ts >= 0 else "down"},
        ],
        "charts": [
            {"id": "c1", "type": "bar", "stacked": True,
             "titlu": "Cum s-a schimbat structura portofoliului în timp",
             "subtitlu": "Ponderea fiecărei clase de active în activul total, în procente. "
                         "Titlurile de stat au fost mereu coloana vertebrală a sistemului.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "zero": True, "xticks": 7,
             "series": [{"name": g, "data": clean(g_pct[g])} for g in ORDINE[:8]]},
            {"id": "c2", "type": "line",
             "titlu": "Titluri de stat față de acțiuni",
             "subtitlu": "Ponderea celor două clase principale. Acțiunile aduc randament mai mare "
                         "pe termen lung, dar și fluctuații mai mari.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": "Titluri de stat", "data": clean(ts)},
                        {"name": "Acțiuni", "data": clean(ac)}]},
            {"id": "c3", "type": "line",
             "titlu": "Valorile absolute ale principalelor plasamente",
             "subtitlu": "Miliarde de lei investiți pe fiecare clasă de active.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": g, "data": clean(g_val[g] / 1e9)} for g in princ]},
            {"id": "c4", "type": "bar", "stacked": True,
             "titlu": f"Politica de investiții a fiecărui fond, {ro_luna(per_max)}",
             "subtitlu": "Ponderea claselor de active în activul total al fiecărui fond, în procente.",
             "labels": fonduri, "unit": "%", "dec": 1, "ydec": 0, "zero": True,
             "xticks": len(fonduri),
             "series": [{"name": g, "data": clean(gf_pct[g])} for g in ORDINE[:8]]},
            {"id": "c5", "type": "line",
             "titlu": "Plasamentele mai mici, urmărite separat",
             "subtitlu": "Ponderi sub 10% din activ: depozite, obligațiuni corporative, "
                         "fonduri de investiții și obligațiuni municipale.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "zero": True,
             "series": [{"name": g, "data": clean(g_pct[g])} for g in
                        ["Depozite bancare", "Obligațiuni corporative",
                         "Fonduri de investiții (OPCVM și AOPC)", "Obligațiuni municipale"]]},
        ],
        "tabel": {
            "titlu": f"Structura lunară — ultimele 36 de luni ({len(g_pct)} luni în fișierul Excel)",
            "columns": ["Luna", "Activ total (mld. lei)"] + princ + ["Alte plasamente (%)"],
            "rows": [[ro_luna(p), ro_num(activ[p] / 1e9, 1)]
                     + [ro_num(g_pct[g][p], 1) for g in princ]
                     + [ro_num(g_pct["Alte plasamente (private equity, mărfuri, acoperirea riscului)"][p], 2)]
                     for p in g_pct.index[-36:][::-1]],
        },
        "note": [
            "Sursa: Autoritatea de Supraveghere Financiară, fișierul "
            "<code>p2-date_statistice.xlsx</code>, foaia <code>Table 6.</code> — structura "
            "investițiilor fondurilor de pensii administrate privat, raportată lunar.",
            "Banii din Pilonul II nu stau într-un cont bancar: sunt investiți, iar regulile de "
            "investire sunt fixate prin lege și supravegheate de ASF. Cea mai mare parte merge în "
            "<strong>titluri de stat</strong> — adică sunt împrumutați statului român, cu dobândă.",
            "<strong>Acțiunile</strong> sunt partea cu potențial de câștig mai mare, dar și cu "
            "fluctuații: valoarea lor urcă și coboară odată cu bursa.",
            "Ponderile sunt calculate de 24reco din valorile absolute raportate, împărțite la activul "
            "total al lunii respective. Suma lor poate depăși ușor 100%, pentru că poziția «alte sume, "
            "inclusiv în curs de decontare» este de regulă negativă.",
            "Un fond cu pondere mai mare în acțiuni are, de obicei, randamente mai bune în anii buni "
            "de bursă și mai slabe în anii de scădere — comparația corectă se face pe perioade lungi.",
            "Regenerare: <code>python3 scripts/financiara_05_02.py</code>.",
        ],
    }
    build_html(os.path.join(P.OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(lung)} obs., {len(g_pct)} luni, {per_min} → {per_max}, "
          f"titluri de stat {ts.iloc[-1]:.1f}%, acțiuni {ac.iloc[-1]:.1f}%, "
          f"activ total {activ.iloc[-1]/1e9:.1f} mld. lei")


if __name__ == "__main__":
    main()
