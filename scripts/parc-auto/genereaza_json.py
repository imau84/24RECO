#!/usr/bin/env python3
"""
genereaza_json.py
=================
Din CSV-urile data/parc-auto/csv/ generează public/parc_auto_autoturisme.json:
pentru fiecare an, la nivel de țară („RO”) și pe fiecare județ:
  total, vechime (2 grupări), combustibil, model nespecificat,
  top 30 mărci, top 30 familii de modele, top modele electrice, top mărci hibride.

Listele sunt compacte: [marca, numar] / [marca, familie, numar].
În 2012–2019 fișierele DGPCI au doar benzină și motorină (electric/hibrid = null);
2012 nu are grupele de vechime 0-4 ... peste 12 (vechime_4ani = null).

Rulare:  python scripts/parc-auto/genereaza_json.py
"""

import csv
import json
from collections import Counter, defaultdict
from datetime import date

from comun import COMBUSTIBIL, CSV_DIR, JSON_OUT, VECHIME_1, VECHIME_2, ani_disponibili
from normalizare import NESPECIFICAT

TOP_MARCI = 30
TOP_FAMILII = 30
TOP_ELECTRICE = 20
TOP_HIBRIDE = 20

JUDETE = {
    "AB": "Alba", "AR": "Arad", "AG": "Argeș", "BC": "Bacău", "BH": "Bihor", "BN": "Bistrița-Năsăud",
    "BT": "Botoșani", "BR": "Brăila", "BV": "Brașov", "B": "București", "BZ": "Buzău", "CL": "Călărași",
    "CS": "Caraș-Severin", "CJ": "Cluj", "CT": "Constanța", "CV": "Covasna", "DB": "Dâmbovița",
    "DJ": "Dolj", "GL": "Galați", "GR": "Giurgiu", "GJ": "Gorj", "HR": "Harghita", "HD": "Hunedoara",
    "IL": "Ialomița", "IS": "Iași", "IF": "Ilfov", "MM": "Maramureș", "MH": "Mehedinți", "MS": "Mureș",
    "NT": "Neamț", "OT": "Olt", "PH": "Prahova", "SJ": "Sălaj", "SM": "Satu Mare", "SB": "Sibiu",
    "SV": "Suceava", "TR": "Teleorman", "TM": "Timiș", "TL": "Tulcea", "VS": "Vaslui", "VL": "Vâlcea",
    "VN": "Vrancea",
}
ETICHETE_VECHIME_1 = ["0-2", "3-5", "6-10", "11-15", "16-20", "peste 20"]
ETICHETE_VECHIME_2 = ["0-4", "5-8", "9-12", "peste 12"]


class Agregat:
    def __init__(self):
        self.col = Counter()
        self.marci = Counter()
        self.familii = Counter()
        self.electrice = Counter()
        self.hibride = Counter()
        self.nespecificat = 0
        self.are_electric = False
        self.are_vechime_2 = False  # 2012 nu are grupele 0-4 ... peste 12

    def adauga(self, r):
        for k in ["numar", "alt_combustibil"] + VECHIME_1 + VECHIME_2 + COMBUSTIBIL:
            if r[k] != "":
                self.col[k] += int(r[k])
        n = int(r["numar"])
        self.are_vechime_2 |= r["v_0_4"] != ""
        self.marci[r["marca"]] += n
        if r["model_familie"] == NESPECIFICAT:
            self.nespecificat += n
        else:
            self.familii[(r["marca"], r["model_familie"])] += n
        if r["electric"] != "":
            self.are_electric = True
            if r["model_familie"] != NESPECIFICAT:
                self.electrice[(r["marca"], r["model_familie"])] += int(r["electric"])
            self.hibride[r["marca"]] += int(r["hibrid"])

    def json(self):
        c = self.col
        el = self.are_electric
        return {
            "total": c["numar"],
            "vechime": dict(zip(ETICHETE_VECHIME_1, (c[k] for k in VECHIME_1))),
            "vechime_4ani": dict(zip(ETICHETE_VECHIME_2, (c[k] for k in VECHIME_2))) if self.are_vechime_2 else None,
            "combustibil": {
                "benzina": c["benzina"], "motorina": c["motorina"],
                "electric": c["electric"] if el else None, "hibrid": c["hibrid"] if el else None,
                "altele": c["alt_combustibil"],
            },
            "model_nespecificat": self.nespecificat,
            "marci": [[m, n] for m, n in self.marci.most_common(TOP_MARCI)],
            "familii": [[m, f, n] for (m, f), n in self.familii.most_common(TOP_FAMILII)],
            "electrice": [[m, f, n] for (m, f), n in self.electrice.most_common(TOP_ELECTRICE) if n > 0] if el else None,
            "hibride": [[m, n] for m, n in self.hibride.most_common(TOP_HIBRIDE) if n > 0] if el else None,
        }


def main():
    ani = ani_disponibili()
    date_ani = {}
    for an in ani:
        agregate = defaultdict(Agregat)
        categorii = set()
        with open(CSV_DIR / f"parc_auto_{an}.csv", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                agregate["RO"].adauga(r)
                agregate[r["judet"]].adauga(r)
                categorii.add(r["categorie"])
        necunoscute = set(agregate) - set(JUDETE) - {"RO"}
        if necunoscute:
            raise SystemExit(f"{an}: coduri de județ necunoscute: {necunoscute}")
        date_ani[str(an)] = {
            "categorii": sorted(categorii),
            "RO": agregate["RO"].json(),
            "judete": {j: agregate[j].json() for j in JUDETE if j in agregate},
        }
        print(f"  {an}: {agregate['RO'].col['numar']:,} autoturisme, {len(agregate) - 1} județe")

    out = {
        "actualizat": date.today().isoformat(),
        "sursa": "DGPCI (Ministerul Afacerilor Interne) — „Parc auto la 31.12.AAAA”, dgpci.mai.gov.ro",
        "note": {
            "categorii": "Autoturisme = categoriile M1, M1G, M1S, M1GS. În 2012–2019 fișierele DGPCI "
                         "folosesc categoria de folosință „AUTOTURISM”, fără împărțirea M1/M1G.",
            "combustibil": "„hibrid” = benzină+electric, motorină+electric și GPL+electric la un loc. "
                           "„altele” = GPL, alți combustibili sau necompletat. În 2012–2019 DGPCI publică "
                           "doar benzină și motorină; electricele și hibridele sunt în „altele”.",
            "vechime": "„vechime_4ani” (0-4 ... peste 12) lipsește în 2012 (null).",
            "modele": "Mărcile și modelele sunt unificate (variante de scriere, greșeli de tastare). "
                      "„model_nespecificat” = mașini fără model în registru.",
        },
        "ani": ani,
        "judete": JUDETE,
        "date": date_ani,
    }
    JSON_OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  -> {JSON_OUT.relative_to(JSON_OUT.parents[1])} ({JSON_OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
