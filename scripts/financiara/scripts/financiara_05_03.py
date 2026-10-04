#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 05 03 — Pilonul II: valoarea unității de fond (VUAN) și randamentele
Sursa: ASF, `p2-date_statistice.xlsx` (Table 5. — VUAN; Table 15. — rate de rentabilitate)
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

COD = "Financiara 05 03"
PAGINA = "https://data.asfromania.ro/pensii/p2-date_statistice.xlsx"


def culege() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    t5 = P.foaie("p2", "Table 5.")
    t15 = P.foaie("p2", "Table 15.")
    b5, b15 = P.blocuri(t5), P.blocuri(t15)

    vuan_b = P.gaseste_bloc(b5, "Valoarea Unitară a Activului Net")
    vuan = P.bloc_wide(t5, vuan_b)

    rid = P.gaseste_bloc(b15, "Rata de rentabilitate anualizata", "ridicat")
    med = P.gaseste_bloc(b15, "Rata de rentabilitate anualizata", "risc mediu")
    risc = {f: "Ridicat" for f, _ in rid["randuri"]}
    risc.update({f: "Mediu" for f, _ in med["randuri"]})
    rate = pd.concat([P.bloc_wide(t15, rid) * 100, P.bloc_wide(t15, med) * 100], axis=1)
    rate = rate.sort_index()

    ind = pd.concat([P.bloc_wide(t15, P.gaseste_bloc(b15, "Indicatori de referinţă", "ridicat")),
                     P.bloc_wide(t15, P.gaseste_bloc(b15, "Indicatori de referinţă", "risc mediu")),
                     P.bloc_wide(t15, P.gaseste_bloc(b15, "Indicatori de referinţă",
                                                     "toate fondurile"))], axis=1) * 100
    ind = ind.sort_index()

    lung = pd.concat([
        P.bloc_lung(t5, vuan_b, indicator="VUAN (lei)"),
        P.bloc_lung(t15, rid, indicator="Rată de rentabilitate anualizată, risc ridicat (fracție)"),
        P.bloc_lung(t15, med, indicator="Rată de rentabilitate anualizată, risc mediu (fracție)"),
    ], ignore_index=True).sort_values(["indicator", "perioada", "entitate"]).reset_index(drop=True)

    fail_if_short(lung, 2800, "ASF Pilon II (Table 5. + Table 15.)")
    fail_if_stale(vuan.index.max(), 4, "ASF Pilon II VUAN")
    return lung, vuan, rate, ind, risc


def main() -> None:
    lung, vuan, rate, ind, risc = culege()
    azi = dt.date.today().isoformat()
    per_min, per_max = vuan.index.min(), vuan.index.max()
    active = [f for f in vuan.columns if pd.notna(vuan.loc[per_max, f])]
    v = vuan[active]

    # ---------------- foi de analiză ---------------------------------------
    a_vuan = v.round(4).reset_index().rename(columns={"perioada": "Luna"})

    cr12 = (v.pct_change(12) * 100).round(2)
    a_cr12 = cr12.reset_index().rename(columns={"perioada": "Luna"})

    a_rate = rate.round(3).reset_index().rename(columns={"perioada": "Luna"})
    a_ind = ind.round(3).reset_index().rename(columns={"perioada": "Luna"})
    a_ind.columns = ["Luna"] + [c.split("(")[0].strip() for c in a_ind.columns[1:]]

    def de_acum(f: str, luni: int):
        if len(v) <= luni or pd.isna(v[f].iloc[-1 - luni]):
            return None
        return P.cagr(float(v[f].iloc[-1 - luni]), float(v[f].iloc[-1]), luni / 12)

    start = {f: v[f].dropna() for f in active}
    a_clasament = pd.DataFrame({
        "Fond de pensii": active,
        "Grad de risc (ASF)": [risc.get(f, "—") for f in active],
        f"VUAN {ro_luna(per_max)} (lei)": [v[f].iloc[-1] for f in active],
        "Creștere 12 luni (%)": [cr12[f].iloc[-1] for f in active],
        "Randament mediu anual, 3 ani (%)": [de_acum(f, 36) for f in active],
        "Randament mediu anual, 5 ani (%)": [de_acum(f, 60) for f in active],
        "Randament mediu anual, 10 ani (%)": [de_acum(f, 120) for f in active],
        "Randament mediu anual de la lansare (%)": [
            P.cagr(float(start[f].iloc[0]), float(start[f].iloc[-1]), len(start[f]) / 12)
            for f in active],
        "Prima lună raportată": [start[f].index.min() for f in active],
        "Valoarea a 10 lei investiți la lansare (lei)": [
            10 * float(start[f].iloc[-1]) / float(start[f].iloc[0]) for f in active],
        "Rata de rentabilitate anualizată raportată de ASF (%)": [
            rate[f].iloc[-1] if f in rate.columns else None for f in active],
    }).sort_values("Randament mediu anual de la lansare (%)", ascending=False).round(2)
    a_clasament = a_clasament.reset_index(drop=True)

    dec = v[v.index.str.endswith("-12")]
    an_randament = (dec.pct_change() * 100).round(2)
    a_anual = an_randament.reset_index()
    a_anual["perioada"] = [p[:4] for p in dec.index]
    a_anual = a_anual.rename(columns={"perioada": "An calendaristic"})
    a_anual["Medie simplă a fondurilor (%)"] = an_randament.mean(axis=1).round(2).values

    a_vol = pd.DataFrame({
        "Fond de pensii": active,
        "Cea mai bună creștere pe 12 luni (%)": [cr12[f].max() for f in active],
        "Luna": [cr12[f].idxmax() if cr12[f].notna().any() else None for f in active],
        "Cea mai slabă creștere pe 12 luni (%)": [cr12[f].min() for f in active],
        "Luna ": [cr12[f].idxmin() if cr12[f].notna().any() else None for f in active],
        "Luni cu scădere pe 12 luni": [int((cr12[f] < 0).sum()) for f in active],
        "Luni raportate": [int(cr12[f].notna().sum()) for f in active],
        "Abaterea standard a creșterii pe 12 luni (p.p.)": [cr12[f].std() for f in active],
    }).round(2)

    sistem = ind.columns[-1]
    a_sistem = pd.DataFrame({
        "Luna": ind.index,
        "Rata medie ponderată a tuturor fondurilor (%)": ind[sistem].round(3).values,
        "Creștere medie simplă a VUAN pe 12 luni (%)": cr12.mean(axis=1).reindex(ind.index).round(2).values,
        "Cel mai mare VUAN (lei)": v.max(axis=1).reindex(ind.index).round(3).values,
        "Cel mai mic VUAN (lei)": v.min(axis=1).reindex(ind.index).round(3).values,
    })

    meta = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": "Pilonul II: cât au crescut banii din pensia privată obligatorie",
        "subtitlu": "Cât a crescut, de la lansarea sistemului în 2008, fiecare leu pus deoparte în "
                    "pensia privată obligatorie — pe fiecare fond în parte.",
        "sursa": "Autoritatea de Supraveghere Financiară (ASF) — date statistice pensii private, Pilon II",
        "sursa_url": PAGINA,
        "cod_set": "p2-date_statistice.xlsx — Table 5. (Valoarea Unitară a Activului Net), "
                   "Table 15. (Rata de rentabilitate și indicatori de referință)",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max}",
        "unitate": "VUAN în lei/unitate de fond; randamente în procente pe an",
        "descarcat": azi,
        "licenta": P.LICENTA,
        "metodologie": "VUAN (valoarea unitară a activului net) este prețul unei unități de fond în "
                       "ultima zi lucrătoare a lunii; toate fondurile au pornit de la 10 lei la "
                       "lansare, deci evoluția VUAN arată direct cât a crescut un leu investit. "
                       "Rata de rentabilitate din Table 15. este calculată de ASF ca rentabilitate "
                       "anualizată pe o fereastră mobilă: începând din 2020 fereastra este de 60 de "
                       "luni, iar înainte era de 24 de luni — verificat prin reproducerea exactă a "
                       "valorilor raportate din seria VUAN. În sursă este raportată ca fracție "
                       "(0,10 = 10%); aici este convertită în procente. "
                       "Randamentele medii anuale pe 3, 5, 10 ani și de la lansare sunt "
                       "calculate de 24reco din VUAN, ca rată compusă anualizată (CAGR).",
        "script": "scripts/financiara_05_03.py",
        "note": [
            "VUAN este net de comisioanele de administrare: randamentul afișat este cel care ajunge "
            "efectiv la participant.",
            "Randamentul din VUAN nu ia în calcul momentul contribuțiilor. Un participant care a "
            "contribuit lunar are un randament personal diferit de creșterea VUAN pe aceeași "
            "perioadă.",
            "Gradul de risc (ridicat/mediu) este atribuit de ASF conform Normei nr. 19/2012 și "
            "determină rata minimă de rentabilitate pe care fondul trebuie să o depășească.",
            "Randamentele sunt nominale (nu sunt ajustate cu inflația).",
        ],
        "avertismente": [
            "Rata de rentabilitate din Table 15. este stocată ca fracție subunitară, nu ca procent — "
            "o citire directă fără înmulțirea cu 100 dă valori de 100 de ori mai mici.",
            "Fondurile fuzionate (BANCPOST, EUREKO, KD, OMNIFORTE, OTP, PENSIA VIVA, PRIMA PENSIE) "
            "au serii VUAN care se opresc la data fuziunii; nu sunt incluse în clasamente.",
            "Randamentul trecut nu garantează randamentul viitor — comparațiile pe perioade scurte "
            "(sub 3 ani) sunt puternic influențate de momentul ales.",
            "Fișierul ASF se actualizează in-place, pe același URL; valorile deja publicate pot fi "
            "rectificate retroactiv.",
        ],
    }

    build_excel(
        os.path.join(P.OUT, f"{COD}.xlsx"), meta=meta,
        date_df=lung.rename(columns={"perioada": "Luna", "entitate": "Fond de pensii",
                                     "indicator": "Indicator", "valoare": "Valoare"}),
        analize={
            "VUAN lunar pe fond": a_vuan,
            "Creștere VUAN pe 12 luni (%)": a_cr12,
            "Clasamentul fondurilor": a_clasament,
            "Randament pe an calendaristic (%)": a_anual,
            "Rate de rentabilitate ASF (%)": a_rate,
            "Indicatori de referință ASF (%)": a_ind,
            "Volatilitate și extreme": a_vol,
            "Sistemul în ansamblu": a_sistem,
        },
        note_analize={
            "VUAN lunar pe fond": "Prețul unei unități de fond, în lei, la finalul fiecărei luni.",
            "Creștere VUAN pe 12 luni (%)": "Randamentul pe ultimele 12 luni, calculat din VUAN.",
            "Clasamentul fondurilor": "Randamente medii anuale pe mai multe orizonturi și "
                                      "valoarea actuală a 10 lei investiți la lansarea fondului.",
            "Randament pe an calendaristic (%)": "Creșterea VUAN de la 31 decembrie la 31 decembrie.",
            "Rate de rentabilitate ASF (%)": "Rata anualizată calculată de ASF (fereastră de 60 de luni din 2020).",
            "Indicatori de referință ASF (%)": "Rata minimă pe categorie de risc și rata medie "
                                               "ponderată a întregului sistem.",
            "Volatilitate și extreme": "Cât de mult variază randamentul pe 12 luni al fiecărui fond.",
            "Sistemul în ansamblu": "Indicatorii agregați, lună de lună.",
        },
        numfmt="#,##0.00")

    # ---------------- pagina HTML ------------------------------------------
    et = [ro_luna(p) for p in v.index]
    top = list(a_clasament["Fond de pensii"])
    lider = a_clasament.iloc[0]
    med_cagr = a_clasament["Randament mediu anual de la lansare (%)"].mean()
    inm = a_clasament["Valoarea a 10 lei investiți la lansare (lei)"]

    spec = {
        "cod": COD, "sectiune": P.SECTIUNE,
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "ASF — date statistice Pilon II, Table 5. și Table 15.", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": "Randament mediu anual de la lansare",
             "valoare": f"{ro_num(med_cagr, 1)}%",
             "nota": "media celor "
                     f"{len(active)} fonduri active, după comisioane"},
            {"eticheta": "10 lei investiți în 2008 valorează azi",
             "valoare": f"{ro_num(inm.mean(), 0)} lei",
             "nota": f"între {ro_num(inm.min(), 0)} și {ro_num(inm.max(), 0)} lei, după fond"},
            {"eticheta": f"Creșterea VUAN în ultimele 12 luni",
             "valoare": f"{ro_num(cr12.mean(axis=1).iloc[-1], 1)}%",
             "nota": f"media fondurilor, până în {ro_luna(per_max)}",
             "trend": "up" if cr12.mean(axis=1).iloc[-1] >= 0 else "down"},
            {"eticheta": "Rata medie ponderată raportată de ASF",
             "valoare": f"{ro_num(ind[sistem].iloc[-1], 1)}%",
             "nota": "randament anualizat pe ultimii 5 ani"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Valoarea unei unități de fond, pe fiecare fond",
             "subtitlu": "Toate fondurile au pornit de la 10 lei în 2008. Graficul arată în cât "
                         "s-a transformat, până azi, fiecare 10 lei.",
             "labels": et, "unit": "lei", "dec": 2, "ydec": 0, "zero": True,
             "series": [{"name": f, "data": clean(v[f])} for f in top]},
            {"id": "c2", "type": "line",
             "titlu": "Randamentul pe ultimele 12 luni",
             "subtitlu": "Creșterea VUAN față de aceeași lună a anului precedent. "
                         "Perioadele negative arată cât de mult poate scădea valoarea pe termen scurt.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0,
             "series": [{"name": f, "data": clean(cr12[f])} for f in top]},
            {"id": "c3", "type": "line",
             "titlu": "Rata de rentabilitate calculată de ASF și pragul minim obligatoriu",
             "subtitlu": "Rata anualizată pe ultimii 5 ani. Fondurile care coboară sub rata minimă a "
                         "categoriei lor de risc trebuie să acopere diferența din capitalul propriu.",
             "labels": [ro_luna(p) for p in ind.index], "unit": "%", "dec": 2, "ydec": 0,
             "series": [{"name": "Rata medie ponderată a sistemului",
                         "data": clean(ind[sistem].values)}]
                       + [{"name": f"Rata minimă — {'risc ridicat' if 'ridicat' in c.lower() else 'risc mediu'}",
                           "data": clean(ind[c].values), "dashed": True}
                          for c in ind.columns if "minim" in c.lower()],
             },
            {"id": "c4", "type": "bar",
             "titlu": "Randamentul pe ani calendaristici",
             "subtitlu": "Media simplă a creșterii VUAN a fondurilor active, de la 31 decembrie la "
                         "31 decembrie.",
             "labels": list(a_anual["An calendaristic"])[1:], "unit": "%", "dec": 1, "ydec": 0,
             "series": [{"name": "Randament mediu al fondurilor",
                         "data": clean(a_anual["Medie simplă a fondurilor (%)"].tolist()[1:])}]},
            {"id": "c5", "type": "bar",
             "titlu": "Cât valorează azi 10 lei investiți la lansarea fondului",
             "subtitlu": "Rezultatul cumulat, net de comisioane, pentru fiecare fond activ.",
             "labels": top, "unit": "lei", "dec": 1, "ydec": 0, "zero": True,
             "xticks": len(top),
             "series": [{"name": "Valoare azi", "data": clean(inm)}]},
        ],
        "tabel": {
            "titlu": f"VUAN lunar — ultimele 36 de luni ({len(v)} luni în fișierul Excel)",
            "columns": ["Luna"] + top,
            "rows": [[ro_luna(p)] + [ro_num(v[f][p], 2) for f in top]
                     for p in v.index[-36:][::-1]],
        },
        "note": [
            "Sursa: Autoritatea de Supraveghere Financiară, fișierul "
            "<code>p2-date_statistice.xlsx</code>, foile <code>Table 5.</code> (valoarea unitară a "
            "activului net) și <code>Table 15.</code> (rate de rentabilitate).",
            "<strong>Unitatea de fond</strong> este «bucata» din fond pe care o cumpără contribuția "
            "lunară. Când VUAN crește, cresc și banii din cont, chiar dacă numărul de unități rămâne "
            "același. Toate fondurile au pornit de la 10 lei pe unitate, în mai 2008.",
            "Randamentul afișat este <strong>net de comisioanele de administrare</strong>: comisionul "
            "este deja scăzut înainte de calculul VUAN.",
            "Randamentul personal al fiecărui participant diferă de creșterea VUAN, pentru că "
            "contribuțiile intră lunar, la prețuri diferite ale unității de fond.",
            "Legea impune fiecărui fond o <strong>rată minimă de rentabilitate</strong>, calculată pe "
            "categoria de risc. Un fond care rămâne sub prag trebuie să acopere diferența din banii "
            "administratorului, nu ai participanților.",
            "Randamentele sunt nominale: nu sunt ajustate cu inflația. Pentru a afla câștigul real, "
            "se scade rata inflației din perioada respectivă.",
            "Regenerare: <code>python3 scripts/financiara_05_03.py</code>.",
        ],
    }
    build_html(os.path.join(P.OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(lung)} obs., {len(v)} luni, {per_min} → {per_max}, "
          f"{len(active)} fonduri active, CAGR mediu {med_cagr:.2f}%, "
          f"10 lei -> {inm.mean():.1f} lei")


if __name__ == "__main__":
    main()
