#!/usr/bin/env python3
"""
fetch_salariati_industrie.py
============================
Actualizare automata a datelor pentru tab-ul "Salariati" din pagina "Industrie".

Sursa : INS TEMPO-Online, matricea FOM105I
        "Efectivul salariatilor la sfarsitul lunii pe activitati (sectiuni si diviziuni)
         ale economiei nationale CAEN Rev.3" (mii persoane, lunar, din ianuarie 2025)

Pastram:
  - 05-39 INDUSTRIE TOTAL, sectiunile B, C, D, E si toate diviziunile 05-39
  - TOTAL ECONOMIE (doar ca reper: cat din salariatii tarii lucreaza in industrie)

Un singur POST /tempo-ins/pivot (~40 activitati x N luni, mult sub pragul de 30.000 celule).
Scrie src/data/industrie/salariati_data.json doar daca s-a schimbat ceva.
"""

import json
import os
import re
from datetime import datetime

import requests

MATRIX = "FOM105I"
BASE = "http://statistici.insse.ro:8077/tempo-ins"
OUTPUT_PATH = "src/data/industrie/salariati_data.json"

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

# Sectiunile industriei (CAEN Rev.3) si diviziunile lor (05-39)
SECTIUNI_INDUSTRIE = {"B", "C", "D", "E"}


def log(*a):
    print(*a, flush=True)


def parse_luna(label: str):
    """'Luna ianuarie 2025' -> (2025, 1). Altfel None."""
    p = label.strip().lower().split()
    if len(p) >= 3 and p[0] == "luna" and p[1] in LUNI_RO:
        try:
            return int(p[2]), LUNI_RO[p[1]]
        except ValueError:
            return None
    return None


def to_number(s: str):
    s = (s or "").strip().strip('"').replace(" ", "")
    if s in ("", "-", ":", "...", "c", "*"):
        return None
    try:
        return round(float(s.replace(",", ".")), 1)
    except ValueError:
        return None


def split_cod(label: str):
    """'05-39 INDUSTRIE TOTAL' -> ('05-39', 'INDUSTRIE TOTAL');  'C INDUSTRIA ...' -> ('C', ...)"""
    label = label.strip()
    if label.upper() == "TOTAL ECONOMIE":
        return "TOTAL", "TOTAL ECONOMIE"
    m = re.match(r"^(\d{2}-\d{2}|\d{2}|[A-Z])\s+(.*)$", label)
    return (m.group(1), m.group(2).strip()) if m else (None, label)


def este_industrie(cod: str) -> bool:
    if cod in ("TOTAL", "05-39") or cod in SECTIUNI_INDUSTRIE:
        return True
    return cod.isdigit() and 5 <= int(cod) <= 39


def latest_month(luni: dict):
    best = (0, 0)
    for a, m in luni.items():
        for l, v in m.items():
            if v is not None:
                best = max(best, (int(a), int(l)))
    return best


def main():
    log(f"[{datetime.now().isoformat()}] Start fetch_salariati_industrie ({MATRIX})")
    log(f"  GET {BASE}/matrix/{MATRIX}")
    meta = requests.get(f"{BASE}/matrix/{MATRIX}", headers=HEADERS, timeout=60).json()
    dims, det = meta["dimensionsMap"], meta["details"]
    caen_opts, luni_opts, um_opts = dims[0]["options"], dims[1]["options"], dims[2]["options"]

    activ = []   # (nomItemId, cod, nume) in ordinea INS
    for o in caen_opts:
        cod, nume = split_cod(o["label"])
        if cod and este_industrie(cod):
            activ.append((o["nomItemId"], cod, nume))
    log(f"  Activitati selectate: {len(activ)} | luni disponibile: {len(luni_opts)}")
    if not any(c == "05-39" for _, c, _ in activ):
        raise RuntimeError("Nu gasesc '05-39 INDUSTRIE TOTAL' in metadata — s-a schimbat matricea?")

    enc = ":".join([
        ",".join(str(i) for i, _, _ in activ),
        ",".join(str(o["nomItemId"]) for o in luni_opts),
        str(um_opts[0]["nomItemId"]),
    ])
    body = {"language": "ro", "arr": [], "matrixName": meta["matrixName"], "matrixDetails": det,
            "encQuery": enc, "matCode": MATRIX, "matMaxDim": det["matMaxDim"],
            "matUMSpec": det["matUMSpec"], "matRegJ": det.get("matRegJ", 0)}
    r = requests.post(f"{BASE}/pivot", json=body, headers=HEADERS, timeout=120)
    r.raise_for_status()

    serii = {cod: {"nume": nume, "luni": {}} for _, cod, nume in activ}
    eticheta_cod = {}
    n = 0
    for line in r.content.decode("utf-8", errors="ignore").splitlines()[1:]:
        # „Activitate (poate contine virgule), Luna …, UM, Valoare” -> parsam de la dreapta
        p = [x.strip() for x in line.split(", ")]
        if len(p) < 4:
            continue
        luna, val = parse_luna(p[-3]), to_number(p[-1])
        if not luna:
            continue
        cod, _ = split_cod(", ".join(p[:-3]))
        if cod not in serii:
            continue
        serii[cod]["luni"].setdefault(str(luna[0]), {})[str(luna[1])] = val
        n += 1
    log(f"  Celule parsate: {n}")

    tot = serii["05-39"]["luni"]
    if n < 10 * len(activ) or not tot:
        raise RuntimeError(f"Date suspecte ({n} celule). Anulez scrierea.")

    u = latest_month(tot)
    out = {
        "matrice": MATRIX,
        "sursa": "INS Romania, FOM105I (Efectivul salariatilor la sfarsitul lunii, CAEN Rev.3)",
        "unitate": "mii persoane",
        "ordine": [cod for _, cod, _ in activ],
        "serii": serii,
        "ultima_luna": f"{u[0]}-{u[1]:02d}",
    }

    old = {}
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            old = json.load(f)
    if {k: v for k, v in old.items() if k != "ultima_actualizare"} == out:
        log("ℹ️  Nicio modificare (datele sunt la zi).")
        return

    out["ultima_actualizare"] = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f"✅ Salvat {OUTPUT_PATH} — ultima luna {out['ultima_luna']}")


if __name__ == "__main__":
    main()
