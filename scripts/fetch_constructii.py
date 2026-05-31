#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Preia date LOC108A de la INSSE TEMPO-Online si adauga lunile lipsa in constructii_data.json
Chei corecte: dimensionsMap[i]["options"] pentru items, "dimCode" pentru id dimensiune
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

def get_data(arr_payload):
    """
    POST cu formatul exact asteptat de INSSE.
    arr = lista de liste, fiecare sublista = o dimensiune cu elementele selectate.
    """
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

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def luna_to_sort_key(luna_str):
    """Converteste 'Luna 4 2026' in (2026, 4) pentru sortare."""
    parts = luna_str.split()
    try:
        return (int(parts[2]), int(parts[1]))
    except (IndexError, ValueError):
        return (0, 0)

def main():
    print(f"[{datetime.now().isoformat()}] Incep preluarea date LOC108A de la INSSE...")

    existing = load_existing()
    existing_perioade = existing.get("perioade", [])
    print(f"  → Perioade existente in JSON: {len(existing_perioade)}, ultima: {existing_perioade[-1] if existing_perioade else 'niciuna'}")

    try:
        # 1. Metadata
        print("  → Preiau metadata LOC108A...")
        meta = get_matrix_metadata()
        dims = meta.get("dimensionsMap", [])
        if isinstance(dims, dict):
            dims = list(dims.values())
        print(f"  ✓ {len(dims)} dimensiuni gasite")

        # 2. Identificam dimensiunile dupa label
        cat_dim = None
        timp_dim = None
        mediu_dim = None
        regiune_dim = None
        um_dim = None

        for dim in dims:
            label = dim.get("label", "").lower()
            options = dim.get("options", [])
            print(f"     '{dim.get('label','')}' (dimCode={dim.get('dimCode')}) — {len(options)} optiuni")
            if "categor" in label:
                cat_dim = dim
            elif "perioad" in label or "luna" in label or "timp" in label:
                timp_dim = dim
            elif "mediu" in label or "rezident" in label:
                mediu_dim = dim
            elif "macroreg" in label or "regiuni" in label or "judet" in label:
                regiune_dim = dim
            elif "um:" in label or "unitate" in label:
                um_dim = dim

        if not timp_dim:
            # Fallback: dim cu cele mai multe optiuni e probabil perioade
            timp_dim = max(dims, key=lambda d: len(d.get("options", [])))

        # 3. Gasim lunile lipsa
        all_perioade_options = timp_dim.get("options", [])
        # Perioade disponibile la INSSE
        all_perioade_labels = [o.get("label", "") for o in all_perioade_options]

        # Perioade pe care NU le avem inca
        missing = [o for o in all_perioade_options
                   if o.get("label", "") not in existing_perioade]

        print(f"  → Perioade disponibile INSSE: {len(all_perioade_options)}")
        print(f"  → Perioade lipsa: {len(missing)} — {[o.get('label') for o in missing]}")

        if not missing:
            print("✅ Datele sunt deja la zi. Modificat: false")
            return

        # 4. Construim payload pentru lunile lipsa
        # Toate categoriile
        cat_options = cat_dim.get("options", []) if cat_dim else []

        # Mediu: Total (primul element)
        mediu_options = mediu_dim.get("options", [])[:1] if mediu_dim else []

        # Regiune: Total national (primul element)
        regiune_options = regiune_dim.get("options", [])[:1] if regiune_dim else []

        # UM: preferabil mp suprafata utila
        um_options = []
        if um_dim:
            for o in um_dim.get("options", []):
                if "mp" in o.get("label", "").lower() or "suprafat" in o.get("label", "").lower():
                    um_options = [o]
                    break
            if not um_options:
                um_options = um_dim.get("options", [])[:1]

        # Construim arr in ordinea dimensiunilor din metadata
        arr = []
        for dim in dims:
            label = dim.get("label", "").lower()
            if "categor" in label:
                arr.append(cat_options)
            elif "perioad" in label or "luna" in label or dim == timp_dim:
                arr.append(missing)
            elif "mediu" in label or "rezident" in label:
                arr.append(mediu_options if mediu_options else dim.get("options", [])[:1])
            elif "macroreg" in label or "regiuni" in label:
                arr.append(regiune_options if regiune_options else dim.get("options", [])[:1])
            elif "um:" in label or "unitate" in label:
                arr.append(um_options if um_options else dim.get("options", [])[:1])
            else:
                arr.append(dim.get("options", [])[:1])

        # Verificam ca nu depasim 30000 celule
        total_cells = 1
        for dim_arr in arr:
            total_cells *= max(len(dim_arr), 1)
        print(f"  → Celule estimate: {total_cells}")

        if total_cells > 29000:
            print("⚠️  Prea multe celule, reduc la 1 luna per request")
            # Procesam cate o luna
            all_results = []
            for luna_opt in missing:
                arr_single = []
                for dim in dims:
                    label = dim.get("label", "").lower()
                    if "categor" in label:
                        arr_single.append(cat_options)
                    elif "perioad" in label or dim == timp_dim:
                        arr_single.append([luna_opt])
                    elif "mediu" in label:
                        arr_single.append(mediu_options or dim.get("options", [])[:1])
                    elif "macroreg" in label:
                        arr_single.append(regiune_options or dim.get("options", [])[:1])
                    elif "um:" in label:
                        arr_single.append(um_options or dim.get("options", [])[:1])
                    else:
                        arr_single.append(dim.get("options", [])[:1])
                print(f"  → Cerere pentru {luna_opt.get('label')}...")
                resp = get_data(arr_single)
                all_results.append((luna_opt, resp))
        else:
            print("  → Cerere date pentru toate lunile lipsa...")
            resp = get_data(arr)
            all_results = [(None, resp)]

        # 5. Parsam raspunsul si actualizam JSON-ul existent
        date_existente = existing.get("date", {})
        categorii_existente = existing.get("categorii", [])

        for luna_opt, resp in all_results:
            raw = resp
            if isinstance(resp, dict):
                raw = resp.get("data", resp.get("matrixData", resp.get("dataset", resp)))

            print(f"  → Raspuns tip: {type(raw).__name__}, len: {len(raw) if hasattr(raw,'__len__') else '?'}")
            if raw and len(raw) > 0:
                print(f"     Primul element: {str(raw[0])[:150]}")

            # Parsam matricea: raw[cat_idx] = [val_luna0, val_luna1, ...]
            if isinstance(raw, list) and len(raw) > 0:
                first = raw[0]

                if isinstance(first, list):
                    # Matrice 2D
                    luna_labels = [luna_opt.get("label")] if luna_opt else [o.get("label") for o in missing]
                    for ci, row in enumerate(raw):
                        cat = cat_options[ci].get("label", f"Cat{ci}") if ci < len(cat_options) else f"Cat{ci}"
                        if cat not in date_existente:
                            date_existente[cat] = []
                            if cat not in categorii_existente:
                                categorii_existente.append(cat)
                        for ti, val_raw in enumerate(row):
                            luna = luna_labels[ti] if ti < len(luna_labels) else f"P{ti}"
                            val = None
                            if val_raw not in [None, "", "-", " ", ":"]:
                                try:
                                    val = float(str(val_raw).replace(",", ".").replace(" ", ""))
                                except ValueError:
                                    pass
                            # Adaugam doar daca luna nu exista deja
                            existing_luni = [d["luna"] for d in date_existente[cat]]
                            if luna not in existing_luni:
                                date_existente[cat].append({"luna": luna, "valoare": val})
                                print(f"     ✓ Adaugat: {cat} / {luna} = {val}")

                elif isinstance(first, (int, float, str, type(None))):
                    # Lista plata — o singura categorie sau o singura luna
                    cat = cat_options[0].get("label", "TOTAL") if cat_options else "TOTAL"
                    luna = luna_opt.get("label") if luna_opt else (missing[0].get("label") if missing else "?")
                    if cat not in date_existente:
                        date_existente[cat] = []
                    val = None
                    if first not in [None, "", "-"]:
                        try:
                            val = float(str(first).replace(",", "."))
                        except ValueError:
                            pass
                    existing_luni = [d["luna"] for d in date_existente[cat]]
                    if luna not in existing_luni:
                        date_existente[cat].append({"luna": luna, "valoare": val})

        # Sortam fiecare serie dupa luna
        for cat in date_existente:
            date_existente[cat].sort(key=lambda x: luna_to_sort_key(x.get("luna", "")))

        # Actualizam lista de perioade
        toate_lunile = set()
        for vals in date_existente.values():
            for d in vals:
                toate_lunile.add(d["luna"])
        perioade_noi = sorted(toate_lunile, key=luna_to_sort_key)

        result = {
            **existing,
            "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
            "categorii": categorii_existente,
            "perioade": perioade_noi,
            "date": date_existente
        }

        save_json(result)
        print(f"✅ Salvat: {OUTPUT_PATH}")
        print(f"   Perioade acum: {len(perioade_noi)}, ultima: {perioade_noi[-1] if perioade_noi else '?'}")
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
