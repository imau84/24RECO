#!/usr/bin/env python3
"""
06_build_series.py
==================
Din toate CSV-urile data/parc-auto/csv/parc_auto_<AAAA>.csv generează seriile pe ani
pentru tab-ul „Evoluție” al paginii: public/parc-auto/serii.json.

Pentru RO și fiecare județ:
  total  = un array pe an, în ordinea din „coloane” (aceeași ca în index.json de la
           05_build_page_data.py); coloanele lipsă într-un an sunt null
           (electric/hibrid înainte de 2020, grupele 0–4 ... peste 12 în 2012);
  marci  = {MARCA: [mașini pe an]} pentru mărcile din top 10 în cel puțin un an.

Verifică: suma județelor = RO în fiecare an și RO = rândul de autoturisme din foaia
TOTAL a fișierului original.

Rulare:  python scripts/parc-auto/06_build_series.py
"""

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from comun import (CSV_DIR, ROOT, citeste_excel, foaie_total, harta_coloane, numar,
                   rand_rezumat_autoturisme)
from genereaza_json import JUDETE

# CAMPURI / COLOANE / fara_diacritice din 05_build_page_data.py (numele începe cu cifră)
_spec = importlib.util.spec_from_file_location("build05", Path(__file__).with_name("05_build_page_data.py"))
_b05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_b05)
CAMPURI, COLOANE, fara_diacritice = _b05.CAMPURI, _b05.COLOANE, _b05.fara_diacritice

TOP_MARCI = 10
OUT = ROOT / "public" / "parc-auto" / "serii.json"


def citeste_an(an):
    """{regiune: vector}, {regiune: Counter(marca)}, coloane lipsă"""
    tot = defaultdict(lambda: [0] * len(CAMPURI))
    marci = defaultdict(Counter)
    lipsa = set(range(len(CAMPURI)))
    with open(CSV_DIR / f"parc_auto_{an}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lipsa -= {i for i in lipsa if r[CAMPURI[i]] != ""}
            v = [int(r[k]) if r[k] != "" else 0 for k in CAMPURI]
            for reg in ("RO", r["judet"]):
                t = tot[reg]
                for i, x in enumerate(v):
                    t[i] += x
                marci[reg][r["marca"]] += v[0]
    for t in tot.values():
        for i in lipsa:
            t[i] = None
    return tot, marci


def main():
    ani = sorted(int(p.stem.rsplit("_", 1)[1]) for p in CSV_DIR.glob("parc_auto_*.csv"))
    pe_an = {an: citeste_an(an) for an in ani}
    regiuni = ["RO"] + sorted(JUDETE, key=lambda c: fara_diacritice(JUDETE[c]))

    date_reg = {}
    for reg in regiuni:
        alese = {m for an in ani for m, _ in pe_an[an][1][reg].most_common(TOP_MARCI)}
        ultim = pe_an[ani[-1]][1][reg]
        date_reg[reg] = {
            "total": [pe_an[an][0][reg] for an in ani],
            "marci": {m: [pe_an[an][1][reg][m] for an in ani]
                      for m in sorted(alese, key=lambda m: (-ultim[m], m))},
        }

    out = {
        "ani": ani,
        "actualizat": date.today().isoformat(),
        "sursa": "DGPCI (MAI) — „Parc auto la 31.12.AAAA”; 2012–2017 prin data.gov.ro, din 2018 dgpci.mai.gov.ro",
        "coloane": COLOANE,
        "note": {
            "total": "Câte un array pe an (ordinea din „ani”), cu valorile în ordinea din „coloane”. "
                     "Coloanele lipsă dintr-un an sunt null: electric/hibrid înainte de 2020 (incluse în "
                     "„gpl_altele”), grupele 0–4 ... peste 12 în 2012.",
            "categorii": "2012–2019: categoria de folosință „AUTOTURISM”; din 2020: M1, M1G, M1S, M1GS.",
            "marci": f"Mărcile din top {TOP_MARCI} în cel puțin un an; numărul de mașini pe an.",
        },
        "judete": [{"cod": "RO", "nume": "România"}] + [{"cod": c, "nume": JUDETE[c]} for c in regiuni[1:]],
        "date": date_reg,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    ok = True
    print("  Verificări (RO = suma județelor = rândul de autoturisme din foaia TOTAL):")
    for i, an in enumerate(ani):
        ro = date_reg["RO"]["total"][i][0]
        judete = sum(date_reg[c]["total"][i][0] for c in regiuni[1:])
        foi = citeste_excel(an)
        _, rand = rand_rezumat_autoturisme(foi[foaie_total(foi)])
        ref = numar(rand[harta_coloane(foi[foaie_total(foi)])["numar"]])
        stare = "OK" if ro == judete == ref else "DIFERENȚĂ"
        ok &= stare == "OK"
        print(f"    {an}: RO {ro:>9,} | județe {judete:>9,} | TOTAL {ref:>9,} -> {stare}")
    print(f"  -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.1f} KB)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
