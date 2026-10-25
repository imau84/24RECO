#!/usr/bin/env python3
"""
build-primari-2024.py
=====================
Din data/raw/alegeri-locale-2024/primari-2024.xlsx (export consolidat AEP, PV final,
alegeri pentru primar, 9 iunie 2024 — prezenta.roaep.ro/locale09062024v2) generează
public/data/alegeri-locale-2024/primari.json, cu o intrare pe UAT (3.180 de UAT-uri +
6 sectoare ale Bucureștiului; Primarul General al Capitalei nu e în fișier).

Structura fișierului: o foaie „judete”, coloana A goală; fiecare județ începe cu un rând
de antet (county_nce în coloana B): coloanele standard (county_nce … a, a1–a4, b, b1–b4,
c, d, e, f), apoi câte o coloană pe candidat, „NUME PRENUME-COMPETITOR-voturi”. Primul
antet (rândul 3) are numere în loc de candidați: e rândul de filtre și se ignoră.

Separarea numelui de competitor: numele și competitorii pot conține „-”, deci nu se
taie după cratimă. Se construiește o listă albă de competitori (sufixele care încep cu
PARTIDUL, ALIANȚA, UNIUNEA etc. + cei din data/alegeri-locale-2024/aliante.json) și se
alege cel mai lung competitor cu care se termină antetul, precedat de „-”. Fără
potrivire = candidat independent.

Validări (scriptul se oprește cu eroare): suma voturilor candidaților = c în fiecare UAT;
3.186 de UAT-uri. Egalitățile pe primul loc nu au câștigător („egalitate – alegeri repetate”).

Rulare:  python scripts/build-primari-2024.py
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SURSA = ROOT / "data" / "raw" / "alegeri-locale-2024" / "primari-2024.xlsx"
ALIANTE = ROOT / "data" / "alegeri-locale-2024" / "aliante.json"
OUT = ROOT / "public" / "data" / "alegeri-locale-2024" / "primari.json"

STANDARD = ["county_nce", "county_name", "uat_name", "uat_siruta", "report_version", "report_stage_code",
            "report_type_scope_code", "report_type_category_code", "report_type_code", "created_at",
            "a", "a1", "a2", "a3", "a4", "b", "b1", "b2", "b3", "b4", "c", "d", "e", "f"]
SUFIX = "-voturi"
CUVINTE_CHEIE = ["PARTIDUL", "ALIANȚA", "UNIUNEA", "FORȚA", "ASOCIAȚIA", "FORUMUL", "COMUNITATEA"]
INDEPENDENT = "INDEPENDENT"
NR_UAT = 3186


def normalizeaza(s: str) -> str:
    """spații multiple / NBSP, ghilimele „” → ", ş/ţ cu sedilă → ș/ț cu virgulă"""
    s = s.replace("\xa0", " ").replace("„", '"').replace("”", '"').replace("“", '"')
    s = s.translate(str.maketrans("şţŞŢ", "șțȘȚ"))
    return re.sub(r"\s+", " ", s).strip()


def cheie(s: str) -> str:
    """forma de comparare: fără spații în jurul cratimelor („USR - PMP” = „USR-PMP”)"""
    return re.sub(r"\s*-\s*", "-", s)


def citeste():
    wb = openpyxl.load_workbook(SURSA, read_only=True, data_only=True)
    ws = wb["judete"]
    antet, randuri = None, []
    for r in ws.iter_rows(values_only=True):
        r = list(r)
        if len(r) < 2 or r[1] is None:
            continue
        if r[1] == "county_nce":
            if r[1:1 + len(STANDARD)] != STANDARD:
                sys.exit(f"Antet neașteptat: {r[1:1 + len(STANDARD)]}")
            candidati = r[1 + len(STANDARD):]
            # rândul de filtre are numere (1, 2, 3...) în loc de candidați
            antet = None if all(not isinstance(c, str) for c in candidati if c is not None) else r
            continue
        if antet is None:
            sys.exit(f"Rând de date fără antet de județ: {r[:5]}")
        randuri.append((antet, r))
    wb.close()
    return randuri


def lista_alba(antete, config):
    """{cheie competitor: forma afișată}"""
    forme = defaultdict(Counter)
    tipar = re.compile(r"-(?=(" + "|".join(CUVINTE_CHEIE) + r")\b)")
    for a in antete:
        m = tipar.search(cheie(a))  # cel mai din stânga = sufixul cel mai lung
        if m:
            # forma originală a sufixului: aceeași poziție a cratimei, numărată de la sfârșit
            k = cheie(a)[m.end():]
            forme[k][_sufix_original(a, k.count("-"))] += 1
    for c in list(config["competitori"]) + config["competitori_fara_cuvant_cheie"]:
        forme[cheie(normalizeaza(c))][normalizeaza(c)] += 1000  # forma din config are prioritate
    return {k: f.most_common(1)[0][0] for k, f in forme.items()}


def _cratima(a, nr_cratime):
    """poziția celei de-a (nr_cratime+1)-a cratime de la sfârșit"""
    poz = len(a)
    for _ in range(nr_cratime + 1):
        poz = a.rindex("-", 0, poz)
    return poz


def _sufix_original(a, nr_cratime):
    return a[_cratima(a, nr_cratime) + 1:].strip()


def separa(antet, alba_sortata):
    """„NUME PRENUME-COMPETITOR-voturi” → (nume, competitor | INDEPENDENT)"""
    a = normalizeaza(antet)
    if not a.endswith(SUFIX):
        sys.exit(f"Antet de candidat fără „{SUFIX}”: {antet!r}")
    a = a[:-len(SUFIX)].strip()
    ka = cheie(a)
    for k, forma in alba_sortata:
        if ka.endswith("-" + k):
            return a[:_cratima(a, k.count("-"))].strip(" -"), forma
    return a, INDEPENDENT


def data_excel(v):
    if isinstance(v, (int, float)):
        return (datetime(1899, 12, 30) + timedelta(days=v)).date().isoformat()
    if isinstance(v, datetime):
        return v.date().isoformat()
    return None


def main():
    config = json.loads(ALIANTE.read_text(encoding="utf-8"))
    randuri = citeste()
    antete = sorted({normalizeaza(c)[:-len(SUFIX)].strip()
                     for ant, _ in randuri for c in ant[1 + len(STANDARD):] if isinstance(c, str)})
    alba = lista_alba(antete, config)
    alba_sortata = sorted(alba.items(), key=lambda kv: -len(kv[0]))

    # competitorii (cu tipul și partidele componente)
    cfg_comp = {cheie(normalizeaza(k)): v for k, v in config["competitori"].items()}
    nume_partid = {cheie(normalizeaza(v)): k for k, v in config["partide"].items()}
    comp_idx, competitori = {}, []

    def idx(forma):
        if forma not in comp_idx:
            if forma == INDEPENDENT:
                info = {"n": INDEPENDENT, "s": "Independenți", "p": [], "t": "independent"}
            elif cheie(forma) in cfg_comp:
                c = cfg_comp[cheie(forma)]
                info = {"n": forma, "s": c.get("scurt") or nume_partid.get(cheie(forma)) or forma,
                        "p": c["partide"], "t": c["tip"]}
                if c.get("nota"):
                    info["nota"] = c["nota"]
            else:
                ab = nume_partid.get(cheie(forma))
                info = {"n": forma, "s": ab or forma, "p": [ab] if ab else [], "t": "partid"}
            comp_idx[forma] = len(competitori)
            competitori.append(info)
        return comp_idx[forma]

    uat, erori, scope = [], [], Counter()
    candidati_comp = defaultdict(set)   # competitor -> {(judet, nume)}
    independenti = set()
    data_max = None
    for ant, r in randuri:
        col = {n: i for i, n in enumerate(ant) if isinstance(n, str)}
        v = lambda k: int(r[col[k]] or 0)  # noqa: E731
        scope[r[col["report_type_code"]]] += 1
        d = data_excel(r[col["created_at"]])
        data_max = max(filter(None, [data_max, d]), default=None)
        judet = normalizeaza(str(r[col["county_name"]]))
        cand = []
        for i in range(1 + len(STANDARD), len(ant)):
            if not isinstance(ant[i], str):
                continue
            nume, comp = separa(ant[i], alba_sortata)
            if comp == INDEPENDENT:
                independenti.add((judet, nume))
            else:
                candidati_comp[comp].add((judet, nume))
            voturi = int(r[i] or 0)
            if voturi > 0:
                cand.append([nume, idx(comp), voturi])
        c = v("c")
        suma = sum(x[2] for x in cand)
        nume_uat = normalizeaza(str(r[col["uat_name"]]))
        if suma != c:
            erori.append(f"{judet} / {nume_uat}: suma candidaților {suma:,} ≠ c {c:,}")
            continue
        cand.sort(key=lambda x: (-x[2], x[0]))
        for x in cand:
            x.append(round(x[2] / c * 100, 2) if c else 0)
        v1 = cand[0][2] if cand else 0
        v2 = cand[1][2] if len(cand) > 1 else 0
        egal = len(cand) > 1 and v1 == v2
        a, b = v("a"), v("b")
        uat.append({
            "j": judet, "u": nume_uat, "s": r[col["uat_siruta"]],
            "t": "sector" if r[col["report_type_code"]] == "P_CE_SECTOR" else "UAT",
            "a": a, "b": b, "c": c, "d": v("d"),
            "pr": round(b / a * 100, 2) if a else 0,
            "k": cand,
            "w": None if egal or not cand else 0,
            "eg": egal,
            "mv": v1 - v2,
            "mp": round((v1 - v2) / c * 100, 2) if c else 0,
            "nc": len(cand),
        })

    if erori:
        print(f"EROARE: {len(erori)} UAT-uri nu se reconciliază (suma voturilor ≠ c):")
        print("\n".join("  " + e for e in erori))
        sys.exit(1)
    if len(uat) != NR_UAT:
        sys.exit(f"EROARE: {len(uat)} UAT-uri, aștept {NR_UAT} ({dict(scope)})")

    # competitorii fără niciun vot apar totuși în lista de verificare
    for comp in candidati_comp:
        idx(comp)
    idx(INDEPENDENT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "sursa": "Autoritatea Electorală Permanentă — prezenta.roaep.ro/locale09062024v2, PV final, alegeri pentru primar",
        "data_pv": data_max,
        "nota": "Primarul General al Municipiului București nu este inclus. Sectoarele 1–6 apar ca UAT-uri (tip „sector”).",
        "partide": config["partide"],
        "competitori": competitori,
        "uat": uat,
    }
    OUT.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ── rezumat pentru verificare ──
    print(f"UAT-uri: {len(uat):,} ({', '.join(f'{k}: {n:,}' for k, n in scope.items())}) — toate reconciliate (Σ candidați = c)")
    print(f"Prezență: {sum(x['b'] for x in uat) / sum(x['a'] for x in uat) * 100:.2f}% · valabile {sum(x['c'] for x in uat):,} · nule {sum(x['d'] for x in uat):,}")
    print(f"\nCompetitori găsiți: {len(candidati_comp)} (număr de candidați)")
    for comp, s in sorted(candidati_comp.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        info = competitori[comp_idx[comp]]
        print(f"  {len(s):>5}  {comp}  [{info['t']}{': ' + ', '.join(info['p']) if info['p'] else ''}]")
    suspecti = [c for c in candidati_comp if " " not in c]
    print(f"\n  competitori dintr-un singur cuvânt (posibile prenume): {suspecti or 'niciunul'}")
    print(f"\nIndependenți: {len(independenti)}")
    for j, n in sorted(independenti):
        print(f"  {j:<20} {n}")
    egal = [x for x in uat if x["eg"]]
    print(f"\nEgalități pe primul loc: {len(egal)}")
    for x in egal:
        print(f"  {x['j']} / {x['u']}: " + ", ".join(f"{k[0]} ({competitori[k[1]]['s']}) {k[2]}" for k in x["k"][:2]))

    castig = Counter(competitori[x["k"][0][1]]["s"] for x in uat if x["w"] == 0)
    print(f"\nTop 10 competitori după primari ({sum(castig.values()):,} primării cu câștigător):")
    for s, n in castig.most_common(10):
        print(f"  {n:>5}  {s}")
    pe_partid = Counter()
    for x in uat:
        if x["w"] == 0:
            c = competitori[x["k"][0][1]]
            for p in c["p"] or [c["s"]]:
                pe_partid[p] += 1
    print("\nTop 10 partide după primari (alianțele descompuse — un primar poate conta la mai multe partide):")
    for s, n in pe_partid.most_common(10):
        print(f"  {n:>5}  {s}")
    print(f"\n{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1024:,.1f} KB")


if __name__ == "__main__":
    main()
