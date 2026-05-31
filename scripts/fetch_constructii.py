#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Preia date LOC108A de la INSSE TEMPO-Online
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

def get_matrix_metadata():
    url = f"{BASE_URL}/matrix/{MATRIX_NAME}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def get_data(dim_ids_payload):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    payload = json.dumps({
        "language": "ro",
        "arr": dim_ids_payload,
        "matrixName": MATRIX_NAME
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def extract_items(dim):
    """
    Incearca toate cheile posibile pentru lista de elemente dintr-o dimensiune INSSE.
    """
    # Chei posibile in API-ul INSSE (variate in functie de versiune)
    for key in ["nomItems", "nomItem", "nomenclator", "items", "elements",
                "values", "nomenclatureItems", "dimensionItems", "membres"]:
        val = dim.get(key)
        if val and isinstance(val, list) and len(val) > 0:
            return val

    # Poate items sunt direct in dim ca lista
    if isinstance(dim, list):
        return dim

    # Ultimul resort: cauta prima cheie care are o lista cu dicts cu "id"
    for key, val in dim.items():
        if isinstance(val, list) and len(val) > 0:
            if isinstance(val[0], dict) and ("id" in val[0] or "nomItemId" in val[0]):
                return val

    return []

def build_payload_from_metadata(meta):
    dims_raw = meta.get("dimensionsMap", [])
    if isinstance(dims_raw, dict):
        dims = list(dims_raw.values())
    elif isinstance(dims_raw, list):
        dims = dims_raw
    else:
        dims = []

    print(f"  → {len(dims)} dimensiuni in metadata")

    # Debug: print toate cheile din prima dimensiune
    if dims:
        first = dims[0]
        if isinstance(first, dict):
            print(f"  → Chei disponibile in dim[0]: {list(first.keys())}")
            # Afisam primele 200 chars din fiecare cheie
            for k, v in first.items():
                preview = str(v)[:100]
                print(f"     '{k}': {preview}")

    arr = []
    for i, dim in enumerate(dims):
        label = (dim.get("label", "") or dim.get("dimensionLabel", "") or
                 dim.get("dimLabel", "") or dim.get("name", "") or f"dim{i}").lower()
        items = extract_items(dim)

        print(f"  → [{i}] '{label}' — {len(items)} elemente", end="")
        if items:
            # Afisam primul element pentru debug
            print(f" | ex: {str(items[0])[:80]}")
        else:
            print()

        if not items:
            continue

        # Perioade: luam ultimele 48
        is_timp = any(kw in label for kw in ["luna", "period", "timp", "luni", "date", "perioad"])
        # UM: sarim (unitate de masura - de obicei 1 element)
        is_um = any(kw in label for kw in ["um:", "unitate", "masura"])

        if is_um and len(items) <= 3:
            # Luam primul element (mp suprafata utila, nu numar)
            mp_item = None
            for el in items:
                txt = (el.get("text", "") or el.get("label", "") or "").lower()
                if "mp" in txt or "suprafat" in txt or "metri" in txt:
                    mp_item = el
                    break
            selected = [mp_item] if mp_item else [items[0]]
        elif is_timp:
            sorted_items = sorted(items, key=lambda x: x.get("id", x.get("nomItemId", 0)), reverse=True)
            selected = sorted_items[:48]
        else:
            selected = items

        # Construim payload — id-ul poate fi "id" sau "nomItemId"
        dim_payload = []
        for el in selected:
            item_id = el.get("id", el.get("nomItemId", el.get("itemId")))
            item_label = el.get("text", el.get("label", el.get("name", "")))
            dim_payload.append({
                "label": item_label,
                "nomItemId": item_id,
                "offset": 1,
                "parentId": None
            })

        if dim_payload:
            arr.append(dim_payload)

    print(f"  ✓ Payload construit: {len(arr)} dimensiuni")
    return arr

def find_dim_by_keyword(dims, keywords):
    for dim in dims:
        label = (dim.get("label", "") or dim.get("dimensionLabel", "") or
                 dim.get("dimLabel", "") or dim.get("name", "") or "").lower()
        if any(kw in label for kw in keywords):
            return dim
    return None

def parse_response_to_json(raw_data, meta):
    dims_raw = meta.get("dimensionsMap", [])
    if isinstance(dims_raw, dict):
        dims = list(dims_raw.values())
    elif isinstance(dims_raw, list):
        dims = dims_raw
    else:
        dims = []

    cat_dim = find_dim_by_keyword(dims, ["categor", "tip cladire", "tip de"])
    timp_dim = find_dim_by_keyword(dims, ["luna", "period", "perioad", "timp"])

    if not cat_dim and not timp_dim and len(dims) >= 2:
        cat_dim = dims[0]
        timp_dim = dims[3] if len(dims) > 3 else dims[-1]

    def get_labels(dim):
        if not dim:
            return []
        items = extract_items(dim)
        return [el.get("text", el.get("label", el.get("name", ""))) for el in items]

    categorii = get_labels(cat_dim)
    if timp_dim:
        timp_items = extract_items(timp_dim)
        timp_sorted = sorted(timp_items, key=lambda x: x.get("id", x.get("nomItemId", 0)))
        perioade = [el.get("text", el.get("label", "")) for el in timp_sorted]
    else:
        perioade = []

    print(f"  → Categorii ({len(categorii)}): {categorii[:4]}")
    print(f"  → Perioade ({len(perioade)}): {perioade[:3]}...{perioade[-2:] if len(perioade)>2 else ''}")

    # Debug raw data
    raw = raw_data
    if isinstance(raw_data, dict):
        print(f"  → Raw data chei: {list(raw_data.keys())}")
        raw = raw_data.get("data", raw_data.get("matrixData", raw_data.get("dataset", [])))

    print(f"  → Raw data tip: {type(raw).__name__}, lungime: {len(raw) if hasattr(raw, '__len__') else '?'}")
    if raw and len(raw) > 0:
        print(f"  → Primul element: {str(raw[0])[:200]}")

    date_out = {cat: [] for cat in categorii} if categorii else {}

    if isinstance(raw, list) and len(raw) > 0:
        first = raw[0]

        if isinstance(first, list):
            if len(first) >= 2 and not isinstance(first[0], list):
                # Matrice 2D: raw[cat_idx][timp_idx] = valoare
                for ci, row in enumerate(raw):
                    cat = categorii[ci] if ci < len(categorii) else f"Cat{ci}"
                    if cat not in date_out:
                        date_out[cat] = []
                    for ti, val_raw in enumerate(row if isinstance(row, list) else [row]):
                        val = None
                        if val_raw not in [None, "", "-", " ", ":"]:
                            try:
                                val = float(str(val_raw).replace(",", ".").replace(" ", ""))
                            except ValueError:
                                pass
                        luna = perioade[ti] if ti < len(perioade) else f"P{ti}"
                        date_out[cat].append({"luna": luna, "valoare": val})
        elif isinstance(first, dict):
            # Format dict cu chei
            print(f"  → Dict format, chei: {list(first.keys())[:6]}")
        elif isinstance(first, (int, float, str)):
            # Lista plata
            cat = categorii[0] if categorii else "TOTAL"
            if cat not in date_out:
                date_out[cat] = []
            for ti, val_raw in enumerate(raw):
                val = None
                if val_raw not in [None, "", "-", " ", ":"]:
                    try:
                        val = float(str(val_raw).replace(",", ".").replace(" ", ""))
                    except ValueError:
                        pass
                luna = perioade[ti] if ti < len(perioade) else f"P{ti}"
                date_out[cat].append({"luna": luna, "valoare": val})

    for cat in date_out:
        date_out[cat].sort(key=lambda x: x.get("luna", ""))

    total_pts = sum(len(v) for v in date_out.values())
    print(f"  → Total puncte parsate: {total_pts}")

    return {
        "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
        "unitate": "mp suprafata utila",
        "sursa": "INS Romania, LOC108A",
        "matrice": MATRIX_NAME,
        "categorii": categorii,
        "perioade": perioade,
        "date": date_out
    }

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
    print(f"[{datetime.now().isoformat()}] Incep preluarea date LOC108A de la INSSE...")
    existing = load_existing()
    old_update = existing.get("ultima_actualizare", "necunoscut")

    try:
        print("  → Preiau metadata LOC108A...")
        meta = get_matrix_metadata()
        top_keys = list(meta.keys()) if isinstance(meta, dict) else str(type(meta))
        print(f"  ✓ Metadata primita — chei: {top_keys}")

        print("  → Construiesc payload cerere date...")
        payload = build_payload_from_metadata(meta)

        if not payload:
            print("❌ Payload gol — nu s-au putut extrage dimensiuni din metadata")
            print("   Salvez metadata pentru debug...")
            debug = {
                "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
                "debug": True,
                "meta_keys": list(meta.keys()) if isinstance(meta, dict) else str(type(meta)),
                "meta_sample": json.dumps(meta, ensure_ascii=False)[:2000]
            }
            save_json(debug)
            sys.exit(1)

        print("  → Cer datele efective (POST)...")
        raw_data = get_data(payload)
        raw_keys = list(raw_data.keys()) if isinstance(raw_data, dict) else str(type(raw_data))
        print(f"  ✓ Date primite — chei: {raw_keys}")

        print("  → Parsez si structurez datele...")
        result = parse_response_to_json(raw_data, meta)

        total_pts = sum(len(v) for v in result.get("date", {}).values())
        if total_pts == 0:
            print("⚠️  0 puncte parsate — salvez cu date de debug")
            result["debug_raw"] = json.dumps(raw_data, ensure_ascii=False)[:1000]

        if result.get("perioade") == existing.get("perioade") and result.get("date") == existing.get("date"):
            print("⚠️  Nu sunt date noi. Modificat: false")
            return

        save_json(result)
        print(f"✅ Salvat: {OUTPUT_PATH} ({total_pts} puncte)")
        print(f"   Ultima actualizare: {old_update} → {result['ultima_actualizare']}")
        print("Modificat: true")

    except urllib.error.URLError as e:
        print(f"❌ Eroare retea INSSE: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"❌ Eroare neasteptata: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
