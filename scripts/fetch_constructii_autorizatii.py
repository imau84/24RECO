# -*- coding: utf-8 -*-
"""Construcții — Set 01: Autorizații de construire pentru clădiri (România + UE27).

Re-descarcă seria completă (din ianuarie 2019 până la ultima lună publicată) din API-ul
Eurostat (dataset sts_cobp_m, date raportate de INS) și rescrie
`src/data/constructii/autorizatii_data.json`.

Rulare:   python scripts/fetch_constructii_autorizatii.py
Programare: lunar (Eurostat publică STS în jurul zilei 15–20) — vezi
.github/workflows/update-constructii-autorizatii.yml
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATASET = "sts_cobp_m"
API = f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{DATASET}"
OUTPUT = Path(__file__).resolve().parent.parent / "src" / "data" / "constructii" / "autorizatii_data.json"

BAZA = {"format": "JSON", "lang": "EN", "freq": "M", "indic_bt": "BPRM_SQM",
        "s_adj": "NSA", "unit": "I21", "sinceTimePeriod": "2019-01"}

# (cheie în JSON, filtre specifice)
SERII = [
    ("total", {"geo": "RO", "cpa2_1": "CPA_F41001_41002"}),
    ("rezidentiale", {"geo": "RO", "cpa2_1": "CPA_F41001"}),
    ("nerezidentiale", {"geo": "RO", "cpa2_1": "CPA_F41002"}),
    ("ue27", {"geo": "EU27_2020", "cpa2_1": "CPA_F41001_41002"}),
]


def descarca(filtre: dict) -> dict:
    """Întoarce {perioada 'YYYY-MM': valoare} pentru o serie (JSON-stat 2.0)."""
    url = API + "?" + urllib.parse.urlencode({**BAZA, **filtre})
    req = urllib.request.Request(url, headers={"User-Agent": "24reco.com data fetcher"})
    with urllib.request.urlopen(req, timeout=60) as r:
        js = json.load(r)
    # toate dimensiunile în afară de timp au o singură valoare → indexul valorii = indexul perioadei
    timp = js["dimension"]["time"]["category"]["index"]
    valori = js.get("value", {})
    out = {}
    for perioada, idx in timp.items():
        v = valori.get(str(idx))
        if v is not None:
            out[perioada] = round(float(v), 1)
    return out


def main() -> int:
    print("Construcții — autorizații de construire (Eurostat sts_cobp_m)")
    serii = {}
    for cheie, filtre in SERII:
        serii[cheie] = descarca(filtre)
        print(f"  {cheie}: {len(serii[cheie])} luni")

    if not serii["total"]:
        print("EROARE: seria România total a venit goală — verificați codurile de dimensiuni.", file=sys.stderr)
        return 1

    # perioadele = lunile pentru care avem totalul României
    perioade = sorted(serii["total"])
    luni = [{"perioada": p, **{k: serii[k].get(p) for k, _ in SERII}} for p in perioade]

    # nu suprascriem cu o serie mai scurtă decât cea existentă (răspuns parțial al API-ului)
    if OUTPUT.exists():
        vechi = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if len(vechi.get("luni", [])) > len(luni):
            print(f"EROARE: serie nouă mai scurtă ({len(luni)} < {len(vechi['luni'])}) — nu suprascriu.", file=sys.stderr)
            return 1
        if vechi.get("luni") == luni:
            print("Nicio schimbare în date.")
            return 0

    data = {
        "meta": {
            "titlu": "Autorizații de construire pentru clădiri",
            "sursa": "Eurostat (date raportate de Institutul Național de Statistică)",
            "dataset": DATASET,
            "url": f"https://ec.europa.eu/eurostat/databrowser/view/{DATASET}/default/table?lang=en",
            "unitate": "Indice, 2021 = 100 (suprafață utilă autorizată)",
            "frecventa": "lunar",
            "perioada": f"{perioade[0]} - {perioade[-1]}",
            "data_extragerii": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        },
        "luni": luni,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scris {OUTPUT} — {len(luni)} luni ({perioade[0]} – {perioade[-1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
