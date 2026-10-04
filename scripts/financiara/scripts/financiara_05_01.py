#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 05 01 — Pilonul II: participanți, active nete și contribuții
Sursa: ASF, `p2-date_statistice.xlsx` (Table 1., Table 4., Table 7.)
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

COD = "Financiara 05 01"
PAGINA = "https://data.asfromania.ro/pensii/p2-date_statistice.xlsx"


def culege() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    t1 = P.foaie("p2", "Table 1.")
    t4 = P.foaie("p2", "Table 4.")
    t7 = P.foaie("p2", "Table 7.")
    b1, b4, b7 = P.blocuri(t1), P.blocuri(t4), P.blocuri(t7)

    spec = [
        (t1, P.gaseste_bloc(b1, "Participanţi", "mii persoane"),
         "Participanți (mii persoane)"),
        (t4, P.gaseste_bloc(b4, "Activului Total"), "Activ total (mil. lei)"),
        (t4, P.gaseste_bloc(b4, "Activului Net", "mil.lei"), "Activ net (mil. lei)"),
        (t7, P.gaseste_bloc(b7, "Viramente contribuţii"),
         "Contribuții brute lunare (mil. lei)"),
        (t7, P.gaseste_bloc(b7, "Contribuţie  medie"),
         "Contribuție medie/participant (lei)"),
    ]
    bucati, wide = [], {}
    for df, bloc, eticheta in spec:
        bucati.append(P.bloc_lung(df, bloc, indicator=eticheta))
        wide[eticheta] = P.bloc_wide(df, bloc, exclude_total=True)
    lung = pd.concat(bucati, ignore_index=True)
    lung = lung.sort_values(["indicator", "perioada", "entitate"]).reset_index(drop=True)

    fail_if_short(lung, 8000, "ASF Pilon II (Table 1/4/7)")
    fail_if_stale(lung.perioada.max(), 4, "ASF Pilon II")
    return lung, wide


def main() -> None:
    lung, wide = culege()
    azi = dt.date.today().isoformat()

    tot = lung[lung.entitate.str.upper() == "TOTAL"].pivot_table(
        index="perioada", columns="indicator", values="valoare", aggfunc="last").sort_index()
    part = tot["Participanți (mii persoane)"]
    net = tot["Activ net (mil. lei)"]
    brut = tot["Activ total (mil. lei)"]
    contrib = tot["Contribuții brute lunare (mil. lei)"]
    contrib_med = tot["Contribuție medie/participant (lei)"]
    mediu = (net * 1_000_000) / (part * 1_000)  # lei per participant

    per_min, per_max = tot.index.min(), tot.index.max()
    fonduri_active = sorted(
        c for c in wide["Activ net (mil. lei)"].columns
        if pd.notna(wide["Activ net (mil. lei)"].loc[per_max, c])
    )

    # ---------------- foi de analiză ---------------------------------------
    a_total = pd.DataFrame({
        "Luna": tot.index,
        "Participanți (mii pers.)": part.round(3).values,
        "Activ net (mil. lei)": net.round(2).values,
        "Activ total (mil. lei)": brut.round(2).values,
        "Activ mediu/participant (lei)": mediu.round(0).values,
        "Contribuții brute lunare (mil. lei)": contrib.round(2).values,
        "Contribuție medie/participant (lei)": contrib_med.round(2).values,
        "Variație lunară activ net (%)": (net.pct_change() * 100).round(2).values,
        "Variație 12 luni activ net (%)": (net.pct_change(12) * 100).round(2).values,
        "Variație 12 luni participanți (%)": (part.pct_change(12) * 100).round(2).values,
    })

    a_net = wide["Activ net (mil. lei)"][fonduri_active].round(2).reset_index().rename(
        columns={"perioada": "Luna"})
    a_part = wide["Participanți (mii persoane)"][fonduri_active].round(3).reset_index().rename(
        columns={"perioada": "Luna"})

    wn, wp = wide["Activ net (mil. lei)"], wide["Participanți (mii persoane)"]
    wc = wide["Contribuții brute lunare (mil. lei)"]
    ultim = pd.DataFrame({
        "Fond de pensii": fonduri_active,
        "Participanți (mii pers.)": [wp.loc[per_max, f] for f in fonduri_active],
        "Cotă participanți (%)": [wp.loc[per_max, f] / part.loc[per_max] * 100
                                  for f in fonduri_active],
        "Activ net (mil. lei)": [wn.loc[per_max, f] for f in fonduri_active],
        "Cotă activ net (%)": [wn.loc[per_max, f] / net.loc[per_max] * 100
                               for f in fonduri_active],
        "Activ mediu/participant (lei)": [wn.loc[per_max, f] * 1e6 / (wp.loc[per_max, f] * 1e3)
                                          for f in fonduri_active],
        "Contribuții luna curentă (mil. lei)": [wc.loc[per_max, f] if f in wc.columns else None
                                                for f in fonduri_active],
        "Creștere activ net 12 luni (%)": [
            (wn.loc[per_max, f] / wn.iloc[-13][f] - 1) * 100
            if len(wn) > 13 and pd.notna(wn.iloc[-13].get(f)) else None
            for f in fonduri_active],
    }).sort_values("Activ net (mil. lei)", ascending=False).round(2).reset_index(drop=True)

    dec = tot[tot.index.str.endswith("-12")]
    dec_net = dec["Activ net (mil. lei)"]
    a_anual = pd.DataFrame({
        "An (situația la 31 decembrie)": [p[:4] for p in dec.index],
        "Participanți (mii pers.)": dec["Participanți (mii persoane)"].round(1).values,
        "Activ net (mil. lei)": dec_net.round(1).values,
        "Creștere activ net față de anul anterior (%)": (dec_net.pct_change() * 100).round(1).values,
        "Activ mediu/participant (lei)": (dec_net * 1e6 /
                                          (dec["Participanți (mii persoane)"] * 1e3)).round(0).values,
        "Contribuții încasate în decembrie (mil. lei)":
            dec["Contribuții brute lunare (mil. lei)"].round(1).values,
    })

    contrib_an = contrib.groupby(contrib.index.str[:4])
    a_contrib = pd.DataFrame({
        "An": contrib_an.sum().index,
        "Contribuții brute virate (mil. lei)": contrib_an.sum().round(1).values,
        "Luni raportate": contrib_an.count().values,
        "Medie lunară (mil. lei)": contrib_an.mean().round(1).values,
        "Contribuție medie/participant (lei, medie anuală)":
            contrib_med.groupby(contrib_med.index.str[:4]).mean().round(1).values,
    })

    ani = (int(per_max[:4]) - int(per_min[:4])) + (int(per_max[5:7]) - int(per_min[5:7])) / 12
    a_repere = pd.DataFrame({
        "Indicator": [
            "Activ net, ultima lună (mil. lei)",
            "Activ net, acum 12 luni (mil. lei)",
            "Creștere activ net în 12 luni (%)",
            "Participanți, ultima lună (mii pers.)",
            "Participanți, acum 12 luni (mii pers.)",
            "Activ mediu/participant, ultima lună (lei)",
            "Activ mediu/participant, acum 12 luni (lei)",
            "Contribuții brute, ultima lună (mil. lei)",
            "Creștere medie anuală a activului net de la start (% pe an)",
            "Total contribuții brute virate, întreaga perioadă (mil. lei)",
        ],
        "Valoare": [
            round(float(net.iloc[-1]), 2),
            round(float(net.iloc[-13]), 2) if len(net) > 13 else None,
            round(float(net.iloc[-1] / net.iloc[-13] - 1) * 100, 2) if len(net) > 13 else None,
            round(float(part.iloc[-1]), 1),
            round(float(part.iloc[-13]), 1) if len(part) > 13 else None,
            round(float(mediu.iloc[-1]), 0),
            round(float(mediu.iloc[-13]), 0) if len(mediu) > 13 else None,
            round(float(contrib.iloc[-1]), 2),
            round(P.cagr(float(net.iloc[0]), float(net.iloc[-1]), ani) or 0, 2),
            round(float(contrib.sum()), 1),
        ],
        "Referință": [ro_luna(per_max), ro_luna(tot.index[-13]) if len(net) > 13 else "—", "—",
                      ro_luna(per_max), ro_luna(tot.index[-13]) if len(part) > 13 else "—",
                      ro_luna(per_max), ro_luna(tot.index[-13]) if len(mediu) > 13 else "—",
                      ro_luna(per_max), f"{ro_luna(per_min)} – {ro_luna(per_max)}",
                      f"{ro_luna(per_min)} – {ro_luna(per_max)}"],
    })

    meta = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": "Pilonul II: participanți, active nete și contribuții",
        "subtitlu": "Câți români au cont de pensie privată obligatorie, câți bani s-au strâns "
                    "în total și cât revine, în medie, fiecărui participant.",
        "sursa": "Autoritatea de Supraveghere Financiară (ASF) — date statistice pensii private, Pilon II",
        "sursa_url": PAGINA,
        "cod_set": "p2-date_statistice.xlsx — Table 1. (participanți), Table 4. (active), "
                   "Table 7. (viramente contribuții)",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "participanți în mii de persoane; active și contribuții în milioane lei; "
                   "activ mediu și contribuție medie în lei/participant",
        "descarcat": azi,
        "licenta": P.LICENTA,
        "metodologie": "Datele sunt raportate lunar ASF de către administratorii fondurilor de "
                       "pensii administrate privat (Pilonul II) și publicate agregat pe fond. "
                       "Numărul de participanți este cel din Norma nr. 22/2009 (toate conturile "
                       "deschise, inclusiv cele fără contribuții în luna curentă). Activul net = "
                       "activul total minus obligațiile fondului; este valoarea care aparține "
                       "efectiv participanților. Activul mediu/participant este calculat de "
                       "24reco ca activ net total împărțit la numărul de participanți.",
        "script": "scripts/financiara_05_01.py",
        "note": [
            "Contribuțiile virate într-o lună corespund, de regulă, salariilor din luna precedentă "
            "sau de acum două luni (sursa indică explicit «luna de referință» pe rândul 3 al Table 7.).",
            "Fondurile dispărute din tabel (BANCPOST, EUREKO, KD, OMNIFORTE, OTP, PENSIA VIVA, "
            "PRIMA PENSIE) au fuzionat cu fonduri existente; coloanele lor rămân goale după fuziune.",
            "Fondurile apar în sursă cu denumirea fondului, nu a administratorului. Corespondența, conform listei publicate de APAPR (apapr.ro/utile): ARIPI — Generali, AZT VIITORUL TAU — Allianz-Țiriac, BCR — BCR, BRD — BRD, METROPOLITAN LIFE — Metropolitan Life, NN — NN, VITAL — Carpathia.",
            "Activul mediu/participant este o medie aritmetică pe tot sistemul: nu spune cât are un "
            "participant anume, pentru că soldul depinde de vechime, salariu și randamentul fondului.",
            "Cotele de piață sunt recalculate de 24reco din valorile absolute, pentru coerență cu "
            "restul foilor.",
        ],
        "avertismente": [
            "Fișierul ASF este actualizat IN-PLACE (același URL, istoricul în coloane), nu publicat "
            "lunar ca fișier separat — un downloader incremental trebuie să compare ultima coloană.",
            "Rapoartele rectificative transmise ulterior de administratori pot modifica retroactiv "
            "valori deja publicate (avertisment explicit în foaia Index a fișierului sursă).",
            "În foile ASF, numele fondurilor apar uneori cu majuscule inconsecvente sau cu asteriscuri "
            "de notă de subsol; aici sunt preluate exact din blocul citit.",
            "Paginile HTML de pe asfromania.ro sunt blocate de WAF; doar subdomeniul "
            "data.asfromania.ro răspunde la descărcări automate.",
        ],
    }

    build_excel(
        os.path.join(P.OUT, f"{COD}.xlsx"), meta=meta,
        date_df=lung.rename(columns={"perioada": "Luna", "entitate": "Fond de pensii",
                                     "indicator": "Indicator", "valoare": "Valoare"}),
        analize={
            "Total sistem lunar": a_total,
            "Activ net pe fond": a_net,
            "Participanți pe fond": a_part,
            "Clasament ultima lună": ultim,
            "Situația la fiecare 31 decembrie": a_anual,
            "Contribuții anuale": a_contrib,
            "Repere": a_repere,
        },
        note_analize={
            "Total sistem lunar": "Agregatul întregului Pilon II, lună de lună, cu ritmurile de creștere.",
            "Activ net pe fond": "Activul net în milioane lei, o coloană per fond activ în ultima lună.",
            "Participanți pe fond": "Numărul de participanți în mii de persoane, per fond.",
            "Clasament ultima lună": "Fotografia ultimei luni raportate: mărime, cotă de piață și creștere.",
            "Situația la fiecare 31 decembrie": "Serie anuală comparabilă (aceeași lună de referință).",
            "Contribuții anuale": "Suma contribuțiilor brute virate în fiecare an calendaristic.",
            "Repere": "Valorile-cheie folosite în pagina HTML.",
        },
        numfmt="#,##0.00")

    # ---------------- pagina HTML ------------------------------------------
    et = [ro_luna(p) for p in tot.index]
    top = list(ultim["Fond de pensii"].head(6))
    var12 = float(net.iloc[-1] / net.iloc[-13] - 1) * 100 if len(net) > 13 else None

    spec = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "ASF — date statistice Pilon II", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Active nete totale, {ro_luna(per_max)}",
             "valoare": f"{ro_num(net.iloc[-1] / 1000, 1)} mld. lei",
             "nota": "banii strânși de toate fondurile Pilon II"},
            {"eticheta": "Participanți",
             "valoare": f"{ro_num(part.iloc[-1] / 1000, 2)} mil.",
             "nota": "conturi deschise, conform Normei 22/2009"},
            {"eticheta": "Activ mediu per participant",
             "valoare": f"{ro_num(mediu.iloc[-1], 0)} lei",
             "nota": f"acum un an: {ro_num(mediu.iloc[-13], 0)} lei" if len(mediu) > 13 else ""},
            {"eticheta": "Creșterea activelor în 12 luni",
             "valoare": f"{'+' if (var12 or 0) >= 0 else ''}{ro_num(var12, 1)}%",
             "nota": f"contribuții virate în {ro_luna(per_max)}: "
                     f"{ro_num(contrib.iloc[-1], 0)} mil. lei",
             "trend": "up" if (var12 or 0) >= 0 else "down"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Activele nete ale Pilonului II",
             "subtitlu": "Totalul banilor administrați pentru participanți, în miliarde de lei.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0, "fill": True, "zero": True,
             "series": [{"name": "Activ net total", "data": clean(net / 1000)}]},
            {"id": "c2", "type": "line",
             "titlu": "Câți participanți are sistemul",
             "subtitlu": "Număr de conturi deschise, în milioane de persoane. "
                         "Creșterea vine din angajații nou intrați pe piața muncii.",
             "labels": et, "unit": "mil. pers.", "dec": 2, "ydec": 1,
             "series": [{"name": "Participanți", "data": clean(part / 1000)}]},
            {"id": "c3", "type": "line",
             "titlu": "Cât revine, în medie, unui participant",
             "subtitlu": "Activ net total împărțit la numărul de participanți, în lei. "
                         "Este o medie pe sistem, nu soldul unui cont anume.",
             "labels": et, "unit": "lei", "dec": 0, "ydec": 0, "fill": True, "zero": True,
             "series": [{"name": "Activ mediu/participant", "data": clean(mediu)}]},
            {"id": "c4", "type": "line",
             "titlu": "Cele mai mari fonduri, după activul net",
             "subtitlu": "Evoluția activelor nete pe fond, în miliarde de lei.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0,
             "series": [{"name": f, "data": clean(wn[f].reindex(tot.index) / 1000)} for f in top]},
            {"id": "c5", "type": "bar",
             "titlu": "Contribuții virate lunar în Pilonul II",
             "subtitlu": "Sumele transferate de angajatori din contribuția la pensie, "
                         "ultimele 60 de luni, în milioane de lei.",
             "labels": et[-60:], "unit": "mil. lei", "dec": 0, "ydec": 0, "zero": True,
             "series": [{"name": "Contribuții brute", "data": clean(contrib.tail(60))}]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(tot)} luni în fișierul Excel)",
            "columns": ["Luna", "Participanți (mii)", "Activ net (mld. lei)",
                        "Activ mediu/participant (lei)", "Contribuții (mil. lei)",
                        "Variație 12 luni activ net (%)"],
            "rows": [[ro_luna(p), ro_num(part[p], 1), ro_num(net[p] / 1000, 2),
                      ro_num(mediu[p], 0), ro_num(contrib[p], 1),
                      ro_num(net.pct_change(12)[p] * 100, 1)]
                     for p in tot.index[-36:][::-1]],
        },
        "note": [
            "Sursa: Autoritatea de Supraveghere Financiară, fișierul "
            "<code>p2-date_statistice.xlsx</code> — Table 1. (participanți), Table 4. (active), "
            "Table 7. (viramente contribuții).",
            "Pilonul II este pensia privată obligatorie: o parte din contribuția de asigurări "
            "sociale reținută din salariu merge automat într-un cont individual, la un fond ales "
            "de participant sau repartizat aleatoriu. Banii rămân ai participantului și se "
            "moștenesc.",
            "<strong>Activul net</strong> este suma care aparține participanților după scăderea "
            "obligațiilor fondului. Creșterea lui vine din două surse: contribuțiile noi virate "
            "lunar și randamentul investițiilor.",
            "Numărul de participanți include și conturile fără contribuții recente (persoane "
            "ieșite temporar din piața muncii), deci nu este identic cu numărul de salariați activi.",
            "În tabele, fondurile apar cu denumirea fondului, nu a administratorului. "
            "Corespondența, conform APAPR: ARIPI — Generali, AZT VIITORUL TAU — Allianz-Țiriac, "
            "BCR — BCR, BRD — BRD, METROPOLITAN LIFE — Metropolitan Life, NN — NN, VITAL — Carpathia.",
            "Contribuțiile virate într-o lună corespund, în general, veniturilor din lunile "
            "anterioare — fișierul sursă precizează luna de referință pentru fiecare coloană.",
            "Valorile pot fi revizuite retroactiv dacă administratorii transmit raportări "
            "rectificative; ASF avertizează explicit asupra acestui lucru.",
            "Regenerare: <code>python3 scripts/financiara_05_01.py</code>.",
        ],
    }
    build_html(os.path.join(P.OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(lung)} obs., {len(tot)} luni, {per_min} → {per_max}, "
          f"activ net {net.iloc[-1]:,.0f} mil. lei, participanți {part.iloc[-1]:,.0f} mii")


if __name__ == "__main__":
    main()
