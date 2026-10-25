#!/usr/bin/env python3
"""
07_build_detaliat.py
====================
Din foaia TOTAL a fișierului DGPCI al unui an generează tabelul „Date complete”
al paginii de parc auto: toate autoturismele (M1, M1G, M1S, M1GS) la nivel de model,
doar la nivel național, în public/parc-auto/<AAAA>/detaliat/RO.json:

  {"an", "coloane", "categorii": [...], "marci": [...],
   "familii": [[i_marca, "Seria 3"], ...],
   "randuri": [[i_categorie, i_familie, "320D XDRIVE", numar, 0–2 ... >20,
                benzina, motorina, electric, hibrid, 0–4 ... peste 12], ...]}

Marca e cea unificată și familia cea din data/parc-auto/model_mapping.csv (prin CSV-ul
anului, scris de extrage.py); modelul e textul din raport. Mărcile sunt ordonate după
numărul de autoturisme. Rândurile cu același text de model sub variante de scriere ale
aceleiași mărci (VW / VOLKSWAGEN) se adună.

La final verifică totalul față de rândul „Autoturisme (M1, M1G)” din foaia TOTAL și
față de suma județelor din CSV, apoi afișează dimensiunea fișierului.

Rulare:  python scripts/parc-auto/07_build_detaliat.py 2025
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict

from comun import (CATEGORII_M1, CSV_DIR, ROOT, VECHIME_1, VECHIME_2, citeste_excel, foaie_total,
                   harta_coloane, numar, parcurge_autoturisme, rand_rezumat_autoturisme)
from extrage import model_original
from normalizare import Marci

CATEGORII = ["M1", "M1G", "M1S", "M1GS"]
CAMPURI = ["numar"] + VECHIME_1 + ["benzina", "motorina", "electric", "hibrid"] + VECHIME_2


def mapare_din_csv(an):
    """{marca_bruta: marca}, {(marca, model_original): familie} și totalul pe țară din CSV-ul anului."""
    marca_de, familie_de, total = {}, {}, [0] * len(CAMPURI)
    with open(CSV_DIR / f"parc_auto_{an}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            marca_de[r["marca_bruta"]] = r["marca"]
            familie_de[(r["marca"], r["model_original"])] = r["model_familie"]
            for i, k in enumerate(CAMPURI):
                total[i] += int(r[k] or 0)
    return marca_de, familie_de, total


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("an", type=int, help="anul datelor (ex. 2025)")
    an = p.parse_args().an

    marca_de, familie_de, total_csv = mapare_din_csv(an)
    foi = citeste_excel(an)
    randuri = foi[foaie_total(foi)]
    col = harta_coloane(randuri)
    if missing := [k for k in CAMPURI if k not in col]:
        sys.exit(f"{an}: lipsesc coloanele {missing} în foaia TOTAL")

    prefix = Marci(Counter())  # prefixul („RANGE ROVER” -> LAND ROVER) nu depinde de numere
    agregat = defaultdict(lambda: [0] * len(CAMPURI))
    fara_mapare = Counter()
    for cat, mb, mo, rd in parcurge_autoturisme(randuri):
        if cat not in CATEGORII_M1:
            continue
        mb, mo = mb.strip(), mo.strip()
        marca = marca_de.get(mb) or prefix.auto(mb)[0]
        model = model_original(prefix.auto(mb)[1], mo)
        familie = familie_de.get((marca, model))
        if familie is None:
            fara_mapare[(marca, model)] += numar(rd[col["numar"]])
            familie = "nespecificat"
        v = agregat[(cat, marca, familie, model)]
        for i, k in enumerate(CAMPURI):
            v[i] += numar(rd[col[k]])

    total_marca = Counter()
    for (_, m, _, _), v in agregat.items():
        total_marca[m] += v[0]
    marci = [m for m, _ in sorted(total_marca.items(), key=lambda kv: (-kv[1], kv[0])) if _ > 0]
    i_marca = {m: i for i, m in enumerate(marci)}
    familii = sorted({(m, f) for (_, m, f, _) in agregat if m in i_marca}, key=lambda mf: (i_marca[mf[0]], mf[1]))
    i_fam = {mf: i for i, mf in enumerate(familii)}
    rows = sorted(([CATEGORII.index(c), i_fam[(m, f)], mo, *v] for (c, m, f, mo), v in agregat.items() if v[0] > 0),
                  key=lambda r: (r[1], -r[3], r[2]))

    out = ROOT / "public" / "parc-auto" / str(an) / "detaliat" / "RO.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "an": an,
        "sursa": "DGPCI (MAI) — „Parc auto la 31.12.AAAA”, foaia TOTAL",
        "coloane": ["categorie", "familie", "model"] + CAMPURI,
        "categorii": CATEGORII,
        "marci": marci,
        "familii": [[i_marca[m], f] for m, f in familii],
        "randuri": rows,
    }
    out.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # verificări
    ok = True
    s = [sum(r[3 + i] for r in rows) for i in range(len(CAMPURI))]
    eticheta, rand = rand_rezumat_autoturisme(randuri)
    rez = [numar(rand[col[k]]) for k in CAMPURI]
    print(f"  {len(rows):,} rânduri (modele), {len(familii):,} familii, {len(marci):,} mărci")
    print(f"  total {s[0]:,} vs „{eticheta}” {rez[0]:,} -> {'OK (toate coloanele)' if s == rez else 'DIFERENȚĂ'}")
    print(f"  total {s[0]:,} vs suma județelor din CSV {total_csv[0]:,} -> "
          f"{'OK (toate coloanele)' if s == total_csv else 'DIFERENȚĂ'}")
    ok &= s == rez and s == total_csv
    if fara_mapare:
        print(f"  ATENȚIE: {len(fara_mapare)} modele fără familie în CSV ({sum(fara_mapare.values()):,} mașini), "
              f"puse la „nespecificat”: {fara_mapare.most_common(5)}")
    print(f"  {out.relative_to(ROOT)}: {out.stat().st_size / 1024:,.1f} KB")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
