#!/usr/bin/env python3
"""
Script: fetch_constructii.py - versiunea finala
Foloseste cheia "options" (confirmata din log), cere doar lunile dupa ultima din JSON.
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

def get_matrix_metadata():
    url = f"{BASE_URL}/matrix/{MATRIX_NAME}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def get_data(arr_payload):
    url = f"{BASE_URL}/matrix/dataSet/{MATRIX_NAME}"
    body = json.dumps({
        "language": "ro",
        "arr": arr_payload,
        "matrixName": MATRIX_NAME
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

def parse_luna_option(label):
    """
    Din 'Luna aprilie 2026' sau 'Luna 4 2026' extrage (2026, 4).
    Din 'Anul 2026' extrage (2026, 0).
    """
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            luna_part = parts[1]
            an = int(parts[2])
            if luna_part in LUNI_RO:
                return (an, LUNI_RO[luna_part])
            else:
                return (an, int(luna_part))
        elif parts[0] == "anul" or parts[0] == "an":
            return (int(parts[1]), 0)
    except (IndexError, ValueError):
        pass
    return (0, 0)

def parse_luna_json(label):
    """
    Din 'Luna 3 2026' (format JSON existent) extrage (2026, 3).
    """
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
    print(f"[{datetime.now().isoformat()}] Incep preluarea date LOC108A de la INSSE...")

    existing = load_existing()

    # Gasim ultima luna din JSON (indiferent de format)
    ultima_luna_key = (0, 0)
    for cat, vals in existing.get("date", {}).items():
        for d in vals:
            k = parse_luna_json(d.get("luna", ""))
            if k > ultima_luna_key:
                ultima_luna_key = k

    print(f"  → Ultima luna in JSON: an={ultima_luna_key[0]}, luna={ultima_luna_key[1]}")

    try:
        print("  → Preiau metadata LOC108A...")
        meta = get_matrix_metadata()
        dims = meta.get("dimensionsMap", [])
        if isinstance(dims, dict):
            dims = list(dims.values())
        print(f"  ✓ {len(dims)} dimensiuni")

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

        if not timp_dim:
            timp_dim = max(dims, key=lambda d: len(d.get("options", [])))

        # Gasim optiunile pentru perioade DUPA ultima luna din JSON
        timp_options = timp_dim.get("options", [])
        missing_options = []
        for opt in timp_options:
            label = opt.get("label", "")
            k = parse_luna_option(label)
            # Vrem: luna stricta dupa ultima din JSON, si doar luni (nu "Anul XXXX")
            if k[1] > 0 and k > ultima_luna_key:
                missing_options.append(opt)

        print(f"  → Luni noi de adaugat: {len(missing_options)}")
        for o in missing_options:
            print(f"     • {o.get('label')}")

        if not missing_options:
            print("✅ Datele sunt deja la zi. Modificat: false")
            return

        # UM: preferabil mp suprafata utila
        um_options = []
        if um_dim:
            for o in um_dim.get("options", []):
                if "mp" in o.get("label", "").lower() or "suprafat" in o.get("label", "").lower():
                    um_options = [o]
                    break
            if not um_options:
                um_options = um_dim.get("options", [])[:1]

        # Procesam cate o luna (sigur sub limita de 30k celule)
        cat_options = cat_dim.get("options", []) if cat_dim else []
        mediu_options = mediu_dim.get("options", [])[:1] if mediu_dim else []
        regiune_options = regiune_dim.get("options", [])[:1] if regiune_dim else []

        date_existente = existing.get("date", {})
        categorii_existente = existing.get("categorii", [])

        for luna_opt in missing_options:
            luna_label = luna_opt.get("label", "")
            print(f"  → Cerere pentru '{luna_label}'...")

            # Construim arr in ordinea exacta a dimensiunilor
            arr = []
            for dim in dims:
                label = dim.get("label", "").lower()
                if "categor" in label:
                    arr.append(cat_options)
                elif "perioad" in label or dim == timp_dim:
                    arr.append([luna_opt])
                elif "mediu" in label or "rezident" in label:
                    arr.append(mediu_options or dim.get("options", [])[:1])
                elif "macroreg" in label or "regiuni" in label:
                    arr.append(regiune_options or dim.get("options", [])[:1])
                elif "um:" in label:
                    arr.append(um_options or dim.get("options", [])[:1])
                else:
                    arr.append(dim.get("options", [])[:1])

            resp = get_data(arr)

            # Parsam raspunsul
            raw = resp
            if isinstance(resp, dict):
                raw = resp.get("data", resp.get("matrixData", resp.get("dataset", [])))

            print(f"     Raw tip: {type(raw).__name__}, len: {len(raw) if hasattr(raw,'__len__') else '?'}")
            if raw and len(raw) > 0:
                print(f"     Primul element: {str(raw[0])[:120]}")

            if isinstance(raw, list) and len(raw) > 0:
                first = raw[0]

                if isinstance(first, list):
                    # raw[cat_idx] = [valoare] (o singura luna)
                    for ci, row in enumerate(raw):
                        cat = cat_options[ci].get("label", f"Cat{ci}") if ci < len(cat_options) else f"Cat{ci}"
                        if cat not in date_existente:
                            date_existente[cat] = []
                        if cat not in categorii_existente:
                            categorii_existente.append(cat)
                        val_raw = row[0] if isinstance(row, list) and row else row
                        val = None
                        if val_raw not in [None, "", "-", " ", ":"]:
                            try:
                                val = float(str(val_raw).replace(",", ".").replace(" ", ""))
                            except ValueError:
                                pass
                        existing_luni = [d["luna"] for d in date_existente[cat]]
                        if luna_label not in existing_luni:
                            date_existente[cat].append({"luna": luna_label, "valoare": val})
                            print(f"     ✓ {cat}: {val}")

                elif isinstance(first, (int, float, str, type(None))):
                    # Lista plata: raw[cat_idx] = valoare
                    for ci, val_raw in enumerate(raw):
                        cat = cat_options[ci].get("label", f"Cat{ci}") if ci < len(cat_options) else f"Cat{ci}"
                        if cat not in date_existente:
                            date_existente[cat] = []
                        if cat not in categorii_existente:
                            categorii_existente.append(cat)
                        val = None
                        if val_raw not in [None, "", "-", " ", ":"]:
                            try:
                                val = float(str(val_raw).replace(",", ".").replace(" ", ""))
                            except ValueError:
                                pass
                        existing_luni = [d["luna"] for d in date_existente[cat]]
                        if luna_label not in existing_luni:
                            date_existente[cat].append({"luna": luna_label, "valoare": val})
                            print(f"     ✓ {cat}: {val}")

        # Sortam fiecare serie
        def sort_key(d):
            return parse_luna_option(d.get("luna", ""))

        for cat in date_existente:
            date_existente[cat].sort(key=sort_key)

        # Perioade actualizate
        toate_lunile = set()
        for vals in date_existente.values():
            for d in vals:
                toate_lunile.add(d["luna"])
        perioade_noi = sorted(toate_lunile, key=parse_luna_option)

        result = {
            **existing,
            "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
            "categorii": categorii_existente,
            "perioade": perioade_noi,
            "date": date_existente
        }

        save_json(result)
        print(f"✅ Salvat: {OUTPUT_PATH}")
        print(f"   Ultima luna acum: {perioade_noi[-1] if perioade_noi else '?'}")
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
