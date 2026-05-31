#!/usr/bin/env python3
"""
Script: fetch_constructii.py - fix final
Structura confirmata din log:
  dim[0] Categorii: nomItemId=17745 (primul)
  dim[1] Medii de rezidenta: nomItemId=100 "Total"
  dim[2] Macroregiuni/judete: nomItemId=112 "TOTAL"
  dim[3] Perioade: nomItemId=4475 "Anul 2002" (primul)
  dim[4] UM: nomItemId=9669 "Numar" (primul) / al doilea = "Metri patrati suprafata utila"

NullPointerException = UM trimis gresit. Solutie: trimitem FARA dimensiunea UM
(sau cu al doilea element al UM).
"""

import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime

OUTPUT_PATH = "src/data/constructii/constructii_data.json"
MATRIX_NAME = "LOC108A"
BASE_URL = "http://statistici.insse.ro:8077/tempo-ins"

LUNI_RO = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
}

def get_metadata():
    url = f"{BASE_URL}/matrix/{MATRIX_NAME}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def post_data(arr_payload):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    body = json.dumps({"language": "ro", "arr": arr_payload, "matrixName": MATRIX_NAME}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try: err_body = e.read().decode("utf-8")[:200]
        except: err_body = str(e)
        return None, f"HTTP {e.code}: {err_body}"

def parse_luna_option(label):
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            an = int(parts[2])
            luna_part = parts[1]
            return (an, LUNI_RO.get(luna_part, int(luna_part) if luna_part.isdigit() else 0))
        elif parts[0] in ("anul", "an"):
            return (int(parts[1]), 0)
    except: pass
    return (0, 0)

def parse_luna_json(label):
    parts = label.strip().split()
    try: return (int(parts[2]), int(parts[1]))
    except: return (0, 0)

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def make_arr(dims, luna_opt, cat_opts, mediu_opts, reg_opts, um_opts, skip_um=False):
    arr = []
    for dim in dims:
        lbl = dim.get("label", "").lower()
        opts = dim.get("options", [])
        if "um:" in lbl:
            if skip_um:
                continue  # sarim complet dimensiunea UM
            else:
                arr.append(um_opts or opts[:1])
        elif "categor" in lbl:
            arr.append(cat_opts)
        elif "perioad" in lbl:
            arr.append([luna_opt])
        elif "mediu" in lbl or "rezident" in lbl:
            arr.append(mediu_opts or opts[:1])
        elif "macroreg" in lbl or "regiuni" in lbl:
            arr.append(reg_opts or opts[:1])
        else:
            arr.append(opts[:1])
    return arr

def main():
    print(f"[{datetime.now().isoformat()}] Start LOC108A...")
    existing = load_existing()

    ultima_key = (0, 0)
    for vals in existing.get("date", {}).values():
        for d in vals:
            k = parse_luna_json(d.get("luna", ""))
            if k > ultima_key:
                ultima_key = k
    print(f"  Ultima luna JSON: an={ultima_key[0]}, luna={ultima_key[1]}")

    try:
        meta = get_metadata()
        dims = meta.get("dimensionsMap", [])
        if isinstance(dims, dict):
            dims = list(dims.values())

        cat_dim = timp_dim = mediu_dim = regiune_dim = um_dim = None
        for dim in dims:
            lbl = dim.get("label", "").lower()
            if "categor" in lbl: cat_dim = dim
            elif "perioad" in lbl: timp_dim = dim
            elif "mediu" in lbl or "rezident" in lbl: mediu_dim = dim
            elif "macroreg" in lbl or "regiuni" in lbl: regiune_dim = dim
            elif "um:" in lbl: um_dim = dim

        missing = [
            o for o in timp_dim.get("options", [])
            if parse_luna_option(o.get("label",""))[1] > 0
            and parse_luna_option(o.get("label","")) > ultima_key
        ]
        print(f"  Luni noi: {[o['label'] for o in missing]}")
        if not missing:
            print("Datele sunt la zi. Modificat: false")
            return

        cat_opts  = cat_dim.get("options", []) if cat_dim else []
        mediu_opts = mediu_dim.get("options", [])[:1] if mediu_dim else []
        reg_opts   = regiune_dim.get("options", [])[:1] if regiune_dim else []

        # UM: "Metri patrati suprafata utila" = al doilea element (confirmat din log: primul e "Numar")
        um_opts_mp = []
        um_opts_nr = []
        if um_dim:
            all_um = um_dim.get("options", [])
            print(f"  UM optiuni: {[o.get('label') for o in all_um]}")
            for o in all_um:
                lbl = o.get("label","").lower()
                if "metri" in lbl or "suprafat" in lbl or "mp" in lbl or "patrati" in lbl:
                    um_opts_mp = [o]
                elif "numar" in lbl or "număr" in lbl:
                    um_opts_nr = [o]
            if not um_opts_mp and len(all_um) >= 2:
                um_opts_mp = [all_um[1]]  # al doilea element = mp

        print(f"  UM mp selectat: {um_opts_mp[0].get('label') if um_opts_mp else 'none'}")

        date_out = existing.get("date", {})
        cats_out = existing.get("categorii", [])
        adaugat_ceva = False

        for luna_opt in missing:
            luna_label = luna_opt.get("label","")
            print(f"\n  === {luna_label} ===")

            # Incercam in ordine:
            # 1. Cu UM=mp (al doilea element)
            # 2. Fara dimensiunea UM complet
            # 3. Cu UM=numar (primul element)
            tentative = [
                ("cu UM=mp", make_arr(dims, luna_opt, cat_opts, mediu_opts, reg_opts, um_opts_mp, skip_um=False)),
                ("fara UM",  make_arr(dims, luna_opt, cat_opts, mediu_opts, reg_opts, [],         skip_um=True)),
                ("cu UM=nr", make_arr(dims, luna_opt, cat_opts, mediu_opts, reg_opts, um_opts_nr, skip_um=False)),
            ]

            resp_data = None
            for name, arr in tentative:
                print(f"  → Incerc {name} ({len(arr)} dim)...")
                resp, err = post_data(arr)
                if resp is not None:
                    print(f"  ✓ Succes cu '{name}'!")
                    resp_data = resp
                    break
                print(f"  ✗ {err[:120]}")

            if resp_data is None:
                print(f"  ❌ Toate variantele au esuat pentru {luna_label}")
                continue

            raw = resp_data
            if isinstance(resp_data, dict):
                raw = resp_data.get("data", resp_data.get("matrixData", resp_data.get("dataset", [])))

            print(f"  Raw: {type(raw).__name__}, len={len(raw) if hasattr(raw,'__len__') else '?'}")
            if raw and hasattr(raw, '__len__') and len(raw) > 0:
                print(f"  Sample[0]: {str(raw[0])[:150]}")

            if isinstance(raw, list) and raw:
                first = raw[0]
                rows = raw

                # Detectam formatul: matrice 2D sau lista plata
                if isinstance(first, list):
                    # raw[cat_idx] = [val_per_luna]  (o singura luna selectata)
                    for ci, row in enumerate(rows):
                        cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        val_raw = row[0] if isinstance(row, list) and row else row
                        val = _to_float(val_raw)
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            adaugat_ceva = True
                            print(f"     + {cat}: {val}")

                elif isinstance(first, (int, float, str, type(None))):
                    # lista plata: raw[cat_idx] = valoare
                    for ci, val_raw in enumerate(rows):
                        cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        val = _to_float(val_raw)
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            adaugat_ceva = True
                            print(f"     + {cat}: {val}")

        if not adaugat_ceva:
            print("\n⚠️  Nu s-a adaugat nimic nou. Modificat: false")
            return

        for cat in date_out:
            date_out[cat].sort(key=lambda d: parse_luna_option(d.get("luna","")))

        toate = sorted({d["luna"] for v in date_out.values() for d in v}, key=parse_luna_option)

        save_json({
            **existing,
            "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
            "categorii": cats_out,
            "perioade": toate,
            "date": date_out
        })
        print(f"\n✅ Salvat! Ultima luna: {toate[-1] if toate else '?'}")
        print("Modificat: true")

    except urllib.error.URLError as e:
        print(f"❌ Eroare retea: {e}"); sys.exit(1)
    except Exception as e:
        import traceback; traceback.print_exc(); sys.exit(1)

def _to_float(val_raw):
    if val_raw in [None, "", "-", " ", ":", "..."]:
        return None
    try:
        return float(str(val_raw).replace(",",".").replace(" ",""))
    except:
        return None

if __name__ == "__main__":
    main()
