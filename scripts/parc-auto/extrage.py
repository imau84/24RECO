#!/usr/bin/env python3
"""
extrage.py
==========
Extrage autoturismele (M1, M1G, M1S, M1GS; în 2018–2019 categoria „AUTOTURISM”)
pe județ, marcă și model, cu vechimea și combustibilul, într-un CSV pe an:
data/parc-auto/csv/parc_auto_<AAAA>.csv.

Mărcile și modelele se unifică (normalizare.py). Mapările se scriu în
  data/parc-auto/marca_mapping.csv   (marca_bruta, marca, numar)
  data/parc-auto/model_mapping.csv   (marca, model_original, model_norm, model_familie, numar)
„numar” = totalul pe toți anii. Corecturile făcute de mână în aceste fișiere se
păstrează și se aplică la rularea următoare.

Rulare:  python scripts/parc-auto/extrage.py
"""

import csv
from collections import Counter, defaultdict

from comun import (COMBUSTIBIL, CSV_DIR, MAPPING_CSV, MARCI_CSV, VECHIME_1, VECHIME_2,
                   ani_disponibili, citeste_excel, este_foaie_judet, foaie_total, harta_coloane,
                   numar, parcurge_autoturisme)
from normalizare import (NESPECIFICAT, Corecturi, Marci, variante_marca, cheie, este_nespecificat,
                         fara_marca, model_familie, model_norm, uneste_greseli)

COLOANE_CSV = (["an", "judet", "categorie", "marca", "model_familie", "model_norm", "marca_bruta",
                "model_original", "numar"] + VECHIME_1 + VECHIME_2 + COMBUSTIBIL + ["alt_combustibil"])


def citeste_randuri():
    """[(an, judet, categorie, marca_bruta, model_brut, {coloane numerice})]"""
    randuri = []
    for an in ani_disponibili():
        foi = citeste_excel(an)
        tot = foaie_total(foi)
        for judet in (n for n in foi if este_foaie_judet(n) and n != tot):
            col = harta_coloane(foi[judet])
            for cat, marca, model, rd in parcurge_autoturisme(foi[judet]):
                val = {k: numar(rd[i]) for k, i in col.items() if not k.startswith("_")}
                randuri.append((an, judet.strip(), cat, marca.strip(), model.strip(), val))
        print(f"  {an}: citit")
    return randuri


def mapare_marci(randuri):
    numar_brute = Counter()
    for _, _, _, mb, _, v in randuri:
        numar_brute[mb] += v["numar"]
    marci = Marci(numar_brute)
    auto, prefix = {}, {}
    for mb in numar_brute:
        auto[(mb,)] = {"marca": marci.auto(mb)[0]}
        prefix[mb] = marci.auto(mb)[1]
    cor = Corecturi(MARCI_CSV, ["marca_bruta"], ["marca"])
    final = {k: cor.aplica(k, a) for k, a in auto.items()}
    cor.scrie(sorted(({"marca_bruta": k[0], **final[k], "numar": numar_brute[k[0]]} for k in final),
                     key=lambda r: (r["marca"], -r["numar"])), auto)
    manuale = sum(final[k] != auto[k] for k in auto)
    return {k[0]: v["marca"] for k, v in final.items()}, prefix, manuale


def model_original(prefix, model_brut):
    if prefix and not model_brut.upper().startswith(prefix):
        return prefix if este_nespecificat(model_brut) else f"{prefix} {model_brut}"
    return model_brut


def mapare_modele(randuri, marca_de, prefix_de):
    numar_perechi = Counter()
    brute_per_marca = defaultdict(set)
    for _, _, _, mb, mo, v in randuri:
        m = marca_de[mb]
        numar_perechi[(m, model_original(prefix_de[mb], mo))] += v["numar"]
        if not prefix_de[mb]:
            brute_per_marca[m].add(mb)

    variante = {m: variante_marca(m, b) for m, b in brute_per_marca.items()}
    auto = {}
    for (m, mo) in numar_perechi:
        c = "" if este_nespecificat(mo) else fara_marca(mo, m, variante[m])
        if not c:
            auto[(m, mo)] = {"model_norm": NESPECIFICAT, "model_familie": NESPECIFICAT}
        else:
            auto[(m, mo)] = {"model_norm": model_norm(c), "model_familie": model_familie(m, c)}

    # aceeași familie scrisă diferit („C-MAX” / „CMAX”, „LAND CRUISER” / „LANDCRUISER”):
    # păstrăm forma cu cele mai multe mașini
    forme = defaultdict(Counter)
    for k, a in auto.items():
        forme[(k[0], cheie(a["model_familie"]))][a["model_familie"]] += numar_perechi[k]
    for k, a in auto.items():
        if a["model_familie"] != NESPECIFICAT:
            a["model_familie"] = forme[(k[0], cheie(a["model_familie"]))].most_common(1)[0][0]

    # greșeli de scriere în familie („Qutlander”, „Evogue”) -> familia mult mai frecventă
    pe_marca = defaultdict(Counter)
    for k, a in auto.items():
        pe_marca[k[0]][a["model_familie"]] += numar_perechi[k]
    greseli = {m: uneste_greseli(c) for m, c in pe_marca.items()}
    for k, a in auto.items():
        a["model_familie"] = greseli[k[0]].get(a["model_familie"], a["model_familie"])
    print(f"  greșeli de scriere unite în familii: {sum(len(g) for g in greseli.values())}")

    cor = Corecturi(MAPPING_CSV, ["marca", "model_original"], ["model_norm", "model_familie"])
    final = {k: cor.aplica(k, a) for k, a in auto.items()}
    cor.scrie(sorted(({"marca": k[0], "model_original": k[1], **final[k], "numar": numar_perechi[k]}
                      for k in final), key=lambda r: (r["marca"], -r["numar"], r["model_original"])), auto)
    manuale = sum(final[k] != auto[k] for k in auto)
    return final, manuale


def main():
    randuri = citeste_randuri()
    marca_de, prefix_de, man_marci = mapare_marci(randuri)
    modele, man_modele = mapare_modele(randuri, marca_de, prefix_de)
    print(f"  mărci: {len(set(marca_de.values()))} (din {len(marca_de)} variante brute), "
          f"corecturi manuale aplicate: {man_marci}")
    print(f"  modele: {len(modele)} perechi marcă-model, "
          f"{len({(k[0], v['model_norm']) for k, v in modele.items()})} model_norm, "
          f"{len({(k[0], v['model_familie']) for k, v in modele.items()})} familii; "
          f"corecturi manuale aplicate: {man_modele}")

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    pe_an = defaultdict(list)
    for r in randuri:
        pe_an[r[0]].append(r)
    print("\n  Model nespecificat pe ani:")
    for an, rr in sorted(pe_an.items()):
        total = nesp = 0
        cale = CSV_DIR / f"parc_auto_{an}.csv"
        with open(cale, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(COLOANE_CSV)
            for _, judet, cat, mb, mo, v in rr:
                m = marca_de[mb]
                mo = model_original(prefix_de[mb], mo)
                mm = modele[(m, mo)]
                comb = [v[k] if k in v else "" for k in COMBUSTIBIL]
                alt = v["numar"] - sum(x for x in comb if x != "")
                w.writerow([an, judet, cat, m, mm["model_familie"], mm["model_norm"], mb, mo, v["numar"]]
                           + [v[k] for k in VECHIME_1 + VECHIME_2] + comb + [alt])
                total += v["numar"]
                if mm["model_norm"] == NESPECIFICAT:
                    nesp += v["numar"]
        print(f"    {an}: {nesp:>9,} din {total:>9,} ({nesp / total:.1%})  -> {cale.name}")


if __name__ == "__main__":
    main()
