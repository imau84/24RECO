#!/usr/bin/env python3
"""
descarca.py
===========
Descarcă arhivele „Parc auto la 31.12.AAAA” de pe dgpci.mai.gov.ro.

Lista știrilor se ia cu POST la /drpciv-api/readNewsMedia (categoria
„statistica”), pentru fiecare an de publicare 2018–2026. Din știrile cu titlul
„Parc auto la (data de) 31.12.AAAA” se descarcă fișierele atașate în
data/parc-auto/raw/; numele începe cu anul datelor (<AAAA>_..., dacă nu începe deja).

Arhivele deja descărcate (aceeași dimensiune) nu se mai descarcă.

Rulare:  python scripts/parc-auto/descarca.py
"""

import re
import sys
from pathlib import Path

import requests

API_URL = "https://dgpci.mai.gov.ro/drpciv-api/readNewsMedia"
FILE_URL = "https://dgpci.mai.gov.ro/assets/uploads/stiri-comunicate/"
ANI_PUBLICARE = range(2018, 2027)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "parc-auto" / "raw"

TITLU_RE = re.compile(r"parc\s+auto\s+la\s+(?:data\s+de\s+)?31\.12\.(\d{4})", re.I)


def lista_arhive(session):
    """Întoarce [(an_date, nume_original, urlFileName, size)] pentru toate știrile „Parc auto”."""
    arhive = {}
    for an in ANI_PUBLICARE:
        body = {"language": "RO", "page": 1, "maxrows": 200, "category": "statistica", "year": an}
        r = session.post(API_URL, json=body, timeout=60)
        r.raise_for_status()
        for stire in r.json()["data"]["news"]:
            for i18n in stire.get("i18n", []):
                if i18n.get("language") != "RO":
                    continue
                m = TITLU_RE.search(i18n.get("titleDescription", ""))
                if not m:
                    continue
                an_date = int(m.group(1))
                for f in i18n.get("files", []):
                    arhive[(an_date, f["urlFileName"])] = (an_date, f["name"], f["urlFileName"], f.get("size"))
    return sorted(arhive.values())


def descarca(session, an_date, nume, url_file, size):
    nume_local = re.sub(r"[^A-Za-z0-9._-]+", "_", nume)
    if not nume_local.startswith(str(an_date)):
        nume_local = f"{an_date}_{nume_local}"
    dest = RAW_DIR / nume_local
    if dest.exists() and (size is None or dest.stat().st_size == size):
        print(f"  {an_date}: {nume_local} există deja")
        return dest
    print(f"  {an_date}: descarc {nume} ({(size or 0) / 1e6:.1f} MB)")
    with session.get(FILE_URL + url_file, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    tmp.replace(dest)
    return dest


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = "24reco.com (date publice)"
    arhive = lista_arhive(session)
    if not arhive:
        sys.exit("Nu am găsit nicio știre „Parc auto la 31.12.AAAA”.")
    print(f"Am găsit {len(arhive)} arhive: ani {sorted({a[0] for a in arhive})}")
    for a in arhive:
        descarca(session, *a)


if __name__ == "__main__":
    main()
