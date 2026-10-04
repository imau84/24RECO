#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 01 05 — Structura pe sectoare a Bursei de Valori București
Sursa: BVB, buletinele lunare, secțiunea D.1 „Indicatori pe sectoare de activitate”.
Frecvență: lunară, ianuarie 2010 – prezent.
Indicatori: capitalizare, valoare tranzacționată, PER, PBV, randamentul dividendelor (DIVY).
"""
import datetime as dt
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, ro_luna, ro_num)
from bvb_buletin import serie_sectoare  # noqa: E402

COD = "Financiara 01 05"
OUT = os.path.join(HERE, "..", "out")
PAGINA = "https://bvb.ro/info/Rapoarte/Lunare"
AN_START, LUNA_START = 2010, 1

SCURT = {
    "Intermedieri financiare și asigurări": "Financiar",
    "Industria extractivă": "Extractiv",
    "Energie electrică, termică și gaze": "Energie",
    "Industria prelucrătoare": "Prelucrător",
    "Transport și depozitare": "Transport",
    "Activități profesionale, științifice și tehnice": "Profesional",
    "Sănătate și asistență socială": "Sănătate",
    "Comerț cu ridicata și cu amănuntul": "Comerț",
    "Informații și comunicații": "IT&C",
    "Construcții": "Construcții",
    "Hoteluri și restaurante": "Hoteluri",
    "Agricultură, silvicultură și pescuit": "Agricultură",
    "Distribuția apei și salubritate": "Apă",
    "Tranzacții imobiliare": "Imobiliare",
    "Servicii administrative și suport": "Servicii adm.",
    "Învățământ": "Învățământ",
    "Spectacole, activități culturale și recreative": "Cultură",
    "Alte sectoare": "Alte sectoare",
}


def _ultima_luna_incheiata() -> tuple[int, int]:
    azi = dt.date.today()
    a, m = azi.year, azi.month - 1
    if m == 0:
        a, m = a - 1, 12
    return a, m


def descarca() -> pd.DataFrame:
    a_stop, m_stop = _ultima_luna_incheiata()
    df = pd.DataFrame(serie_sectoare(AN_START, LUNA_START, a_stop, m_stop))
    fail_if_short(df, 1200, "BVB buletine lunare — secțiunea D.1 (sectoare)")
    if df.perioada.nunique() < 150:
        raise SystemExit(
            f"EȘEC: secțiunea D.1 s-a extras doar pentru {df.perioada.nunique()} luni. "
            "Structura buletinelor BVB pare schimbată.")
    pe_luna = df.groupby("perioada").size()
    if pe_luna.median() < 7:
        raise SystemExit(
            f"EȘEC: mediana sectoarelor extrase pe lună este {pe_luna.median()} (<7). "
            "Parserul secțiunii D.1 nu mai prinde tabelul.")
    fail_if_stale(df.perioada.max(), 3, "buletinele lunare BVB — sectoare")
    return df.sort_values(["perioada", "capitalizare_ron"],
                          ascending=[True, False]).reset_index(drop=True)


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()
    per_min, per_max = df.perioada.min(), df.perioada.max()

    cap = df.pivot_table(index="perioada", columns="sector",
                         values="capitalizare_ron", aggfunc="first").sort_index()
    trn = df.pivot_table(index="perioada", columns="sector",
                         values="valoare_tranzactionata_ron", aggfunc="first").sort_index()
    per_ = df.pivot_table(index="perioada", columns="sector", values="per", aggfunc="first").sort_index()
    pbv = df.pivot_table(index="perioada", columns="sector", values="pbv", aggfunc="first").sort_index()
    divy = df.pivot_table(index="perioada", columns="sector", values="divy", aggfunc="first").sort_index()

    total_cap = cap.sum(axis=1)
    total_trn = trn.sum(axis=1)
    pondere = cap.div(total_cap, axis=0) * 100

    # ordinea sectoarelor după capitalizarea din ultima lună
    ordine = list(cap.loc[per_max].dropna().sort_values(ascending=False).index)
    ordine += [c for c in cap.columns if c not in ordine]
    # sectoarele urmărite grafic: prezente în cel puțin 90% din luni
    urmarite = [s for s in ordine if cap[s].notna().mean() >= 0.9][:6]

    cap_mld = cap / 1e9
    trn_mil = trn / 1e6

    # Câte sectoare apar în serie, câte mai sunt raportate acum și care s-au retras.
    n_luni = int(cap.shape[0])
    n_total = int(cap.shape[1])
    n_ultima = int(cap.loc[per_max].notna().sum())
    pe_luna_n = cap.notna().sum(axis=1)
    n_min, n_max = int(pe_luna_n.min()), int(pe_luna_n.max())
    retrase = [(s, cap[s].dropna().index[-1]) for s in cap.columns
               if pd.isna(cap.loc[per_max, s])]
    retrase.sort(key=lambda x: x[1], reverse=True)
    txt_retrase = "; ".join(f"„{s}” (ultima raportare {ro_luna(p)})" for s, p in retrase)

    # ---------------- foi de analiză ----------------
    a_cap = cap_mld.reindex(columns=ordine).round(3).reset_index().rename(columns={"perioada": "Luna"})
    a_cap.insert(1, "TOTAL (mld. RON)", (total_cap / 1e9).round(3).values)

    a_pond = pondere.reindex(columns=ordine).round(2).reset_index().rename(columns={"perioada": "Luna"})

    a_trn = trn_mil.reindex(columns=ordine).round(3).reset_index().rename(columns={"perioada": "Luna"})
    a_trn.insert(1, "TOTAL (mil. RON)", (total_trn / 1e6).round(3).values)

    a_per = per_.reindex(columns=ordine).round(2).reset_index().rename(columns={"perioada": "Luna"})
    a_pbv = pbv.reindex(columns=ordine).round(2).reset_index().rename(columns={"perioada": "Luna"})
    a_divy = divy.reindex(columns=ordine).round(2).reset_index().rename(columns={"perioada": "Luna"})

    u = df[df.perioada == per_max].copy()
    idx12 = cap.index[-13] if len(cap) > 13 else None
    a_clasament = pd.DataFrame({
        "Loc": range(1, len(u) + 1),
        "Sector": u["sector"].values,
        "Capitalizare (mld. RON)": (u["capitalizare_ron"] / 1e9).round(3).values,
        "Pondere în capitalizare (%)":
            (u["capitalizare_ron"] / u["capitalizare_ron"].sum() * 100).round(2).values,
        "Valoare tranzacționată (mil. RON)": (u["valoare_tranzactionata_ron"] / 1e6).round(3).values,
        "Pondere în tranzacții (%)":
            (u["valoare_tranzactionata_ron"] / u["valoare_tranzactionata_ron"].sum() * 100).round(2).values,
        "PER": u["per"].round(2).values,
        "PBV": u["pbv"].round(2).values,
        "Randamentul dividendelor (%)": u["divy"].round(2).values,
    })
    a_clasament["Capitalizare acum 12 luni (mld. RON)"] = [
        round(cap[s][idx12] / 1e9, 3) if idx12 is not None and s in cap
        and pd.notna(cap[s].get(idx12)) else None for s in u["sector"]]
    a_clasament["Variație 12 luni (%)"] = (
        (a_clasament["Capitalizare (mld. RON)"]
         / a_clasament["Capitalizare acum 12 luni (mld. RON)"] - 1) * 100).round(2)

    a_dinamica = pd.DataFrame({
        "Luna": cap.index,
        "Capitalizare totală (mld. RON)": (total_cap / 1e9).round(3).values,
        "Variație lunară (%)": (total_cap.pct_change() * 100).round(2).values,
        "Variație 12 luni (%)": (total_cap.pct_change(12) * 100).round(2).values,
        "Valoare tranzacționată totală (mil. RON)": (total_trn / 1e6).round(3).values,
        "Pondere sector financiar (%)":
            pondere.get("Intermedieri financiare și asigurări",
                        pd.Series(index=cap.index, dtype=float)).round(2).values,
        "Pondere sector extractiv (%)":
            pondere.get("Industria extractivă",
                        pd.Series(index=cap.index, dtype=float)).round(2).values,
        "Pondere sector energie (%)":
            pondere.get("Energie electrică, termică și gaze",
                        pd.Series(index=cap.index, dtype=float)).round(2).values,
        "Nr. sectoare raportate": cap.notna().sum(axis=1).values,
    })

    rows = []
    for s in ordine:
        gol = pd.Series(dtype=float)
        cs = cap[s].dropna() if s in cap else gol
        ds = divy[s].dropna() if s in divy else gol
        ps = per_[s].dropna() if s in per_ else gol
        if cs.empty:
            continue
        rows.append({
            "Sector": s,
            "Luni cu date": int(len(cs)),
            "Prima lună": ro_luna(cs.index[0]),
            "Capitalizare maximă (mld. RON)": round(float(cs.max()) / 1e9, 3),
            "Luna maximului": ro_luna(cs.idxmax()),
            "Capitalizare curentă (mld. RON)":
                round(float(cs.iloc[-1]) / 1e9, 3) if cs.index[-1] == per_max else None,
            "PER mediu (ultimele 36 luni)": round(float(ps.tail(36).mean()), 2) if len(ps) else None,
            "Randament mediu al dividendelor (ultimele 36 luni, %)":
                round(float(ds.tail(36).mean()), 2) if len(ds) else None,
        })
    a_repere = pd.DataFrame(rows)

    meta = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": "Structura pe sectoare a Bursei de Valori București",
        "subtitlu": "Ce ramuri ale economiei domină bursa românească, cât valorează fiecare, "
                    "cât de scump se tranzacționează și ce dividende plătește.",
        "sursa": "Bursa de Valori București — buletinele lunare, secțiunea D.1 "
                 "„Indicatori pe sectoare de activitate”",
        "sursa_url": PAGINA,
        "cod_set": "BVB Buletin lunar, fișiere /info/Rapoarte/Lunare/{LUNA}{AN}.pdf, secțiunea D.1",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max} ({n_luni} luni). În total apar {n_total} sectoare "
                    f"de-a lungul seriei, dintre care {n_ultima} sunt raportate în ultima lună "
                    f"({ro_luna(per_max)}). Numărul de sectoare raportate variază între "
                    f"{n_min} și {n_max} de la o lună la alta."
                    + (f" Nu mai apare în buletinele recente: {txt_retrase}." if retrase else ""),
        "unitate": "lei pentru capitalizare și valoare tranzacționată (în foile de analiză: "
                   "miliarde, respectiv milioane de lei); PER și PBV sunt multipli; "
                   "randamentul dividendelor în procente",
        "descarcat": azi,
        "licenta": "Date publice publicate de BVB în buletinele lunare. Reutilizare cu "
                   "menționarea sursei (Bursa de Valori București).",
        "metodologie": "Tabelul pe sectoare din secțiunea D.1 a buletinului lunar PDF este extras "
                       "automat cu pdftotext -layout. Sectoarele urmează clasificarea CAEN "
                       "agregată folosită de BVB. PER (preț/profit), PBV (preț/valoare contabilă) "
                       "și DIVY (randamentul dividendelor) sunt calculate de BVB, nu în acest set; "
                       "ponderile, totalurile și variațiile sunt calculate aici.",
        "script": "scripts/financiara_01_05.py (+ scripts/bvb_buletin.py)",
        "note": [
            "PER arată de câte ori se plătește profitul anual al companiilor dintr-un sector. "
            "Un PER mare înseamnă acțiuni scumpe raportat la profit, sau profituri temporar mici.",
            "PBV compară prețul acțiunii cu valoarea contabilă a companiei. Sub 1 înseamnă că "
            "piața evaluează compania sub valoarea din bilanț.",
            "Randamentul dividendelor (DIVY) arată cât plătesc companiile ca dividend raportat "
            "la prețul acțiunii.",
            "Categoria „Alte sectoare” cuprinde emitenți pe care BVB nu îi încadrează într-o "
            "ramură CAEN distinctă, inclusiv Fondul Proprietatea în anumite perioade.",
            f"Numărul de sectoare raportate variază de la lună la lună (între {n_min} și {n_max}), "
            "pentru că un sector apare în tabel doar dacă are cel puțin o companie listată activă. "
            f"Seria cuprinde în total {n_total} sectoare, iar în {ro_luna(per_max)} sunt raportate "
            f"{n_ultima}."
            + (f" Sector ieșit din raportare: {txt_retrase}." if retrase else ""),
        ],
        "avertismente": [
            "BVB precizează în buletin că PER pe sectoare este calculat doar pe capitalizarea "
            "societăților care au înregistrat profit, iar PBV și DIVY doar pentru emitenții "
            "români — nu sunt medii pe întreg sectorul.",
            "Când un indicator lipsește din buletin (marcat „-”), celula rămâne goală. "
            "Nu se folosesc valori estimate.",
            "Denumirea sectoarelor s-a schimbat ușor în timp („Comert” vs. „Comertul cu ridicata”); "
            "parserul le unifică pe baza cuvintelor-cheie stabile.",
            "Totalul capitalizării pe sectoare poate diferi cu câteva zecimi de capitalizarea "
            "raportată în secțiunea A (setul Financiara 01 02), din cauza rotunjirilor și a "
            "emitenților neîncadrați.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=df.rename(columns={
            "perioada": "Luna", "sector": "Sector",
            "capitalizare_ron": "Capitalizare (RON)",
            "valoare_tranzactionata_ron": "Valoare tranzacționată (RON)",
            "per": "PER", "pbv": "PBV", "divy": "Randamentul dividendelor (%)"}),
        analize={
            "Capitalizare pe sectoare": a_cap,
            "Structura capitalizarii (%)": a_pond,
            "Tranzactii pe sectoare": a_trn,
            "Evaluare PER": a_per,
            "Evaluare PBV": a_pbv,
            "Randamentul dividendelor": a_divy,
            "Clasament ultima luna": a_clasament,
            "Dinamica totalului": a_dinamica,
            "Repere pe sector": a_repere,
        },
        note_analize={
            "Capitalizare pe sectoare": "Valoarea de piață a companiilor din fiecare sector, "
                                        "în miliarde de lei, la sfârșitul fiecărei luni.",
            "Structura capitalizarii (%)": "Ponderea fiecărui sector în capitalizarea totală.",
            "Tranzactii pe sectoare": "Valoarea tranzacționată lunar, în milioane de lei.",
            "Evaluare PER": "Multiplul preț/profit calculat de BVB pentru fiecare sector.",
            "Evaluare PBV": "Multiplul preț/valoare contabilă.",
            "Randamentul dividendelor": "Dividendul raportat la prețul acțiunii, în procente.",
            "Clasament ultima luna": "Fotografia ultimei luni, cu variația față de anul trecut.",
            "Dinamica totalului": "Evoluția capitalizării totale și a ponderilor sectoarelor mari.",
            "Repere pe sector": "Acoperire, maxime și medii pe fiecare sector.",
        },
        numfmt="#,##0.00")

    # ---------------- pagina HTML ----------------
    et = [ro_luna(p) for p in cap.index]
    top1 = a_clasament.iloc[0]
    fin_pond = float(pondere["Intermedieri financiare și asigurări"].iloc[-1])
    cap_tot_now = float(total_cap.iloc[-1] / 1e9)
    divy_u = u.dropna(subset=["divy"]).sort_values("divy", ascending=False)
    per_u = u.dropna(subset=["per"])

    et_cls = [SCURT.get(s, s) for s in a_clasament["Sector"]]

    spec = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Bursa de Valori București — buletine lunare, secțiunea D.1",
        "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Capitalizare pe sectoare, {ro_luna(per_max)}",
             "valoare": f"{ro_num(cap_tot_now, 1)} mld. lei",
             "nota": f"{n_ultima} sectoare raportate, din {n_total} apărute în serie"},
            {"eticheta": "Cel mai mare sector",
             "valoare": SCURT.get(top1["Sector"], top1["Sector"]),
             "nota": f"{ro_num(top1['Capitalizare (mld. RON)'], 1)} mld. lei — "
                     f"{ro_num(top1['Pondere în capitalizare (%)'], 1)}% din bursă"},
            {"eticheta": "Cât cântărește sectorul financiar",
             "valoare": f"{ro_num(fin_pond, 1)}%",
             "nota": "din capitalizarea totală a bursei"},
            {"eticheta": "Cel mai generos sector la dividende",
             "valoare": f"{ro_num(divy_u['divy'].iloc[0], 1)}%"
                        if len(divy_u) else "–",
             "nota": SCURT.get(divy_u['sector'].iloc[0], "") if len(divy_u) else ""},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Cât valorează fiecare ramură a bursei",
             "subtitlu": "Capitalizarea companiilor listate, pe sectoare de activitate, "
                         "în miliarde de lei.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": SCURT.get(s, s), "data": clean(cap_mld[s])} for s in urmarite]},
            {"id": "c2", "type": "line",
             "titlu": "Cum s-a schimbat structura bursei",
             "subtitlu": "Ponderea fiecărui sector în capitalizarea totală. Suma tuturor "
                         "sectoarelor este 100%.",
             "labels": et, "unit": "%", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": SCURT.get(s, s), "data": clean(pondere[s])} for s in urmarite]},
            {"id": "c3", "type": "bar",
             "titlu": f"Clasamentul sectoarelor în {ro_luna(per_max)}",
             "subtitlu": "Capitalizarea bursieră a fiecărui sector, în miliarde de lei.",
             "labels": et_cls, "unit": "mld. lei", "dec": 2, "ydec": 0, "zero": True,
             "xticks": 14,
             "series": [{"name": "Capitalizare",
                         "data": clean(a_clasament["Capitalizare (mld. RON)"])}]},
            {"id": "c4", "type": "line",
             "titlu": "Cât de scump se tranzacționează fiecare sector (PER)",
             "subtitlu": "De câte ori se plătește profitul anual al companiilor. "
                         "Valorile mari indică acțiuni scumpe raportat la profit.",
             "labels": et, "unit": "", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": SCURT.get(s, s), "data": clean(per_.reindex(columns=[s])[s])} for s in urmarite]},
            {"id": "c5", "type": "bar",
             "titlu": f"Randamentul dividendelor pe sectoare, {ro_luna(per_max)}",
             "subtitlu": "Cât plătesc companiile ca dividend, raportat la prețul acțiunii.",
             "labels": [SCURT.get(s, s) for s in divy_u["sector"]], "unit": "%",
             "dec": 2, "ydec": 0, "zero": True, "xticks": 14,
             "series": [{"name": "Randamentul dividendelor", "data": clean(divy_u["divy"])}]},
        ],
        "tabel": {
            "titlu": f"Situația sectoarelor în {ro_luna(per_max)} "
                     f"(seriile lunare complete sunt în fișierul Excel)",
            "columns": ["Sector", "Capitalizare (mld. lei)", "Pondere (%)",
                        "Tranzacții (mil. lei)", "PER", "PBV", "Dividende (%)",
                        "Variație 12 luni (%)"],
            "rows": [[r["Sector"], ro_num(r["Capitalizare (mld. RON)"], 2),
                      ro_num(r["Pondere în capitalizare (%)"], 1),
                      ro_num(r["Valoare tranzacționată (mil. RON)"], 1),
                      ro_num(r["PER"], 2), ro_num(r["PBV"], 2),
                      ro_num(r["Randamentul dividendelor (%)"], 2),
                      ro_num(r["Variație 12 luni (%)"], 1)]
                     for _, r in a_clasament.iterrows()],
        },
        "note": [
            "Sursa: <strong>Bursa de Valori București</strong>, buletinele lunare publicate la "
            "<code>bvb.ro/info/Rapoarte/Lunare/</code>, secțiunea D.1 „Indicatori pe sectoare de "
            "activitate”. Valorile sunt extrase automat din PDF-uri, fără intervenție editorială.",
            "<strong>PER</strong> (preț/profit) arată de câte ori se plătește profitul anual al "
            "companiilor dintr-un sector. <strong>PBV</strong> compară prețul cu valoarea contabilă: "
            "sub 1 înseamnă că piața evaluează companiile sub valoarea din bilanț. "
            "<strong>Randamentul dividendelor</strong> arată cât primește anual un investitor "
            "sub formă de dividend, raportat la prețul plătit pe acțiune.",
            "BVB precizează că PER pe sectoare se calculează doar pe capitalizarea societăților "
            "profitabile, iar PBV și DIVY doar pentru emitenții români — nu sunt medii pe tot sectorul.",
            f"Un sector apare în tabel doar dacă are companii listate active în luna respectivă, "
            f"de aceea numărul de sectoare raportate variază între {n_min} și {n_max} de-a lungul "
            f"seriei. În total apar <strong>{n_total} sectoare</strong>, dintre care "
            f"<strong>{n_ultima}</strong> sunt raportate în {ro_luna(per_max)}."
            + (f" Sector ieșit din raportare: {txt_retrase}." if retrase else ""),
            "„Alte sectoare” cuprinde emitenții pe care BVB nu îi încadrează într-o ramură distinctă.",
            "Regenerare: <code>python3 scripts/financiara_01_05.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(df)} rânduri, {cap.shape[0]} luni, {cap.shape[1]} sectoare, "
          f"{per_min} → {per_max}, total {cap_tot_now:.1f} mld. RON")


if __name__ == "__main__":
    main()
