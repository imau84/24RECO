#!/usr/bin/env python3
"""
verifica.py
===========
Verifică totalurile din CSV-urile extrase: pentru fiecare an, suma pe mărci și
județe trebuie să fie egală cu rândul „Autoturisme (M1, M1G)” din foaia TOTAL
(2018–2019: „AUTOTURISM”). Se compară toate coloanele (număr, vechime,
combustibil), apoi fiecare județ cu rândul de rezumat din foaia lui.

Ieșire cu cod 1 dacă vreun total nu se potrivește.

Rulare:  python scripts/parc-auto/verifica.py
"""

import csv
import sys
from collections import Counter, defaultdict

from comun import (COMBUSTIBIL, CSV_DIR, VECHIME_1, VECHIME_2, ani_disponibili, citeste_excel,
                   este_foaie_judet, foaie_total, harta_coloane, numar, rand_rezumat_autoturisme)

COLOANE = ["numar"] + VECHIME_1 + VECHIME_2 + COMBUSTIBIL


def rezumat(randuri):
    col = harta_coloane(randuri)
    _, rand = rand_rezumat_autoturisme(randuri)
    return {k: numar(rand[col[k]]) for k in COLOANE if k in col}


def main():
    ok = True
    for an in ani_disponibili():
        cale = CSV_DIR / f"parc_auto_{an}.csv"
        pe_judet = defaultdict(Counter)
        pe_marca = Counter()
        with open(cale, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                for k in COLOANE:
                    if r[k] != "":
                        pe_judet[r["judet"]][k] += int(r[k])
                pe_marca[r["marca"]] += int(r["numar"])
        total_csv = sum(pe_judet.values(), Counter())

        foi = citeste_excel(an)
        tot = foaie_total(foi)
        ref = rezumat(foi[tot])
        dif = {k: (total_csv[k], v) for k, v in ref.items() if total_csv[k] != v}
        if sum(pe_marca.values()) != ref["numar"]:
            dif["suma pe mărci"] = (sum(pe_marca.values()), ref["numar"])

        judete_gresite = []
        for n in (n for n in foi if este_foaie_judet(n) and n != tot):
            rj = rezumat(foi[n])
            if any(pe_judet[n.strip()][k] != v for k, v in rj.items()):
                judete_gresite.append(n)

        stare = "OK" if not dif and not judete_gresite else "DIFERENȚĂ"
        ok &= stare == "OK"
        print(f"  {an}: {total_csv['numar']:>9,} în CSV ({len(pe_marca)} mărci, {len(pe_judet)} județe) "
              f"vs {ref['numar']:>9,} în TOTAL -> {stare}")
        for k, (a, b) in dif.items():
            print(f"      {k}: CSV {a:,} ≠ TOTAL {b:,}")
        if judete_gresite:
            print(f"      județe care nu se potrivesc: {judete_gresite}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
