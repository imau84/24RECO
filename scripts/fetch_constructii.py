#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Testeaza mai multe formate de payload pana gaseste unul acceptat de INSSE.
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

def post_data(body_dict):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    body = json.dumps(body_dict).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"

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
    except (IndexError, ValueError):
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

    # Ultima luna din JSON
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

        # UM: mp suprafata utila
        um_sel = []
        if um_dim:
            for o in um_dim.get("options", []):
                if "mp" in o.get("label","").lower() or "suprafat" in o.get("label","").lower():
                    um_sel = [o]; break
            if not um_sel:
                um_sel = um_dim.get("options", [])[:1]

        cat_opts = cat_dim.get("options", []) if cat_dim else []
        mediu_opts = mediu_dim.get("options", [])[:1] if mediu_dim else []
        reg_opts = regiune_dim.get("options", [])[:1] if regiune_dim else []

        date_out = existing.get("date", {})
        cats_out = existing.get("categorii", [])

        for luna_opt in missing:
            luna_label = luna_opt.get("label", "")
            print(f"\n  === Procesez: {luna_label} ===")

            # Construim arr in ordinea dimensiunilor
            arr_full = []
            for dim in dims:
                lbl = dim.get("label", "").lower()
                opts = dim.get("options", [])
                if "categor" in lbl:
                    arr_full.append(cat_opts)
                elif "perioad" in lbl or dim == timp_dim:
                    arr_full.append([luna_opt])
                elif "mediu" in lbl or "rezident" in lbl:
                    arr_full.append(mediu_opts or opts[:1])
                elif "macroreg" in lbl or "regiuni" in lbl:
                    arr_full.append(reg_opts or opts[:1])
                elif "um:" in lbl:
                    arr_full.append(um_sel or opts[:1])
                else:
                    arr_full.append(opts[:1])

            # --- Incercam 4 formate diferite de payload ---

            # Format 1: cu offset si parentId (format standard)
            def make_arr_fmt1(arr):
                result = []
                for dim_opts in arr:
                    result.append([{
                        "label": o.get("label",""),
                        "nomItemId": o.get("nomItemId", o.get("id")),
                        "offset": o.get("offset", 1),
                        "parentId": o.get("parentId", None)
                    } for o in dim_opts])
                return result

            # Format 2: doar nomItemId si label
            def make_arr_fmt2(arr):
                result = []
                for dim_opts in arr:
                    result.append([{
                        "label": o.get("label",""),
                        "nomItemId": o.get("nomItemId", o.get("id"))
                    } for o in dim_opts])
                return result

            # Format 3: pastram exact obiectele din options (as-is)
            def make_arr_fmt3(arr):
                return arr

            # Format 4: fara dimensiunea UM (unele matrice nu o cer)
            def make_arr_fmt4(arr):
                result = []
                for i, dim in enumerate(dims):
                    lbl = dim.get("label","").lower()
                    if "um:" in lbl:
                        continue
                    result.append([{
                        "label": o.get("label",""),
                        "nomItemId": o.get("nomItemId", o.get("id")),
                        "offset": o.get("offset", 1),
                        "parentId": o.get("parentId", None)
                    } for o in arr_full[i]])
                return result

            formats = [
                ("fmt1 (standard cu offset/parentId)", make_arr_fmt1(arr_full)),
                ("fmt2 (doar label+nomItemId)", make_arr_fmt2(arr_full)),
                ("fmt3 (options as-is)", make_arr_fmt3(arr_full)),
                ("fmt4 (fara UM)", make_arr_fmt4(arr_full)),
            ]

            resp_data = None
            for fmt_name, arr_payload in formats:
                print(f"  → Incerc {fmt_name}...")
                print(f"     Payload dim 0 sample: {str(arr_payload[0][0])[:120]}")
                body = {
                    "language": "ro",
                    "arr": arr_payload,
                    "matrixName": MATRIX_NAME
                }
                resp, err = post_data(body)
                if resp is not None:
                    print(f"  ✓ Succes cu {fmt_name}!")
                    resp_data = resp
                    break
                else:
                    print(f"  ✗ {err}")

            if resp_data is None:
                print(f"  ❌ Toate formatele au esuat pentru {luna_label}")
                continue

            # Parsam raspunsul
            raw = resp_data
            if isinstance(resp_data, dict):
                raw = resp_data.get("data", resp_data.get("matrixData", []))

            print(f"  Raw: {type(raw).__name__}, len={len(raw) if hasattr(raw,'__len__') else '?'}")
            if raw:
                print(f"  Sample: {str(raw[0])[:150]}")

            if isinstance(raw, list) and raw:
                first = raw[0]
                if isinstance(first, list):
                    for ci, row in enumerate(raw):
                        cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        val_raw = row[0] if row else None
                        val = None
                        if val_raw not in [None, "", "-", " ", ":"]:
                            try: val = float(str(val_raw).replace(",",".").replace(" ",""))
                            except: pass
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            print(f"     + {cat}: {val}")
                elif isinstance(first, (int, float, str, type(None))):
                    for ci, val_raw in enumerate(raw):
                        cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        val = None
                        if val_raw not in [None, "", "-", " ", ":"]:
                            try: val = float(str(val_raw).replace(",",".").replace(" ",""))
                            except: pass
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            print(f"     + {cat}: {val}")

        # Sortam si salvam
        for cat in date_out:
            date_out[cat].sort(key=lambda d: parse_luna_option(d.get("luna","")))

        toate = sorted({d["luna"] for v in date_out.values() for d in v},
                       key=parse_luna_option)

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
