#!/usr/bin/env python3
"""
Transport — 5 statistici Eurostat pentru România → src/data/transport/eurostat.json

  1. Cifra de afaceri în transport și depozitare   sts_setu_m     lunar
  2. Pasageri aerieni                               avia_paoc      lunar
  3. Marfă și poștă aeriană                         avia_gooc      lunar
  4. Prețuri de consum în transport (IAPC)          prc_hicp_minr  lunar
  5. Trafic portuar maritim                         mar_go_qm      trimestrial

Rulează lunar din GitHub Actions (.github/workflows/update-eurostat-transport.yml).
Bazat pe scripturile „Transport 0X - ….py”: același endpoint TSV (SDMX 2.1) și aceleași reguli:
  - valorile pot avea flag-uri (p = provizoriu, e = estimat, b = ruptură de serie) → păstrăm „p”/„e”;
  - „:” = nepublicat → null, niciodată 0;
  - dacă un set nu poate fi descărcat, păstrăm versiunea veche a lui (jobul nu strică datele existente).

Rulare: pip install requests ; python scripts/fetch_eurostat_transport.py
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

OUT = Path("src/data/transport/eurostat.json")
API = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
START = "2015"
HEADERS = {"User-Agent": "24reco.com data pipeline (+https://24reco.com)"}  # fără Accept: text/plain → Eurostat răspunde 406

SETURI = [
    {
        "key": "cifra", "scurt": "Cifra de afaceri",
        "titlu": "Cifra de afaceri în transport și depozitare",
        "descriere": "Cât încasează firmele de transport și depozitare, ca indice: 100 = media lunară din 2021. "
                     "150 înseamnă cu 50% mai mult decât în 2021. Valorile sunt în lei curenți, deci creșterea include și scumpirile.",
        "cod": "sts_setu_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "query": "M.NETTUR.H+H49+H50+H51+H52+H53.SCA.I21.RO",
        "serii": {
            "M,NETTUR,H,SCA,I21,RO": "Total transport și depozitare",
            "M,NETTUR,H49,SCA,I21,RO": "Transport rutier, feroviar și prin conducte",
            "M,NETTUR,H50,SCA,I21,RO": "Transport pe apă",
            "M,NETTUR,H51,SCA,I21,RO": "Transport aerian",
            "M,NETTUR,H52,SCA,I21,RO": "Depozitare și servicii auxiliare",
            "M,NETTUR,H53,SCA,I21,RO": "Poștă și curierat",
        },
        "note": ["Serie ajustată sezonier și după numărul de zile lucrătoare: se poate compara direct o lună cu luna precedentă.",
                 "Fiecare ramură are propriul indice; totalul nu este suma ramurilor.",
                 "Transportul aerian a scăzut aproape la zero în 2020 (pandemia), așa că creșterile din 2021 sunt foarte mari."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/STS_SETU_M/default/table?lang=en",
    },
    {
        "key": "pasageri", "scurt": "Pasageri aerieni",
        "titlu": "Pasageri aerieni pe aeroporturile din România",
        "descriere": "Câți pasageri au plecat sau au sosit pe aeroporturile din România. "
                     "Un zbor intern e numărat de două ori (la plecare și la sosire).",
        "cod": "avia_paoc", "freq": "M", "unitate": "pasageri", "zecimale": 0, "agregare": "suma",
        "query": "M.PAS.PAS_CRD.TOTAL+NAT+INTL.TOTAL.RO",
        "serii": {
            "M,PAS,PAS_CRD,TOTAL,TOTAL,RO": "Total pasageri",
            "M,PAS,PAS_CRD,INTL,TOTAL,RO": "Zboruri internaționale",
            "M,PAS,PAS_CRD,NAT,TOTAL,RO": "Zboruri interne",
        },
        "note": ["Aprilie–iunie 2020: traficul aerian aproape oprit din cauza pandemiei.",
                 "Include zborurile regulate și charter."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/AVIA_PAOC/default/table?lang=en",
    },
    {
        "key": "marfa_aer", "scurt": "Marfă aeriană",
        "titlu": "Marfă și poștă transportate pe calea aerului",
        "descriere": "Câte tone de marfă și colete poștale au fost încărcate sau descărcate pe aeroporturile din România.",
        "cod": "avia_gooc", "freq": "M", "unitate": "tone", "zecimale": 0, "agregare": "suma",
        "query": "M.T.FRM_LD_NLD+FRM_LD+FRM_NLD.TOTAL.TOTAL+NAT+INTL.RO",
        "serii": {
            "M,T,FRM_LD_NLD,TOTAL,TOTAL,RO": "Total (încărcată + descărcată)",
            "M,T,FRM_NLD,TOTAL,TOTAL,RO": "Descărcată (sosită în România)",
            "M,T,FRM_LD,TOTAL,TOTAL,RO": "Încărcată (plecată din România)",
            "M,T,FRM_LD_NLD,TOTAL,INTL,RO": "Zboruri internaționale",
            "M,T,FRM_LD_NLD,TOTAL,NAT,RO": "Zboruri interne",
        },
        "note": ["Marfa care sosește în România e de obicei mai multă decât cea care pleacă."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/AVIA_GOOC/default/table?lang=en",
    },
    {
        "key": "preturi", "scurt": "Prețuri transport",
        "titlu": "Prețuri de consum în transport",
        "descriere": "Cât de scump e transportul pentru populație: mașini, carburanți, service și bilete. "
                     "Indice: 100 = prețurile medii din 2025. 110 înseamnă cu 10% mai scump decât în 2025.",
        "cod": "prc_hicp_minr", "freq": "M", "unitate": "indice, 2025 = 100", "zecimale": 1, "agregare": "medie",
        "query": "M.I25.CP07+CP07221+CP07222+CP071+CP0723+CP0731+CP0733.RO",
        "serii": {
            "M,I25,CP07,RO": "Transport — total",
            "M,I25,CP07221,RO": "Motorină",
            "M,I25,CP07222,RO": "Benzină",
            "M,I25,CP071,RO": "Cumpărarea unei mașini",
            "M,I25,CP0723,RO": "Service și reparații auto",
            "M,I25,CP0731,RO": "Bilete de tren",
            "M,I25,CP0733,RO": "Bilete de avion",
        },
        "note": ["Indicele armonizat al prețurilor de consum (IAPC), calculat la fel în toate țările UE.",
                 "Variația față de aceeași lună a anului trecut = rata anuală a inflației pentru acel produs.",
                 "Din 2026, Eurostat folosește clasificarea COICOP 2018 și baza 2025 = 100 (setul prc_hicp_minr); "
                 "seria a fost recalculată retroactiv, așa că anii vechi se compară direct."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/PRC_HICP_MINR/default/table?lang=en",
    },
    {
        "key": "porturi", "scurt": "Porturi maritime",
        "titlu": "Mărfuri în porturile maritime",
        "descriere": "Câte mii de tone de mărfuri au trecut prin porturile maritime românești (în principal Constanța), pe trimestre.",
        "cod": "mar_go_qm", "freq": "Q", "unitate": "mii tone", "zecimale": 0, "agregare": "suma",
        "query": "Q.TOTAL+IN+OUT.TOTAL+INTL_IEU27_2020+INTL_XEU27_2020.THS_T.RO",
        "serii": {
            "Q,TOTAL,TOTAL,THS_T,RO": "Total mărfuri",
            "Q,IN,TOTAL,THS_T,RO": "Descărcate (intrate în țară)",
            "Q,OUT,TOTAL,THS_T,RO": "Încărcate (plecate din țară)",
            "Q,TOTAL,INTL_XEU27_2020,THS_T,RO": "Cu țări din afara UE",
            "Q,TOTAL,INTL_IEU27_2020,THS_T,RO": "Cu țări din UE",
        },
        "note": ["Date trimestriale; Eurostat le publică cu o întârziere de aproximativ 5–6 luni.",
                 "Defalcarea UE / non-UE există din 2020."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/MAR_GO_QM/default/table?lang=en",
    },
]


def descarca(cod: str, query: str) -> str:
    url = f"{API}/{cod}/{query}?format=TSV&startPeriod={START}"
    for i in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=120)
            if r.ok and "TIME_PERIOD" in r.text[:500]:
                return r.text
            print(f"  încercarea {i + 1}: HTTP {r.status_code} {r.text[:120]!r}")
        except requests.RequestException as e:
            print(f"  încercarea {i + 1}: {e}")
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"nu am putut descărca {url}")


def parse_tsv(text: str):
    """Rând 1: 'dim1,dim2,…\\TIME_PERIOD<TAB>2019-01<TAB>…'; apoi 'COD1,COD2,…<TAB>88.1 p<TAB>: …'."""
    linii = [l for l in text.replace("\r", "").split("\n") if l.strip()]
    perioade = [c.strip() for c in linii[0].split("\t")[1:]]
    date_, flaguri = {}, {}
    for l in linii[1:]:
        cel = l.split("\t")
        vals, fl = [], []
        for c in cel[1:]:
            c = c.strip()
            if not c or c.startswith(":"):
                vals.append(None); fl.append("")
                continue
            p = c.split()
            try:
                vals.append(float(p[0]))
            except ValueError:
                vals.append(None)
            fl.append(p[1] if len(p) > 1 else "")
        vals += [None] * (len(perioade) - len(vals))
        fl += [""] * (len(perioade) - len(fl))
        date_[cel[0].strip()] = vals[:len(perioade)]
        flaguri[cel[0].strip()] = fl[:len(perioade)]
    return perioade, date_, flaguri


def construieste(cfg: dict) -> dict:
    perioade, date_, flaguri = parse_tsv(descarca(cfg["cod"], cfg["query"]))
    lipsa = [k for k in cfg["serii"] if k not in date_]
    if len(lipsa) == len(cfg["serii"]):
        raise RuntimeError(f"nicio serie găsită; chei primite: {list(date_)[:5]}")
    if lipsa:
        print(f"  ATENȚIE: serii lipsă: {lipsa}")
    ordine = sorted(range(len(perioade)), key=lambda i: perioade[i])
    serii = [k for k in cfg["serii"] if k in date_]
    # tăiem perioadele goale de la coadă (Eurostat anunță coloanele înainte să aibă date)
    ultim = max((i for i in ordine if any(date_[k][i] is not None for k in serii)), key=lambda i: perioade[i])
    ordine = [i for i in ordine if perioade[i] <= perioade[ultim]]
    z = cfg["zecimale"]
    rot = (lambda v: None if v is None else (round(v, z) if z else int(round(v))))
    return {
        **{k: cfg[k] for k in ("key", "scurt", "titlu", "descriere", "cod", "freq", "unitate", "zecimale", "agregare", "note", "url")},
        "actualizat": date.today().isoformat(),
        "perioade": [perioade[i] for i in ordine],
        "serii": [{
            "nume": cfg["serii"][k],
            "valori": [rot(date_[k][i]) for i in ordine],
            # doar flag-urile utile pentru cititor: provizoriu / estimat
            "provizorii": [j for j, i in enumerate(ordine) if flaguri[k][i][:1] in ("p", "e")],
        } for k in serii],
    }


def main():
    vechi = {}
    if OUT.exists():
        vechi = {s["key"]: s for s in json.loads(OUT.read_text(encoding="utf-8"))["seturi"]}
    seturi, erori = [], []
    for cfg in SETURI:
        print(f"[{cfg['key']}] {cfg['cod']}")
        try:
            s = construieste(cfg)
            v = vechi.get(cfg["key"])
            if v and v["perioade"] == s["perioade"] and v["serii"] == s["serii"]:
                s["actualizat"] = v["actualizat"]  # date neschimbate → fără commit inutil
            print(f"  ok: {len(s['perioade'])} perioade, ultima {s['perioade'][-1]}")
            seturi.append(s)
        except Exception as e:  # păstrăm datele vechi ale setului
            erori.append(f"{cfg['key']}: {e}")
            print(f"  EROARE: {e}")
            if cfg["key"] in vechi:
                seturi.append(vechi[cfg["key"]])
    if not seturi:
        sys.exit("::error::Niciun set Eurostat nu a putut fi descărcat.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"sursa": "Eurostat", "seturi": seturi}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scris {OUT} ({OUT.stat().st_size // 1024} KB)")
    if erori:
        print("::warning::Seturi nedescărcate (s-au păstrat datele vechi): " + "; ".join(erori))


if __name__ == "__main__":
    main()
