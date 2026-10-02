#!/usr/bin/env python3
"""
LOC108B (INS TEMPO) → src/data/imobiliare/autorizatii_localitati.json

Autorizații de construire pentru clădiri, pe județe și localități, anual (2002–...).
Date anuale: INS actualizează matricea o dată pe an (aprilie), deci rularea e manuală:

  1. python scripts/fetch_loc108b.py          # LOCAL — portul 8077 al INS nu răspunde din GitHub Actions
  2. python scripts/build_autorizatii_localitati.py LOC108B_export.xlsx

Capcane (vezi și fetch_loc108b.py):
  - rândurile lipsă = 0 autorizații;
  - ruptură de serie în 2009: până în 2008 există doar agregatul „Alte cladiri (hoteluri…, comert…)”,
    din 2009 subcategoriile Hoteluri / Comerț / Alte clădiri → le adunăm în grupul „altele”.
"""
import json
import sys
from pathlib import Path

import pandas as pd

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "LOC108B_export.xlsx")
OUT = Path("src/data/imobiliare/autorizatii_localitati.json")
ANI_LOC = 10  # câți ani păstrăm per localitate (seria completă rămâne la nivel național și județean)

C_CAT, C_NR, C_MP = "Categorie constructii", "Numar autorizatii", "Suprafata utila (mp)"

# categoriile INS → 3 grupe ușor de înțeles și comparabile în timp
GRUPE = {
    "Cladiri rezidentiale (exclusiv cele pentru colectivitati)": "locuinte",
    "Cladiri rezidentiale pentru colectivitati": "altele",
    "Cladiri administrative": "birouri",
    "Hoteluri si cladiri similare": "altele",
    "Cladiri pentru comert cu ridicata si cu amanuntul": "altele",
    "Alte cladiri": "altele",
    "Alte cladiri (hoteluri si cladiri similare, cladiri pentru comert cu ridicata si cu amanuntul, etc)": "altele",
}


def main():
    df = pd.read_excel(SRC, sheet_name="Date")
    necunoscute = set(df[C_CAT]) - set(GRUPE)
    if necunoscute:
        sys.exit(f"Categorii noi, necartografiate: {necunoscute}")
    df["g"] = df[C_CAT].map(GRUPE)
    ani = sorted(int(a) for a in df["An"].unique())

    def serie(sub: pd.DataFrame, col: str) -> list[int]:
        s = sub.groupby("An")[col].sum()
        return [int(s.get(a, 0)) for a in ani]

    national = {"nr": serie(df, C_NR), "mp": serie(df, C_MP)}
    for g in ("locuinte", "birouri", "altele"):
        sub = df[df.g == g]
        national[f"{g}_nr"] = serie(sub, C_NR)
        national[f"{g}_mp"] = serie(sub, C_MP)

    judete = {}
    for j, sub in df.groupby("Judet"):
        loc = sub[sub.g == "locuinte"]
        judete[j] = {"nr": serie(sub, C_NR), "mp": serie(sub, C_MP),
                     "locuinte_nr": serie(loc, C_NR), "locuinte_mp": serie(loc, C_MP)}

    ani_loc = ani[-ANI_LOC:]
    localitati = []
    for (j, siruta, nume), sub in df[df.An.isin(ani_loc)].groupby(["Judet", "Cod SIRUTA", "Localitate"]):
        s = sub.groupby("An")[C_NR].sum()
        nr = [int(s.get(a, 0)) for a in ani_loc]
        if not any(nr):
            continue
        ultim = sub[sub.An == ani_loc[-1]]
        localitati.append({
            "j": j, "s": int(siruta), "n": nume, "nr": nr,
            "mp": int(ultim[C_MP].sum()),
            "loc": int(ultim[ultim.g == "locuinte"][C_NR].sum()),
        })

    info = pd.read_excel(SRC, sheet_name="Info", header=None) if "Info" in pd.ExcelFile(SRC).sheet_names else None
    actualizat = None
    if info is not None:
        m = dict(zip(info[0].astype(str), info[1].astype(str)))
        actualizat = m.get("Ultima actualizare INS")

    out = {
        "meta": {
            "sursa": "INS TEMPO-Online, LOC108B — Autorizații de construire eliberate pentru clădiri, pe județe și localități",
            "url": "http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table",
            "actualizat_ins": actualizat,
            "ani": ani,
            "ani_localitati": ani_loc,
        },
        "national": national,
        "judete": judete,
        "localitati": localitati,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT}: {len(judete)} județe, {len(localitati)} localități, ani {ani[0]}–{ani[-1]}, "
          f"{OUT.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
