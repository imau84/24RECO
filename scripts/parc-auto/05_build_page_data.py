#!/usr/bin/env python3
"""
05_build_page_data.py
=====================
Din data/parc-auto/csv/parc_auto_<AAAA>.csv generează datele paginii de parc auto
pentru un an, în public/parc-auto/<AAAA>/:

  index.json         se încarcă la deschiderea paginii: lista județelor (+ RO) și,
                     pentru fiecare, totalul, top 15 mărci, top 20 familii de modele,
                     top 12 modele electrice, top 12 mărci hibride, mașinile cu model
                     nespecificat și numărul de mărci;
  judete/<COD>.json  toate mărcile și familiile de modele dintr-un județ (sau RO),
                     grupate pe marcă: {"MARCA": {"total": [...], "modele": {"Familie": [...]}}}.

Fiecare valoare e un array de numere în ordinea din index.json -> "coloane"
(total, vechime în 2 grupări, combustibil). Rândurile cu total 0 nu se scriu.
Coloanele care lipsesc din fișierul unui an sunt null: electric/hibrid în 2012–2019
(iar listele de electrice/hibride sunt null), grupele 0–4 ... peste 12 în 2012.

La final verifică totalurile (fișiere județ vs index, județe vs RO, RO vs foaia
TOTAL din Excel) și afișează dimensiunea fiecărui fișier.

Rulare:  python scripts/parc-auto/05_build_page_data.py 2025
"""

import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from datetime import date

from comun import (CSV_DIR, ROOT, VECHIME_1, VECHIME_2, citeste_excel, foaie_total, harta_coloane,
                   numar, rand_rezumat_autoturisme)
from genereaza_json import JUDETE
from normalizare import NESPECIFICAT

TOP_MARCI = 15
TOP_FAMILII = 20
TOP_ELECTRICE = 12
TOP_HIBRIDE = 12
LIMITA_JUDET = 1_000_000  # octeți

# coloana din CSV -> numele din „coloane”
CAMPURI = ["numar"] + VECHIME_1 + VECHIME_2 + ["benzina", "motorina", "electric", "hibrid", "alt_combustibil"]
COLOANE = (["total", "v_0_2", "v_3_5", "v_6_10", "v_11_15", "v_16_20", "v_peste_20",
            "v_0_4", "v_5_8", "v_9_12", "v_peste_12",
            "benzina", "motorina", "electric", "hibrid", "gpl_altele"])
I_ELECTRIC = COLOANE.index("electric")
I_HIBRID = COLOANE.index("hibrid")


def zero():
    return [0] * len(CAMPURI)


def aduna(a, b):
    for i, x in enumerate(b):
        a[i] += x


def fara_diacritice(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()


class Regiune:
    def __init__(self):
        self.total = zero()
        self.marci = defaultdict(zero)
        self.familii = defaultdict(zero)  # (marca, familie) -> vector

    def adauga(self, marca, familie, v):
        aduna(self.total, v)
        aduna(self.marci[marca], v)
        aduna(self.familii[(marca, familie)], v)


def citeste_csv(an):
    regiuni = defaultdict(Regiune)
    lipsa = set(range(len(CAMPURI)))  # coloanele goale în tot fișierul
    with open(CSV_DIR / f"parc_auto_{an}.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lipsa -= {i for i in lipsa if r[CAMPURI[i]] != ""}
            v = [int(r[k]) if r[k] != "" else 0 for k in CAMPURI]
            regiuni["RO"].adauga(r["marca"], r["model_familie"], v)
            regiuni[r["judet"]].adauga(r["marca"], r["model_familie"], v)
    necunoscute = set(regiuni) - set(JUDETE) - {"RO"}
    if necunoscute:
        sys.exit(f"{an}: coduri de județ necunoscute: {necunoscute}")
    return regiuni, lipsa


def build(an, regiuni, lipsa):
    are_electric = I_ELECTRIC not in lipsa

    def iesire(v):
        if not lipsa:
            return v
        return [None if i in lipsa else x for i, x in enumerate(v)]

    def ordonat(d):
        return sorted(((k, v) for k, v in d.items() if v[0] > 0), key=lambda kv: (-kv[1][0], kv[0]))

    date_index, fisiere = {}, {}
    for cod, reg in regiuni.items():
        familii = [((m, f), v) for (m, f), v in ordonat(reg.familii) if f != NESPECIFICAT]
        bloc = {
            "total": iesire(reg.total),
            "model_nespecificat": sum(v[0] for (m, f), v in reg.familii.items() if f == NESPECIFICAT),
            "numar_marci": sum(1 for v in reg.marci.values() if v[0] > 0),
            "marci": [[m, iesire(v)] for m, v in ordonat(reg.marci)[:TOP_MARCI]],
            "familii": [[m, f, iesire(v)] for (m, f), v in familii[:TOP_FAMILII]],
            "electrice": None,
            "hibride": None,
        }
        if are_electric:
            el = sorted((kv for kv in familii if kv[1][I_ELECTRIC] > 0), key=lambda kv: -kv[1][I_ELECTRIC])
            hb = sorted((kv for kv in reg.marci.items() if kv[1][I_HIBRID] > 0), key=lambda kv: -kv[1][I_HIBRID])
            bloc["electrice"] = [[m, f, v] for (m, f), v in el[:TOP_ELECTRICE]]
            bloc["hibride"] = [[m, v] for m, v in hb[:TOP_HIBRIDE]]
        date_index[cod] = bloc

        pe_marca = defaultdict(dict)
        for (m, f), v in ordonat(reg.familii):
            pe_marca[m][f] = iesire(v)
        fisiere[cod] = {m: {"total": iesire(v), "modele": pe_marca[m]} for m, v in ordonat(reg.marci)}

    judete = [{"cod": "RO", "nume": "România"}] + [
        {"cod": c, "nume": n} for c, n in sorted(JUDETE.items(), key=lambda cn: fara_diacritice(cn[1]))
        if c in regiuni]
    index = {
        "an": an,
        "actualizat": date.today().isoformat(),
        "sursa": "DGPCI (Ministerul Afacerilor Interne) — „Parc auto la 31.12.AAAA”, dgpci.mai.gov.ro",
        "coloane": COLOANE,
        "note": {
            "coloane": "Fiecare array de numere urmează ordinea din „coloane”: total, vechime în ani "
                       "(0–2, 3–5, 6–10, 11–15, 16–20, peste 20 și 0–4, 5–8, 9–12, peste 12), apoi "
                       "combustibil. „gpl_altele” = total minus benzină, motorină, electric și hibrid."
                       + (" În acest an DGPCI nu publică grupele 0–4 ... peste 12: coloanele sunt null."
                          if CAMPURI.index("v_0_4") in lipsa else ""),
            "combustibil": "„hibrid” = benzină+electric, motorină+electric și GPL+electric la un loc."
                           + ("" if are_electric else " În acest an DGPCI publică doar benzină și "
                              "motorină: electric/hibrid sunt null și incluse în „gpl_altele”."),
            "electrice": "Modelele ordonate după numărul de mașini electrice (coloana „electric”); "
                         "celelalte coloane sunt pentru toate mașinile modelului. La fel pentru "
                         "mărcile hibride (coloana „hibrid”).",
            "familii": "Top familii fără mașinile cu model nespecificat (date separat în "
                       "„model_nespecificat”). În judete/<COD>.json ele apar ca model „nespecificat”.",
        },
        "judete": judete,
        "date": date_index,
    }
    return index, fisiere


def scrie(cale, obj):
    cale.parent.mkdir(parents=True, exist_ok=True)
    cale.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return cale.stat().st_size


def verifica(an, out):
    """Recitește fișierele scrise și verifică totalurile. Întoarce True dacă totul se potrivește."""
    ok = True
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    n = lambda x: x or 0  # noqa: E731  (null = coloană lipsă în acel an)

    print("\n  1. Suma mărcilor din judete/<COD>.json = totalul din index.json")
    gresite = []
    for j in index["judete"]:
        marci = json.loads((out / "judete" / f"{j['cod']}.json").read_text(encoding="utf-8"))
        s = zero()
        for m, b in marci.items():
            aduna(s, map(n, b["total"]))
            sm = zero()
            for v in b["modele"].values():
                aduna(sm, map(n, v))
            if sm != [n(x) for x in b["total"]]:
                gresite.append(f"{j['cod']}/{m} (modele ≠ total marcă)")
        if s != [n(x) for x in index["date"][j["cod"]]["total"]]:
            gresite.append(j["cod"])
    ok &= not gresite
    print(f"     {'OK' if not gresite else 'DIFERENȚĂ: ' + ', '.join(gresite)} "
          f"({len(index['judete'])} fișiere; și suma modelelor = totalul fiecărei mărci)")

    print("  2. Suma celor 42 de județe = RO")
    s = zero()
    judete = [j["cod"] for j in index["judete"] if j["cod"] != "RO"]
    for c in judete:
        aduna(s, map(n, index["date"][c]["total"]))
    ro = [n(x) for x in index["date"]["RO"]["total"]]
    ok &= s == ro and len(judete) == 42
    print(f"     {len(judete)} județe: {s[0]:,} vs RO {ro[0]:,} -> "
          f"{'OK' if s == ro and len(judete) == 42 else 'DIFERENȚĂ'}")

    print("  3. RO = rândul „Autoturisme (M1, M1G)” din foaia TOTAL")
    foi = citeste_excel(an)
    randuri = foi[foaie_total(foi)]
    col = harta_coloane(randuri)
    eticheta, rand = rand_rezumat_autoturisme(randuri)
    dif = []
    for i, k in enumerate(CAMPURI):
        if k in col and numar(rand[col[k]]) != ro[i]:
            dif.append(f"{COLOANE[i]}: {ro[i]:,} ≠ {numar(rand[col[k]]):,}")
    ok &= not dif
    print(f"     RO {ro[0]:,} vs „{str(eticheta).strip()}” {numar(rand[col['numar']]):,} -> "
          f"{'OK (toate coloanele)' if not dif else 'DIFERENȚĂ: ' + '; '.join(dif)}")
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("an", type=int, help="anul datelor (ex. 2025)")
    an = p.parse_args().an

    regiuni, lipsa = citeste_csv(an)
    index, fisiere = build(an, regiuni, lipsa)

    out = ROOT / "public" / "parc-auto" / str(an)
    marimi = {"index.json": scrie(out / "index.json", index)}
    for cod in [j["cod"] for j in index["judete"]]:
        marimi[f"judete/{cod}.json"] = scrie(out / "judete" / f"{cod}.json", fisiere[cod])

    ok = verifica(an, out)

    print(f"\n  4. Dimensiuni ({out.relative_to(ROOT)}):")
    prea_mari = []
    for nume, b in marimi.items():
        semn = ""
        if nume.startswith("judete/") and b > LIMITA_JUDET:
            prea_mari.append(nume)
            semn = "  <-- peste 1 MB"
        print(f"     {nume:<18} {b / 1024:>8.1f} KB{semn}")
    print(f"     {'total':<18} {sum(marimi.values()) / 1024:>8.1f} KB")
    if prea_mari:
        print(f"\n  ATENȚIE: fișiere de județ peste 1 MB: {', '.join(prea_mari)}")
    sys.exit(0 if ok and not prea_mari else 1)


if __name__ == "__main__":
    main()
