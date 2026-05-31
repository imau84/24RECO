#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Abordare noua: folosim exact formatul din browser (inspectat via DevTools pe tempo-online)
LOC108A: 5 dimensiuni confirmate din log:
  [0] Categorii de constructii (dimCode=1) - 7 optiuni
  [1] Medii de rezidenta (dimCode=2) - 3 optiuni  
  [2] Macroregiuni, regiuni de dezvoltare si judete (dimCode=3) - 55 optiuni
  [3] Perioade (dimCode=4) - 316 optiuni
  [4] UM: Numar, mp suprafata utila (dimCode=5) - 2 optiuni
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
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def post_data(arr_payload):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    body = json.dumps({
        "language": "ro",
        "arr": arr_payload,
        "matrixName": MATRIX_NAME
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        body_err = ""
        try:
            body_err = e.read().decode("utf-8")[:300]
        except:
            pass
        return None, f"HTTP {e.code}: {body_err}"

def parse_luna_option(label):
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            luna_part = parts[1]
            an = int(parts[2])
            return (an, LUNI_RO.get(luna_part, int(luna_part) if luna_part.isdigit() else 0))
        elif parts[0] in ("anul", "an"):
            return (int(parts[1]), 0)
    except (IndexError, ValueError):
        pass
    return (0, 0)

def parse_luna_json(label):
    parts = label.strip().split()
    try:
        return (int(parts[2]), int(parts[1]))
    except:
        return (0, 0)

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

        # Print complet prima dimensiune pentru debug
        print(f"\n  === DEBUG: Prima optiune din fiecare dimensiune ===")
        for i, dim in enumerate(dims):
            opts = dim.get("options", [])
            lbl = dim.get("label", "")
            first_opt = opts[0] if opts else {}
            print(f"  dim[{i}] '{lbl}': {json.dumps(first_opt, ensure_ascii=False)}")
        print()

        # Identificam dimensiunile
        cat_dim = timp_dim = mediu_dim = regiune_dim = um_dim = None
        for dim in dims:
            label = dim.get("label", "").lower()
            if "categor" in label:
                cat_dim = dim
            elif "perioad" in label:
                timp_dim = dim
            elif "mediu" in label or "rezident" in label:
                mediu_dim = dim
            elif "macroreg" in label or "regiuni" in label:
                regiune_dim = dim
            elif "um:" in label:
                um_dim = dim

        # Luni noi
        missing = [
            o for o in timp_dim.get("options", [])
            if parse_luna_option(o.get("label", ""))[1] > 0
            and parse_luna_option(o.get("label", "")) > ultima_key
        ]
        print(f"  Luni noi: {[o['label'] for o in missing]}")

        if not missing:
            print("Datele sunt la zi. Modificat: false")
            return

        # Selectii fixe pentru dimensiunile non-timp
        # Categorii: toate cele 7
        cat_opts = cat_dim.get("options", []) if cat_dim else []
        
        # Medii: "Total" = primul element
        mediu_total = mediu_dim.get("options", [])[:1] if mediu_dim else []
        
        # Regiuni: "TOTAL" national = primul element (nomItemId=112 din log)
        reg_total = regiune_dim.get("options", [])[:1] if regiune_dim else []
        
        # UM: mp suprafata utila (al doilea element de obicei)
        um_mp = []
        if um_dim:
            for o in um_dim.get("options", []):
                txt = o.get("label", "").lower()
                if "mp" in txt or "suprafat" in txt or "metri" in txt:
                    um_mp = [o]
                    break
            if not um_mp:
                # Incercam ambele
                um_mp = um_dim.get("options", [])

        print(f"  Categorii selectate: {len(cat_opts)}")
        print(f"  Mediu: {mediu_total[0].get('label') if mediu_total else 'none'}")
        print(f"  Regiune: {reg_total[0].get('label') if reg_total else 'none'}")
        print(f"  UM: {[o.get('label') for o in um_mp]}")

        date_out = existing.get("date", {})
        cats_out = existing.get("categorii", [])
        adaugat_ceva = False

        for luna_opt in missing:
            luna_label = luna_opt.get("label", "")
            print(f"\n  === {luna_label} ===")

            # Incercam variante de UM
            um_variante = [um_mp, um_dim.get("options", [])[:1], um_dim.get("options", [])[1:2]] if um_dim else [[]]
            
            succes = False
            for um_sel in um_variante:
                if succes:
                    break
                    
                # Construim arr in ordinea exacta a dimensiunilor din metadata
                arr = []
                for dim in dims:
                    lbl = dim.get("label", "").lower()
                    opts = dim.get("options", [])
                    if "categor" in lbl:
                        sel = cat_opts
                    elif "perioad" in lbl or dim == timp_dim:
                        sel = [luna_opt]
                    elif "mediu" in lbl or "rezident" in lbl:
                        sel = mediu_total or opts[:1]
                    elif "macroreg" in lbl or "regiuni" in lbl:
                        sel = reg_total or opts[:1]
                    elif "um:" in lbl:
                        sel = um_sel or opts[:1]
                    else:
                        sel = opts[:1]
                    arr.append(sel)

                print(f"  → POST cu UM={um_sel[0].get('label') if um_sel else 'none'}...")
                resp, err = post_data(arr)
                
                if err:
                    print(f"  ✗ {err}")
                    continue
                    
                print(f"  ✓ Succes!")
                succes = True

                raw = resp
                if isinstance(resp, dict):
                    raw = resp.get("data", resp.get("matrixData", resp.get("dataset", resp)))

                print(f"  Raw: {type(raw).__name__}, len={len(raw) if hasattr(raw,'__len__') else '?'}")
                if raw and hasattr(raw, '__len__') and len(raw) > 0:
                    print(f"  Sample[0]: {str(raw[0])[:200]}")
                    if len(raw) > 1:
                        print(f"  Sample[1]: {str(raw[1])[:200]}")

                # Parsam
                if isinstance(raw, list) and raw:
                    first = raw[0]
                    if isinstance(first, list):
                        # raw[cat_idx] = [val] sau raw[cat_idx][0] = val
                        for ci, row in enumerate(raw):
                            cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                            if cat not in date_out: date_out[cat] = []
                            if cat not in cats_out: cats_out.append(cat)
                            val_raw = row[0] if isinstance(row, list) and row else row
                            val = None
                            if val_raw not in [None, "", "-", " ", ":", "..."]:
                                try: val = float(str(val_raw).replace(",",".").replace(" ",""))
                                except: pass
                            if luna_label not in [d["luna"] for d in date_out[cat]]:
                                date_out[cat].append({"luna": luna_label, "valoare": val})
                                adaugat_ceva = True
                                print(f"     + {cat}: {val}")
                    elif isinstance(first, (int, float, str, type(None))):
                        for ci, val_raw in enumerate(raw):
                            cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                            if cat not in date_out: date_out[cat] = []
                            if cat not in cats_out: cats_out.append(cat)
                            val = None
                            if val_raw not in [None, "", "-", " ", ":", "..."]:
                                try: val = float(str(val_raw).replace(",",".").replace(" ",""))
                                except: pass
                            if luna_label not in [d["luna"] for d in date_out[cat]]:
                                date_out[cat].append({"luna": luna_label, "valoare": val})
                                adaugat_ceva = True
                                print(f"     + {cat}: {val}")
                    elif isinstance(resp, dict) and "header" in resp:
                        # Format SDMX-like cu header
                        print(f"  Format cu header: {list(resp.keys())}")

            if not succes:
                print(f"  ❌ Esuat pentru {luna_label}")

        if not adaugat_ceva:
            print("\n⚠️  Nu s-a adaugat nicio valoare noua.")
            print("Modificat: false")
            return

        # Sortam si salvam
        for cat in date_out:
            date_out[cat].sort(key=lambda d: parse_luna_option(d.get("luna","")))

        toate = sorted(
            {d["luna"] for v in date_out.values() for d in v},
            key=parse_luna_option
        )

        result = {
            **existing,
            "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
            "categorii": cats_out,
            "perioade": toate,
            "date": date_out
        }
        save_json(result)
        print(f"\n✅ Salvat! Ultima luna: {toate[-1] if toate else '?'}")
        print("Modificat: true")

    except urllib.error.URLError as e:
        print(f"❌ Eroare retea: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
