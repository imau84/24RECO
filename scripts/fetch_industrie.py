#!/usr/bin/env python3
"""
fetch_industrie.py
==================
Actualizare automata a datelor pentru pagina "Industrie" (Exporturi).

Sursa : INS TEMPO-Online, matricea EXP101I
        "Exporturi (FOB) pe sectiuni conform Clasificarii Standard de Comert
         International (CSCI) Rev.4, pe Total, Intra-UE si Extra-UE - date lunare"

Strategie (cea mai simpla & robusta):
  1. GET metadata matrice          -> http://statistici.insse.ro:8077/tempo-ins/matrix/EXP101I
  2. Construieste encQuery cu TOATE optiunile (11 sectiuni x 3 dest x N luni x 1 UM)
     = ~5.300 celule, mult sub limita de 30.000 -> un singur request descarca tot.
  3. POST /tempo-ins/pivot         -> raspuns CSV
  4. Parseaza CSV (detectie coloane pe baza continutului, robust la reordonare)
  5. Reconstruieste blocul RAW, PASTREAZA blocul JD existent (judete - alta matrice)
  6. Scrie src/data/industrie/industrie_data.json doar daca s-a schimbat ceva

Ruleaza fara browser (doar HTTP) -> rapid si stabil in GitHub Actions.
Compatibil cu fluxul "fara mediu local": modificarile sunt comise direct de Actions.
"""

import csv
import io
import json
import os
import re
import sys
from datetime import datetime

import requests

# ─── Config ──────────────────────────────────────────────────────────────────
MATRIX     = "EXP101I"
BASE       = "http://statistici.insse.ro:8077/tempo-ins"
META_URL   = f"{BASE}/matrix/{MATRIX}"
PIVOT_URL  = f"{BASE}/pivot"

OUTPUT_PATH = "src/data/industrie/industrie_data.json"
# Fallback de migrare: prima rulare poate citi vechiul fisier din /public
LEGACY_PATH = "public/industrie_data.json"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "http://statistici.insse.ro:8077",
    "Referer": "http://statistici.insse.ro:8077/tempo-online/",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}

LUNI_RO = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}
UE_SET = {"total", "intra-ue", "extra-ue"}

DEBUG = "--debug" in sys.argv


# ─── Helpers ─────────────────────────────────────────────────────────────────
def log(*a):
    print(*a, flush=True)


def norm_sectiune(label: str) -> str:
    """Eticheta sectiunii: virgulele devin spatii (convenția folosita in JSON-ul existent).
    ex: 'Materiale crude, necomestibile, exclusiv combustibili'
        -> 'Materiale crude  necomestibile  exclusiv combustibili'"""
    return label.replace(",", " ").strip()


def parse_luna(label: str):
    """'Luna ianuarie 2013' -> (2013, 1).  'Anul 2013' -> (2013, 0). Altfel None."""
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna" and len(parts) >= 3:
            return (int(parts[2]), LUNI_RO.get(parts[1], 0))
        if parts[0] in ("anul", "an"):
            return (int(parts[1]), 0)
    except (ValueError, IndexError):
        pass
    return None


def to_number(s: str):
    s = (s or "").strip().strip('"').replace("\xa0", "").replace(" ", "")
    if s in ("", "-", ":", "...", "c", "*"):
        return None
    if "." in s and "," in s:          # 1.234.567,8 -> 1234567.8
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:                      # 1234,5 -> 1234.5
        s = s.replace(",", ".")
    try:
        f = float(s)
        return int(f) if f == int(f) else round(f, 1)
    except ValueError:
        return None


def load_existing() -> dict:
    for path in (OUTPUT_PATH, LEGACY_PATH):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                log(f"  Citesc structura existenta din {path}")
                return json.load(f)
    return {}


# ─── Pas 1: metadata ─────────────────────────────────────────────────────────
def fetch_metadata() -> dict:
    log(f"  GET {META_URL}")
    r = requests.get(META_URL, headers=HEADERS, timeout=60)
    r.raise_for_status()
    meta = r.json()
    dims = meta["dimensionsMap"]            # poate fi lista (handled as such)
    log(f"  Matrice: {meta.get('matrixName', MATRIX)} | {len(dims)} dimensiuni")
    for d in dims:
        log(f"    · {d.get('label','?').strip()} ({len(d.get('options',[]))} optiuni)")
    return meta


def build_enc_query(dims: list) -> str:
    """Toate optiunile, toate dimensiunile -> 'ids:ids:ids:ids'."""
    parts = []
    for d in dims:
        ids = [str(o["nomItemId"]) for o in d["options"]]
        parts.append(",".join(ids))
    return ":".join(parts)


# ─── Pas 2-3: download CSV ───────────────────────────────────────────────────
def fetch_pivot_csv(meta: dict) -> str:
    dims = meta["dimensionsMap"]
    det = meta["details"]
    payload = {
        "language": "ro",
        "encQuery": build_enc_query(dims),
        "matCode": MATRIX,
        "matMaxDim": det["matMaxDim"],
        "matUMSpec": det["matUMSpec"],
        "matRegJ": det.get("matRegJ", 0),
    }
    log(f"  POST {PIVOT_URL}  (encQuery {len(payload['encQuery'])} caractere)")
    r = requests.post(PIVOT_URL, json=payload, headers=HEADERS, timeout=120)
    r.raise_for_status()
    text = r.content.decode("utf-8", errors="ignore")
    low = text.lower()
    if "celule" in low and ("30000" in text or "pragul" in low):
        raise RuntimeError("INS a respins cererea: depasire prag 30.000 celule.")
    if DEBUG:
        log("  --- primele 600 caractere CSV ---")
        log(text[:600])
        log("  ----------------------------------")
    return text


# ─── Pas 4: parsare CSV (detectie coloane pe continut) ───────────────────────
def classify_columns(rows: list) -> dict:
    """rows = lista de liste (fara header daca a fost detectat). Returneaza indecsi."""
    ncols = max(len(r) for r in rows)
    cols = [[r[i].strip().strip('"') if i < len(r) else "" for r in rows]
            for i in range(ncols)]

    idx = {"sec": None, "ue": None, "luna": None, "um": None, "val": None}
    for i, c in enumerate(cols):
        vals = [v for v in c if v]
        if not vals:
            continue
        distinct = {v.lower() for v in vals}
        # luna
        if sum(1 for v in vals if parse_luna(v)) > 0.6 * len(vals):
            idx["luna"] = i; continue
        # destinatie UE (setul de valori e exact {total,intra-ue,extra-ue})
        if distinct and distinct <= UE_SET:
            idx["ue"] = i; continue
        # UM
        if all("euro" in v.lower() for v in vals):
            idx["um"] = i; continue
        # valoare numerica
        if sum(1 for v in vals if to_number(v) is not None) > 0.6 * len(vals):
            idx["val"] = i; continue
        # restul textual cu multe valori distincte = sectiune
        if len(distinct) >= 3:
            idx["sec"] = i

    # valoarea e ultima coloana daca n-am gasit-o
    if idx["val"] is None:
        idx["val"] = ncols - 1
    # sectiunea: prima coloana textuala ramasa
    if idx["sec"] is None:
        used = {v for v in idx.values() if v is not None}
        for i, c in enumerate(cols):
            if i in used:
                continue
            if any(c) and sum(1 for v in c if to_number(v) is not None) < 0.5 * len([v for v in c if v]):
                idx["sec"] = i; break
    return idx


def parse_csv(text: str, meta: dict) -> dict:
    """Returneaza RAW: {sectiune: {dest: {an: {luna: valoare}}}} in ordinea metadatelor."""
    # Detectam separatorul (TEMPO foloseste virgula; campurile cu virgula sunt cu ghilimele)
    sample = text[:4000]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    all_rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not all_rows:
        raise RuntimeError("CSV gol.")

    # Eliminam eventualul header (rand fara nicio 'Luna'/'Anul' si fara valori numerice)
    def is_data_row(r):
        return any(parse_luna(c.strip().strip('"')) for c in r)
    data_rows = [r for r in all_rows if is_data_row(r)]
    if not data_rows:
        raise RuntimeError("Nu am gasit randuri cu luni in CSV.")

    idx = classify_columns(data_rows)
    log(f"  Coloane detectate: {idx} (din {len(data_rows)} randuri)")
    if idx["sec"] is None or idx["ue"] is None or idx["luna"] is None:
        raise RuntimeError(f"Nu am putut identifica toate coloanele: {idx}")

    # Ordine canonica din metadata
    dims = meta["dimensionsMap"]
    sec_order = [norm_sectiune(o["label"]) for o in dims[0]["options"]]
    ue_order = [o["label"].strip() for o in dims[1]["options"]]

    raw = {s: {u: {} for u in ue_order} for s in sec_order}

    n_added = 0
    for r in data_rows:
        def cell(k):
            i = idx[k]
            return r[i].strip().strip('"') if i is not None and i < len(r) else ""
        sec = norm_sectiune(cell("sec"))
        ue = cell("ue").strip()
        ym = parse_luna(cell("luna"))
        val = to_number(cell("val"))
        if not ym or ym[1] == 0:        # ignoram totalurile anuale
            continue
        if sec not in raw or ue not in raw[sec]:
            # eticheta noua / neasteptata -> o adaugam totusi, sa nu pierdem date
            raw.setdefault(sec, {}).setdefault(ue, {})
        y, m = str(ym[0]), str(ym[1])
        raw[sec][ue].setdefault(y, {})[m] = val
        n_added += 1

    log(f"  Celule parsate: {n_added}")
    return raw


# ─── Pas 5-6: merge + scriere ────────────────────────────────────────────────
def latest_month(raw: dict):
    best = (0, 0)
    for ue in raw.get("Total", {}).values():
        for y, months in ue.items():
            for m, v in months.items():
                if v is not None:
                    best = max(best, (int(y), int(m)))
    return best


def main():
    log(f"[{datetime.now().isoformat()}] Start fetch_industrie ({MATRIX})")
    existing = load_existing()
    old_raw = existing.get("RAW", {})

    meta = fetch_metadata()
    csv_text = fetch_pivot_csv(meta)
    raw = parse_csv(csv_text, meta)

    # Validari de siguranta: nu suprascriem cu date corupte
    n_sec = len([s for s in raw if any(raw[s].get(u) for u in raw[s])])
    if n_sec < 5 or "Total" not in raw or not raw["Total"].get("Total"):
        raise RuntimeError(f"Date suspecte (doar {n_sec} sectiuni cu valori). Anulez scrierea.")

    ly_new = latest_month(raw)
    ly_old = latest_month(old_raw) if old_raw else (0, 0)
    log(f"  Ultima luna noua: {ly_new}  |  veche: {ly_old}")

    out = {
        **existing,                      # pastram orice alte chei (ex. JD - judete)
        "RAW": raw,
        "matrice": MATRIX,
        "sursa": "INS Romania, EXP101I (Exporturi FOB pe sectiuni CSCI Rev.4)",
        "unitate": "mii EUR",
        "ultima_luna": f"{ly_new[0]}-{ly_new[1]:02d}" if ly_new[0] else None,
        "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    new_str = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    old_str = ""
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            old_str = json.dumps(json.load(f), ensure_ascii=False, indent=2, sort_keys=True)

    if new_str == old_str:
        log("ℹ️  Nicio modificare (datele sunt la zi).")
        log("Modificat: false")
        return

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f"✅ Salvat {OUTPUT_PATH} — ultima luna {out['ultima_luna']}")
    log("Modificat: true")


if __name__ == "__main__":
    main()
