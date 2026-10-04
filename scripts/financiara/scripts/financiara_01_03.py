#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 01 03 — Indicii Bursei de Valori București
Sursa: BVB, buletinele lunare (https://bvb.ro/info/Rapoarte/Lunare/{LUNA}{AN}.pdf), secțiunea A.
Frecvență: lunară, ianuarie 2010 – prezent. Valori de închidere de lună, în puncte (RON).
"""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from fin_common import (build_excel, build_html, clean, fail_if_short,  # noqa: E402
                        fail_if_stale, ro_luna, ro_num)
from bvb_buletin import serie  # noqa: E402

COD = "Financiara 01 03"
OUT = os.path.join(HERE, "..", "out")
PAGINA = "https://bvb.ro/info/Rapoarte/Lunare"
AN_START, LUNA_START = 2010, 1

# indice -> (valuta din buletin, descriere scurtă)
INDICI = {
    "BET": ("RON", "cele mai lichide 20 de companii, fără dividende"),
    "BET-TR": ("RON", "BET cu dividendele reinvestite (randament total)"),
    "BET-XT": ("RON", "cele mai lichide 30 de companii, inclusiv SIF-uri și FP"),
    "BET-FI": ("RON", "societățile de investiții financiare (fostele SIF) și Fondul Proprietatea"),
    "BET-NG": ("RON", "companiile din energie și utilități"),
    "BET-BK": ("RON", "indice de referință pentru fondurile de investiții"),
    "BETPlus": ("RON", "toate companiile care trec pragurile de lichiditate"),
    "BET-C": ("RON", "indice compozit, calculat până în 2014"),
    "ROTX": ("EUR", "indicele Blue-chip al BVB calculat de Bursa din Viena, în euro"),
}
PRINCIPALI = ["BET", "BET-TR", "BET-XT", "BET-FI", "BET-NG", "BET-BK", "BETPlus"]


def _ultima_luna_incheiata() -> tuple[int, int]:
    azi = dt.date.today()
    a, m = azi.year, azi.month - 1
    if m == 0:
        a, m = a - 1, 12
    return a, m


def descarca() -> pd.DataFrame:
    a_stop, m_stop = _ultima_luna_incheiata()
    brut = serie(AN_START, LUNA_START, a_stop, m_stop)
    randuri = []
    for per in sorted(brut):
        d = brut[per]
        r = {"perioada": per}
        for ind, (valuta, _) in INDICI.items():
            r[ind] = d.get(ind, {}).get(valuta)
        randuri.append(r)
    df = pd.DataFrame(randuri)
    fail_if_short(df, 150, "BVB buletine lunare — indici (secțiunea A)")
    if df["BET"].notna().mean() < 0.98:
        raise SystemExit(
            f"EȘEC: indicele BET e completat doar în {df['BET'].notna().mean():.0%} din luni. "
            "Parserul buletinelor BVB nu mai prinde câmpul.")
    fail_if_stale(df.perioada.max(), 3, "buletinele lunare BVB")
    return df


def _randament(s: pd.Series, luni: int):
    if len(s.dropna()) <= luni:
        return None
    x = s.dropna()
    return float(x.iloc[-1] / x.iloc[-1 - luni] - 1) * 100


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()
    d = df.set_index("perioada")
    per_min, per_max = d.index.min(), d.index.max()
    bet = d["BET"].dropna()

    # Câți indici are setul, câți mai sunt publicați și când a început fiecare serie.
    acoperire = {i: d[i].dropna() for i in INDICI if d[i].notna().any()}
    n_indici = len(acoperire)
    activi = [i for i, s_ in acoperire.items() if s_.index[-1] == per_max]
    incheiate = [(i, s_.index[-1]) for i, s_ in acoperire.items() if s_.index[-1] != per_max]
    n_activi = len(activi)
    txt_start = ", ".join(f"{i} din {ro_luna(s_.index[0])}" for i, s_ in acoperire.items())
    txt_incheiate = "; ".join(f"{i} (ultima lună {ro_luna(p)})" for i, p in incheiate)

    # ---------------- foi de analiză ----------------
    a_serii = pd.DataFrame({"Luna": d.index})
    for ind in INDICI:
        a_serii[f"{ind} (puncte)"] = d[ind].round(2).values

    dd = (bet / bet.cummax() - 1) * 100  # scădere față de maximul istoric
    a_bet = pd.DataFrame({
        "Luna": bet.index,
        "BET (puncte)": bet.round(2).values,
        "Variație lunară (%)": (bet.pct_change() * 100).round(2).values,
        "Variație 12 luni (%)": (bet.pct_change(12) * 100).round(2).values,
        "Medie mobilă 12 luni (puncte)": bet.rolling(12).mean().round(2).values,
        "Maxim istoric până la acea lună (puncte)": bet.cummax().round(2).values,
        "Scădere față de maximul istoric (%)": dd.round(2).values,
    })

    # randamente calendaristice: ultima lună a anului vs ultima lună a anului anterior
    ani = sorted(set(d.index.str[:4]))
    rows = []
    for an in ani:
        sub = d[d.index.str[:4] == an]
        ant = d[d.index.str[:4] == str(int(an) - 1)]
        r = {"An": an, "Luni raportate": int(sub["BET"].notna().sum())}
        for ind in PRINCIPALI:
            v_fin = sub[ind].dropna()
            v_ant = ant[ind].dropna()
            r[f"{ind} (%)"] = (round(float(v_fin.iloc[-1] / v_ant.iloc[-1] - 1) * 100, 2)
                               if len(v_fin) and len(v_ant) else None)
        rows.append(r)
    a_anual = pd.DataFrame(rows)

    # efectul dividendelor: BET vs BET-TR rebazate la 100 din prima lună comună
    comun = d[["BET", "BET-TR"]].dropna()
    a_div = pd.DataFrame({
        "Luna": comun.index,
        "BET rebazat (100 = prima lună)": (comun["BET"] / comun["BET"].iloc[0] * 100).round(2).values,
        "BET-TR rebazat (100 = prima lună)": (comun["BET-TR"] / comun["BET-TR"].iloc[0] * 100).round(2).values,
    })
    a_div["Câștig suplimentar din dividende (p.p.)"] = (
        a_div["BET-TR rebazat (100 = prima lună)"] - a_div["BET rebazat (100 = prima lună)"]).round(2)

    orizonturi = [("1 lună", 1), ("3 luni", 3), ("6 luni", 6), ("12 luni", 12),
                  ("3 ani", 36), ("5 ani", 60), ("10 ani", 120)]
    rows = []
    for ind in PRINCIPALI + ["ROTX"]:
        s = d[ind].dropna()
        if s.empty:
            continue
        r = {"Indice": ind, "Descriere": INDICI[ind][1],
             "Ultima valoare (puncte)": round(float(s.iloc[-1]), 2),
             "Ultima lună disponibilă": ro_luna(s.index[-1])}
        for et, n in orizonturi:
            v = _randament(s, n)
            r[f"Randament {et} (%)"] = round(v, 2) if v is not None else None
        rows.append(r)
    a_perf = pd.DataFrame(rows)

    rows = []
    for ind in INDICI:
        s = d[ind].dropna()
        if s.empty:
            continue
        rows.append({
            "Indice": ind,
            "Prima lună": ro_luna(s.index[0]),
            "Ultima lună": ro_luna(s.index[-1]),
            "Luni cu date": int(len(s)),
            "Maxim (puncte)": round(float(s.max()), 2),
            "Luna maximului": ro_luna(s.idxmax()),
            "Minim (puncte)": round(float(s.min()), 2),
            "Luna minimului": ro_luna(s.idxmin()),
            "Ultima valoare (puncte)": round(float(s.iloc[-1]), 2),
            "Distanță până la maxim (%)": round(float(s.iloc[-1] / s.max() - 1) * 100, 2),
        })
    a_repere = pd.DataFrame(rows)

    vol = pd.DataFrame({
        "Luna": bet.index,
        "Variație lunară BET (%)": (bet.pct_change() * 100).round(2).values,
        "Volatilitate 12 luni (abatere standard a variațiilor lunare, p.p.)":
            (bet.pct_change() * 100).rolling(12).std().round(2).values,
        "Cea mai bună lună din ultimele 12 (%)":
            (bet.pct_change() * 100).rolling(12).max().round(2).values,
        "Cea mai slabă lună din ultimele 12 (%)":
            (bet.pct_change() * 100).rolling(12).min().round(2).values,
    })

    meta = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": "Indicii Bursei de Valori București",
        "subtitlu": "Cum au evoluat BET și ceilalți indici ai bursei românești, lună de lună, "
                    "din 2010 până astăzi — inclusiv cât adaugă dividendele la randamentul investitorilor.",
        "sursa": "Bursa de Valori București — buletinele lunare, secțiunea A "
                 "„Indicatori bursieri de bază”",
        "sursa_url": PAGINA,
        "cod_set": "BVB Buletin lunar, fișiere /info/Rapoarte/Lunare/{LUNA}{AN}.pdf, secțiunea A",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max} ({len(d)} luni). Setul cuprinde "
                    f"{n_indici} indici, dintre care {n_activi} sunt încă publicați în "
                    f"ultima lună ({ro_luna(per_max)})."
                    + (f" Serii încheiate: {txt_incheiate}." if incheiate else ""),
        "unitate": "puncte de indice (RON, cu excepția ROTX, exprimat în EUR); "
                   "randamentele și variațiile în procente",
        "descarcat": azi,
        "licenta": "Date publice publicate de BVB în buletinele lunare. Reutilizare cu "
                   "menționarea sursei (Bursa de Valori București).",
        "metodologie": "Valorile de închidere ale ultimei ședințe din fiecare lună, extrase automat "
                       "din secțiunea A a buletinului lunar PDF cu pdftotext -layout. Se preiau "
                       "valorile în RON, singura excepție fiind ROTX, pe care BVB îl raportează "
                       "în EUR după 2012. Randamentele, mediile mobile, volatilitatea și scăderea "
                       "față de maximul istoric sunt calculate în acest set.",
        "script": "scripts/financiara_01_03.py (+ scripts/bvb_buletin.py)",
        "note": [
            "BET urmărește prețurile celor mai lichide 20 de companii, fără dividende. "
            "BET-TR urmărește aceleași companii, dar presupune reinvestirea dividendelor; "
            "diferența dintre cele două arată cât contează dividendele pe bursa românească.",
            "Indicii din acest set au date de lansare diferite: " + txt_start + ". "
            "Lunile anterioare lansării sunt goale, nu lipsă de date.",
            "Buletinul BVB mai publică și alți indici (BET-XT-TR, BET-TRN, BET-XT-TRN, "
            "BET-EF), care nu sunt incluși în acest set pentru că au serii prea scurte; "
            "ei pot fi extrași cu același parser, scripts/bvb_buletin.py.",
            "BET-C a fost calculat până în mai 2014, apoi retras; seria se oprește acolo.",
            "ROTX este calculat de Bursa de Valori din Viena pe baza acțiunilor românești; "
            "în buletinele din 2010–2012 apare în RON, ulterior doar în EUR — cele două "
            "segmente nu sunt direct comparabile.",
        ],
        "avertismente": [
            "Valorile sunt cele de la sfârșitul lunii, nu medii lunare. Un randament lunar "
            "calculat aici poate diferi de mediile publicate în alte surse.",
            "Randamentele calendaristice anuale se calculează din decembrie în decembrie; "
            "pentru anul curent, ultima lună raportată ține locul lui decembrie.",
            "Structura PDF-ului s-a schimbat de mai multe ori între 2010 și 2026; scriptul "
            "se oprește cu eroare dacă BET nu se extrage în cel puțin 98% din luni.",
            "Nu se folosesc valori estimate: dacă un indice nu apare în buletin, celula rămâne goală.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=df.rename(columns={"perioada": "Luna"}),
        analize={
            "Serii lunare": a_serii,
            "Dinamica BET": a_bet,
            "Randamente anuale": a_anual,
            "Efectul dividendelor": a_div,
            "Performanțe comparate": a_perf,
            "Volatilitate BET": vol,
            "Repere istorice": a_repere,
        },
        note_analize={
            "Serii lunare": "Valorile de închidere de lună, o coloană per indice.",
            "Dinamica BET": "Variații, medie mobilă și scăderea față de maximul istoric.",
            "Randamente anuale": "Randament calendaristic, din decembrie în decembrie.",
            "Efectul dividendelor": "BET și BET-TR rebazate la 100 în prima lună comună; "
                                    "diferența măsoară aportul dividendelor reinvestite.",
            "Performanțe comparate": "Randamente pe orizonturi, pentru fiecare indice.",
            "Volatilitate BET": "Cât de mult oscilează indicele de la o lună la alta.",
            "Repere istorice": "Maxime, minime și acoperirea fiecărei serii.",
        },
        numfmt="#,##0.00")

    # ---------------- pagina HTML ----------------
    et = [ro_luna(p) for p in d.index]
    bet_now = float(bet.iloc[-1])
    bet_12 = _randament(bet, 12)
    dd_now = float(dd.iloc[-1])
    div_bonus = float(a_div["Câștig suplimentar din dividende (p.p.)"].iloc[-1])
    ani_div = len(comun) / 12.0

    reb_start = "2014-09"
    sub = d.loc[d.index >= reb_start, PRINCIPALI].copy()
    reb = {}
    for ind in ["BET", "BET-TR", "BET-FI", "BET-NG", "BETPlus"]:
        s = sub[ind]
        baza = s.dropna()
        if baza.empty:
            continue
        reb[ind] = (s / baza.iloc[0] * 100)
    et_reb = [ro_luna(p) for p in sub.index]

    spec = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Bursa de Valori București — buletine lunare", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Indicele BET, {ro_luna(per_max)}",
             "valoare": f"{ro_num(bet_now, 0)} puncte",
             "nota": "închiderea ultimei ședințe din lună"},
            {"eticheta": "Randament pe ultimele 12 luni",
             "valoare": f"{'+' if (bet_12 or 0) >= 0 else ''}{ro_num(bet_12, 1)}%",
             "nota": "fără dividende",
             "trend": "up" if (bet_12 or 0) >= 0 else "down"},
            {"eticheta": "Distanță față de maximul istoric",
             "valoare": f"{ro_num(dd_now, 1)}%",
             "nota": f"maxim: {ro_num(bet.max(), 0)} puncte ({ro_luna(bet.idxmax())})",
             "trend": "down" if dd_now < -0.05 else "up"},
            {"eticheta": "Aport suplimentar al dividendelor",
             "valoare": f"+{ro_num(div_bonus, 0)} p.p.",
             "nota": f"BET-TR față de BET, în {ro_num(ani_div, 0)} ani"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Indicele BET, principalul barometru al bursei românești",
             "subtitlu": "Valoarea de închidere a ultimei ședințe din fiecare lună, în puncte.",
             "labels": et, "unit": "puncte", "dec": 0, "ydec": 0, "fill": True,
             "series": [{"name": "BET", "data": clean(d["BET"])}]},
            {"id": "c2", "type": "line",
             "titlu": "Cât adaugă dividendele: BET față de BET-TR",
             "subtitlu": f"Ambii indici rebazați la 100 în {ro_luna(comun.index[0])}. "
                         "BET-TR presupune că dividendele primite sunt reinvestite în aceleași acțiuni.",
             "labels": [ro_luna(p) for p in comun.index], "unit": "puncte (bază 100)",
             "dec": 1, "ydec": 0,
             "series": [
                 {"name": "BET (fără dividende)",
                  "data": clean(comun["BET"] / comun["BET"].iloc[0] * 100)},
                 {"name": "BET-TR (cu dividende reinvestite)",
                  "data": clean(comun["BET-TR"] / comun["BET-TR"].iloc[0] * 100)}]},
            {"id": "c3", "type": "line",
             "titlu": "Indicii bursieri, comparați pe aceeași scară",
             "subtitlu": f"Toți indicii rebazați la 100 în {ro_luna(reb_start)}, prima lună "
                         "în care sunt disponibili împreună.",
             "labels": et_reb, "unit": "puncte (bază 100)", "dec": 1, "ydec": 0,
             "series": [{"name": k, "data": clean(v)} for k, v in reb.items()]},
            {"id": "c4", "type": "bar",
             "titlu": "Randamentul anual al indicelui BET",
             "subtitlu": "Variația din decembrie în decembrie, în procente. Anul curent cuprinde "
                         "doar lunile raportate până acum.",
             "labels": [a for a, v in zip(a_anual["An"], a_anual["BET (%)"]) if v is not None],
             "unit": "%", "dec": 1, "ydec": 0,
             "series": [{"name": "Randament BET",
                         "data": clean([v for v in a_anual["BET (%)"] if v is not None])}]},
            {"id": "c5", "type": "line",
             "titlu": "Cât de departe este bursa de recordul ei",
             "subtitlu": "Scăderea indicelui BET față de cel mai mare nivel atins până în luna "
                         "respectivă. Zero înseamnă maxim istoric nou.",
             "labels": [ro_luna(p) for p in bet.index], "unit": "%", "dec": 1, "ydec": 0,
             "fill": True,
             "series": [{"name": "Scădere față de maximul istoric", "data": clean(dd)}]},
        ],
        "tabel": {
            "titlu": f"Valori lunare — ultimele 36 de luni ({len(d)} luni în fișierul Excel)",
            "columns": ["Luna"] + PRINCIPALI + ["ROTX (EUR)"],
            "rows": [[ro_luna(p)] + [ro_num(d[i][p], 1) for i in PRINCIPALI]
                     + [ro_num(d["ROTX"][p], 1)]
                     for p in list(d.index[-36:])[::-1]],
        },
        "note": [
            "Sursa: <strong>Bursa de Valori București</strong>, buletinele lunare publicate la "
            "<code>bvb.ro/info/Rapoarte/Lunare/</code>, secțiunea A. Valorile sunt extrase automat "
            "din PDF-uri, fără intervenție editorială.",
            "<strong>BET</strong> urmărește prețurile celor mai lichide 20 de companii listate. "
            "<strong>BET-TR</strong> urmărește aceleași companii, dar adaugă dividendele reinvestite — "
            "de aceea crește mai repede. Diferența dintre cele două este câștigul pe care îl pierde "
            "un investitor care nu reinvestește dividendele.",
            "<strong>BET-FI</strong> acoperă societățile de investiții financiare și Fondul Proprietatea, "
            "<strong>BET-NG</strong> companiile din energie și utilități, "
            "<strong>BETPlus</strong> toate companiile care trec pragurile de lichiditate.",
            f"Setul cuprinde <strong>{n_indici} indici</strong>, dintre care "
            f"<strong>{n_activi}</strong> mai sunt publicați în {ro_luna(per_max)}. "
            "Ei au fost lansați la date diferite (" + txt_start + "), iar lunile goale din "
            "serii reflectă aceste date de lansare, nu date lipsă."
            + (f" Serii încheiate: {txt_incheiate}." if incheiate else ""),
            "Valorile sunt de sfârșit de lună, nu medii lunare — un randament calculat aici poate "
            "diferi ușor de cel raportat în alte surse.",
            "Regenerare: <code>python3 scripts/financiara_01_03.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(d)} luni, {per_min} → {per_max}, BET = {bet_now:.0f} puncte, "
          f"randament 12 luni {bet_12:.1f}%")


if __name__ == "__main__":
    main()
