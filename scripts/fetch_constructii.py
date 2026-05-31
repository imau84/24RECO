#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Preia date LOC108A (Autorizatii construire - suprafata utila mp) de la INSSE TEMPO-Online
si actualizeaza src/data/constructii/constructii_data.json

Ruleaza automat prin GitHub Actions in prima zi a fiecarei luni.
"""

import json
import urllib.request
import urllib.error
import os
import sys
from datetime import datetime

OUTPUT_PATH = "src/data/constructii/constructii_data.json"

# Dimensiunile LOC108A:
# - Categorii de cladiri (Locuinte / Industriale / Comerciale / Birouri / Alte)
# - Luna (format: "Luna X YYYY")
# Vom cere toate categoriile, ultimii 3 ani

MATRIX_NAME = "LOC108A"
BASE_URL = "http://statistici.insse.ro:8077/tempo-ins"

CATEGORII_IDS = {
    "Locuinte": "LOC",
    "Cladiri industriale": "IND", 
    "Cladiri comerciale": "COM",
    "Birouri": "BIR",
    "Alte cladiri": "ALT",
    "TOTAL": "TOT"
}

def get_matrix_metadata():
    """Obtine metadata matricei LOC108A pentru a afla dimensiunile disponibile."""
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
    """Face POST catre INSSE pentru datele efective."""
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
    Construieste payload-ul pentru POST din metadata.
    LOC108A are 2 dimensiuni: Categorii + Perioade
    Luam toate categoriile si ultimele 36 luni.
    """
    dims = meta.get("dimensionsMap", {})
    arr = []
    
    for dim_key, dim_info in dims.items():
        elements = dim_info.get("nomItems", [])
        if not elements:
            continue
        
        dim_label = dim_info.get("label", "").lower()
        
        if "categor" in dim_label or "tip" in dim_label:
            # Toate categoriile
            arr.append([{
                "label": el.get("text", ""),
                "nomItemId": el.get("id"),
                "offset": 1,
                "parentId": None
            } for el in elements])
        elif "luna" in dim_label or "period" in dim_label or "timp" in dim_label:
            # Ultimele 36 luni disponibile
            sorted_els = sorted(elements, key=lambda x: x.get("id", 0), reverse=True)
            recent = sorted_els[:36]
            arr.append([{
                "label": el.get("text", ""),
                "nomItemId": el.get("id"),
                "offset": 1,
                "parentId": None
            } for el in recent])
        else:
            # Orice alta dimensiune: primul element (national)
            arr.append([{
                "label": elements[0].get("text", ""),
                "nomItemId": elements[0].get("id"),
                "offset": 1,
                "parentId": None
            }])
    
    return arr

def parse_response_to_json(raw_data, meta):
    """
    Transforma raspunsul brut INSSE intr-un JSON structurat:
    {
      "ultima_actualizare": "...",
      "unitate": "mp suprafata utila",
      "sursa": "INS Romania, LOC108A",
      "categorii": ["Locuinte", "Cladiri industriale", ...],
      "date": {
        "Locuinte": [{"luna": "Luna 1 2023", "valoare": 12345}, ...],
        ...
      }
    }
    """
    dims = meta.get("dimensionsMap", {})
    
    # Identificam ce dimensiune e categorie si ce e timp
    cat_dim = None
    timp_dim = None
    for dk, dv in dims.items():
        label = dv.get("label", "").lower()
        if "categor" in label or "tip" in label:
            cat_dim = dv
        elif "luna" in label or "period" in label:
            timp_dim = dv
    
    categorii = []
    if cat_dim:
        categorii = [el.get("text", "") for el in cat_dim.get("nomItems", [])]
    
    perioade = []
    if timp_dim:
        els = sorted(timp_dim.get("nomItems", []), key=lambda x: x.get("id", 0))
        perioade = [el.get("text", "") for el in els]
    
    # Construim structura de date
    # raw_data["data"] e de obicei o lista de liste sau dict
    date_out = {}
    
    # Incercam sa parsam formatul INSSE
    raw = raw_data.get("data", raw_data)
    
    if isinstance(raw, list):
        # Format: lista de randuri, fiecare rand = [cat_index, timp_index, valoare]
        for cat in categorii:
            date_out[cat] = []
        
        for row in raw:
            if len(row) >= 3:
                try:
                    cat_idx = int(row[0]) if isinstance(row[0], (int, str)) else 0
                    timp_idx = int(row[1]) if isinstance(row[1], (int, str)) else 0
                    val = float(str(row[-1]).replace(",", ".")) if row[-1] not in [None, "", "-"] else None
                    
                    cat_name = categorii[cat_idx] if cat_idx < len(categorii) else "Unknown"
                    luna = perioade[timp_idx] if timp_idx < len(perioade) else ""
                    
                    if cat_name not in date_out:
                        date_out[cat_name] = []
                    date_out[cat_name].append({"luna": luna, "valoare": val})
                except (ValueError, IndexError):
                    pass
    elif isinstance(raw, dict):
        # Alt format posibil
        for cat, values in raw.items():
            date_out[cat] = values
    
    # Sortam fiecare categorie dupa luna
    for cat in date_out:
        date_out[cat].sort(key=lambda x: x.get("luna", ""))
    
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
    old_update = existing.get("ultima_actualizare", "")
    
    try:
        print("  → Preiau metadata LOC108A...")
        meta = get_matrix_metadata()
        print("  ✓ Metadata primita")
        
        print("  → Construiesc payload cerere date...")
        payload = build_payload_from_metadata(meta)
        
        print("  → Cer datele efective (POST)...")
        raw_data = get_data(payload)
        print("  ✓ Date primite")
        
        print("  → Parsez si structurez datele...")
        result = parse_response_to_json(raw_data, meta)
        
        num_categorii = len(result.get("categorii", []))
        num_perioade = len(result.get("perioade", []))
        print(f"  ✓ {num_categorii} categorii, {num_perioade} perioade")
        
        # Verificam daca sunt date noi
        if result.get("perioade") == existing.get("perioade") and result.get("date") == existing.get("date"):
            print("⚠️  Nu sunt date noi fata de versiunea existenta.")
            print(f"Modificat: false")
            return
        
        save_json(result)
        print(f"✅ Salvat: {OUTPUT_PATH}")
        print(f"   Ultima actualizare: {old_update} → {result['ultima_actualizare']}")
        print(f"Modificat: true")
        
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
