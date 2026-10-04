#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financiara 01 02 — Activitatea de tranzacționare și capitalizarea Bursei de Valori București
Sursa: BVB, buletinele lunare (https://bvb.ro/info/Rapoarte/Lunare/{LUNA}{AN}.pdf), secțiunea A.
Frecvență: lunară, ianuarie 2010 – prezent.
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
from bvb_buletin import serie  # noqa: E402

COD = "Financiara 01 02"
OUT = os.path.join(HERE, "..", "out")
PAGINA = "https://bvb.ro/info/Rapoarte/Lunare"
AN_START, LUNA_START = 2010, 1


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
        randuri.append({
            "perioada": per,
            "val_tranz_mil_ron": d.get("valoare_tranzactionata", {}).get("RON"),
            "val_tranz_mil_eur": d.get("valoare_tranzactionata", {}).get("EUR"),
            "val_medie_zilnica_mil_ron": d.get("valoare_medie_zilnica", {}).get("RON"),
            "capitalizare_mil_ron": d.get("capitalizare", {}).get("RON"),
            "capitalizare_mil_eur": d.get("capitalizare", {}).get("EUR"),
            "nr_titluri_tranzactionate": d.get("nr_titluri", {}).get("NR"),
            "nr_tranzactii": d.get("nr_tranzactii", {}).get("NR"),
        })
    df = pd.DataFrame(randuri)
    fail_if_short(df, 150, "BVB buletine lunare (secțiunea A)")
    # datele de bază trebuie să existe pe aproape toate lunile
    for c in ("val_tranz_mil_ron", "capitalizare_mil_ron", "nr_tranzactii"):
        acoperire = df[c].notna().mean()
        if acoperire < 0.95:
            raise SystemExit(
                f"EȘEC: coloana {c} e completată doar în {acoperire:.0%} din luni. "
                "Parserul buletinelor BVB nu mai prinde câmpul — verifică structura PDF-urilor.")
    fail_if_stale(df.perioada.max(), 3, "buletinele lunare BVB")
    return df


def main() -> None:
    df = descarca()
    azi = dt.date.today().isoformat()
    d = df.set_index("perioada")
    per_min, per_max = d.index.min(), d.index.max()

    # Acoperirea reală a indicatorilor de bază, declarată în foaia Sursa.
    col_ind = ["val_tranz_mil_ron", "val_medie_zilnica_mil_ron", "capitalizare_mil_ron",
               "nr_titluri_tranzactionate", "nr_tranzactii"]
    n_ind = len(col_ind)
    n_compl = int(d[col_ind].notna().all(axis=1).sum())

    cap_mld = d["capitalizare_mil_ron"] / 1000.0          # miliarde RON
    cap_mld_eur = d["capitalizare_mil_eur"] / 1000.0
    tr_mld = d["val_tranz_mil_ron"] / 1000.0              # miliarde RON
    trz = d["nr_tranzactii"]
    # rata de lichiditate anualizată: valoarea lunii × 12 / capitalizare
    lich = (d["val_tranz_mil_ron"] * 12.0 / d["capitalizare_mil_ron"] * 100.0)
    val_medie_tranz = d["val_tranz_mil_ron"] * 1e6 / d["nr_tranzactii"]  # RON / tranzacție

    # ---------------- foi de analiză ----------------
    a_serii = pd.DataFrame({
        "Luna": d.index,
        "Valoare tranzacționată (mil. RON)": d["val_tranz_mil_ron"].round(2).values,
        "Valoare tranzacționată (mil. EUR)": d["val_tranz_mil_eur"].round(2).values,
        "Valoare medie zilnică (mil. RON)": d["val_medie_zilnica_mil_ron"].round(2).values,
        "Capitalizare (mil. RON)": d["capitalizare_mil_ron"].round(2).values,
        "Capitalizare (mil. EUR)": d["capitalizare_mil_eur"].round(2).values,
        "Nr. tranzacții": d["nr_tranzactii"].values,
        "Nr. titluri tranzacționate": d["nr_titluri_tranzactionate"].values,
    })

    a_dinamica = pd.DataFrame({
        "Luna": d.index,
        "Capitalizare (mld. RON)": cap_mld.round(2).values,
        "Variație lunară capitalizare (%)": (cap_mld.pct_change() * 100).round(2).values,
        "Variație 12 luni capitalizare (%)": (cap_mld.pct_change(12) * 100).round(2).values,
        "Valoare tranzacționată (mld. RON)": tr_mld.round(3).values,
        "Variație 12 luni valoare (%)": (tr_mld.pct_change(12) * 100).round(2).values,
        "Medie mobilă 12 luni valoare (mld. RON)": tr_mld.rolling(12).mean().round(3).values,
        "Nr. tranzacții": trz.values,
        "Medie mobilă 12 luni nr. tranzacții": trz.rolling(12).mean().round(0).values,
    })

    a_lichid = pd.DataFrame({
        "Luna": d.index,
        "Rata de lichiditate anualizată (%)": lich.round(2).values,
        "Medie mobilă 12 luni (%)": lich.rolling(12).mean().round(2).values,
        "Valoare medie pe tranzacție (RON)": val_medie_tranz.round(0).values,
        "Valoare medie zilnică (mil. RON)": d["val_medie_zilnica_mil_ron"].round(2).values,
        "Zile de tranzacționare estimate": (
            d["val_tranz_mil_ron"] / d["val_medie_zilnica_mil_ron"]).round(1).values,
    })

    ani = d.index.str[:4]
    g = d.groupby(ani)
    a_anual = pd.DataFrame({
        "An": g["val_tranz_mil_ron"].sum().index,
        "Total tranzacționat (mld. RON)": (g["val_tranz_mil_ron"].sum() / 1000).round(2).values,
        "Total tranzacționat (mld. EUR)": (g["val_tranz_mil_eur"].sum() / 1000).round(2).values,
        "Capitalizare la sfârșitul perioadei (mld. RON)": (g["capitalizare_mil_ron"].last() / 1000).round(2).values,
        "Capitalizare la sfârșitul perioadei (mld. EUR)": (g["capitalizare_mil_eur"].last() / 1000).round(2).values,
        "Nr. total tranzacții": g["nr_tranzactii"].sum().values,
        "Luna cea mai activă": g["val_tranz_mil_ron"].idxmax().values,
        "Luni raportate": g["val_tranz_mil_ron"].count().values,
    })
    a_anual["Rata de lichiditate (%)"] = (
        a_anual["Total tranzacționat (mld. RON)"]
        / a_anual["Capitalizare la sfârșitul perioadei (mld. RON)"] * 100).round(2)

    top = d.sort_values("val_tranz_mil_ron", ascending=False).head(20)
    a_top = pd.DataFrame({
        "Loc": range(1, len(top) + 1),
        "Luna": [ro_luna(p) for p in top.index],
        "Valoare tranzacționată (mld. RON)": (top["val_tranz_mil_ron"] / 1000).round(3).values,
        "Nr. tranzacții": top["nr_tranzactii"].values,
        "Capitalizare (mld. RON)": (top["capitalizare_mil_ron"] / 1000).round(2).values,
    })

    a_repere = pd.DataFrame({
        "Indicator": [
            "Capitalizare — maxim istoric (mld. RON)",
            "Capitalizare — valoare curentă (mld. RON)",
            "Capitalizare — minim din 2010 (mld. RON)",
            "Valoare tranzacționată — luna record (mld. RON)",
            "Valoare tranzacționată — ultima lună (mld. RON)",
            "Valoare tranzacționată — medie lunară 2010–prezent (mld. RON)",
            "Nr. tranzacții — luna record",
            "Nr. tranzacții — ultima lună",
            "Rata de lichiditate — medie ultimele 12 luni (%)",
        ],
        "Valoare": [
            round(cap_mld.max(), 2), round(cap_mld.iloc[-1], 2), round(cap_mld.min(), 2),
            round(tr_mld.max(), 3), round(tr_mld.iloc[-1], 3), round(tr_mld.mean(), 3),
            float(trz.max()), float(trz.iloc[-1]), round(lich.tail(12).mean(), 2),
        ],
        "Luna": [
            ro_luna(cap_mld.idxmax()), ro_luna(per_max), ro_luna(cap_mld.idxmin()),
            ro_luna(tr_mld.idxmax()), ro_luna(per_max), "—",
            ro_luna(trz.idxmax()), ro_luna(per_max), "—",
        ],
    })

    meta = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": "Activitatea de tranzacționare și capitalizarea Bursei de Valori București",
        "subtitlu": "Cât valorează companiile listate la BVB, cât se tranzacționează lunar "
                    "și câte tranzacții se încheie — indicatorii de bază ai pieței românești de capital.",
        "sursa": "Bursa de Valori București — buletinele lunare, secțiunea A "
                 "„Indicatori bursieri de bază”",
        "sursa_url": PAGINA,
        "cod_set": "BVB Buletin lunar, fișiere /info/Rapoarte/Lunare/{LUNA}{AN}.pdf, secțiunea A",
        "frecventa": "Lunară",
        "perioada": f"{per_min} → {per_max} ({len(d)} luni, fără întreruperi). "
                    f"Toți cei {n_ind} indicatori de bază sunt completați în {n_compl} "
                    f"din cele {len(d)} luni.",
        "unitate": "milioane RON / milioane EUR pentru valori; număr pentru tranzacții și titluri; "
                   "procente pentru rate și variații",
        "descarcat": azi,
        "licenta": "Date publice publicate de BVB în buletinele lunare. Reutilizare cu "
                   "menționarea sursei (Bursa de Valori București).",
        "metodologie": "Valorile sunt extrase automat din secțiunea A a buletinului lunar PDF "
                       "publicat de BVB, cu pdftotext -layout, și nu sunt recalculate. "
                       "Capitalizarea bursieră este cea de la sfârșitul lunii, pentru societățile "
                       "listate pe Piața Reglementată. Valoarea tranzacționată însumează toate "
                       "instrumentele (acțiuni, obligațiuni, unități de fond, produse structurate, "
                       "drepturi, futures). Rata de lichiditate și valoarea medie pe tranzacție "
                       "sunt calculate în acest set, nu preluate din buletin.",
        "script": "scripts/financiara_01_02.py (+ scripts/bvb_buletin.py)",
        "note": [
            "Rata de lichiditate anualizată = valoarea tranzacționată a lunii × 12 / capitalizare. "
            "Este o aproximare folosită pentru comparații în timp, nu un indicator oficial BVB.",
            "Valoarea medie pe tranzacție = valoarea tranzacționată / numărul de tranzacții.",
            "Capitalizarea include și emitenții mari listați ulterior (de exemplu Hidroelectrica, "
            "din iulie 2023), ceea ce explică salturile bruște din serie.",
            "Seria pornește din ianuarie 2010, prima lună pentru care buletinul PDF are "
            "structura parsabilă de acest script.",
        ],
        "avertismente": [
            "Structura PDF-ului s-a schimbat de cel puțin trei ori (2010–2013, 2014–2019, "
            "2020–prezent). Parserul tratează toate variantele, dar orice reformatare viitoare "
            "a buletinului poate sparge extragerea — scriptul se oprește dacă acoperirea "
            "coloanelor cheie scade sub 95%.",
            "În buletinul din octombrie 2010 unitatea „Nr./No.” apare pe linia etichetei, iar "
            "cifrele pe linia următoare; parserul tratează explicit acest caz.",
            "Valorile în EUR și USD din buletin sunt convertite de BVB la cursul din perioada "
            "respectivă; nu sunt recalculate aici.",
            "Nu se folosesc valori estimate: dacă un câmp nu se extrage sigur, celula rămâne goală.",
        ],
    }

    build_excel(
        os.path.join(OUT, f"{COD}.xlsx"), meta=meta,
        date_df=df.rename(columns={
            "perioada": "Luna",
            "val_tranz_mil_ron": "Valoare tranzacționată (mil. RON)",
            "val_tranz_mil_eur": "Valoare tranzacționată (mil. EUR)",
            "val_medie_zilnica_mil_ron": "Valoare medie zilnică (mil. RON)",
            "capitalizare_mil_ron": "Capitalizare bursieră (mil. RON)",
            "capitalizare_mil_eur": "Capitalizare bursieră (mil. EUR)",
            "nr_titluri_tranzactionate": "Nr. titluri tranzacționate",
            "nr_tranzactii": "Nr. tranzacții"}),
        analize={
            "Serii lunare": a_serii,
            "Dinamica pieței": a_dinamica,
            "Lichiditate": a_lichid,
            "Agregări anuale": a_anual,
            "Top luni după valoare": a_top,
            "Repere istorice": a_repere,
        },
        note_analize={
            "Serii lunare": "Indicatorii bruți, o linie pe lună, exact ca în buletinul BVB.",
            "Dinamica pieței": "Variații lunare și anuale, plus medii mobile pe 12 luni.",
            "Lichiditate": "Cât de intens se rotește piața raportat la mărimea ei.",
            "Agregări anuale": "Totaluri și capitalizare la final de an. Ultimul an conține "
                               "doar lunile raportate până acum.",
            "Top luni după valoare": "Cele mai active 20 de luni din 2010 încoace.",
            "Repere istorice": "Maxime, minime și medii pe întreaga serie.",
        },
        numfmt="#,##0.00",
        numfmt_map={"Nr. tranzacții": "#,##0", "Nr. titluri tranzacționate": "#,##0",
                    "Nr. total tranzacții": "#,##0",
                    "Medie mobilă 12 luni nr. tranzacții": "#,##0",
                    "Valoare medie pe tranzacție (RON)": "#,##0"})

    # ---------------- pagina HTML ----------------
    et = [ro_luna(p) for p in d.index]
    cap_now, cap_eur_now = float(cap_mld.iloc[-1]), float(cap_mld_eur.iloc[-1])
    cap_var12 = float(cap_mld.pct_change(12).iloc[-1] * 100)
    tr_now = float(tr_mld.iloc[-1])
    trz_now = float(trz.iloc[-1])
    lich12 = float(lich.tail(12).mean())

    spec = {
        "cod": COD, "sectiune": "01 Piața de capital",
        "titlu": meta["titlu"], "subtitlu": meta["subtitlu"],
        "sursa": "Bursa de Valori București — buletine lunare", "sursa_url": PAGINA,
        "frecventa": "Lunar", "perioada": f"{ro_luna(per_min)} – {ro_luna(per_max)}",
        "actualizat": azi,
        "kpis": [
            {"eticheta": f"Capitalizare bursieră, {ro_luna(per_max)}",
             "valoare": f"{ro_num(cap_now, 1)} mld. lei",
             "nota": f"≈ {ro_num(cap_eur_now, 1)} mld. euro"},
            {"eticheta": "Variație capitalizare față de anul trecut",
             "valoare": f"{'+' if cap_var12 >= 0 else ''}{ro_num(cap_var12, 1)}%",
             "nota": f"față de {ro_luna(d.index[-13])}",
             "trend": "up" if cap_var12 >= 0 else "down"},
            {"eticheta": "Valoare tranzacționată în lună",
             "valoare": f"{ro_num(tr_now, 2)} mld. lei",
             "nota": f"recordul lunar: {ro_num(tr_mld.max(), 2)} mld. lei "
                     f"({ro_luna(tr_mld.idxmax())})"},
            {"eticheta": "Număr de tranzacții în lună",
             "valoare": ro_num(trz_now, 0),
             "nota": f"lichiditate anualizată: {ro_num(lich12, 1)}% (medie 12 luni)"},
        ],
        "charts": [
            {"id": "c1", "type": "line",
             "titlu": "Capitalizarea bursieră a companiilor listate",
             "subtitlu": "Valoarea totală de piață a societăților de pe Piața Reglementată, "
                         "la sfârșitul fiecărei luni, în miliarde de lei.",
             "labels": et, "unit": "mld. lei", "dec": 1, "ydec": 0, "fill": True, "zero": True,
             "series": [{"name": "Capitalizare", "data": clean(cap_mld)}]},
            {"id": "c2", "type": "bar",
             "titlu": "Valoarea tranzacționată în fiecare lună",
             "subtitlu": "Suma tuturor tranzacțiilor din lună, pe toate instrumentele. "
                         "Vârfurile corespund de regulă listărilor mari și ofertelor publice.",
             "labels": et, "unit": "mld. lei", "dec": 2, "ydec": 0, "zero": True,
             "series": [{"name": "Valoare tranzacționată", "data": clean(tr_mld)}]},
            {"id": "c3", "type": "line",
             "titlu": "Câte tranzacții se încheie lunar",
             "subtitlu": "Numărul de tranzacții arată cât de mulți investitori sunt activi; "
                         "linia punctată netezește sezonalitatea.",
             "labels": et, "unit": "tranzacții", "dec": 0, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Număr de tranzacții", "data": clean(trz)},
                 {"name": "Medie mobilă 12 luni", "data": clean(trz.rolling(12).mean()),
                  "dashed": True}]},
            {"id": "c4", "type": "line",
             "titlu": "Cât de lichidă este bursa",
             "subtitlu": "Valoarea tranzacționată, anualizată, raportată la capitalizare. "
                         "Cu cât procentul e mai mic, cu atât acțiunile își schimbă mai rar proprietarul.",
             "labels": et, "unit": "%", "dec": 2, "ydec": 0, "zero": True,
             "series": [
                 {"name": "Rata de lichiditate anualizată", "data": clean(lich)},
                 {"name": "Medie mobilă 12 luni", "data": clean(lich.rolling(12).mean()),
                  "dashed": True}]},
            {"id": "c5", "type": "bar",
             "titlu": "Total tranzacționat pe an",
             "subtitlu": "Agregarea seriei lunare. Ultimul an cuprinde doar lunile raportate până acum.",
             "labels": list(a_anual["An"]), "unit": "mld. lei", "dec": 1, "ydec": 0, "zero": True,
             "series": [{"name": "Total anual",
                         "data": clean(a_anual["Total tranzacționat (mld. RON)"])}]},
        ],
        "tabel": {
            "titlu": f"Date lunare — ultimele 36 de luni ({len(d)} luni în fișierul Excel)",
            "columns": ["Luna", "Capitalizare (mld. lei)", "Capitalizare (mld. euro)",
                        "Valoare tranzacționată (mld. lei)", "Valoare medie zilnică (mil. lei)",
                        "Nr. tranzacții", "Lichiditate anualizată (%)"],
            "rows": [[ro_luna(p), ro_num(cap_mld[p], 1), ro_num(cap_mld_eur[p], 1),
                      ro_num(tr_mld[p], 2), ro_num(d["val_medie_zilnica_mil_ron"][p], 1),
                      ro_num(trz[p], 0), ro_num(lich[p], 2)]
                     for p in list(d.index[-36:])[::-1]],
        },
        "note": [
            "Sursa: <strong>Bursa de Valori București</strong>, buletinele lunare publicate la "
            "<code>bvb.ro/info/Rapoarte/Lunare/</code>, secțiunea A „Indicatori bursieri de bază”. "
            "Valorile sunt extrase automat din PDF-uri, fără intervenție editorială.",
            "<strong>Capitalizarea bursieră</strong> este suma valorilor de piață ale companiilor "
            "listate pe Piața Reglementată la sfârșitul lunii. Crește atât când acțiunile se scumpesc, "
            "cât și când se listează companii noi.",
            "<strong>Valoarea tranzacționată</strong> însumează toate instrumentele: acțiuni, "
            "obligațiuni, unități de fond, produse structurate, drepturi de preferință și futures. "
            "Include și ofertele publice, de unde vârfurile izolate.",
            "<strong>Rata de lichiditate</strong> este calculată în acest set (valoarea lunii × 12 "
            "împărțită la capitalizare) ca aproximare comparabilă în timp; nu este un indicator "
            "oficial publicat de BVB.",
            "Structura buletinului s-a schimbat de mai multe ori între 2010 și 2026; scriptul "
            "tratează toate variantele și se oprește cu eroare dacă acoperirea câmpurilor scade.",
            "Regenerare: <code>python3 scripts/financiara_01_02.py</code>.",
        ],
    }
    build_html(os.path.join(OUT, f"{COD}.html"), spec)
    print(f"OK {COD}: {len(d)} luni, {per_min} → {per_max}, "
          f"capitalizare {cap_now:.1f} mld. RON, tranzacționat {tr_now:.2f} mld. RON")


if __name__ == "__main__":
    main()
