"""Export complet LOC108B din INS TEMPO-Online -> Excel. Rulează local (portul 8077 e blocat din cloud).
Apoi: python scripts/build_autorizatii_localitati.py LOC108B_export.xlsx  (generează JSON-ul pentru /imobiliare)."""
import time, requests, pandas as pd

BASE = "http://statistici.insse.ro:8077/tempo-ins"
CODE = "LOC108B"
m = requests.get(f"{BASE}/matrix/{CODE}", timeout=60).json()
cats, juds, locs, ani, ums = m["dimensionsMap"]
det = m["details"]

def pivot(jud, um):
    loc_ids = [o["nomItemId"] for o in locs["options"] if o["parentId"] == jud["nomItemId"]]
    enc = ":".join([
        ",".join(str(o["nomItemId"]) for o in cats["options"]),
        str(jud["nomItemId"]),
        ",".join(map(str, loc_ids)),
        ",".join(str(o["nomItemId"]) for o in ani["options"]),
        str(um["nomItemId"]),
    ])
    body = {"language": "ro", "arr": [], "matrixName": m["matrixName"], "matrixDetails": det,
            "encQuery": enc, "matCode": CODE, "matMaxDim": det["matMaxDim"],
            "matUMSpec": det["matUMSpec"], "matRegJ": det["matRegJ"]}
    for a in range(4):
        try:
            r = requests.post(f"{BASE}/pivot", json=body, timeout=120)
            if r.ok and len(r.text) > 100:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(3 * (a + 1))
    raise RuntimeError(f"Esec: {jud['label']} / {um['label']}")

rows = []
for jud in juds["options"][1:]:          # sare peste TOTAL
    for um in ums["options"]:
        for line in pivot(jud, um).splitlines()[1:]:
            if not line.strip():
                continue
            p = line.split(", ")
            val, u, an, loc, jd = p.pop(), p.pop(), p.pop(), p.pop(), p.pop()
            rows.append((jd.strip(), loc.strip(), ", ".join(p), int(an.split()[-1]),
                         "nr" if u.startswith("Numar") else "mp", float(val)))
        print(jud["label"], um["label"], "ok")

df = pd.DataFrame(rows, columns=["Judet", "Loc", "Categorie", "An", "um", "val"])
w = df.pivot_table(index=["Judet", "Loc", "Categorie", "An"], columns="um", values="val", aggfunc="sum").fillna(0).reset_index()
w[["Cod SIRUTA", "Localitate"]] = w["Loc"].str.extract(r"^(\d+)\s+(.*)$")
w = w.rename(columns={"nr": "Numar autorizatii", "mp": "Suprafata utila (mp)"})
w = w[["Judet", "Cod SIRUTA", "Localitate", "Categorie", "An", "Numar autorizatii", "Suprafata utila (mp)"]]
w.to_excel(f"{CODE}_export.xlsx", sheet_name="Date", index=False)
print(len(w), "randuri")
