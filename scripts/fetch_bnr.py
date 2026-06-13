# -*- coding: utf-8 -*-
"""
Actualizare automata a datelor BNR pentru pagina /institutii/bnr (24reco.com).

Sursa: Baza de date interactiva BNR (https://www.bnr.ro)
Endpoint export descoperit prin reverse-engineering:
    GET https://www.bnr.ro/idbsfiles?cid={CID}&dfrom=&dto=&period=all&format=CSV

CID-uri (identificate 2026-06):
    1190 - Balanta de plati - serii lunare          (pagina /2024-balanta-de-plati)
    1367 - Investitii directe - Tranzactii lunare    (pagina /2026-investitii-directe-principiul-directional)
     572 - Depozite pe sectoare institutionale       (pagina /1984-depozitele-gospodariilor-populatiei)
     571 - Credite pe sectoare institutionale        (aceeasi pagina)

Format CSV: separator ';', celule intre ghilimele (etichetele contin ';' intern),
cateva randuri de metadate, apoi antetul care incepe cu "Data" (fiecare celula
se termina cu codul seriei, ex. BOP6L_S_1), apoi randuri "YYYY-MM";"val";...
Valorile lipsa sunt "-". Serverul intoarce uneori 503 cat timp genereaza
exportul, deci e nevoie de retry cu pauze.

Output: public/bnr_data.json cu cheile BP_DATA, ISD_DATA, DEP, CR
(aceleasi chei pe care le citeste src/app/institutii/bnr/page.tsx).
"""

import csv
import io
import json
import re
import sys
import time
from datetime import date

import requests

BASE = "https://www.bnr.ro/idbsfiles?cid={cid}&dfrom=&dto=&period=all&format=CSV"
WARMUP_URL = "https://www.bnr.ro/1928-statistica"
OUT_PATH = "public/bnr_data.json"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    "Referer": "https://www.bnr.ro/1928-statistica",
}

# Sesiune partajata: prima cerere pe pagina HTML poate seta cookie-ul WAF (F5),
# pe care exportul il foloseste apoi.
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def warmup():
    """Viziteaza pagina de statistica pentru eventualul cookie WAF."""
    try:
        SESSION.get(WARMUP_URL, timeout=60)
        print(f"  warmup: cookies={list(SESSION.cookies.keys())}")
    except requests.RequestException as e:
        print(f"  warmup esuat (continui oricum): {e}")

# Maparea cod BNR -> cheie JSON. Validata prin compararea valorilor 2026-03
# cu datele existente in bnr_data.json (exporturi manuale anterioare).
SERIES = {
    "BP_DATA": {
        "cid": 1190,
        "scale": 1.0,            # mil. EUR
        "round": 0,
        "codes": {
            "BOP6L_S_1":   "cc",   # Sold cont curent
            "BOP6L_S_1B":  "b",    # Sold bunuri
            "BOP6L_S_1S":  "s",    # Sold servicii
            "BOP6L_S_1VP": "vp",   # Sold venituri primare
            "BOP6L_S_1VS": "vs",   # Sold venituri secundare
            "BOP6L_S_2":   "ck",   # Sold cont de capital
        },
    },
    "ISD_DATA": {
        "cid": 1367,
        "scale": 1.0,            # mil. EUR
        "round": 2,
        "codes": {
            "IDT6L_T":   "idt",    # ISD total (net)
            "IDT6L_R":   "res",    # Investitii ale rezidentilor in strainatate
            "IDT6L_N":   "nro",    # Investitii ale nerezidentilor in Romania
            "IDT6L_NS":  "ns",     # Nerezidenti - soc. care accepta depozite
            "IDT6L_NSC": "nsc",    # ... participatii la capital
            "IDT6L_NX":  "nx",     # Nerezidenti - alte sectoare
            "IDT6L_NXC": "nxc",    # ... participatii la capital
            "IDT6L_NXD": "nxd",    # ... instrumente de natura datoriei
        },
    },
    "DEP": {
        "cid": 572,
        "scale": 1e-6,           # mii lei -> miliarde lei
        "round": 2,
        "codes": {
            "IFMDL_G":   "gp",     # Gospodarii - total
            "IFMDL_GO":  "gpo",    # Gospodarii - overnight
            "IFMDL_GOL": "gpol",   # ... in lei
            "IFMDL_GOE": "gpoe",   # ... in euro
            "IFMDL_GT":  "gpt",    # Gospodarii - la termen
            "IFMDL_GTL": "gptl",   # ... in lei
            "IFMDL_GTE": "gpte",   # ... in euro
            "IFMDL_S":   "sn",     # Societati nefinanciare
            "IFMDL_AP":  "ap",     # Administratie publica
            "IFMDL_APC": "apc",    # ... centrala
            "IFMDL_APL": "apl",    # ... locala
        },
    },
    "CR": {
        "cid": 571,
        "scale": 1e-6,           # mii lei -> miliarde lei
        "round": 2,
        "codes": {
            "IFMCL_G":   "g",      # Gospodarii - total
            "IFMCL_GR":  "gl",     # ... in lei (RON)
            "IFMCL_GE":  "ge",     # ... in euro
            "IFMCL_GC":  "gc",     # Credite de consum
            "IFMCL_GCL": "gcl",    # ... in lei
            "IFMCL_GCE": "gce",    # ... in euro
            "IFMCL_GL":  "glo",    # Credite pentru locuinte
            "IFMCL_GLL": "gll",    # ... in lei
            "IFMCL_GLE": "gle",    # ... in euro
            "IFMCL_GX":  "gx",     # Alte scopuri
            "IFMCL_S":   "sn",     # Societati nefinanciare
            "IFMCL_SL":  "snl",    # ... in lei
            "IFMCL_SE":  "sne",    # ... in euro
            "IFMCL_I":   "ifn",    # Institutii financiare nemonetare
            "IFMCL_AP":  "ap",     # Administratie publica
            "IFMCL_APC": "apc",    # ... centrala
            "IFMCL_APL": "apl",    # ... locala
        },
    },
}

# Numar minim de randuri asteptat per serie (sanity check)
MIN_ROWS = {"BP_DATA": 60, "ISD_DATA": 150, "DEP": 220, "CR": 220}

CODE_RE = re.compile(r"([A-Z][A-Z0-9_]{4,})\s*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}$")


def fetch_csv(cid, attempts=8, delay=15):
    """Descarca CSV-ul unei serii; serverul intoarce 503 cat genereaza exportul."""
    url = BASE.format(cid=cid)
    last_status = None
    for i in range(attempts):
        try:
            r = SESSION.get(url, timeout=120)
            last_status = r.status_code
            ctype = r.headers.get("content-type", "")
            if r.status_code == 200 and ("csv" in ctype or r.text.startswith('"Nume')):
                print(f"  cid={cid}: OK ({len(r.text)} caractere, incercarea {i+1})")
                return r.text
            print(f"  cid={cid}: status {r.status_code} ({ctype}), reincerc in {delay}s...")
        except requests.RequestException as e:
            print(f"  cid={cid}: eroare retea {e}, reincerc in {delay}s...")
        time.sleep(delay)
    raise RuntimeError(f"cid={cid}: esec dupa {attempts} incercari (ultimul status: {last_status})")


def parse_value(s):
    s = (s or "").strip()
    if s in ("", "-"):
        return None
    try:
        return float(s.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def parse_series(text, codes_map, scale, ndigits):
    """Parseaza CSV-ul si intoarce lista de randuri {d: 'YYYY-MM', <chei>...}."""
    reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
    header = None
    rows = []
    col_for_key = {}

    for row in reader:
        if not row:
            continue
        if header is None:
            if row[0].strip() == "Data":
                header = row
                # construiesc maparea coloana -> cheie pe baza codului din antet
                found = {}
                for idx, cell in enumerate(header):
                    m = CODE_RE.search(cell.strip())
                    if m and m.group(1) in codes_map:
                        found[codes_map[m.group(1)]] = idx
                missing = [c for c, k in codes_map.items() if k not in found]
                if missing:
                    available = sorted({CODE_RE.search(c.strip()).group(1)
                                        for c in header if CODE_RE.search(c.strip())})
                    raise RuntimeError(
                        f"Coduri lipsa in antet: {missing}\nCoduri disponibile: {available}")
                col_for_key = found
            continue
        # rand de date
        d = row[0].strip().strip('"')
        if not DATE_RE.match(d):
            continue
        entry = {"d": d}
        for key, idx in col_for_key.items():
            v = parse_value(row[idx] if idx < len(row) else None)
            entry[key] = round(v * scale, ndigits) if v is not None else None
            if entry[key] is not None and ndigits == 0:
                entry[key] = int(entry[key])
        rows.append(entry)

    if header is None:
        raise RuntimeError("Nu am gasit antetul (randul care incepe cu 'Data')")
    rows.sort(key=lambda r: r["d"])
    return rows


def main():
    out = {}
    print("Warmup sesiune...")
    warmup()
    for i, (name, cfg) in enumerate(SERIES.items()):
        print(f"[{i+1}/4] Descarc {name} (cid={cfg['cid']})...")
        text = fetch_csv(cfg["cid"])
        rows = parse_series(text, cfg["codes"], cfg["scale"], cfg["round"])
        print(f"  {name}: {len(rows)} randuri, {rows[0]['d']} -> {rows[-1]['d']}")
        if len(rows) < MIN_ROWS[name]:
            raise RuntimeError(f"{name}: doar {len(rows)} randuri (minim {MIN_ROWS[name]}) - abandonez")
        out[name] = rows
        if i < 3:
            time.sleep(10)  # pauza intre serii, sa nu deranjam serverul

    out["meta"] = {
        "updated": date.today().isoformat(),
        "source": "Banca Nationala a Romaniei - Baza de date interactiva (bnr.ro)",
        "series": {n: {"cid": c["cid"]} for n, c in SERIES.items()},
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Scris {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"EROARE: {e}", file=sys.stderr)
        sys.exit(1)
