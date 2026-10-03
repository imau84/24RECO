#!/usr/bin/env python3
"""
Industrie — 6 statistici lunare pentru România → src/data/industrie/eurostat.json

  1. Producția industrială pe mari grupe       Eurostat sts_inpr_m (SCA)
  2. Producția industrială pe ramuri           Eurostat sts_inpr_m (CA)
  3. Prețurile producției industriale          Eurostat sts_inppd_m + sts_inppnd_m
  4. Salariați, ore lucrate, salarii           Eurostat sts_inlb_m
  5. Energie electrică pe surse                Ember — Monthly Electricity Data (CC BY 4.0)
  6. Consumul de energie electrică             energy-charts.info (Fraunhofer ISE, date ENTSO-E)

Rulează lunar din GitHub Actions (.github/workflows/update-eurostat-industrie.yml).
Bazat pe scripturile „Productie 0X_update.py”. Reguli, ca la transport:
  - flag-urile Eurostat „p”/„e” (provizoriu/estimat) se păstrează; „:” = nepublicat → null, niciodată 0;
  - dacă un set nu poate fi descărcat sau iese prea scurt, păstrăm versiunea veche a lui.

Rulare: pip install requests pandas ; python scripts/fetch_eurostat_industrie.py
"""
import io
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from fetch_eurostat_transport import HEADERS, descarca, parse_tsv

OUT = Path("src/data/industrie/eurostat.json")
START = "2015-01"
MIN_LUNI = 48  # sub atât, sursa pare incompletă → păstrăm datele vechi

EMBER = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv"
EC_PP = "https://api.energy-charts.info/public_power?country=ro&start={}-01-01&end={}-01-01"
EC_CBET = "https://api.energy-charts.info/cbet?country=ro&start={}-01-01&end={}-01-01"

MIG = "MIG_CAG+MIG_ING+MIG_DCOG+MIG_NDCOG+MIG_NRG_X_E"
SETURI = [
    {
        "key": "productie", "scurt": "Producția industrială",
        "titlu": "Indicele producției industriale",
        "descriere": "Cât produc fabricile, minele și centralele din România față de media lunară din 2021. "
                     "Peste 100 = mai mult decât în 2021, sub 100 = mai puțin. Este un indice de volum: scumpirile nu umflă cifra.",
        "cod": "sts_inpr_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_inpr_m", f"M.PRD.B-D+{MIG}.SCA.I21.RO")],
        "serii": {
            "M,PRD,B-D,SCA,I21,RO": "Toată industria",
            "M,PRD,MIG_CAG,SCA,I21,RO": "Bunuri de capital (utilaje, mașini)",
            "M,PRD,MIG_ING,SCA,I21,RO": "Bunuri intermediare (oțel, chimicale, plastic)",
            "M,PRD,MIG_DCOG,SCA,I21,RO": "Bunuri de consum durabile (mobilă, electrocasnice)",
            "M,PRD,MIG_NDCOG,SCA,I21,RO": "Bunuri de consum nedurabile (alimente, haine, medicamente)",
            "M,PRD,MIG_NRG_X_E,SCA,I21,RO": "Energie",
        },
        "note": ["Serie ajustată sezonier și după numărul de zile lucrătoare: se poate compara direct o lună cu luna precedentă.",
                 "Prăbușirea din aprilie 2020 (lockdown) este reală: uzinele auto au fost oprite.",
                 "Grupa „Energie” este fără apă și salubritate, ca să se potrivească perimetrului totalului (minerit, fabrici, energie).",
                 "Ultimele 2–3 luni sunt provizorii și se revizuiesc de regulă cu câteva zecimi."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_inpr_m/default/table?lang=en",
    },
    {
        "key": "ramuri", "scurt": "Producția pe ramuri",
        "titlu": "Producția industrială pe ramuri",
        "descriere": "Nouă ramuri ale industriei prelucrătoare, de la mașini și piese auto la mobilă și medicamente. "
                     "100 = media lunară din 2021; sub 100 înseamnă că ramura produce mai puțin decât atunci.",
        "cod": "sts_inpr_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_inpr_m", "M.PRD.C29+C27+C20+C24+C22+C13-C15+C31+C21+C26.CA.I21.RO")],
        "serii": {
            "M,PRD,C29,CA,I21,RO": "Mașini și piese auto",
            "M,PRD,C27,CA,I21,RO": "Echipamente electrice",
            "M,PRD,C20,CA,I21,RO": "Chimicale",
            "M,PRD,C24,CA,I21,RO": "Metalurgie",
            "M,PRD,C22,CA,I21,RO": "Cauciuc și mase plastice",
            "M,PRD,C13-C15,CA,I21,RO": "Textile, haine, încălțăminte",
            "M,PRD,C31,CA,I21,RO": "Mobilă",
            "M,PRD,C21,CA,I21,RO": "Medicamente",
            "M,PRD,C26,CA,I21,RO": "Electronice și calculatoare",
        },
        "note": ["Serie ajustată doar după zilele lucrătoare, NU sezonier: căderea din fiecare august (concediile din fabricile auto) și cea din decembrie sunt reale.",
                 "Mașinile și piesele auto sunt ramura cea mai volatilă: o oprire de linie la Mioveni sau Craiova se vede imediat în indice.",
                 "Fiecare ramură are propriul indice; ramurile nu se adună.",
                 "Ultimele două luni sunt provizorii."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_inpr_m/default/table?lang=en",
    },
    {
        "key": "preturi", "scurt": "Prețuri la poarta fabricii",
        "titlu": "Prețurile producției industriale",
        "descriere": "Cu cât vând fabricile din România, separat pentru clienții din țară și pentru export. "
                     "E prețul din poarta fabricii, fără TVA și fără adaos — scumpirile de aici ajung de obicei în magazine peste câteva luni. "
                     "100 = prețurile medii din 2021; 180 înseamnă cu 80% mai scump.",
        "cod": "sts_inppd_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_inppd_m", "M.PRC_PRR_DOM.B-E36+MIG_NRG+MIG_ING+MIG_CAG+MIG_COG.NSA.I21.RO"),
                  ("sts_inppnd_m", "M.PRC_PRR_NDOM.B-E36+MIG_NRG+MIG_ING+MIG_CAG+MIG_COG.NSA.I21.RO")],
        "serii": {
            "M,PRC_PRR_DOM,B-E36,NSA,I21,RO": "Toată industria — în țară",
            "M,PRC_PRR_NDOM,B-E36,NSA,I21,RO": "Toată industria — la export",
            "M,PRC_PRR_DOM,MIG_NRG,NSA,I21,RO": "Energie — în țară",
            "M,PRC_PRR_NDOM,MIG_NRG,NSA,I21,RO": "Energie — la export",
            "M,PRC_PRR_DOM,MIG_ING,NSA,I21,RO": "Bunuri intermediare — în țară",
            "M,PRC_PRR_NDOM,MIG_ING,NSA,I21,RO": "Bunuri intermediare — la export",
            "M,PRC_PRR_DOM,MIG_CAG,NSA,I21,RO": "Bunuri de capital — în țară",
            "M,PRC_PRR_NDOM,MIG_CAG,NSA,I21,RO": "Bunuri de capital — la export",
            "M,PRC_PRR_DOM,MIG_COG,NSA,I21,RO": "Bunuri de consum — în țară",
            "M,PRC_PRR_NDOM,MIG_COG,NSA,I21,RO": "Bunuri de consum — la export",
        },
        "note": ["Variația față de aceeași lună a anului trecut = „inflația din fabrici”.",
                 "Prețurile la export sunt în lei: dacă leul se depreciază, indicele urcă chiar dacă prețul în euro rămâne la fel.",
                 "Energia a explodat în 2021–2022 (criza gazelor și a electricității) și a tras după ea tot indicele — saltul e real.",
                 "Serie neajustată sezonier (la prețuri nu se aplică). Ultimele două luni sunt provizorii."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_inppd_m/default/table?lang=en",
    },
    {
        "key": "munca", "scurt": "Oameni, ore, salarii",
        "titlu": "Oameni, ore lucrate și salarii în industrie",
        "descriere": "Câți oameni lucrează în industrie, câte ore lucrează și câți bani primesc în total pe salarii — toate ca indice, 100 = media din 2021. "
                     "Pe scurt: tot mai puțini oameni, cu facturi de salarii tot mai mari.",
        "cod": "sts_inlb_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_inlb_m", "M.EMP+HW+WAGE.B-E36+C+MIG_CAG+MIG_ING+MIG_NDCOG+MIG_NRG.SCA.I21.RO")],
        "serii": {
            "M,EMP,B-E36,SCA,I21,RO": "Salariați — toată industria",
            "M,EMP,C,SCA,I21,RO": "Salariați — fabrici (industria prelucrătoare)",
            "M,EMP,MIG_CAG,SCA,I21,RO": "Salariați — bunuri de capital",
            "M,EMP,MIG_ING,SCA,I21,RO": "Salariați — bunuri intermediare",
            "M,EMP,MIG_NDCOG,SCA,I21,RO": "Salariați — bunuri de consum nedurabile",
            "M,EMP,MIG_NRG,SCA,I21,RO": "Salariați — energie",
            "M,HW,B-E36,SCA,I21,RO": "Ore lucrate — toată industria",
            "M,HW,C,SCA,I21,RO": "Ore lucrate — fabrici",
            "M,WAGE,B-E36,SCA,I21,RO": "Salarii plătite — toată industria",
            "M,WAGE,C,SCA,I21,RO": "Salarii plătite — fabrici",
        },
        # indicator calculat de noi: masa salarială / ore lucrate × 100
        "derivat": ("Cost salarial pe oră lucrată (calcul 24reco)", "M,WAGE,B-E36,SCA,I21,RO", "M,HW,B-E36,SCA,I21,RO"),
        "note": ["Salariile sunt în lei curenți: creșterea include inflația și majorările salariului minim.",
                 "„Cost salarial pe oră lucrată” e calculat de 24reco.com (salarii ÷ ore × 100). E o aproximare, nu o statistică oficială.",
                 "Serii ajustate sezonier și după zilele lucrătoare. Ultimele două luni sunt provizorii."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_inlb_m/default/table?lang=en",
    },
    {
        "key": "electricitate", "scurt": "Electricitate pe surse",
        "titlu": "Producția de energie electrică, pe surse",
        "descriere": "Câtă electricitate produce România în fiecare lună și din ce: nuclear, apă, cărbune, gaze, vânt, soare. "
                     "Pentru o fabrică asta nu e ecologie, ci cost: mixul decide cât plătește pe factură. 1 TWh = 1 miliard kWh.",
        "cod": "Ember", "sursa": "Ember — Monthly Electricity Data (CC BY 4.0)",
        "freq": "M", "unitate": "TWh", "zecimale": 2, "agregare": "suma",
        "note": ["Seria nu e ajustată sezonier: iarna se consumă mai mult, apa urcă primăvara, soarele are vârful vara.",
                 "Suma pe surse poate diferi puțin (sub 2%) de producția totală: Ember include în total și categorii mici nepublicate separat.",
                 "Import net pozitiv = România a cumpărat mai mult curent decât a vândut.",
                 "Datele ultimei luni sunt preliminare."],
        "url": "https://ember-energy.org/data/monthly-electricity-data/",
    },
    {
        "key": "consum", "scurt": "Consumul de electricitate",
        "titlu": "Consumul de energie electrică: vârfuri, goluri și schimburi la graniță",
        "descriere": "Cât consumă România în fiecare lună, cât de mare e vârful de seară și cât cumpărăm de la vecini. "
                     "Calculat de 24reco.com din datele la sfert de oră ale rețelei naționale.",
        "cod": "energy-charts.info", "sursa": "energy-charts.info (Fraunhofer ISE), date ENTSO-E / Transelectrica",
        "freq": "M", "unitate": "TWh", "zecimale": 2, "agregare": "suma",
        "note": ["Pozitiv la schimburi = import în România, negativ = export.",
                 "Până în 2021 datele sunt orare, din 2022 la 15 minute: vârfurile recente sunt măsurate mai fin.",
                 "Granița cu R. Moldova apare abia din martie 2022 (sincronizarea cu rețeaua europeană). Lunile anterioare sunt goale, nu zero.",
                 "Lunile cu date pentru mai puțin de 90% din ore sunt eliminate; luna în curs apare după ce se încheie.",
                 "Prețurile spot nu sunt incluse: licența sursei interzice reutilizarea lor."],
        "url": "https://energy-charts.info/",
    },
]

META = ("key", "scurt", "titlu", "descriere", "cod", "freq", "unitate", "zecimale", "agregare", "note", "url")


def rot(v, z):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(v, z) if z else int(round(v))


def taie(perioade: list, serii: list) -> list:
    """Indicii perioadelor ≥ START, sortate, fără perioadele goale de la coadă."""
    idx = sorted((i for i, p in enumerate(perioade) if p >= START), key=lambda i: perioade[i])
    while idx and all(s[idx[-1]] is None for s in serii):
        idx.pop()
    return idx


def iesire(cfg: dict, perioade: list, serii: list) -> dict:
    """serii: [{nume, valori(aliniat la perioade), provizorii(set de indici), unitate?, zecimale?, agregare?}]"""
    idx = taie(perioade, [s["valori"] for s in serii])
    if len(idx) < MIN_LUNI:
        raise RuntimeError(f"serie prea scurtă ({len(idx)} luni) — sursa pare incompletă")
    out = []
    for s in serii:
        z = s.get("zecimale", cfg["zecimale"])
        r = {"nume": s["nume"], "valori": [rot(s["valori"][i], z) for i in idx],
             "provizorii": [j for j, i in enumerate(idx) if i in s.get("provizorii", ())]}
        r.update({k: s[k] for k in ("unitate", "zecimale", "agregare") if k in s})
        out.append(r)
    return {**{k: cfg[k] for k in META}, **{k: cfg[k] for k in ("sursa", "rata") if k in cfg},
            "actualizat": date.today().isoformat(), "perioade": [perioade[i] for i in idx], "serii": out}


# ── Eurostat ────────────────────────────────────────────────────────────────

def eurostat(cfg: dict) -> dict:
    per, date_, fl = set(), {}, {}
    for cod, query in cfg["parti"]:
        p, d, f = parse_tsv(descarca(cod, query))
        for k in d:
            date_[k] = dict(zip(p, d[k]))
            fl[k] = dict(zip(p, f[k]))
        per.update(p)
    perioade = sorted(per)
    lipsa = [k for k in cfg["serii"] if k not in date_]
    if len(lipsa) == len(cfg["serii"]):
        raise RuntimeError(f"nicio serie găsită; chei primite: {list(date_)[:5]}")
    if lipsa:
        print(f"  ATENȚIE: serii lipsă: {lipsa}")
    serii = [{"nume": n,
              "valori": [date_[k].get(p) for p in perioade],
              "provizorii": {i for i, p in enumerate(perioade) if fl[k].get(p, "")[:1] in ("p", "e")}}
             for k, n in cfg["serii"].items() if k in date_]
    if "derivat" in cfg:
        nume, a, b = cfg["derivat"]
        if a in date_ and b in date_:
            va, vb = date_[a], date_[b]
            serii.append({"nume": nume,
                          "valori": [va[p] / vb[p] * 100 if va.get(p) is not None and vb.get(p) else None for p in perioade],
                          "provizorii": {i for i, p in enumerate(perioade) if (fl[a].get(p, "") + fl[b].get(p, ""))[:1] in ("p", "e")}})
    return iesire(cfg, perioade, serii)


# ── Ember ───────────────────────────────────────────────────────────────────

def ember(cfg: dict) -> dict:
    print("  descarc fișierul Ember (~70 MB)…")
    r = requests.get(EMBER, headers=HEADERS, timeout=600)
    r.raise_for_status()
    d = pd.read_csv(io.BytesIO(r.content), low_memory=False,
                    usecols=["Area", "Date", "Category", "Subcategory", "Variable", "Unit", "Value"])
    ro = d[d["Area"] == "Romania"].copy()
    if ro.empty:
        raise RuntimeError("fișierul Ember nu are rânduri pentru Romania")
    ro["Luna"] = ro["Date"].astype(str).str[:7]

    def serie(cat, sub, var, unit):
        s = ro[(ro["Category"] == cat) & (ro["Subcategory"] == sub) & (ro["Variable"] == var) & (ro["Unit"] == unit)]
        if s.empty:
            raise RuntimeError(f"serie lipsă: {cat}/{sub}/{var}/{unit}")
        return s.groupby("Luna")["Value"].last()

    # (nume, (categorie, subcategorie, variabilă, unitate), suprascrieri)
    spec = [
        ("Producție totală", ("Electricity generation", "Total", "Total Generation", "TWh"), {}),
        ("Consum (cerere)", ("Electricity demand", "Demand", "Demand", "TWh"), {}),
        ("Import net", ("Electricity imports", "Electricity imports", "Net Imports", "TWh"), {}),
        ("Nuclear", ("Electricity generation", "Fuel", "Nuclear", "TWh"), {}),
        ("Hidro (apă)", ("Electricity generation", "Fuel", "Hydro", "TWh"), {}),
        ("Cărbune", ("Electricity generation", "Fuel", "Coal", "TWh"), {}),
        ("Gaze naturale", ("Electricity generation", "Fuel", "Gas", "TWh"), {}),
        ("Eolian (vânt)", ("Electricity generation", "Fuel", "Wind", "TWh"), {}),
        ("Solar", ("Electricity generation", "Fuel", "Solar", "TWh"), {}),
        ("Biomasă", ("Electricity generation", "Fuel", "Bioenergy", "TWh"), {}),
        ("Pondere regenerabile", ("Electricity generation", "Aggregate fuel", "Renewables", "%"),
         {"unitate": "% din producție", "zecimale": 1, "agregare": "medie"}),
        ("Intensitate CO₂", ("Power sector emissions", "CO2 intensity", "CO2 intensity", "gCO2/kWh"),
         {"unitate": "grame CO₂ pe kWh", "zecimale": 0, "agregare": "medie"}),
    ]
    cols = {n: serie(*k) for n, k, _ in spec}
    perioade = sorted(set().union(*(c.index for c in cols.values())))
    serii = [{"nume": n, "valori": [None if pd.isna(cols[n].get(p)) else float(cols[n][p]) for p in perioade], **extra}
             for n, _, extra in spec]
    return iesire(cfg, perioade, serii)


# ── energy-charts.info ──────────────────────────────────────────────────────

def ec_get(url: str):
    time.sleep(3)  # API-ul limitează cererile dese (HTTP 429)
    for i in range(6):
        try:
            r = requests.get(url, headers=HEADERS, timeout=400)
            if r.ok:
                return r.json()
            print(f"  încercarea {i + 1}: HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  încercarea {i + 1}: {e}")
        time.sleep(15 * (i + 1))
    raise RuntimeError(f"nu am putut descărca {url}")


VECINI = {"Bulgaria": "Bulgaria", "Hungary": "Ungaria", "Moldova": "R. Moldova", "Serbia": "Serbia", "Ukraine": "Ucraina"}


def consum(cfg: dict) -> dict:
    pp_f, cb_f = [], []
    for y in range(2019, date.today().year + 1):
        d = ec_get(EC_PP.format(y, y + 1))
        s = {x["name"]: x["data"] for x in d["production_types"]}
        t = pd.to_datetime(d["unix_seconds"], unit="s", utc=True)
        pp_f.append(pd.DataFrame({"t": t, "load": s["Load"], "cb": s["Cross border electricity trading"],
                                  "rs": s.get("Renewable share of load", [None] * len(t))}))
        c = ec_get(EC_CBET.format(y, y + 1))
        cc = {x["name"]: x["data"] for x in c["countries"]}
        f = pd.DataFrame({"t": pd.to_datetime(c["unix_seconds"], unit="s", utc=True)})
        for k, n in VECINI.items():
            f[n] = cc.get(k, [None] * len(f))
        cb_f.append(f)
        print(f"  {y}: {len(t)} puncte")

    def pregateste(f):
        f = f.drop_duplicates(subset="t").sort_values("t").reset_index(drop=True)
        # durata fiecărei observații = până la următoarea (60 min până în 2021, 15 min după)
        f["h"] = f["t"].diff().shift(-1).dt.total_seconds().div(3600).clip(upper=1).fillna(0.25)
        f["Luna"] = f["t"].dt.tz_convert("Europe/Bucharest").dt.strftime("%Y-%m")
        return f

    pp = pregateste(pd.concat(pp_f))
    for c in ("load", "cb", "rs"):
        pp[c] = pd.to_numeric(pp[c], errors="coerce")
    pp = pp[pp["load"] > 0]  # sarcina 0 MW = date lipsă la sursă, nu consum real
    cb = pregateste(pd.concat(cb_f))

    rows = {}
    for luna, x in pp.groupby("Luna"):
        w = x["h"]
        rs = x["rs"].notna()
        rows[luna] = {
            "Consum total": (x["load"] * w).sum() / 1e6,
            "Consum mediu": (x["load"] * w).sum() / w.sum(),
            "Vârf de consum": x["load"].max(),
            "Consum minim": x["load"].min(),
            "Import net (toate granițele)": (x["cb"].fillna(0) * w).sum() / 1e6,
            "Pondere regenerabile în consum": (x["rs"] * w)[rs].sum() / w[rs].sum() if rs.any() else None,
            "_ore": w.sum(),
        }
    for luna, x in cb.groupby("Luna"):
        if luna in rows:
            for n in VECINI.values():
                v = pd.to_numeric(x[n], errors="coerce")
                # schimburile la graniță vin în GW → ×ore / 1000 = TWh
                rows[luna][n] = (v * x["h"]).sum() / 1e3 if v.notna().any() else None
    perioade = []
    for luna in sorted(rows):
        ore = pd.Period(luna, "M").days_in_month * 24
        if rows[luna]["_ore"] / ore >= 0.9:
            perioade.append(luna)
    if perioade and perioade[-1] >= date.today().strftime("%Y-%m"):
        perioade.pop()  # luna în curs nu e completă
    r = rows

    def col(n):
        return [r[p].get(n) for p in perioade]

    for p in perioade:
        r[p]["Factor de încărcare"] = r[p]["Consum mediu"] / r[p]["Vârf de consum"] * 100
    MW = {"unitate": "MW", "zecimale": 0, "agregare": "medie"}
    serii = [
        {"nume": "Consum total", "valori": col("Consum total")},
        {"nume": "Consum mediu", "valori": col("Consum mediu"), **MW},
        {"nume": "Vârf de consum", "valori": col("Vârf de consum"), **MW},
        {"nume": "Consum minim (golul lunii)", "valori": col("Consum minim"), **MW},
        {"nume": "Factor de încărcare a rețelei", "valori": col("Factor de încărcare"),
         "unitate": "% (consum mediu ÷ vârf)", "zecimale": 1, "agregare": "medie"},
        {"nume": "Pondere regenerabile în consum", "valori": col("Pondere regenerabile în consum"),
         "unitate": "% din consum", "zecimale": 1, "agregare": "medie"},
        {"nume": "Import net (toate granițele)", "valori": col("Import net (toate granițele)")},
    ] + [{"nume": f"Schimb cu {n}", "valori": col(n), "zecimale": 3} for n in VECINI.values()]
    return iesire(cfg, perioade, serii)


SURSE = {"electricitate": ember, "consum": consum}


def main():
    vechi = {}
    if OUT.exists():
        vechi = {s["key"]: s for s in json.loads(OUT.read_text(encoding="utf-8"))["seturi"]}
    seturi, erori = [], []
    for cfg in SETURI:
        print(f"[{cfg['key']}] {cfg['cod']}")
        try:
            s = SURSE.get(cfg["key"], eurostat)(cfg)
            v = vechi.get(cfg["key"])
            if v and v["perioade"] == s["perioade"] and v["serii"] == s["serii"]:
                s["actualizat"] = v["actualizat"]  # date neschimbate → fără commit inutil
            print(f"  ok: {len(s['perioade'])} luni, {s['perioade'][0]} → {s['perioade'][-1]}")
            seturi.append(s)
        except Exception as e:  # păstrăm datele vechi ale setului
            erori.append(f"{cfg['key']}: {e}")
            print(f"  EROARE: {e}")
            if cfg["key"] in vechi:
                seturi.append(vechi[cfg["key"]])
    if not seturi:
        sys.exit("::error::Niciun set nu a putut fi descărcat.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seturi": seturi}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scris {OUT} ({OUT.stat().st_size // 1024} KB)")
    if erori:
        print("::warning::Seturi nedescărcate (s-au păstrat datele vechi): " + "; ".join(erori))


if __name__ == "__main__":
    main()
