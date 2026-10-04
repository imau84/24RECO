#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 05 04 — Pilonul III (pensii facultative): participanți, active, randamente
Sursa: ASF, `p3-date_statistice.xlsx` (Table 1., 2., 3., 5., 9.) + `p2-date_statistice.xlsx`
       (Table 1., Table 4.) pentru comparația cu Pilonul II.
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

COD = "Financiara 05 04"
PAGINA = "https://data.asfromania.ro/pensii/p3-date_statistice.xlsx"
PAGINA_P2 = "https://data.asfromania.ro/pensii/p2-date_statistice.xlsx"


def culege():
    t1, t2, t3 = P.foaie("p3", "Table 1."), P.foaie("p3", "Table 2."), P.foaie("p3", "Table 3.")
    t5, t9 = P.foaie("p3", "Table 5."), P.foaie("p3", "Table 9.")
    b1, b2, b3, b5, b9 = (P.blocuri(x) for x in (t1, t2, t3, t5, t9))

    spec = [
        (t1, P.gaseste_bloc(b1, "Participanti", "persoane"), "Participanți (persoane)"),
        (t2, P.gaseste_bloc(b2, "Activului Total"), "Activ total (mil. lei)"),
        (t2, P.gaseste_bloc(b2, "Activului Net"), "Activ net (mil. lei)"),
        (t3, P.gaseste_bloc(b3, "Valoarea Unitară a Activului Net"), "VUAN (lei)"),
        (t5, P.gaseste_bloc(b5, "Viramente contribuţii"), "Contribuții brute lunare (lei)"),
        (t5, P.gaseste_bloc(b5, "Contribuţie  medie"), "Contribuție medie/participant (lei)"),
    ]
    bucati, wide = [], {}
    for df, bloc, eticheta in spec:
        bucati.append(P.bloc_lung(df, bloc, indicator=eticheta))
        wide[eticheta] = P.bloc_wide(df, bloc, exclude_total=True)

    rid = P.gaseste_bloc(b9, "high risk")
    med = P.gaseste_bloc(b9, "medium risk")
    risc = {f: "Ridicat" for f, _ in rid["randuri"]}
    risc.update({f: "Mediu" for f, _ in med["randuri"] if f not in risc})
    rate = pd.concat([P.bloc_wide(t9, rid) * 100, P.bloc_wide(t9, med) * 100], axis=1).sort_index()
    rate = rate.loc[:, ~rate.columns.duplicated()]
    bucati.append(P.bloc_lung(t9, rid, indicator="Rată de rentabilitate anualizată, risc ridicat (fracție)"))
    bucati.append(P.bloc_lung(t9, med, indicator="Rată de rentabilitate anualizată, risc mediu (fracție)"))

    lung = pd.concat(bucati, ignore_index=True).sort_values(
        ["indicator", "perioada", "entitate"]).reset_index(drop=True)
    fail_if_short(lung, 8000, "ASF Pilon III (Table 1/2/3/5/9)")
    fail_if_stale(lung.perioada.max(), 4, "ASF Pilon III")

    # --- Pilonul II, pentru comparație -------------------------------------
    p2_1, p2_4 = P.foaie("p2", "Table 1."), P.foaie("p2", "Table 4.")
    p2_part = P.bloc_lung(p2_1, P.gaseste_bloc(P.blocuri(p2_1), "Participanţi", "mii persoane"),
                          indicator="x")
    p2_net = P.bloc_lung(p2_4, P.gaseste_bloc(P.blocuri(p2_4), "Activului Net", "mil.lei"),
                         indicator="x")
    p2 = pd.DataFrame({
        "Participanți Pilon II (persoane)":
            p2_part[p2_part.entitate.str.upper() == "TOTAL"].set_index("perioada")["valoare"] * 1000,
        "Activ net Pilon II (mil. lei)":
            p2_net[p2_net.entitate.str.upper() == "TOTAL"].set_index("perioada")["valoare"],
    }).sort_index()
    return lung, wide, rate, risc, p2


def main() -> None:
    lung, wide, rate, risc, p2 = culege()
    azi = dt.date.today().isoformat()

    tot = lung[lung.entitate.str.upper() == "TOTAL"].pivot_table(
        index="perioada", columns="indicator", values="valoare", aggfunc="last").sort_index()
    part = tot["Participanți (persoane)"]
    net = tot["Activ net (mil. lei)"]
    contrib = tot["Contribuții brute lunare (lei)"]
    contrib_med = tot["Contribuție medie/participant (lei)"]
    mediu = net * 1e6 / part
    per_min, per_max = tot.index.min(), tot.index.max()

    wn, wp = wide["Activ net (mil. lei)"], wide["Participanți (persoane)"]
    wv, wc = wide["VUAN (lei)"], wide["Contribuții brute lunare (lei)"]
    active = [f for f in wn.columns if pd.notna(wn.loc[per_max, f])]

    # ---------------- foi de analiză ---------------------------------------
    a_total = pd.DataFrame({
        "Luna": tot.index,
        "Participanți (persoane)": part.round(0).values,
        "Activ net (mil. lei)": net.round(2).values,
        "Activ mediu/participant (lei)": mediu.round(0).values,
        "Contribuții brute lunare (lei)": contrib.round(0).values,
        "Contribuție medie/participant (lei)": contrib_med.round(2).values,
        "Variație 12 luni activ net (%)": (net.pct_change(12) * 100).round(2).values,
        "Variație 12 luni participanți (%)": (part.pct_change(12) * 100).round(2).values,
    })

    a_net = wn[active].round(2).reset_index().rename(columns={"perioada": "Luna"})
    a_part = wp[active].round(0).reset_index().rename(columns={"perioada": "Luna"})
    a_vuan = wv[[f for f in wv.columns if f in active]].round(4).reset_index().rename(
        columns={"perioada": "Luna"})

    start = {f: wv[f].dropna() for f in active if f in wv.columns}
    a_clasament = pd.DataFrame({
        "Fond de pensii facultative": active,
        "Grad de risc (ASF)": [risc.get(f, "—") for f in active],
        "Participanți": [wp.loc[per_max, f] for f in active],
        "Cotă participanți (%)": [wp.loc[per_max, f] / part.loc[per_max] * 100 for f in active],
        "Activ net (mil. lei)": [wn.loc[per_max, f] for f in active],
        "Cotă activ net (%)": [wn.loc[per_max, f] / net.loc[per_max] * 100 for f in active],
        "Activ mediu/participant (lei)": [wn.loc[per_max, f] * 1e6 / wp.loc[per_max, f]
                                          for f in active],
        "Contribuții luna curentă (lei)": [wc.loc[per_max, f] if f in wc.columns else None
                                           for f in active],
        f"VUAN {ro_luna(per_max)} (lei)": [wv.loc[per_max, f] if f in wv.columns else None
                                           for f in active],
        "Randament mediu anual de la lansare (%)": [
            P.cagr(float(start[f].iloc[0]), float(start[f].iloc[-1]), len(start[f]) / 12)
            if f in start and len(start[f]) > 12 else None for f in active],
        "Creștere VUAN 12 luni (%)": [
            (wv[f].iloc[-1] / wv[f].iloc[-13] - 1) * 100
            if f in wv.columns and len(wv) > 13 and pd.notna(wv[f].iloc[-13]) else None
            for f in active],
        "Rata de rentabilitate ASF (%)": [rate[f].iloc[-1] if f in rate.columns else None
                                          for f in active],
    }).sort_values("Activ net (mil. lei)", ascending=False).round(2).reset_index(drop=True)

    cmp_idx = [p for p in tot.index if p in p2.index]
    c_part2 = p2.loc[cmp_idx, "Participanți Pilon II (persoane)"]
    c_net2 = p2.loc[cmp_idx, "Activ net Pilon II (mil. lei)"]
    a_cmp = pd.DataFrame({
        "Luna": cmp_idx,
        "Participanți Pilon III": part.loc[cmp_idx].round(0).values,
        "Participanți Pilon II": c_part2.round(0).values,
        "Participanți III / II (%)": (part.loc[cmp_idx] / c_part2 * 100).round(2).values,
        "Activ net Pilon III (mil. lei)": net.loc[cmp_idx].round(1).values,
        "Activ net Pilon II (mil. lei)": c_net2.round(1).values,
        "Activ net III / II (%)": (net.loc[cmp_idx] / c_net2 * 100).round(2).values,
        "Activ mediu/participant, Pilon III (lei)": mediu.loc[cmp_idx].round(0).values,
        "Activ mediu/participant, Pilon II (lei)": (c_net2 * 1e6 / c_part2).round(0).values,
    })

    dec = tot[tot.index.str.endswith("-12")]
    a_anual = pd.DataFrame({
        "An (situația la 31 decembrie)": [p[:4] for p in dec.index],
        "Participanți": dec["Participanți (persoane)"].round(0).values,
        "Activ net (mil. lei)": dec["Activ net (mil. lei)"].round(1).values,
        "Creștere activ net (%)": (dec["Activ net (mil. lei)"].pct_change() * 100).round(1).values,
        "Activ mediu/participant (lei)": (dec["Activ net (mil. lei)"] * 1e6 /
                                          dec["Participanți (persoane)"]).round(0).values,
    })

    contrib_an = contrib.groupby(contrib.index.str[:4])
    a_contrib = pd.DataFrame({
        "An": contrib_an.sum().index,
        "Contribuții brute virate (mil. lei)": (contrib_an.sum() / 1e6).round(2).values,
        "Luni raportate": contrib_an.count().values,
        "Medie lunară (mil. lei)": (contrib_an.mean() / 1e6).round(2).values,
        "Contribuție medie/participant (lei, medie anuală)":
            contrib_med.groupby(contrib_med.index.str[:4]).mean().round(1).values,
    })

    a_rate = rate.round(3).reset_index().rename(columns={"perioada": "Luna"})

    meta = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": "Pilonul III: pensiile facultative, în cifre",
        "subtitlu": "Cei care pun bani deoparte în plus, pe lângă pensia obligatorie: câți sunt, "
                    "cât au strâns și cum se compară cu Pilonul II.",
        "sursa": "Autoritatea de Supraveghere Financiară (ASF) — date statistice pensii private, "
                 "Pilon III (și Pilon II pentru comparație)",
        "sursa_url": PAGINA,
        "cod_set": "p3-date_statistice.xlsx — Table 1. (participanți), Table 2. (active), "
                   "Table 3. (VUAN), Table 5. (viramente), Table 9. (rate de rentabilitate); "
                   "p2-date_statistice.xlsx — Table 1. și Table 4. pentru comparație",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "participanți în persoane; active în milioane lei; contribuții în lei; "
                   "VUAN în lei/unitate; randamente în procente pe an",
        "descarcat": azi,
        "licenta": P.LICENTA,
        "metodologie": "Pilonul III este pensia privată facultativă: contribuții voluntare, plătite "
                       "de participant sau de angajator, deductibile fiscal în limita a 400 de euro "
                       "pe an pentru fiecare dintre cei doi. Datele sunt raportate lunar ASF de "
                       "administratori. Activul mediu/participant, cotele de piață, randamentele "
                       "anualizate din VUAN și raportul cu Pilonul II sunt calculate de 24reco din "
                       "valorile absolute publicate.",
        "script": "scripts/financiara_05_04.py",
        "note": [
            "Spre deosebire de Pilonul II, la Pilonul III aceeași persoană poate avea conturi la mai "
            "multe fonduri, iar numărul de participanți raportat este pe fond — totalul poate "
            "conține dublări.",
            "Contribuția nu este fixă: fiecare participant decide suma, în limita a 15% din venitul "
            "brut. De aceea contribuția medie lunară variază mult mai mult decât la Pilonul II.",
            "Fondurile au grade de risc diferite (ridicat, mediu, iar până în 2011 și scăzut), deci "
            "randamentele nu sunt direct comparabile între ele fără a ține cont de risc.",
            "Comparația cu Pilonul II folosește totalurile din p2-date_statistice.xlsx pentru "
            "aceleași luni; participanții Pilon II sunt convertiți din mii de persoane în persoane.",
        ],
        "avertismente": [
            "În foaia Table 5., prima coloană este agregatul «2007-2010», nu o lună — trebuie "
            "ignorată; parserul acceptă doar coloanele cu dată calendaristică reală.",
            "Ratele de rentabilitate din Table 9. sunt stocate ca fracții subunitare (0,10 = 10%).",
            "Blocul fondurilor cu grad de risc scăzut se oprește în noiembrie 2011 și nu mai este "
            "actualizat.",
            "Fișierul ASF este actualizat in-place; valorile pot fi rectificate retroactiv.",
        ],
    }

    build_excel(
        os.path.join(P.OUT, f"{COD}.xlsx"), meta=meta,
        date_df=lung.rename(columns={"perioada": "Luna", "entitate": "Fond de pensii facultative",
                                     "indicator": "Indicator", "valoare": "Valoare"}),
        analize={
            "Total sistem lunar": a_total,
            "Activ net pe fond": a_net,
            "Participanți pe fond": a_part,
            "VUAN pe fond": a_vuan,
            "Clasament ultima lună": a_clasament,
            "Pilon III față de Pilon II": a_cmp,
            "Situația la 31 decembrie": a_anual,
            "Contribuții anuale": a_contrib,
            "Rate de rentabilitate ASF (%)": a_rate,
        },
        note_analize={
            "Total sistem lunar": "Agregatul Pilonului III, lună de lună.",
            "Activ net pe fond": "Activul net în milioane lei, per fond activ.",
            "Participanți pe fond": "Număr de participanți, per fond activ.",
            "VUAN pe fond": "Valoarea unitară a activului net, în lei.",
            "Clasament ultima lună": "Mărime, cotă de piață și randamente, în ultima lună raportată.",
            "Pilon III față de Pilon II": "Cât de mic este sistemul facultativ față de cel obligatoriu.",
            "Situația la 31 decembrie": "Serie anuală comparabilă.",
            "Contribuții anuale": "Suma contribuțiilor voluntare virate în fiecare an.",
            "Rate de rentabilitate ASF (%)": "Rata anualizată calculată de ASF (fereastră de 60 de luni din 2020).",
        },
        numfmt="#,##0.00")

    # ---------------- pagina HTML ------------------------------------------
    et = [ro_luna(p) for p in tot.index]
    top = list(a_clasament["Fond de pensii facultative"].head(6))
    var12 = float(net.iloc[-1] / net.iloc[-13] - 1) * 100 if len(net) > 13 else None
    cmp_et = [ro_luna(p) for p in cmp_idx]
    pond = float(net.loc[per_max] / (net.loc[per_max] + c_net2.loc[per_max]) * 100)

    spec = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "ASF — date statistice Pilon III", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Active nete, {ro_luna(per_max)}",
             "valoare": f"{ro_num(net.iloc[-1] / 1000, 2)} mld. lei",
             "nota": f"{ro_num(pond, 1)}% din tot ce administrează pensiile private"},
            {"eticheta": "Participanți",
             "valoare": f"{ro_num(part.iloc[-1] / 1000, 0)} mii",
             "nota": f"față de {ro_num(c_part2.loc[per_max] / 1e6, 2)} mil. la Pilonul II"},
            {"eticheta": "Activ mediu per participant",
             "valoare": f"{ro_num(mediu.iloc[-1], 0)} lei",
             "nota": f"la Pilonul II: {ro_num(c_net2.loc[per_max] * 1e6 / c_part2.loc[per_max], 0)} lei"},
            {"eticheta": "Creșterea activelor în 12 luni",
             "valoare": f"{'+' if (var12 or 0) >= 0 else ''}{ro_num(var12, 1)}%",
             "nota": f"contribuții în {ro_luna(per_max)}: {ro_num(contrib.iloc[-1] / 1e6, 1)} mil. lei",
             "trend": "up" if (var12 or 0) >= 0 else "down"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Activele nete ale Pilonului III",
             "subtitlu": "Totalul economisit voluntar pentru pensie, în miliarde de lei.",
             "labels": et, "unit": "mld. lei", "dec": 2, "ydec": 1, "fill": True, "zero": True,
             "series": [{"name": "Activ net total", "data": clean(net / 1000)}]},
            {"id": "c2", "type": "line",
             "titlu": "Câți români contribuie voluntar",
             "subtitlu": "Număr de participanți, în mii de persoane. O persoană poate avea conturi "
                         "la mai multe fonduri.",
             "labels": et, "unit": "mii pers.", "dec": 0, "ydec": 0, "zero": True,
             "series": [{"name": "Participanți", "data": clean(part / 1000)}]},
            {"id": "c3", "type": "line",
             "titlu": "Cât are, în medie, un participant — Pilonul III față de Pilonul II",
             "subtitlu": "Activ net împărțit la numărul de participanți, în lei. La Pilonul III "
                         "soldul mediu e mai mare, pentru că participanții sunt mai puțini și "
                         "contribuie mai mult.",
             "labels": cmp_et, "unit": "lei", "dec": 0, "ydec": 0, "zero": True,
             "series": [{"name": "Pilonul III (facultativ)", "data": clean(mediu.loc[cmp_idx])},
                        {"name": "Pilonul II (obligatoriu)",
                         "data": clean(c_net2 * 1e6 / c_part2)}]},
            {"id": "c4", "type": "line",
             "titlu": "Valoarea unității de fond, pe fiecare fond facultativ",
             "subtitlu": "Toate fondurile au pornit de la 10 lei. Graficul arată cât valorează azi.",
             "labels": et, "unit": "lei", "dec": 2, "ydec": 0, "zero": True,
             "series": [{"name": f, "data": clean(wv[f].reindex(tot.index))}
                        for f in top if f in wv.columns]},
            {"id": "c5", "type": "bar",
             "titlu": "Contribuții voluntare virate lunar",
             "subtitlu": "Ultimele 60 de luni, în milioane de lei.",
             "labels": et[-60:], "unit": "mil. lei", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": "Contribuții brute", "data": clean(contrib.tail(60) / 1e6)}]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(tot)} luni în fișierul Excel)",
            "columns": ["Luna", "Participanți", "Activ net (mil. lei)",
                        "Activ mediu/participant (lei)", "Contribuții (mil. lei)",
                        "Contribuție medie (lei)"],
            "rows": [[ro_luna(p), ro_num(part[p], 0), ro_num(net[p], 1), ro_num(mediu[p], 0),
                      ro_num(contrib[p] / 1e6, 1), ro_num(contrib_med[p], 0)]
                     for p in tot.index[-36:][::-1]],
        },
        "note": [
            "Sursa: Autoritatea de Supraveghere Financiară, fișierul "
            "<code>p3-date_statistice.xlsx</code> (Table 1., 2., 3., 5., 9.). Comparația cu "
            "Pilonul II folosește <code>p2-date_statistice.xlsx</code> (Table 1. și Table 4.).",
            "<strong>Pilonul III</strong> este pensia facultativă: bani puși deoparte în plus, din "
            "proprie inițiativă sau prin angajator. Contribuția este deductibilă fiscal în limita a "
            "400 de euro pe an pentru participant și încă 400 de euro pentru angajator.",
            "Spre deosebire de Pilonul II, aici nimeni nu e înscris automat — de aceea sistemul are "
            "de aproape opt ori mai puțini participanți, dar un sold mediu pe cont mai mare.",
            "Aceeași persoană poate avea conturi la mai multe fonduri facultative, deci totalul "
            "participanților poate conține dublări.",
            "Banii se pot retrage, de regulă, de la 60 de ani; retragerea anticipată e posibilă doar "
            "în cazuri limitate (invaliditate, deces — către moștenitori).",
            "Randamentele sunt nete de comisioanele de administrare și nominale (neajustate cu "
            "inflația).",
            "Regenerare: <code>python3 scripts/financiara_05_04.py</code>.",
        ],
    }
    build_html(os.path.join(P.OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(lung)} obs., {len(tot)} luni, {per_min} → {per_max}, "
          f"activ net {net.iloc[-1]:,.0f} mil. lei, participanți {part.iloc[-1]:,.0f}, "
          f"{pond:.1f}% din pensiile private")


if __name__ == "__main__":
    main()
