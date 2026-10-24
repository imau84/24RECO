#!/usr/bin/env python3
"""
structura.py
============
Verifică structura Excelului „Parc auto” în fiecare an și raportează diferențele:
foi, coloane (vechime, combustibil), categoriile de autoturisme, rândurile
„total categorie / total marca / model” și dacă totalurile se potrivesc.

Rulare:  python scripts/parc-auto/structura.py [AN ...]
"""

import sys
from collections import Counter

from comun import (COMBUSTIBIL, VECHIME_1, VECHIME_2, ani_disponibili, citeste_excel,
                   este_foaie_judet, fisier_excel, foaie_total, harta_coloane, numar,
                   parcurge_autoturisme, rand_rezumat_autoturisme, text, tip_rand)


def analizeaza(an: int) -> dict:
    foi = citeste_excel(an)
    tot = foaie_total(foi)
    judete = [n for n in foi if este_foaie_judet(n) and n != tot]
    alte = [n for n in foi if n != tot and n not in judete]
    r = {
        "an": an, "fisier": fisier_excel(an).name, "foaie_total": tot, "judete": len(judete),
        "alte_foi": {n: len(foi[n]) for n in alte},
    }

    harti = {n: harta_coloane(foi[n]) for n in [tot] + judete}
    col = harti[tot]
    r["coloane"] = [k for k in ["numar"] + VECHIME_1 + COMBUSTIBIL + VECHIME_2 if k in col]
    r["coloane_diferite_pe_judete"] = [n for n, h in harti.items() if h != col]

    # categorii din foaia TOTAL (toate) și cele de autoturisme
    r["categorii_toate"] = sorted({v for rand in foi[tot]
                                   for t, v in [tip_rand(text(rand[0] if rand else None))] if t == "categorie"})

    eticheta, rand = rand_rezumat_autoturisme(foi[tot])
    r["rand_rezumat"] = eticheta
    r["rezumat_total"] = numar(rand[col["numar"]]) if rand else None

    pe_cat = Counter()
    randuri_model = 0
    nespecificat = 0
    vechime_gresita = Counter()
    combustibil = Counter()
    marci = set()
    for n in judete:
        c = harti[n]
        for cat, marca, model, rd in parcurge_autoturisme(foi[n]):
            x = numar(rd[c["numar"]])
            pe_cat[cat] += x
            randuri_model += 1
            marci.add(marca.strip())
            if model.strip().lower() in ("nespecificat", ""):
                nespecificat += x
            if sum(numar(rd[c[k]]) for k in VECHIME_1) != x:
                vechime_gresita["0-2…>20"] += 1
            if "v_0_4" in c and sum(numar(rd[c[k]]) for k in VECHIME_2) != x:
                vechime_gresita["0-4…peste 12"] += 1
            for k in COMBUSTIBIL:
                if k in c:
                    combustibil[k] += numar(rd[c[k]])
    total = sum(pe_cat.values())
    r["categorii_autoturisme"] = dict(sorted(pe_cat.items()))
    r["total_judete"] = total
    r["randuri_model"] = randuri_model
    r["marci_brute"] = len(marci)
    r["model_nespecificat"] = nespecificat
    r["vechime_nu_insumeaza"] = dict(vechime_gresita)
    r["combustibil"] = dict(combustibil)
    r["combustibil_neacoperit"] = total - sum(combustibil.values())

    total_foaie_total = sum(numar(rd[col["numar"]]) for *_, rd in parcurge_autoturisme(foi[tot]))
    r["total_foaia_total"] = total_foaie_total
    return r


def main():
    ani = [int(a) for a in sys.argv[1:]] or ani_disponibili()
    rezultate = []
    for an in ani:
        r = analizeaza(an)
        rezultate.append(r)
        ok = r["rezumat_total"] == r["total_judete"] == r["total_foaia_total"]
        print(f"\n=== {an}  ({r['fisier']}) ===")
        print(f"  foi: {r['foaie_total']} + {r['judete']} județe"
              + (f"; alte foi: {r['alte_foi']}" if r["alte_foi"] else ""))
        print(f"  coloane: {', '.join(r['coloane'])}")
        if r["coloane_diferite_pe_judete"]:
            print(f"  ATENȚIE coloane diferite în: {r['coloane_diferite_pe_judete']}")
        print(f"  categorii autoturisme: {r['categorii_autoturisme']}")
        print(f"  rând rezumat: „{r['rand_rezumat']}” = {r['rezumat_total']:,}")
        print(f"  suma modelelor: județe {r['total_judete']:,}, foaia TOTAL {r['total_foaia_total']:,}"
              f"  -> {'OK' if ok else 'DIFERENȚĂ'}")
        print(f"  rânduri model: {r['randuri_model']:,}; mărci brute: {r['marci_brute']}")
        print(f"  model nespecificat: {r['model_nespecificat']:,} "
              f"({r['model_nespecificat'] / r['total_judete']:.1%})")
        print(f"  combustibil: {r['combustibil']}; neacoperit (GPL/altele): {r['combustibil_neacoperit']:,}")
        if r["vechime_nu_insumeaza"]:
            print(f"  rânduri unde vechimea nu dă „Numar”: {r['vechime_nu_insumeaza']}")

    print("\n=== Diferențe față de anul anterior ===")
    for a, b in zip(rezultate, rezultate[1:]):
        dif = []
        if a["coloane"] != b["coloane"]:
            dif.append(f"coloane {a['coloane']} -> {b['coloane']}")
        ca, cb = set(a["categorii_autoturisme"]), set(b["categorii_autoturisme"])
        if ca != cb:
            dif.append(f"categorii autoturisme {sorted(ca)} -> {sorted(cb)}")
        if a["rand_rezumat"] != b["rand_rezumat"]:
            dif.append(f"rând rezumat „{a['rand_rezumat']}” -> „{b['rand_rezumat']}”")
        if a["foaie_total"] != b["foaie_total"]:
            dif.append(f"foaia total „{a['foaie_total']}” -> „{b['foaie_total']}”")
        if a["alte_foi"] != b["alte_foi"]:
            dif.append(f"alte foi {list(a['alte_foi'])[:3]}… -> {list(b['alte_foi'])[:3]}…")
        print(f"  {a['an']} -> {b['an']}: " + ("; ".join(dif) if dif else "aceeași structură"))


if __name__ == "__main__":
    main()
