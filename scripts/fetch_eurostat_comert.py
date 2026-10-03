#!/usr/bin/env python3
"""
Comerț — 5 statistici lunare pentru România → src/data/comert/eurostat.json

  1. Vânzările cu amănuntul pe categorii       Eurostat sts_trtu_m
  2. Comerțul online față de magazine          Eurostat sts_trtu_m
  3. Inflația pe grupe, România vs. UE27       Eurostat prc_hicp_minr (rata anuală)
  4. Creditele populației (solduri)            BCE BSI (raportare BNR) + curs EXR
  5. Dobânzile la creditele noi                BCE MIR (raportare BNR)

Rulează lunar din GitHub Actions (.github/workflows/update-eurostat-comert.yml).
Bazat pe scripturile „Comert 0X_update.py”. Folosește aceleași funcții ca scripts/fetch_eurostat_industrie.py
(flag-uri p/e păstrate, perioadele goale tăiate, setul vechi păstrat dacă descărcarea eșuează).

Rulare: pip install requests pandas ; python scripts/fetch_eurostat_comert.py
"""
import csv
import io
import json
import sys
import time
from pathlib import Path

import requests

from fetch_eurostat_industrie import HEADERS, eurostat, iesire

OUT = Path("src/data/comert/eurostat.json")
ECB = "https://data-api.ecb.europa.eu/service/data"
ECB_START = "2015-01"

SETURI = [
    {
        "key": "vanzari", "scurt": "Pe categorii",
        "titlu": "Vânzările cu amănuntul",
        "descriere": "Cât cumpără românii din magazine, benzinării și online, în cantitate (nu în lei): 100 = media lunară din 2021. "
                     "Scumpirile sunt scoase din calcul, deci 117 înseamnă cu 17% mai multe produse vândute decât în 2021.",
        "cod": "sts_trtu_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_trtu_m", "M.VOL_SLS.G47+G47_FOOD+G47_NFOOD_X_G473+G473.CA.I21.RO")],
        "serii": {
            "M,VOL_SLS,G47,CA,I21,RO": "Tot comerțul cu amănuntul",
            "M,VOL_SLS,G47_FOOD,CA,I21,RO": "Alimente, băuturi și tutun",
            "M,VOL_SLS,G47_NFOOD_X_G473,CA,I21,RO": "Produse nealimentare (fără carburanți)",
            "M,VOL_SLS,G473,CA,I21,RO": "Carburanți",
        },
        "note": ["Serie ajustată doar după zilele lucrătoare, NU sezonier: decembrie e mereu vârf, februarie minim. Compară cu aceeași lună din anul trecut.",
                 "Aprilie–mai 2020 (carantina) e o prăbușire reală, nu o eroare.",
                 "Nu include vânzările de mașini și motociclete.",
                 "Eurostat revizuiește des ultimele 2–3 luni."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_trtu_m/default/table?lang=en",
    },
    {
        "key": "online", "scurt": "Online vs. magazine",
        "titlu": "Comerțul online față de magazine",
        "descriere": "Cum evoluează vânzările firmelor care vând în principal online sau prin poștă, comparat cu supermarketurile și cu tot comerțul. "
                     "100 = media lunară din 2021; valorile arată cantitatea vândută, nu banii.",
        "cod": "sts_trtu_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_trtu_m", "M.VOL_SLS.G4791+G479+G47+G471.CA.I21.RO")],
        "serii": {
            "M,VOL_SLS,G4791,CA,I21,RO": "Magazine online și prin poștă",
            "M,VOL_SLS,G479,CA,I21,RO": "Vânzări în afara magazinelor (total)",
            "M,VOL_SLS,G471,CA,I21,RO": "Supermarketuri și magazine generale",
            "M,VOL_SLS,G47,CA,I21,RO": "Tot comerțul cu amănuntul",
        },
        "note": ["În fiecare noiembrie online-ul sare cu peste 50% față de octombrie: e Black Friday, nu o eroare.",
                 "Un supermarket care vinde și pe site rămâne la „magazine”, deci seria online subestimează comerțul electronic real.",
                 "Indicele arată evoluția față de 2021, nu cât cântărește online-ul din total.",
                 "Serie neajustată sezonier. Eurostat revizuiește ultimele luni."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_trtu_m/default/table?lang=en",
    },
    {
        "key": "inflatie", "scurt": "România vs. UE",
        "titlu": "Inflația pe grupe de produse: România față de media UE",
        "descriere": "Cu cât s-au scumpit lucrurile față de aceeași lună a anului trecut: alimente, haine și electrocasnice, energie și servicii. "
                     "8% înseamnă că ce costa 100 de lei acum un an costă acum 108 lei.",
        "cod": "prc_hicp_minr", "freq": "M", "unitate": "% față de aceeași lună a anului trecut", "zecimale": 1, "agregare": "medie",
        "rata": True,
        "parti": [("prc_hicp_minr", "M.RCH_A.TOTAL+FOOD+IGD_NNRG+NRG+SERV.RO+EU27_2020")],
        "serii": {
            "M,RCH_A,TOTAL,RO": "România — toate produsele",
            "M,RCH_A,FOOD,RO": "România — alimente, băuturi, tutun",
            "M,RCH_A,IGD_NNRG,RO": "România — haine, electrocasnice, alte bunuri",
            "M,RCH_A,NRG,RO": "România — energie (curent, gaze, carburanți)",
            "M,RCH_A,SERV,RO": "România — servicii",
            "M,RCH_A,TOTAL,EU27_2020": "UE — toate produsele",
            "M,RCH_A,FOOD,EU27_2020": "UE — alimente, băuturi, tutun",
            "M,RCH_A,IGD_NNRG,EU27_2020": "UE — haine, electrocasnice, alte bunuri",
            "M,RCH_A,NRG,EU27_2020": "UE — energie",
            "M,RCH_A,SERV,EU27_2020": "UE — servicii",
        },
        "note": ["Indicele armonizat (IAPC), calculat la fel în toate țările UE; diferă cu 0,2–0,5 puncte de inflația anunțată de INS.",
                 "Creșterea TVA de la 19% la 21% (august 2025) și scoaterea plafonării la curent (iulie 2025) au urcat brusc inflația; după 12 luni efectul iese din calcul și rata scade fără ca prețurile să scadă.",
                 "Din 2026 Eurostat publică seria în setul prc_hicp_minr (clasificarea COICOP 2018)."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table?lang=en",
    },
    {
        "key": "credite", "scurt": "Cât datorăm băncilor",
        "titlu": "Creditele populației",
        "descriere": "Cât au de dat înapoi românii băncilor la sfârșitul fiecărei luni: credite de consum (nevoi personale, carduri, rate la produse), "
                     "credite pentru locuințe și altele. Sumele sunt în milioane de euro; jos găsești și echivalentul în miliarde de lei.",
        "cod": "BCE BSI", "sursa": "Banca Centrală Europeană (date raportate de BNR)",
        "freq": "M", "unitate": "milioane euro", "zecimale": 0, "agregare": "medie",
        "bsi": [("A20", "Total credite ale populației"), ("A21", "Credite pentru consum"),
                ("A22", "Credite pentru locuințe"), ("A23", "Alte credite")],
        "lei": [("A20", "Total credite — în lei"), ("A21", "Credite pentru consum — în lei")],
        "note": ["Sunt solduri (cât mai e de plătit), nu credite noi acordate în luna respectivă.",
                 "BCE exprimă totul în euro: când leul se depreciază, soldul în euro scade chiar dacă în lei a crescut. Seriile „în lei” corectează asta (curs mediu lunar BCE).",
                 "Ultima lună e provizorie; BNR mai revizuiește istoricul."],
        "url": "https://data.ecb.europa.eu/data/datasets/BSI/BSI.M.RO.N.A.A21.A.1.U6.2250.Z01.E",
    },
    {
        "key": "dobanzi", "scurt": "Dobânzi",
        "titlu": "Dobânzile la creditele noi",
        "descriere": "Ce dobândă pe an plătește cine se împrumută în luna respectivă, în lei: credite de consum, carduri de credit, credite pentru casă. "
                     "Pentru comparație: cât primești pe banii ținuți în contul curent.",
        "cod": "BCE MIR", "sursa": "Banca Centrală Europeană (date raportate de BNR)",
        "freq": "M", "unitate": "% pe an", "zecimale": 2, "agregare": "medie", "rata": True,
        "mir": [("A2B", "Credite noi de consum"), ("A2Z", "Carduri de credit și descoperit de cont"),
                ("A2C", "Credite noi pentru locuințe"), ("L21", "Depozite la vedere (cont curent)")],
        "note": ["Dobânda „anuală convenită”, fără comisioane: DAE-ul din ofertele băncilor e mai mare.",
                 "Doar împrumuturile în lei; cele în euro au dobânzi mult mai mici.",
                 "La carduri și descoperit de cont dobânda e media tuturor soldurilor, nu doar a celor noi."],
        "url": "https://data.ecb.europa.eu/data/datasets/MIR/MIR.M.RO.B.A2B.A.R.A.2250.RON.N",
    },
]


def ecb(cheie: str) -> dict:
    """{perioadă: (valoare, status)} pentru o serie BCE (csvdata)."""
    url = f"{ECB}/{cheie}?format=csvdata&startPeriod={ECB_START}"
    for i in range(5):
        try:
            r = requests.get(url, headers=HEADERS, timeout=120)
            if r.ok and r.text.startswith("KEY"):
                rows = csv.DictReader(io.StringIO(r.text))
                out = {x["TIME_PERIOD"]: (float(x["OBS_VALUE"]), x.get("OBS_STATUS", "")) for x in rows if x.get("OBS_VALUE")}
                if out:
                    return out
            print(f"  încercarea {i + 1}: HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  încercarea {i + 1}: {e}")
        time.sleep(10 * (i + 1))  # portalul BCE dă uneori 504 câteva minute
    raise RuntimeError(f"nu am putut descărca {url}")


def serii_ecb(chei: list) -> tuple:
    date_ = {n: ecb(k) for k, n in chei}
    perioade = sorted(set().union(*date_.values()))
    serii = [{"nume": n, "valori": [d.get(p, (None,))[0] for p in perioade],
              "provizorii": {i for i, p in enumerate(perioade) if d.get(p, (0, ""))[1] in ("P", "E")}}
             for n, d in date_.items()]
    return perioade, serii


def credite(cfg: dict) -> dict:
    perioade, serii = serii_ecb([(f"BSI/M.RO.N.A.{c}.A.1.U6.2250.Z01.E", n) for c, n in cfg["bsi"]])
    curs = ecb("EXR/M.RON.EUR.SP00.A")
    dupa_cod = dict(zip((c for c, _ in cfg["bsi"]), serii))
    for cod, nume in cfg["lei"]:
        s = dupa_cod[cod]
        serii.append({"nume": nume, "unitate": "miliarde lei", "zecimale": 1, "provizorii": s["provizorii"],
                      "valori": [v * curs[p][0] / 1000 if v is not None and p in curs else None for v, p in zip(s["valori"], perioade)]})
    return iesire(cfg, perioade, serii)


def dobanzi(cfg: dict) -> dict:
    perioade, serii = serii_ecb([(f"MIR/M.RO.B.{c}.A.R.A.2250.RON.N", n) for c, n in cfg["mir"]])
    return iesire(cfg, perioade, serii)


SURSE = {"credite": credite, "dobanzi": dobanzi}


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
