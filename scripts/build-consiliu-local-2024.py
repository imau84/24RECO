#!/usr/bin/env python3
"""
build-consiliu-local-2024.py
============================
Din data/raw/alegeri-locale-2024/consiliu-local/pv_final_cnty_cl_<cod>.csv (export AEP, PV final,
alegeri pentru consiliul local, 9 iunie 2024 — prezenta.roaep.ro/locale09062024v2; 41 de județe +
„b” = sectoarele Bucureștiului, fără Consiliul General) generează
public/data/alegeri-locale-2024/consiliu-local.json, cu o intrare pe UAT.

Fiecare CSV are antetul lui: coloanele standard (county_nce … c, d, e, f, g1.1, g1.2, g1.3, g4),
apoi câte un grup de coloane pe competitor (listă, nu candidat):
  <COMPETITOR>-voturi, -mandate-faza-1, -mandate-faza-2, -mandate-g8 (minorități), -mandate-g9.
Numele competitorului = antetul fără sufixul ancorat la final (numele pot conține „-”).
Mandate pe competitor = faza-1 + faza-2 + g8 + g9.

Clasificare: partid / alianță / alianță locală (data/alegeri-locale-2024/aliante.json), organizație a
minorităților (UNIUNEA/FORUMUL/COMUNITATEA/ASOCIAȚIA … a unei minorități; UDMR = partid) și
independent = orice competitor al cărui nume nu începe cu PARTIDUL, ALIANȚA, UNIUNEA… și nu e în
„competitori_fara_cuvant_cheie” (numele persoanei).

Legătura cu primarul: din public/data/alegeri-locale-2024/primari.json (după SIRUTA), competitorul
primarului ales și mandatele lui în consiliu.

Validări (scriptul se oprește cu eroare): 3.186 de UAT-uri, 42 de județe; Σ voturi competitori = c
în fiecare UAT; Σ mandate = 39.858 (faza-1 34.262 + faza-2 5.477 + g8 119); mărimea fiecărui consiliu
în {9, 11, …, 31}; controlul pe Municipiul Timișoara.

Rulare:  python scripts/build-consiliu-local-2024.py   (după build-primari-2024.py)
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURSA = ROOT / "data" / "raw" / "alegeri-locale-2024" / "consiliu-local"
ALIANTE = ROOT / "data" / "alegeri-locale-2024" / "aliante.json"
PRIMARI = ROOT / "public" / "data" / "alegeri-locale-2024" / "primari.json"
OUT = ROOT / "public" / "data" / "alegeri-locale-2024" / "consiliu-local.json"

STANDARD = ["county_nce", "county_name", "uat_name", "uat_siruta", "report_version", "report_stage_code",
            "report_type_scope_code", "report_type_category_code", "report_type_code", "created_at",
            "a", "a1", "a2", "a3", "a4", "b", "b1", "b2", "b3", "b4", "c", "d", "e", "f",
            "g1.1", "g1.2", "g1.3", "g4"]
SUFIX = re.compile(r"-(voturi|mandate-faza-1|mandate-faza-2|mandate-g8|mandate-g9)$")
CUVINTE_CHEIE = ("PARTIDUL", "ALIANȚA", "UNIUNEA", "FORȚA", "ASOCIAȚIA", "FORUMUL", "COMUNITATEA")
MINORITATI = re.compile(r"^(UNIUNEA (?!SALVAȚI|NAȚIUNII|CREȘTIN)|FORUMUL|COMUNITATEA|ASOCIAȚIA)")
UDMR = "UNIUNEA DEMOCRATĂ MAGHIARĂ DIN ROMÂNIA"  # organizație a minorității, dar o tratăm ca partid
NR_UAT, NR_JUDETE = 3186, 42
MANDATE = {"f1": 34262, "f2": 5477, "g8": 119}
MARIMI = {9, 11, 13, 15, 17, 19, 21, 23, 27, 31}
CONTROL = ("MUNICIPIUL TIMIȘOARA", 27, {
    "ALIANȚA TIMIȘOARA UNITĂ USR - PMP - FORȚA DREPTEI - UDMR": 13,
    "ALIANȚA ELECTORALĂ PSD PNL": 11,
    "ALIANȚA PENTRU UNIREA ROMÂNILOR": 3,
})


def normalizeaza(s: str) -> str:
    """spații multiple / NBSP, ghilimele „” → ", ş/ţ cu sedilă → ș/ț cu virgulă (ca la primari)"""
    s = s.replace("\xa0", " ").replace("„", '"').replace("”", '"').replace("“", '"')
    s = s.translate(str.maketrans("şţŞŢ", "șțȘȚ"))
    return re.sub(r"\s+", " ", s).strip()


def cheie(s: str) -> str:
    """forma de comparare: fără spații în jurul cratimelor („USR - PMP” = „USR-PMP”)"""
    return re.sub(r"\s*-\s*", "-", normalizeaza(s))


def citeste():
    """[(cod fișier, {competitor: {sufix: coloană}}, rând)]"""
    fisiere = sorted(SURSA.glob("pv_final_cnty_cl_*.csv"))
    if len(fisiere) != NR_JUDETE:
        sys.exit(f"EROARE: {len(fisiere)} fișiere CSV, aștept {NR_JUDETE}")
    randuri = []
    for f in fisiere:
        with f.open(encoding="utf-8-sig", newline="") as fh:
            rd = csv.reader(fh)
            antet = next(rd)
            if antet[:len(STANDARD)] != STANDARD:
                sys.exit(f"EROARE: antet neașteptat în {f.name}: {antet[:len(STANDARD)]}")
            grupuri = defaultdict(dict)
            for i in range(len(STANDARD), len(antet)):
                m = SUFIX.search(antet[i])
                if not m:
                    sys.exit(f"EROARE: coloană fără sufix cunoscut în {f.name}: {antet[i]!r}")
                grupuri[normalizeaza(antet[i][:m.start()])][m.group(1)] = i
            for comp, g in grupuri.items():
                if "voturi" not in g:
                    sys.exit(f"EROARE: {f.name}: competitorul {comp!r} nu are coloană de voturi")
            for r in rd:
                if r:
                    randuri.append((f.stem.rsplit("_", 1)[1], antet, grupuri, r))
    return randuri


def main():
    config = json.loads(ALIANTE.read_text(encoding="utf-8"))
    cfg_comp = {cheie(k): v for k, v in config["competitori"].items()}
    fara_cuvant = {cheie(x) for x in config["competitori_fara_cuvant_cheie"]}
    nume_partid = {cheie(v): k for k, v in config["partide"].items()}
    randuri = citeste()

    comp_idx, competitori = {}, []

    def tip(forma):
        k = cheie(forma)
        if k in cfg_comp:
            return cfg_comp[k]["tip"]
        if forma.startswith(CUVINTE_CHEIE) or k in fara_cuvant:
            return "minoritate" if MINORITATI.match(forma) and forma != UDMR else "partid"
        return "independent"

    def idx(forma, independent=False):
        """indicele competitorului; „independent=True” = persoană (candidat independent la primar)"""
        cheia = ("I:" if independent else "") + forma
        if cheia not in comp_idx:
            t = "independent" if independent else tip(forma)
            if t == "independent":
                info = {"n": forma, "s": forma, "p": [], "t": t}
            elif cheie(forma) in cfg_comp:
                c = cfg_comp[cheie(forma)]
                info = {"n": forma, "s": c.get("scurt") or nume_partid.get(cheie(forma)) or forma, "p": c["partide"], "t": t}
                if c.get("nota"):
                    info["nota"] = c["nota"]
            else:
                ab = nume_partid.get(cheie(forma))
                info = {"n": forma, "s": ab or forma, "p": [ab] if ab else [], "t": t}
            comp_idx[cheia] = len(competitori)
            competitori.append(info)
        return comp_idx[cheia]

    # primarii aleși, după SIRUTA: (nume, competitor | None = independent)
    pr = json.loads(PRIMARI.read_text(encoding="utf-8"))
    primar = {}
    for u in pr["uat"]:
        if u["w"] == 0:
            nume, ci = u["k"][0][0], u["k"][0][1]
            c = pr["competitori"][ci]
            primar[u["s"]] = (nume, None if c["t"] == "independent" else c["n"])

    uat, erori, tipuri, judete = [], [], Counter(), set()
    total = Counter()
    for cod, antet, grupuri, r in randuri:
        v = lambda i: int(r[i] or 0)  # noqa: E731
        col = {n: i for i, n in enumerate(antet[:len(STANDARD)])}
        judet = normalizeaza(r[col["county_name"]])
        nume_uat = normalizeaza(r[col["uat_name"]])
        siruta = int(r[col["uat_siruta"]])
        judete.add(cod)
        tipuri[r[col["report_type_code"]]] += 1
        k = []
        for comp, g in grupuri.items():
            vot = v(g["voturi"])
            f1, f2 = v(g["mandate-faza-1"]) if "mandate-faza-1" in g else 0, v(g["mandate-faza-2"]) if "mandate-faza-2" in g else 0
            g8 = v(g["mandate-g8"]) if "mandate-g8" in g else 0
            g9 = v(g["mandate-g9"]) if "mandate-g9" in g else 0
            total.update(f1=f1, f2=f2, g8=g8, g9=g9)
            if vot > 0 or f1 + f2 + g8 + g9 > 0:
                k.append([idx(comp), vot, 0, f1, f2, g8 + g9, f1 + f2 + g8 + g9])
        c = v(col["c"])
        loc = f"{judet} / {nume_uat}"
        if sum(x[1] for x in k) != c:
            erori.append(f"{loc}: Σ voturi competitori {sum(x[1] for x in k):,} ≠ c {c:,}")
        m = sum(x[6] for x in k)
        if m not in MARIMI:
            erori.append(f"{loc}: {m} mandate — mărime de consiliu neașteptată")
        for x in k:
            x[2] = round(x[1] / c * 100, 2) if c else 0
        k.sort(key=lambda x: (-x[6], -x[1], competitori[x[0]]["n"]))
        lider = k[0]
        prag = m // 2 + 1
        a, b = v(col["a"]), v(col["b"])
        o = {
            "j": judet, "u": nume_uat, "s": siruta,
            "t": "sector" if r[col["report_type_code"]] == "CL_CE_SECTOR" else "UAT",
            "a": a, "b": b, "c": c, "d": v(col["d"]), "e": v(col["e"]), "f": v(col["f"]),
            "g": [r[col["g1.1"]], r[col["g1.2"]], r[col["g1.3"]], r[col["g4"]]],
            "pr": round(b / a * 100, 2) if a else 0,
            "m": m,
            "k": k,
            "maj": lider[6] >= prag,
            "lp": max(0, prag - lider[6]),
            "eg": len(k) > 1 and k[1][6] == lider[6],
        }
        if siruta in primar:
            nume, comp = primar[siruta]
            if comp is None:
                # independent: poate a candidat și la consiliu, cu numele lui
                ci = comp_idx.get(nume) if tip(nume) == "independent" else None
                ci = ci if ci is not None else idx(nume, independent=True)
            else:
                ci = comp_idx.get(comp)
                if ci is None:
                    # primarul e de la un competitor care n-are listă în acest UAT (sau nicăieri)
                    ci = next((comp_idx[x] for x in comp_idx if not x.startswith("I:") and cheie(x) == cheie(comp)), None)
                    ci = ci if ci is not None else idx(comp)
            mand = next((x[6] for x in k if x[0] == ci), 0)
            o["p"] = [nume, ci, mand, mand >= prag]
        uat.append(o)

    if len(uat) != NR_UAT:
        erori.append(f"{len(uat)} UAT-uri, aștept {NR_UAT} ({dict(tipuri)})")
    if len(judete) != NR_JUDETE:
        erori.append(f"{len(judete)} județe, aștept {NR_JUDETE}")
    for f, n in MANDATE.items():
        if total[f] != n:
            erori.append(f"mandate {f}: {total[f]:,}, aștept {n:,}")
    if sum(total.values()) != sum(MANDATE.values()):
        erori.append(f"total mandate {sum(total.values()):,}, aștept {sum(MANDATE.values()):,}")
    ctl = [u for u in uat if u["u"] == CONTROL[0]]
    if len(ctl) != 1 or ctl[0]["m"] != CONTROL[1] or \
            {competitori[x[0]]["n"]: x[6] for x in ctl[0]["k"] if x[6]} != CONTROL[2]:
        erori.append(f"controlul {CONTROL[0]} nu se potrivește: {ctl and [(competitori[x[0]]['n'], x[6]) for x in ctl[0]['k']]}")
    if erori:
        print(f"EROARE: {len(erori)} validări picate:")
        print("\n".join("  " + e for e in erori))
        sys.exit(1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "sursa": "Autoritatea Electorală Permanentă — prezenta.roaep.ro/locale09062024v2, PV final, alegeri pentru consiliul local",
        "nota": "Consiliul General al Municipiului București nu este inclus. Sectoarele 1–6 apar ca UAT-uri (tip „sector”). "
                "k = [competitor, voturi, % din c, mandate faza 1, mandate faza 2, mandate minorități (g8+g9), total]; "
                "p = [primar, competitor, mandatele competitorului primarului, are majoritate]; g = [g1.1, g1.2, g1.3, g4] din PV.",
        "partide": config["partide"],
        "competitori": competitori,
        "uat": uat,
    }
    OUT.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ── rezumat pentru verificare ──
    print(f"UAT-uri: {len(uat):,} ({', '.join(f'{k}: {n:,}' for k, n in tipuri.items())}), {len(judete)} județe — toate reconciliate")
    print(f"Mandate: {sum(total.values()):,} = faza 1 {total['f1']:,} + faza 2 {total['f2']:,} + minorități (g8) {total['g8']:,} + g9 {total['g9']:,}")
    print("Mărimea consiliilor: " + ", ".join(f"{m}: {n:,}" for m, n in sorted(Counter(u['m'] for u in uat).items())))
    print(f"Prezență: {sum(u['b'] for u in uat) / sum(u['a'] for u in uat) * 100:.2f}% · valabile {sum(u['c'] for u in uat):,} · nule {sum(u['d'] for u in uat):,}")

    mand = Counter()
    for u in uat:
        for x in u["k"]:
            mand[x[0]] += x[6]
    print("\nTop 15 competitori după mandate:")
    for ci, n in mand.most_common(15):
        print(f"  {n:>6,}  {competitori[ci]['s']}  [{competitori[ci]['t']}]")
    print("\nTipuri de competitori: " + ", ".join(f"{t}: {n}" for t, n in Counter(c['t'] for c in competitori).items()))
    print("Organizații ale minorităților: " + "; ".join(c["n"] for c in competitori if c["t"] == "minoritate"))
    ind = defaultdict(list)
    for u in uat:
        for x in u["k"]:
            if competitori[x[0]]["t"] == "independent":
                ind[competitori[x[0]]["n"]].append((u["j"], u["u"], x[6]))
    print(f"\nIndependenți (candidați la consiliu): {len(ind)}, aleși: {sum(1 for v in ind.values() if any(z[2] for z in v))}")
    for n, v in sorted(ind.items(), key=lambda kv: (kv[1][0][0], kv[0])):
        for j, u, m in v:
            print(f"  {j:<20} {u:<35} {n}{'  — ales' if m else ''}")

    maj = Counter()
    for u in uat:
        if u["maj"]:
            c = competitori[u["k"][0][0]]
            maj[c["s"] if c["t"] != "independent" else "Independent"] += 1
    print(f"\nConsilii cu majoritate absolută: {sum(maj.values()):,} din {len(uat):,} (fragmentate: {len(uat) - sum(maj.values()):,})")
    for s, n in maj.most_common():
        print(f"  {n:>5}  {s}")
    pe_partid = Counter()
    for u in uat:
        if u["maj"]:
            c = competitori[u["k"][0][0]]
            for p in c["p"] or [c["s"] if c["t"] != "independent" else "Independenți"]:
                pe_partid[p] += 1
    print("Pe partid (alianțele descompuse):")
    for s, n in pe_partid.most_common(12):
        print(f"  {n:>5}  {s}")
    cu_p = [u for u in uat if "p" in u]
    print(f"\nPrimari cu majoritate proprie în consiliu: {sum(u['p'][3] for u in cu_p):,} din {len(cu_p):,}")
    print(f"\n{OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1024:,.1f} KB")


if __name__ == "__main__":
    main()
