#!/usr/bin/env python3
"""
01b_download_datagov.py
=======================
Descarcă „Parc auto la 31.12.AAAA” pentru 2012–2017 de pe data.gov.ro
(setul „parc-auto-romania”), în data/parc-auto/raw/AAAA_PARC_AUTO.<extensie>.

Lista fișierelor vine din package_show; resursele se aleg după ID. Dacă vreun ID
lipsește, se listează toate resursele setului și scriptul se oprește.
Fișierele deja descărcate (aceeași dimensiune ca pe server) nu se mai descarcă.

Rulare:  python scripts/parc-auto/01b_download_datagov.py
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

API_URL = "https://data.gov.ro/api/3/action/package_show?id=parc-auto-romania"
RESURSE = {
    2017: "d64518ef-bfcd-4962-bc2d-bdd2753b6d13",
    2016: "a82d6057-4828-444c-9c9a-f83d4488b5f2",
    2015: "e3ef3521-2d19-45d3-a686-8e4b9118dc8a",
    2014: "6840c8a0-9bf7-499e-8188-38b7c992b083",
    2013: "bfdce0c7-c797-44c5-8a08-d7b419850c50",
    2012: "3de380e6-c20b-4026-b925-b1beb71dd366",
}

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "parc-auto" / "raw"


def descarca(session, an, res):
    ext = Path(urlparse(res["url"]).path).suffix.lower() or "." + (res.get("format") or "bin").lower().strip(".")
    dest = RAW_DIR / f"{an}_PARC_AUTO{ext}"
    with session.get(res["url"], stream=True, timeout=300) as r:
        r.raise_for_status()
        marime = int(r.headers.get("Content-Length") or 0)
        if dest.exists() and marime and dest.stat().st_size == marime:
            print(f"  {an}: {dest.name} există deja ({marime / 1e6:.1f} MB)")
            return dest
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    tmp.replace(dest)
    print(f"  {an}: {dest.name} — format {res.get('format')}, {dest.stat().st_size / 1e6:.1f} MB")
    return dest


def main():
    session = requests.Session()
    session.headers["User-Agent"] = "24reco.com (date publice)"
    r = session.get(API_URL, timeout=60)
    r.raise_for_status()
    resurse = r.json()["result"]["resources"]
    pe_id = {x["id"]: x for x in resurse}

    lipsa = {an: rid for an, rid in RESURSE.items() if rid not in pe_id}
    if lipsa:
        print(f"ID-uri negăsite: {lipsa}\n\nResursele setului:")
        for x in resurse:
            print(f"  {x.get('name')} | {x.get('format')} | {x['url']}")
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for an in sorted(RESURSE):
        descarca(session, an, pe_id[RESURSE[an]])


if __name__ == "__main__":
    main()
