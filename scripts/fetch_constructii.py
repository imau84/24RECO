#!/usr/bin/env python3
"""
Script: fetch_constructii.py - versiunea FINALA cu payload corect din browser.

Payload real (vazut in DevTools):
{
  "language": "ro",
  "arr": [[{"label":"Cladiri rezidentiale...","nomitemid":17745,"offset":1,"parentId":null}, ...],
          [{"label":"Total","nomitemid":100,"offset":1,"parentId":null}],
          [{"label":"TOTAL","nomitemid":112,"offset":1,"parentId":null}, ...judete...],
          [{"label":"Luna aprilie 2026","nomitemid":4941,"offset":316,"parentId":null}],
          [{"label":"Metri patrati suprafata utila","nomitemid":17749,"offset":2,"parentId":null}]],
  "matrixName": "Autorizatii de construire eliberate...",  <- numele lung!
  "matrixDetails": {"nomJud":0,"nomLoc":0,"matMaxDim":5,"matUMSpec":0,"matSiruta":0,"matCaen1":0,"matCaen2":0,"matRegJ":2,...}
}

Diferente fata de ce trimiteam:
1. "nomitemid" (lowercase 'i') nu "nomItemId"
2. matrixName = numele complet al matricei, NU codul "LOC108A"
3. matrixDetails e obligatoriu
4. offset = pozitia elementului in lista (1-based), nu mereu 1
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def post_data(payload):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://statistici.insse.ro:8077/tempo-online/",
        "Origin": "http://statistici.insse.ro:8077"
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), None
    except urllib.error.HTTPError as e:
        try: err = e.read().decode("utf-8")[:300]
        except: err = str(e)
        return None, f"HTTP {e.code}: {err}"

def parse_luna_option(label):
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            an = int(parts[2])
            lp = parts[1]
            return (an, LUNI_RO.get(lp, int(lp) if lp.isdigit() else 0))
        elif parts[0] in ("anul", "an"):
            return (int(parts[1]), 0)
    except: pass
    return (0, 0)

def parse_luna_json(label):
    parts = label.strip().split()
    try: return (int(parts[2]), int(parts[1]))
    except: return (0, 0)

def to_float(v):
    if v in [None, "", "-", " ", ":", "..."]: return None
    try: return float(str(v).replace(",",".").replace(" ",""))
    except: return None

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def make_item(opt):
    """Construieste un item pentru arr folosind 'nomitemid' (lowercase) si offset din options."""
    return {
        "label": opt.get("label", ""),
        "nomitemid": opt.get("nomItemId", opt.get("nomitemid", opt.get("id"))),
        "offset": opt.get("offset", 1),
        "parentId": opt.get("parentId", None)
    }

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

        # Numele complet al matricei (obligatoriu in payload)
        matrix_name_full = meta.get("matrixName", MATRIX_NAME)
        print(f"  matrixName complet: {matrix_name_full[:60]}...")

        # matrixDetails din metadata
        matrix_details = meta.get("matrixDetails", {
            "nomJud": 0, "nomLoc": 0, "matMaxDim": 5,
            "matUMSpec": 0, "matSiruta": 0, "matCaen1": 0,
            "matCaen2": 0, "matRegJ": 2, "matCharge": 0,
            "matViews": 0, "matDownloads": 0, "matActive": 1, "matTime": 4
        })

        # Identificam dimensiunile
        cat_dim = timp_dim = mediu_dim = regiune_dim = um_dim = None
        for dim in dims:
            lbl = dim.get("label", "").lower()
            if "categor" in lbl: cat_dim = dim
            elif "perioad" in lbl: timp_dim = dim
            elif "mediu" in lbl or "rezident" in lbl: mediu_dim = dim
            elif "macroreg" in lbl or "regiuni" in lbl: regiune_dim = dim
            elif "um:" in lbl: um_dim = dim

        # Luni noi de adaugat
        missing = [
            o for o in timp_dim.get("options", [])
            if parse_luna_option(o.get("label",""))[1] > 0
            and parse_luna_option(o.get("label","")) > ultima_key
        ]
        print(f"  Luni noi: {[o['label'] for o in missing]}")
        if not missing:
            print("Datele sunt la zi. Modificat: false")
            return

        # Selectii fixe
        cat_opts = cat_dim.get("options", []) if cat_dim else []
        mediu_total = mediu_dim.get("options", [])[:1] if mediu_dim else []
        reg_total = regiune_dim.get("options", [])[:1] if regiune_dim else []

        # UM: "Metri patrati suprafata utila" - al doilea element (offset=2)
        um_mp = []
        if um_dim:
            all_um = um_dim.get("options", [])
            print(f"  UM optiuni: {[(o.get('label'), o.get('offset')) for o in all_um]}")
            for o in all_um:
                lbl = o.get("label","").lower()
                if "metri" in lbl or "patrati" in lbl or "suprafat" in lbl:
                    um_mp = [o]
                    break
            if not um_mp and len(all_um) >= 2:
                um_mp = [all_um[1]]

        print(f"  UM selectat: {um_mp[0].get('label') if um_mp else 'none'}")

        date_out = existing.get("date", {})
        cats_out = existing.get("categorii", [])
        adaugat = False

        for luna_opt in missing:
            luna_label = luna_opt.get("label","")
            print(f"\n  === {luna_label} ===")

            # Construim arr in ordinea exacta a dimensiunilor
            arr = []
            for dim in dims:
                lbl = dim.get("label","").lower()
                opts = dim.get("options", [])
                if "categor" in lbl:
                    arr.append([make_item(o) for o in cat_opts])
                elif "perioad" in lbl:
                    arr.append([make_item(luna_opt)])
                elif "mediu" in lbl or "rezident" in lbl:
                    sel = mediu_total or opts[:1]
                    arr.append([make_item(o) for o in sel])
                elif "macroreg" in lbl or "regiuni" in lbl:
                    sel = reg_total or opts[:1]
                    arr.append([make_item(o) for o in sel])
                elif "um:" in lbl:
                    sel = um_mp or opts[:1]
                    arr.append([make_item(o) for o in sel])
                else:
                    arr.append([make_item(o) for o in opts[:1]])

            payload = {
                "language": "ro",
                "arr": arr,
                "matrixName": matrix_name_full,
                "matrixDetails": matrix_details
            }

            print(f"  → POST cu {len(arr)} dimensiuni...")
            resp, err = post_data(payload)

            if err:
                print(f"  ✗ {err[:150]}")
                continue

            print(f"  ✓ Succes!")
            raw = resp
            if isinstance(resp, dict):
                raw = resp.get("data", resp.get("matrixData", resp.get("dataset", [])))

            print(f"  Raw: {type(raw).__name__}, len={len(raw) if hasattr(raw,'__len__') else '?'}")
            if raw and hasattr(raw,'__len__') and len(raw) > 0:
                print(f"  Sample[0]: {str(raw[0])[:150]}")

            if isinstance(raw, list) and raw:
                first = raw[0]
                if isinstance(first, list):
                    for ci, row in enumerate(raw):
                        cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        val_raw = row[0] if isinstance(row, list) and row else row
                        val = to_float(val_raw)
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            adaugat = True
                            print(f"     + {cat}: {val}")
                elif isinstance(first, (int, float, str, type(None))):
                    for ci, val_raw in enumerate(raw):
                        cat = cat_opts[ci].get("label", f"Cat{ci}") if ci < len(cat_opts) else f"Cat{ci}"
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        val = to_float(val_raw)
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            adaugat = True
                            print(f"     + {cat}: {val}")

        if not adaugat:
            print("\n⚠️  Nu s-a adaugat nimic. Modificat: false")
            return

        for cat in date_out:
            date_out[cat].sort(key=lambda d: parse_luna_option(d.get("luna","")))

        toate = sorted(
            {d["luna"] for v in date_out.values() for d in v},
            key=parse_luna_option
        )

        save_json({**existing,
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

if __name__ == "__main__":
    main()
