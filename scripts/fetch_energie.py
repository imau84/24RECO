#!/usr/bin/env python3
"""
Energie — 15 statistici despre energia din România → src/data/energie/date.json
Grupate pe sursa datelor (un tab pe pagină pentru fiecare sursă):

  Eurostat            01 producția de electricitate pe surse      nrg_cb_pem
                      02 consum, import, export electricitate      nrg_cb_em (+ nrg_cb_pem)
                      04 eolian, solar, hidro                      nrg_cb_pem
                      05 bilanțul gazelor naturale                 nrg_cb_gasm
                      06 importuri/exporturi de gaze pe țări       nrg_ti_gasm + nrg_te_gasm
                      07 cărbunele                                 nrg_cb_sffm
                      09 țițeiul                                   nrg_cb_oilm (O4100_TOT)
                      10 livrări de produse petroliere             nrg_cb_oilm (GID_OBS)
                      12 inflația energiei (IAPC)                  prc_hicp_minr
                      13 prețurile producției, industria energiei  sts_inppd_m
                      14 producția industriei energetice           sts_inpr_m
                      15 prețuri finale electricitate și gaz       nrg_pc_202…205 (semestrial)
  Ember               03 cererea de electricitate și emisiile      monthly_full_release_long_format.csv
  Comisia Europeană   08 prețurile carburanților la pompă          Weekly Oil Bulletin (săptămânal → lunar)
  OPCOM               11 prețul angro al electricității (PZU)      export CSV zilnic → lunar

Bazat pe pachetul „Energie 01…15” (Excel + note metodologice). Capcanele de acolo sunt respectate:
  - nrg_cb_pem are defalcarea pe combustibili doar din 2017-01 → seriile derivate pornesc din 2017;
  - gaze: STK_CHG_MG e pozitiv la injecție; seria în TJ (GCV) merge din 2008, cea în mil. m³ doar din 2014;
  - motorina rutieră (O46711) e inclusă în motorina totală (O4671) — nu se adună;
  - IAPC: setul viu e prc_hicp_minr (dimensiunea coicop18), filtrat strict pe unit=I15;
  - indicii industriali: NSA la prețuri, SCA la producție — nu se amestecă;
  - prețuri finale: o singură bandă de consum per serie, taxa și moneda filtrate explicit;
  - Weekly Oil Bulletin: RO_exchange_rate = euro pentru un leu (pentru lei se împarte);
  - OPCOM: un fișier pe zi; indicele ROPEX publicat de OPCOM (ține cont de 24/96 de intervale și de schimbarea orei).
    Istoricul lunar stă în scripts/data/opcom_pzu_lunar.csv; la fiecare rulare se recalculează doar lunile neîncheiate.

Dacă un set nu poate fi descărcat, se păstrează versiunea veche din JSON.
Rulează lunar din GitHub Actions (.github/workflows/update-energie.yml).
Rulare: pip install requests pandas openpyxl ; python scripts/fetch_energie.py
"""
import calendar
import csv
import io
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import openpyxl
import pandas as pd
import requests

from fetch_eurostat_transport import parse_tsv
from fetch_oil_bulletin import HEADERS as WOB_HEADERS, history_url

OUT = Path("src/data/energie/date.json")
OPCOM_CSV = Path("scripts/data/opcom_pzu_lunar.csv")
ES_API = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
EMBER = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv"
OPCOM = "https://www.opcom.ro/rapoarte-pzu-raportMarketResults-export-csv/{d}/{m}/{y}/ro"
HEADERS = {"User-Agent": "24reco.com data pipeline (+https://24reco.com)"}
START = "2008-01"


# ── utilitare ───────────────────────────────────────────────────────────────

def get(url: str, *, timeout=180, headers=HEADERS, ok=lambda r: True) -> requests.Response:
    for i in range(4):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.ok and ok(r):
                return r
            print(f"  încercarea {i + 1}: HTTP {r.status_code} {r.text[:100]!r}")
        except requests.RequestException as e:
            print(f"  încercarea {i + 1}: {e}")
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"nu am putut descărca {url}")


def es(cod: str, query: str, start: str = START[:4]) -> dict:
    """Eurostat SDMX TSV → {cheie: {perioadă: (valoare, flag)}}."""
    r = get(f"{ES_API}/{cod}/{query}?format=TSV&startPeriod={start}", ok=lambda r: "TIME_PERIOD" in r.text[:500])
    per, d, f = parse_tsv(r.text)
    return {k: {p: (v, fl) for p, v, fl in zip(per, d[k], f[k]) if v is not None} for k in d}


def val(src: dict, k: str) -> dict:
    """Seria `k` ca {perioadă: valoare} (goală dacă lipsește)."""
    return {p: v for p, (v, _) in src.get(k, {}).items()}


def prov(src: dict, *chei) -> set:
    return {p for k in chei for p, (_, fl) in src.get(k, {}).items() if fl[:1] in ("p", "e")}


def suma(*serii: dict, de_la: str = "") -> dict:
    """Suma pe perioade; o perioadă intră doar dacă măcar o componentă are valoare."""
    per = set().union(*serii)
    return {p: sum(s.get(p) or 0 for s in serii) for p in per if p >= de_la and any(s.get(p) is not None for s in serii)}


def dif(a: dict, b: dict) -> dict:
    return {p: a[p] - b[p] for p in a if p in b}


def pondere(a: dict, total: dict) -> dict:
    return {p: a[p] / total[p] * 100 for p in a if total.get(p)}


def S(nume, valori, provizorii=(), **extra) -> dict:
    return {"nume": nume, "valori": valori, "provizorii": set(provizorii), **extra}


def rot(v, z):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(v, z) if z else int(round(v))


def construieste(meta: dict, serii: list) -> dict:
    """meta: key, scurt, icon, titlu, descriere, cod, freq, unitate, zecimale, agregare, note, url, sursa?, rata?"""
    serii = [s for s in serii if any(v is not None for v in s["valori"].values())]
    per = sorted(set().union(*(s["valori"] for s in serii)))
    plin = [p for p in per if any(s["valori"].get(p) is not None for s in serii)]
    per = per[per.index(plin[0]):per.index(plin[-1]) + 1]
    out = []
    for s in serii:
        z = s.get("zecimale", meta["zecimale"])
        r = {"nume": s["nume"], "valori": [rot(s["valori"].get(p), z) for p in per],
             "provizorii": [i for i, p in enumerate(per) if p in s["provizorii"]]}
        r.update({k: s[k] for k in ("unitate", "zecimale", "agregare") if k in s})
        out.append(r)
    lungime = {"M": 36, "Q": 12, "S": 8}[meta["freq"]]
    if len(per) < lungime:
        raise RuntimeError(f"serie prea scurtă ({len(per)} perioade) — sursa pare incompletă")
    return {**meta, "actualizat": date.today().isoformat(), "perioade": per, "serii": out}


# ── Eurostat ────────────────────────────────────────────────────────────────

def e01(meta):
    k = lambda s: f"M,{s},GWH,RO"
    d = es("nrg_cb_pem", "M.TOTAL+C0000+G3000+N9000+RA100+RA200+RA300+RA400+RA500_5160+CF_R+O4000XBIO+X9900.GWH.RO")
    v = {s: val(d, k(s)) for s in ("TOTAL", "C0000", "G3000", "N9000", "RA100", "RA200", "RA300", "RA400", "RA500_5160", "CF_R", "O4000XBIO", "X9900")}
    # defalcarea completă există doar din 2017-01; înainte doar TOTAL, N9000, RA100, RA300 au sens
    din17 = lambda x: {p: y for p, y in x.items() if p >= "2017-01"}
    pv = prov(d, *(k(s) for s in v))
    altele = suma(v["O4000XBIO"], v["X9900"], v["RA200"], v["RA500_5160"], v["CF_R"], de_la="2017-01")
    return construieste(meta, [
        S("Producție totală", v["TOTAL"], pv),
        S("Cărbune", din17(v["C0000"]), pv), S("Gaz natural", din17(v["G3000"]), pv),
        S("Nuclear", v["N9000"], pv), S("Hidro", v["RA100"], pv), S("Eolian", v["RA300"], pv),
        S("Solar", din17(v["RA400"]), pv), S("Altele (biomasă, petrol, alte surse)", altele, pv),
        S("Regenerabile (total)", suma(v["RA100"], v["RA300"], v["RA400"], v["RA200"], v["RA500_5160"], v["CF_R"], de_la="2017-01"), pv),
        S("Fosile (total)", suma(v["C0000"], v["G3000"], v["O4000XBIO"], de_la="2017-01"), pv),
    ])


def e02(meta):
    d = es("nrg_cb_em", "M.AIM+IMP+EXP+IMP_FROM_EU+EXP_TO_EU.E7000.GWH.RO")
    p = es("nrg_cb_pem", "M.TOTAL.GWH.RO")
    k = lambda b: f"M,{b},E7000,GWH,RO"
    pv = prov(d, *(k(b) for b in ("AIM", "IMP", "EXP")))
    imp, exp_, prod = val(d, k("IMP")), val(d, k("EXP")), val(p, "M,TOTAL,GWH,RO")
    return construieste(meta, [
        S("Consum (disponibil pentru piața internă)", val(d, k("AIM")), pv),
        S("Producție netă", prod, prov(p, "M,TOTAL,GWH,RO")),
        S("Importuri", imp, pv), S("Exporturi", exp_, pv),
        S("Import net (import − export)", dif(imp, exp_), pv),
        S("Importuri din UE", val(d, k("IMP_FROM_EU")), pv), S("Exporturi în UE", val(d, k("EXP_TO_EU")), pv),
    ])


def e04(meta):
    d = es("nrg_cb_pem", "M.TOTAL+RA100+RA300+RA400.GWH.RO", "2017")
    v = {s: val(d, f"M,{s},GWH,RO") for s in ("TOTAL", "RA100", "RA300", "RA400")}
    pv = prov(d, *(f"M,{s},GWH,RO" for s in v))
    es_ = suma(v["RA300"], v["RA400"])
    pct = dict(unitate="% din producție", zecimale=1, agregare="medie")
    return construieste(meta, [
        S("Eolian", v["RA300"], pv), S("Solar", v["RA400"], pv), S("Hidro", v["RA100"], pv),
        S("Eolian + solar", es_, pv),
        S("Eolian (% din producție)", pondere(v["RA300"], v["TOTAL"]), pv, **pct),
        S("Solar (% din producție)", pondere(v["RA400"], v["TOTAL"]), pv, **pct),
        S("Hidro (% din producție)", pondere(v["RA100"], v["TOTAL"]), pv, **pct),
        S("Eolian + solar (% din producție)", pondere(es_, v["TOTAL"]), pv, **pct),
    ])


def e05(meta):
    d = es("nrg_cb_gasm", "M.IPRD+IMP+EXP+IC_OBS+STK_CHG_MG+TI_EHG_MAP.G3000.TJ_GCV.RO")
    m3 = es("nrg_cb_gasm", "M.IPRD+IMP+IC_OBS.G3000.MIO_M3.RO", "2014")
    k = lambda b: f"M,{b},G3000,TJ_GCV,RO"
    km = lambda b: f"M,{b},G3000,MIO_M3,RO"
    pv = prov(d, *(k(b) for b in ("IPRD", "IMP", "EXP", "IC_OBS")))
    imp, exp_ = val(d, k("IMP")), val(d, k("EXP"))
    mm = dict(unitate="mil. m³", agregare="suma")
    return construieste(meta, [
        S("Consum intern", val(d, k("IC_OBS")), pv),
        S("Producție internă", val(d, k("IPRD")), pv),
        S("Importuri", imp, pv), S("Exporturi", exp_, pv), S("Import net (import − export)", dif(imp, exp_), pv),
        S("Variația stocurilor (+ injecție în depozite, − extracție)", val(d, k("STK_CHG_MG")), pv),
        S("Ars în centrale (electricitate și căldură)", val(d, k("TI_EHG_MAP")), pv),
        S("Consum intern (mil. m³)", val(m3, km("IC_OBS")), prov(m3, km("IC_OBS")), **mm),
        S("Producție internă (mil. m³)", val(m3, km("IPRD")), prov(m3, km("IPRD")), **mm),
        S("Importuri (mil. m³)", val(m3, km("IMP")), prov(m3, km("IMP")), **mm),
    ])


def e06(meta):
    imp_t = {"TOTAL": "Import total", "RU": "Import din Rusia", "BG": "Import din Bulgaria", "HU": "Import din Ungaria",
             "UA": "Import din Ucraina", "AT": "Import din Austria", "MD": "Import din Moldova", "TM": "Import din Turkmenistan"}
    exp_t = {"TOTAL": "Export total", "HU": "Export către Ungaria", "MD": "Export către Moldova",
             "BG": "Export către Bulgaria", "UA": "Export către Ucraina"}
    i = es("nrg_ti_gasm", f"M.G3000.{'+'.join(imp_t)}.TJ_GCV.RO")
    e = es("nrg_te_gasm", f"M.G3000.{'+'.join(exp_t)}.TJ_GCV.RO")
    k = lambda p: f"M,G3000,{p},TJ_GCV,RO"
    serii = [S(n, val(i, k(p)), prov(i, k(p))) for p, n in imp_t.items()]
    serii += [S(n, val(e, k(p)), prov(e, k(p))) for p, n in exp_t.items()]
    serii.insert(1, S("Import net (import − export)", dif(val(i, k("TOTAL")), val(e, k("TOTAL"))), prov(i, k("TOTAL")) | prov(e, k("TOTAL"))))
    return construieste(meta, serii)


def e07(meta):
    d = es("nrg_cb_sffm", "M.IPRD+IMP+EXP+TI_EHG_MAP+GID_OBS+STKCL_NAT.C0100+C0200+C0311.THS_T.RO")
    k = lambda b, s: f"M,{b},{s},THS_T,RO"
    v = lambda b, s: val(d, k(b, s))
    pv = prov(d, k("IPRD", "C0200"), k("TI_EHG_MAP", "C0200"))
    stoc = dict(agregare="medie")
    return construieste(meta, [
        S("Producție lignit", v("IPRD", "C0200"), pv), S("Producție huilă", v("IPRD", "C0100"), pv),
        S("Ars în centrale — lignit", v("TI_EHG_MAP", "C0200"), pv), S("Ars în centrale — huilă", v("TI_EHG_MAP", "C0100"), pv),
        S("Livrări interne lignit", v("GID_OBS", "C0200"), pv),
        S("Import huilă", v("IMP", "C0100"), pv), S("Import lignit", v("IMP", "C0200"), pv), S("Import cocs", v("IMP", "C0311"), pv),
        S("Export cărbune (lignit + huilă)", suma(v("EXP", "C0100"), v("EXP", "C0200")), pv),
        S("Stoc la final de lună — lignit", v("STKCL_NAT", "C0200"), pv, **stoc),
        S("Stoc la final de lună — huilă", v("STKCL_NAT", "C0100"), pv, **stoc),
    ])


def e09(meta):
    d = es("nrg_cb_oilm", "M.IPRD+IMP+EXP+RI_OBS+STK_CHG.O4100_TOT.THS_T.RO")
    k = lambda b: f"M,{b},O4100_TOT,THS_T,RO"
    pv = prov(d, *(k(b) for b in ("IPRD", "IMP", "RI_OBS")))
    imp, exp_ = val(d, k("IMP")), val(d, k("EXP"))
    return construieste(meta, [
        S("Producție internă", val(d, k("IPRD")), pv), S("Importuri", imp, pv), S("Exporturi", exp_, pv),
        S("Import net (import − export)", dif(imp, exp_), pv),
        S("Intrări în rafinării", val(d, k("RI_OBS")), pv), S("Variația stocurilor", val(d, k("STK_CHG")), pv),
    ])


def e10(meta):
    prod = {"O4671": "Motorină (total)", "O46711": "din care motorină rutieră", "O4652": "Benzină auto",
            "O4630": "GPL", "O4661": "Combustibil de aviație"}
    d = es("nrg_cb_oilm", f"M.GID_OBS.{'+'.join(prod)}.THS_T.RO")
    k = lambda s: f"M,GID_OBS,{s},THS_T,RO"
    pv = prov(d, *(k(s) for s in prod))
    rutier = suma(val(d, k("O46711")), val(d, k("O4652")), val(d, k("O4630")))  # O4671 NU se adună (include O46711)
    return construieste(meta, [S(n, val(d, k(s)), pv) for s, n in prod.items()] +
                        [S("Carburanți rutieri (motorină rutieră + benzină + GPL)", rutier, pv)])


def e12(meta):
    c = {"NRG": "Energie (total)", "ELC_GAS": "Electricitate, gaz, combustibili solizi și termie",
         "CP0451": "Electricitate", "CP0452": "Gaze", "CP0455": "Energie termică (căldură)", "CP0454": "Combustibili solizi (lemne, cărbune)",
         "FUEL": "Combustibili lichizi și carburanți", "CP0722": "Carburanți auto", "CP0453": "Combustibili lichizi (pentru încălzire)",
         "TOTAL": "Toate prețurile (pentru comparație)", "TOT_X_NRG": "Toate prețurile, fără energie"}
    d = es("prc_hicp_minr", f"M.I15.{'+'.join(c)}.RO", "2005")
    k = lambda x: f"M,I15,{x},RO"
    return construieste(meta, [S(n, val(d, k(x)), prov(d, k(x))) for x, n in c.items()])


def e13(meta):
    c = {"D35": "Electricitate, gaze, abur (producție și distribuție)", "C19": "Rafinarea petrolului",
         "B06": "Extracția țițeiului și gazelor", "B05": "Extracția cărbunelui",
         "B": "Industria extractivă (total)", "C": "Industria prelucrătoare (pentru comparație)"}
    d = es("sts_inppd_m", f"M.PRC_PRR_DOM.{'+'.join(c)}.NSA.I21.RO", "2005")
    k = lambda x: f"M,PRC_PRR_DOM,{x},NSA,I21,RO"
    return construieste(meta, [S(n, val(d, k(x)), prov(d, k(x))) for x, n in c.items()])


def e14(meta):
    c = {"D35": "Electricitate, gaze, abur", "B06": "Extracția țițeiului și gazelor", "C19": "Rafinarea petrolului",
         "B05": "Extracția cărbunelui", "B-D": "Toată industria (pentru comparație)"}
    d = es("sts_inpr_m", f"M.PRD.{'+'.join(c)}.SCA.I21.RO", "2005")
    k = lambda x: f"M,PRD,{x},SCA,I21,RO"
    return construieste(meta, [S(n, val(d, k(x)), prov(d, k(x))) for x, n in c.items()])


def e15(meta):
    tipuri = [("nrg_pc_204", "E7000", "TOT_KWH", "Electricitate — casnici"), ("nrg_pc_205", "E7000", "TOT_KWH", "Electricitate — firme"),
              ("nrg_pc_202", "G3000", "GJ20-199", "Gaz — casnici"), ("nrg_pc_203", "G3000", "GJ10000-99999", "Gaz — firme")]
    serii = []
    for cod, siec, banda, nume in tipuri:
        d = es(cod, f"S.{siec}.{banda}.KWH.I_TAX+X_TAX.EUR+NAC.RO+EU27_2020", "2007")
        k = lambda tax, cur, geo: f"S,{siec},{banda},KWH,{tax},{cur},{geo}"
        serii += [S(f"{nume}, România (euro/kWh)", val(d, k("I_TAX", "EUR", "RO"))),
                  S(f"{nume}, media UE (euro/kWh)", val(d, k("I_TAX", "EUR", "EU27_2020"))),
                  S(f"{nume}, România (lei/kWh)", val(d, k("I_TAX", "NAC", "RO")), unitate="lei/kWh"),
                  S(f"{nume}, România fără taxe (euro/kWh)", val(d, k("X_TAX", "EUR", "RO")))]
    return construieste(meta, serii)


# ── Ember ───────────────────────────────────────────────────────────────────

def e03(meta):
    print("  descarc fișierul Ember (~70 MB)…")
    r = get(EMBER, timeout=600, ok=lambda r: r.content[:200].count(b",") > 3)
    d = pd.read_csv(io.BytesIO(r.content), low_memory=False,
                    usecols=["Area", "Date", "Category", "Subcategory", "Variable", "Unit", "Value"])
    ro = d[d["Area"] == "Romania"].copy()
    if ro.empty:
        raise RuntimeError("fișierul Ember nu are rânduri pentru Romania")
    ro["Luna"] = ro["Date"].astype(str).str[:7]

    def v(cat, sub, var, unit):
        s = ro[(ro.Category == cat) & (ro.Subcategory == sub) & (ro.Variable == var) & (ro.Unit == unit)]
        if s.empty:
            raise RuntimeError(f"serie Ember lipsă: {cat}/{sub}/{var}/{unit}")
        return {p: float(x) for p, x in s.groupby("Luna")["Value"].last().items() if not pd.isna(x)}

    pct = dict(unitate="% din producție", zecimale=1, agregare="medie")
    mt = dict(unitate="milioane tone CO₂", zecimale=2)
    return construieste(meta, [
        S("Cererea de electricitate", v("Electricity demand", "Demand", "Demand", "TWh")),
        S("Producție (brută)", v("Electricity generation", "Total", "Total Generation", "TWh")),
        S("Import net", v("Electricity imports", "Electricity imports", "Net Imports", "TWh")),
        S("Emisii de CO₂ ale sectorului electric", v("Power sector emissions", "Total", "Total emissions", "mtCO2"), **mt),
        S("Emisii din cărbune", v("Power sector emissions", "Fuel", "Coal", "mtCO2"), **mt),
        S("Emisii din gaz", v("Power sector emissions", "Fuel", "Gas", "mtCO2"), **mt),
        S("Intensitate CO₂ (grame pe kWh)", v("Power sector emissions", "CO2 intensity", "CO2 intensity", "gCO2/kWh"),
          unitate="grame CO₂ pe kWh", zecimale=0, agregare="medie"),
        S("Energie curată (regenerabile + nuclear)", v("Electricity generation", "Aggregate fuel", "Clean", "%"), **pct),
        S("Combustibili fosili", v("Electricity generation", "Aggregate fuel", "Fossil", "%"), **pct),
        S("Eolian + solar", v("Electricity generation", "Aggregate fuel", "Wind and Solar", "%"), **pct),
    ])


# ── Comisia Europeană — Weekly Oil Bulletin ─────────────────────────────────

def e08(meta):
    url = history_url()
    print("  descarc", url)
    r = get(url, timeout=300, headers=WOB_HEADERS, ok=lambda r: r.content[:2] == b"PK")
    wb = openpyxl.load_workbook(io.BytesIO(r.content), read_only=True, data_only=True)

    def foaie(nume):
        rows = wb[nume].iter_rows(values_only=True)
        h = [str(x or "") for x in next(rows)]
        date_ = [x for x in rows if hasattr(x[0], "year")]  # ultimele rânduri au note cu text în coloana de dată
        return h, date_

    produse = {"euro95": "Benzină 95", "diesel": "Motorină", "LPG": "GPL"}
    h, rows = foaie("Prices with taxes")
    hw, rows_wo = foaie("Prices wo taxes")
    col = lambda hdr, n: hdr.index(n) if n in hdr else None
    i_rate = col(h, "RO_exchange_rate")
    if i_rate is None or col(h, "RO_price_with_tax_euro95") is None:
        raise RuntimeError("coloanele României lipsesc din Weekly Oil Bulletin")

    def lunar(rows_, idx, transf):
        acc = {}
        for x in rows_:
            v = x[idx] if idx is not None else None
            if isinstance(v, (int, float)) and v > 0:
                y = transf(v, x)
                if y is not None:
                    acc.setdefault(x[0].strftime("%Y-%m"), []).append(y)
        return {p: sum(a) / len(a) for p, a in acc.items() if p >= START}

    euro = lambda v, x: v / 1000  # €/1000 l → €/l
    lei = lambda v, x: v / 1000 / x[i_rate] if isinstance(x[i_rate], (int, float)) and x[i_rate] > 0 else None  # rata = € pentru 1 leu
    serii = [S(f"{n} (lei/litru)", lunar(rows, col(h, f"RO_price_with_tax_{p}"), lei), unitate="lei/litru") for p, n in produse.items()]
    serii += [S(f"{n} (euro/litru)", lunar(rows, col(h, f"RO_price_with_tax_{p}"), euro), zecimale=3) for p, n in produse.items()]
    serii += [S(f"{n} — media UE (euro/litru)", lunar(rows, col(h, f"EU_price_with_tax_{p}"), euro), zecimale=3) for p, n in produse.items()]
    serii += [S(f"{n} fără taxe (euro/litru)", lunar(rows_wo, col(hw, f"RO_price_wo_tax_{p}"), euro), zecimale=3) for p, n in produse.items()]
    azi = date.today().strftime("%Y-%m")
    for s in serii:  # luna în curs = medie parțială
        s["provizorii"] = {azi} & set(s["valori"])
    return construieste(meta, serii)


# ── OPCOM — PZU ─────────────────────────────────────────────────────────────

def opcom_zi(z: date) -> dict | None:
    try:
        r = requests.get(OPCOM.format(d=z.day, m=z.month, y=z.year), headers=HEADERS, timeout=60)
    except requests.RequestException:
        return None
    if not r.ok or "ROPEX_DAM_Base" not in r.text:
        return None  # zi fără sesiune: HTTP 200, dar fără blocul ROPEX
    idx, pret, in_tabel = {}, [], False
    for linie in r.text.splitlines():
        c = [x.strip().strip('"') for x in linie.split(",")]
        if c[0] in ("ROPEX_DAM_Base", "ROPEX_DAM_Peak", "ROPEX_DAM_Off_Peak") and len(c) > 1:
            idx[c[0]] = float(c[1])
        elif c[0] == "Interval":
            in_tabel = True
        elif in_tabel and c[0].isdigit() and len(c) > 1 and c[1]:
            pret.append(float(c[1]))
    if "ROPEX_DAM_Base" not in idx:
        return None
    return {"base": idx["ROPEX_DAM_Base"], "peak": idx.get("ROPEX_DAM_Peak"), "offpeak": idx.get("ROPEX_DAM_Off_Peak"),
            "max": max(pret) if pret else None, "min": min(pret) if pret else None}


def opcom_luna(an: int, luna: int, pana_la: date) -> dict | None:
    zile = [date(an, luna, z) for z in range(1, calendar.monthrange(an, luna)[1] + 1) if date(an, luna, z) <= pana_la]
    with ThreadPoolExecutor(max_workers=6) as ex:
        rez = [x for x in ex.map(opcom_zi, zile) if x]
    if not rez:
        return None
    med = lambda k: round(sum(x[k] for x in rez if x[k] is not None) / max(1, sum(x[k] is not None for x in rez)), 3)
    base = [x["base"] for x in rez]
    mins = [x["min"] for x in rez if x["min"] is not None]
    return {"luna": f"{an}-{luna:02d}", "base": med("base"), "peak": med("peak"), "offpeak": med("offpeak"),
            "max_zi": max(base), "min_zi": min(base),
            "max_interval": max((x["max"] for x in rez if x["max"] is not None), default=None),
            "min_interval": min(mins, default=None), "zile_negative": sum(m <= 0 for m in mins), "zile": len(rez)}


def e11(meta):
    rows = list(csv.DictReader(OPCOM_CSV.open(encoding="utf-8")))
    luni = {r["luna"]: r for r in rows}
    azi = date.today()
    # recalculăm de la prima lună neîncheiată din istoric (sau ultima lună) până la luna curentă
    # (doar în ultimele 3 luni: în istoric există luni cu zile lipsă la sursă, care nu se mai completează)
    recent = (azi.replace(day=1) - timedelta(days=62)).strftime("%Y-%m")
    incomplete = [l for l, r in luni.items() if l >= recent and int(r["zile"]) < calendar.monthrange(int(l[:4]), int(l[5:]))[1]]
    de_la = min(incomplete) if incomplete else max(luni)
    an, luna = int(de_la[:4]), int(de_la[5:])
    while (an, luna) <= (azi.year, azi.month):
        print(f"  OPCOM {an}-{luna:02d}…", flush=True)
        r = opcom_luna(an, luna, azi)
        if r:
            luni[r["luna"]] = {k: str(v) for k, v in r.items()}
        an, luna = (an + 1, 1) if luna == 12 else (an, luna + 1)
    with OPCOM_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(luni[k] for k in sorted(luni))

    f = lambda c: {l: float(r[c]) for l, r in luni.items() if r[c] not in ("", "None")}
    pv = {l for l, r in luni.items() if int(r["zile"]) < calendar.monthrange(int(l[:4]), int(l[5:]))[1]}
    zile = dict(unitate="zile", zecimale=0, agregare="suma")
    return construieste(meta, [
        S("Preț mediu (Base, toate orele)", f("base"), pv), S("Preț mediu la orele de vârf (Peak)", f("peak"), pv),
        S("Preț mediu în afara vârfului (Off-Peak)", f("offpeak"), pv),
        S("Cea mai scumpă zi", f("max_zi"), pv), S("Cea mai ieftină zi", f("min_zi"), pv),
        S("Cel mai mare preț pe un interval", f("max_interval"), pv), S("Cel mai mic preț pe un interval", f("min_interval"), pv),
        S("Zile cu preț zero sau negativ (măcar un interval)", f("zile_negative"), pv, **zile),
    ])


# ── configurație: tab-uri (surse) → subtab-uri (statistici) ─────────────────

ES = "https://ec.europa.eu/eurostat/databrowser/view/{}/default/table?lang=en"
GWH = dict(freq="M", unitate="GWh", zecimale=0, agregare="suma")
TEME = {
    "eurostat": {
        "label": "Eurostat", "icon": "🇪🇺",
        "intro": "Statistica oficială a UE, din datele trimise de INS și ministere: electricitate, gaze, cărbune, petrol, prețuri și industria energetică.",
        "seturi": [
            (e01, dict(key="productie", scurt="Producția de electricitate", icon="⚡", titlu="Producția de electricitate pe surse",
                       descriere="Câtă electricitate produce România în fiecare lună și din ce: hidro, nuclear, cărbune, gaz, vânt, soare. "
                                 "1 GWh = un milion de kWh, cât consumă ~400 de familii într-un an.",
                       cod="nrg_cb_pem", url=ES.format("nrg_cb_pem"), **GWH,
                       note=["Producție NETĂ (fără consumul propriu al centralelor).",
                             "Defalcarea pe combustibili (cărbune, gaz, solar) există doar din ianuarie 2017; înainte, doar totalul, nuclear, hidro și eolian.",
                             "„Altele” = petrol, biomasă și alte surse; regenerabilele includ hidro, eolian, solar, geotermal și biomasă.",
                             "Ultimele luni sunt provizorii."])),
            (e02, dict(key="consum", scurt="Consum, import și export", icon="🔌", titlu="Consumul, importul și exportul de electricitate",
                       descriere="Câtă electricitate consumă România, câtă produce și câtă cumpără sau vinde vecinilor. "
                                 "Import net pozitiv = am cumpărat mai mult decât am vândut.",
                       cod="nrg_cb_em", url=ES.format("nrg_cb_em"), **GWH,
                       note=["„Consumul” e energia disponibilă pentru piața internă (producție + import − export).",
                             "Iarna și în anii secetoși (hidro slab) România devine importator net.",
                             "Fluxurile cu UE sunt raportate separat doar în ultimii ani."])),
            (e04, dict(key="variabile", scurt="Eolian, solar și hidro", icon="🌬️", titlu="Sursele variabile: eolian, solar și hidro",
                       descriere="Cât produc vântul, soarele și apa și ce parte din toată electricitatea țării acoperă. "
                                 "Depind de vreme: solarul are vârf vara, hidro primăvara, eolianul iarna.",
                       cod="nrg_cb_pem", url=ES.format("nrg_cb_pem"), **GWH,
                       note=["Ponderile sunt calculate din producția netă totală a lunii.",
                             "Capacitățile instalate (MW) sunt publicate doar anual, de aceea nu apar aici.",
                             "Solarul crește foarte repede după 2023 (prosumatori și parcuri noi)."])),
            (e05, dict(key="gaze", scurt="Gazele naturale", icon="🔥", titlu="Bilanțul lunar al gazelor naturale",
                       descriere="Cât gaz extrage România, cât importă, cât consumă și cât pune în depozite (vara) sau scoate (iarna). "
                                 "1 TJ ≈ 26.000 m³ de gaz.",
                       cod="nrg_cb_gasm", url=ES.format("nrg_cb_gasm"), freq="M", unitate="TJ", zecimale=0, agregare="suma",
                       note=["Variația stocurilor: plus = gaz injectat în depozite (vara), minus = gaz scos din depozite (iarna).",
                             "Consum = producție + import − export − variația stocurilor.",
                             "Seria în milioane m³ începe abia în 2014; cea în TJ din 2008.",
                             "Ultimele luni sunt provizorii."])),
            (e06, dict(key="gaze-tari", scurt="Gaze: import și export pe țări", icon="🗺️", titlu="Importurile și exporturile de gaze, pe țări",
                       descriere="De la ce vecini intră gazul importat și către cine îl vindem. România nu are terminal de gaz lichefiat (GNL), deci tot importul vine prin conducte.",
                       cod="nrg_ti_gasm", url=ES.format("nrg_ti_gasm"), freq="M", unitate="TJ", zecimale=0, agregare="suma",
                       note=["„Partener” = țara din care intră fizic gazul, nu țara unde a fost extras: gazul din Bulgaria sau Ungaria poate fi de oriunde.",
                             "Importul direct din Rusia a încetat; din 2022 gazul vine mai ales prin Bulgaria și Ungaria.",
                             "Exportul către Moldova a crescut după 2022."])),
            (e07, dict(key="carbune", scurt="Cărbunele", icon="⛏️", titlu="Cărbunele: producție, import și ardere în centrale",
                       descriere="Cât lignit și huilă se extrag în România, cât se importă și cât se arde în termocentrale, în mii de tone.",
                       cod="nrg_cb_sffm", url=ES.format("nrg_cb_sffm"), freq="M", unitate="mii tone", zecimale=0, agregare="suma",
                       note=["Aproape tot cărbunele românesc e lignit din Oltenia, ars în centralele de la Rovinari, Turceni și Craiova.",
                             "Producția de huilă (Valea Jiului) a scăzut aproape de zero.",
                             "Stocurile sunt la final de lună (pentru ele, media anuală, nu suma)."])),
            (e09, dict(key="titei", scurt="Țițeiul", icon="🛢️", titlu="Țițeiul: producție, import și rafinare",
                       descriere="Cât petrol brut extrage România, cât importă și cât intră în rafinăriile Petrobrazi și Petromidia, în mii de tone.",
                       cod="nrg_cb_oilm", url=ES.format("nrg_cb_oilm"), freq="M", unitate="mii tone", zecimale=0, agregare="suma",
                       note=["Producția internă scade încet de ani de zile; peste două treimi din țițeiul rafinat e importat.",
                             "Lunile cu rafinare foarte mică sunt de obicei opriri planificate pentru revizie.",
                             "Ultimele luni sunt provizorii."])),
            (e10, dict(key="produse-petroliere", scurt="Benzină, motorină, GPL vândute", icon="⛽", titlu="Livrările interne de produse petroliere",
                       descriere="Câtă motorină, benzină, GPL și combustibil de avion s-au livrat pe piața din România, în mii de tone.",
                       cod="nrg_cb_oilm", url=ES.format("nrg_cb_oilm"), freq="M", unitate="mii tone", zecimale=0, agregare="suma",
                       note=["Motorina rutieră e inclusă în „Motorină (total)” — nu le aduna.",
                             "România consumă de aproape 5 ori mai multă motorină decât benzină (camioane și mașini diesel).",
                             "Livrări = vânzări pe piața internă, nu consum măsurat la pompă."])),
            (e12, dict(key="preturi", scurt="Inflația la energie", icon="🏷️", titlu="Prețurile energiei pentru consumatori (IAPC)",
                       descriere="Cât de scumpe sunt electricitatea, gazul, căldura, lemnele și carburanții pentru gospodării. "
                                 "Indice: 100 = prețurile din 2015; 250 înseamnă de 2,5 ori mai scump.",
                       cod="prc_hicp_minr", url=ES.format("prc_hicp_minr"), freq="M", unitate="indice, 2015 = 100", zecimale=1, agregare="medie",
                       note=["Plafonările și compensările din 2022–2025 se văd direct în serie: prețul plătit a crescut mai puțin decât cel de pe piață.",
                             "Compară cu „Toate prețurile”: dacă energia urcă mai repede, s-a scumpit peste inflație.",
                             "Indicele armonizat (IAPC), clasificarea COICOP 2018."])),
            (e13, dict(key="preturi-productie", scurt="Prețurile producătorilor", icon="🏭", titlu="Prețurile producției în industria energetică",
                       descriere="Cu cât își vând producția firmele care extrag cărbune, petrol și gaz, rafinăriile și producătorii de electricitate. "
                                 "Indice: 100 = 2021, anul dinaintea crizei energetice.",
                       cod="sts_inppd_m", url=ES.format("sts_inppd_m"), freq="M", unitate="indice, 2021 = 100", zecimale=1, agregare="medie",
                       note=["Prețuri pe piața internă, fără TVA.",
                             "Pentru extracția cărbunelui indicele lipsește în multe luni — golurile sunt reale, nu erori.",
                             "Serie neajustată sezonier."])),
            (e14, dict(key="productie-industrie", scurt="Producția industriei energetice", icon="📉", titlu="Producția industriei energetice",
                       descriere="Cât produc minele, sondele, rafinăriile și centralele, ca volum (fără efectul prețurilor). Indice: 100 = 2021.",
                       cod="sts_inpr_m", url=ES.format("sts_inpr_m"), freq="M", unitate="indice, 2021 = 100", zecimale=1, agregare="medie",
                       note=["Serii ajustate sezonier și după zilele lucrătoare: două luni la rând se pot compara direct.",
                             "Extracția cărbunelui a scăzut la mai puțin de o treime față de anii 2000."])),
            (e15, dict(key="preturi-finale", scurt="Prețul la factură (semestrial)", icon="🧾", titlu="Prețurile finale la electricitate și gaz",
                       descriere="Cât plătesc pe kWh gospodăriile și firmele pentru electricitate și gaz, cu toate taxele, comparat cu media UE. "
                                 "Eurostat publică aceste prețuri doar o dată la șase luni.",
                       cod="nrg_pc_204", url=ES.format("nrg_pc_204"), freq="S", unitate="euro/kWh", zecimale=4, agregare="medie",
                       note=["Semestrial: S1 = ianuarie–iunie, S2 = iulie–decembrie.",
                             "Electricitate: media tuturor consumatorilor. Gaz: banda tipică (casnici 20–199 GJ/an, firme 10.000–99.999 GJ/an).",
                             "Plafonările și compensările din 2022–2025 sunt incluse în prețuri.",
                             "Fără taxe = fără TVA, accize și alte taxe."])),
        ],
    },
    "ember": {
        "label": "Ember", "icon": "🌍",
        "intro": "Ember e un centru de analiză independent care publică lunar date despre electricitatea din toată lumea, inclusiv emisiile de CO₂.",
        "seturi": [
            (e03, dict(key="cerere-emisii", scurt="Cerere și emisii CO₂", icon="🌫️", titlu="Cererea de electricitate și emisiile sectorului",
                       descriere="Câtă electricitate cere România, câtă produce și cât CO₂ eliberează centralele. "
                                 "Intensitatea arată câte grame de CO₂ „costă” fiecare kWh.",
                       cod="Monthly electricity data", url="https://ember-energy.org/data/monthly-electricity-data/", sursa="Ember",
                       freq="M", unitate="TWh", zecimale=2, agregare="suma",
                       note=["Producția Ember e BRUTĂ; cea Eurostat e netă (cu ~8% mai mică — consumul propriu al centralelor).",
                             "Energie curată = regenerabile + nuclear.",
                             "Date Ember sub licență CC BY 4.0."])),
        ],
    },
    "comisia-europeana": {
        "label": "Comisia Europeană", "icon": "⛽",
        "intro": "Weekly Oil Bulletin: prețurile carburanților la pompă, raportate săptămânal de fiecare stat membru Comisiei Europene.",
        "seturi": [
            (e08, dict(key="carburanti", scurt="Prețurile la pompă", icon="⛽", titlu="Prețurile carburanților la pompă",
                       descriere="Cât costă un litru de benzină, motorină și GPL în România, cu și fără taxe, comparat cu media UE. Media lunară a prețurilor de luni.",
                       cod="Weekly Oil Bulletin", url="https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en",
                       sursa="Comisia Europeană (DG ENER)", freq="M", unitate="euro/litru", zecimale=2, agregare="medie",
                       note=["Prețuri medii naționale raportate de Ministerul Energiei, în fiecare luni.",
                             "Prețul în lei e calculat cu cursul folosit de Comisie în săptămâna respectivă.",
                             "Taxele (TVA + accize) sunt de regulă 40–50% din prețul benzinei.",
                             "Luna curentă e o medie parțială."])),
        ],
    },
    "opcom": {
        "label": "OPCOM", "icon": "⚖️",
        "intro": "OPCOM e bursa de energie a României. Pe Piața pentru Ziua Următoare (PZU) se stabilește în fiecare zi prețul angro al electricității pentru a doua zi.",
        "seturi": [
            (e11, dict(key="pzu", scurt="Prețul angro (PZU)", icon="💹", titlu="Prețul angro al electricității (PZU)",
                       descriere="Cât costă electricitatea pe bursă, la producători, în euro pe MWh (1 MWh = 1.000 kWh). "
                                 "100 euro/MWh înseamnă 10 eurocenți pe kWh, înainte de transport, distribuție și taxe.",
                       cod="ROPEX DAM", url="https://www.opcom.ro/rapoarte-pzu-raportMarketResults/ro", sursa="OPCOM",
                       freq="M", unitate="euro/MWh", zecimale=2, agregare="medie",
                       note=["Media lunară a indicelui zilnic ROPEX publicat de OPCOM.",
                             "Peak = orele de vârf de zi (8–20); Off-Peak = restul orelor.",
                             "Din 2025 piața are intervale de 15 minute; prețurile negative apar la prânz, când solarul produce mult.",
                             "Luna curentă e provizorie (nu s-a încheiat)."])),
        ],
    },
}


def main():
    vechi = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    rezultat, erori = {}, []
    for tkey, tema in TEME.items():
        v_tema = {s["key"]: s for s in vechi.get(tkey, {}).get("seturi", [])}
        lista = []
        for fn, meta in tema["seturi"]:
            print(f"[{tkey}/{meta['key']}] {meta['cod']}", flush=True)
            try:
                s = fn(meta)
                v = v_tema.get(meta["key"])
                if v and v["perioade"] == s["perioade"] and v["serii"] == s["serii"]:
                    s["actualizat"] = v["actualizat"]  # date neschimbate → fără commit inutil
                print(f"  ok: {len(s['perioade'])} perioade, {s['perioade'][0]} → {s['perioade'][-1]}, {len(s['serii'])} serii")
                lista.append(s)
            except Exception as e:  # păstrăm datele vechi ale setului
                erori.append(f"{meta['key']}: {e}")
                print(f"  EROARE: {e}")
                if meta["key"] in v_tema:
                    lista.append(v_tema[meta["key"]])
        rezultat[tkey] = {"label": tema["label"], "icon": tema["icon"], "intro": tema["intro"], "seturi": lista}
    if not any(t["seturi"] for t in rezultat.values()):
        sys.exit("::error::Niciun set nu a putut fi descărcat.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rezultat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scris {OUT} ({OUT.stat().st_size // 1024} KB)")
    if erori:
        print("::warning::Seturi nedescărcate (s-au păstrat datele vechi): " + "; ".join(erori))


if __name__ == "__main__":
    main()
