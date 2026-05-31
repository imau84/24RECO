#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Preia date LOC108A (Autorizatii construire - suprafata utila mp) de la INSSE TEMPO-Online
si actualizeaza src/data/constructii/constructii_data.json
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
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def get_data(dim_ids_payload):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    payload = json.dumps({
        "language": "ro",
        "arr": dim_ids_payload,
        "matrixName": MATRIX_NAME
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"
        }
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def build_payload_from_metadata(meta):
    """
    dimensionsMap poate fi dict SAU lista — tratam ambele cazuri.
    Fiecare dimensiune are: label, nomItems (lista de {id, text, ...})
    Luam toate elementele din fiecare dimensiune.
    """
    dims_raw = meta.get("dimensionsMap", {})

    # Normalizam la lista de dict-uri
    if isinstance(dims_raw, dict):
        dims = list(dims_raw.values())
    elif isinstance(dims_raw, list):
        dims = dims_raw
    else:
        dims = []

    print(f"  → {len(dims)} dimensiuni gasite in metadata")
    for i, dim in enumerate(dims):
        label = dim.get("label", dim.get("dimensionLabel", "?"))
        items = dim.get("nomItems", dim.get("nomItem", []))
        print(f"     [{i}] '{label}' — {len(items)} elemente")

    arr = []
    for dim in dims:
        items = dim.get("nomItems", dim.get("nomItem", []))
        if not items:
            continue
        label = (dim.get("label", "") or dim.get("dimensionLabel", "")).lower()

        # Perioade: luam ultimele 48 luni (limita 30k celule)
        if any(kw in label for kw in ["luna", "period", "timp", "luni", "date"]):
            sorted_items = sorted(items, key=lambda x: x.get("id", 0), reverse=True)
            selected = sorted_items[:48]
        else:
            # Toate elementele din dimensiune
            selected = items

        arr.append([{
            "label": el.get("text", el.get("label", "")),
            "nomItemId": el.get("id", el.get("nomItemId")),
            "offset": 1,
            "parentId": None
        } for el in selected])

    return arr

def find_dim_by_keyword(dims, keywords):
    """Gaseste o dimensiune dupa cuvinte cheie in label."""
    for dim in dims:
        label = (dim.get("label", "") or dim.get("dimensionLabel", "")).lower()
        if any(kw in label for kw in keywords):
            return dim
    return None

def parse_response_to_json(raw_data, meta):
    dims_raw = meta.get("dimensionsMap", {})
    if isinstance(dims_raw, dict):
        dims = list(dims_raw.values())
    elif isinstance(dims_raw, list):
        dims = dims_raw
    else:
        dims = []

    # Identificam dimensiunile
    cat_dim = find_dim_by_keyword(dims, ["categor", "tip cladire", "tip de", "felul"])
    timp_dim = find_dim_by_keyword(dims, ["luna", "period", "timp", "luni", "date"])

    # Fallback: prima dim = categorii, a doua = timp (sau invers)
    if not cat_dim and not timp_dim:
        if len(dims) >= 2:
            cat_dim = dims[0]
            timp_dim = dims[1]
        elif len(dims) == 1:
            timp_dim = dims[0]

    categorii = []
    if cat_dim:
        items = cat_dim.get("nomItems", cat_dim.get("nomItem", []))
        categorii = [el.get("text", "") for el in items]

    perioade = []
    if timp_dim:
        items = timp_dim.get("nomItems", timp_dim.get("nomItem", []))
        sorted_items = sorted(items, key=lambda x: x.get("id", 0))
        perioade = [el.get("text", "") for el in sorted_items]

    print(f"  → Categorii: {categorii}")
    print(f"  → Perioade (primele 5): {perioade[:5]}")

    # Parsam datele brute
    # Formatul INSSE: {"data": [[val1, val2, ...], ...]} sau o matrice plata
    raw = raw_data
    if isinstance(raw_data, dict):
        raw = raw_data.get("data", raw_data.get("matrixData", raw_data))

    date_out = {cat: [] for cat in categorii}

    if isinstance(raw, list) and len(raw) > 0:
        first = raw[0]

        if isinstance(first, list):
            # Matrice 2D: raw[cat_idx][timp_idx] = valoare
            # Sau raw[i] = [cat_idx, timp_idx, valoare]
            if len(first) == 3 and isinstance(first[0], (int, float)):
                # Format triplet [cat_idx, timp_idx, val]
                for row in raw:
                    try:
                        ci = int(row[0])
                        ti = int(row[1])
                        val_raw = row[2]
                        val = float(str(val_raw).replace(",", ".")) if val_raw not in [None, "", "-", " "] else None
                        cat = categorii[ci] if ci < len(categorii) else f"Cat{ci}"
                        luna = perioade[ti] if ti < len(perioade) else f"P{ti}"
                        if cat not in date_out:
                            date_out[cat] = []
                        date_out[cat].append({"luna": luna, "valoare": val})
                    except (ValueError, IndexError, TypeError):
                        pass
            else:
                # Matrice 2D: raw[cat_idx] = [val_t0, val_t1, ...]
                for ci, row in enumerate(raw):
                    cat = categorii[ci] if ci < len(categorii) else f"Cat{ci}"
                    if cat not in date_out:
                        date_out[cat] = []
                    for ti, val_raw in enumerate(row):
                        val = float(str(val_raw).replace(",", ".")) if val_raw not in [None, "", "-", " "] else None
                        luna = perioade[ti] if ti < len(perioade) else f"P{ti}"
                        date_out[cat].append({"luna": luna, "valoare": val})
        elif isinstance(first, (int, float, str)):
            # Lista plata — o singura dimensiune (sau TOTAL)
            cat = categorii[0] if categorii else "TOTAL"
            if cat not in date_out:
                date_out[cat] = []
            for ti, val_raw in enumerate(raw):
                val = float(str(val_raw).replace(",", ".")) if val_raw not in [None, "", "-", " "] else None
                luna = perioade[ti] if ti < len(perioade) else f"P{ti}"
                date_out[cat].append({"luna": luna, "valoare": val})

    # Sortam dupa luna
    for cat in date_out:
        date_out[cat].sort(key=lambda x: x.get("luna", ""))

    # Verificare
    total_pts = sum(len(v) for v in date_out.values())
    print(f"  → Total puncte de date parsate: {total_pts}")

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
        # Debug: afisam structura top-level
        top_keys = list(meta.keys()) if isinstance(meta, dict) else type(meta).__name__
        print(f"  ✓ Metadata primita — chei: {top_keys}")

        print("  → Construiesc payload cerere date...")
        payload = build_payload_from_metadata(meta)
        print(f"  ✓ Payload: {len(payload)} dimensiuni")

        print("  → Cer datele efective (POST)...")
        raw_data = get_data(payload)
        raw_keys = list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data).__name__
        print(f"  ✓ Date primite — chei: {raw_keys}")

        print("  → Parsez si structurez datele...")
        result = parse_response_to_json(raw_data, meta)

        num_cat = len(result.get("categorii", []))
        num_per = len(result.get("perioade", []))
        print(f"  ✓ {num_cat} categorii, {num_per} perioade")

        if not result.get("date") or all(len(v) == 0 for v in result["date"].values()):
            print("⚠️  Nu s-au putut parsa date. Salvez structura de debug:")
            result["debug_meta_keys"] = list(meta.keys()) if isinstance(meta, dict) else str(type(meta))
            result["debug_raw_type"] = str(type(raw_data))
            result["debug_raw_sample"] = str(raw_data)[:500]

        if result.get("perioade") == existing.get("perioade") and result.get("date") == existing.get("date"):
            print("⚠️  Nu sunt date noi fata de versiunea existenta.")
            print("Modificat: false")
            return

        save_json(result)
        print(f"✅ Salvat: {OUTPUT_PATH}")
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
