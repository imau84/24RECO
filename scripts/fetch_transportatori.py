#!/usr/bin/env python3
"""
fetch_transportatori.py
=======================
Job lunar (prima zi a lunii) care preia operatorii de transport marfă prin
API-ul autorizatiiauto.ro și actualizează datele pentru pagina Transport.

Bazat pe Transportatori_API_Excel.py (endpoint-urile reale):
  POST /Marfa/ListaClase/GetListaClase                 -> {"Data":[{ClasaID, Denumire, ...}]}
  POST /Marfa/ListaClase/GetListaClaseOperator?clasaId=X -> {"Data":[{...operator...}]}

Diferența față de scriptul original: cookie-urile de sesiune NU mai sunt
hardcodate (acelea expiră). Folosim o sesiune `requests` care întâi deschide
pagina /Marfa/ListaClase ca să obțină cookie-uri proaspete + token-ul anti-forgery.

Clasificarea pe clase (mici/medii 1/medii 2/mari) se RECALCULEAZĂ din Nr.Vehicule
folosind pragurile tale (1–9 / 10–39 / 40–99 / 100+), exact ca formula din Excel.

Etichetare lună („Export data"): datele preluate în prima zi a lunii M reprezintă
luna anterioară (M-1). Ex.: rulare 1 iunie -> 2026.05 (Mai).

Output în folderul `public/`:
  transport-data.json          -> actualizat: evolutie + clase + operatoriMari + metrics
                                  (păstrează dieselData + countryNames)
  operatori-istoric.csv         -> TOATE lunile, cumulat (pentru Excel)
  operatori-<YYYY.MM>.csv       -> doar luna curentă

Rulare locală:  pip install requests ; python fetch_transportatori.py
"""

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://www.autorizatiiauto.ro"
PAGE_URL = f"{BASE_URL}/Marfa/ListaClase"
URL_CLASE = f"{BASE_URL}/Marfa/ListaClase/GetListaClase"
URL_OPERATORI = f"{BASE_URL}/Marfa/ListaClase/GetListaClaseOperator"

# Pragurile TALE pe Nr.Vehicule (identice cu formula din Excel)
BUCKETS = [
    {"nume": "Operatori mici",    "min": 1,   "max": 9,    "color": "#1d5fa8"},
    {"nume": "Operatori medii 1", "min": 10,  "max": 39,   "color": "#0d7c5a"},
    {"nume": "Operatori medii 2", "min": 40,  "max": 99,   "color": "#b06a0d"},
    {"nume": "Operatori mari",    "min": 100, "max": None, "color": "#c93a2b"},
]

LUNI_RO = ["", "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
           "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"]

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE_URL,
    "Origin": BASE_URL,
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}


def luna_export(today: date):
    """Luna anterioară rulării (datele de pe 1 ale lunii = luna trecută)."""
    y, m = today.year, today.month
    if m == 1:
        y, m = y - 1, 12
    else:
        m -= 1
    return f"{y}.{m:02d}", f"{LUNI_RO[m]} {y}"


def bucket_for(veh: int):
    for b in BUCKETS:
        if veh >= b["min"] and (b["max"] is None or veh <= b["max"]):
            return b["nume"]
    return None


def pick(d: dict, *needles):
    """Găsește prima cheie care conține unul dintre fragmente (case-insensitive)."""
    for k, v in d.items():
        kl = str(k).lower()
        if any(n in kl for n in needles):
            return v
    return None


# ---------------------------------------------------------------------------

def build_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    # Deschide pagina ca să obținem cookie-uri proaspete (ASP.NET_SessionId, TMSessionId,
    # __RequestVerificationToken) + eventual token-ul din formular.
    r = s.get(PAGE_URL, timeout=30)
    r.raise_for_status()
    token = None
    m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', r.text)
    if m:
        token = m.group(1)
    return s, token


def post_json(session, url, token, params=None):
    """POST cu fallback: întâi simplu, apoi cu token anti-forgery dacă serverul îl cere."""
    attempts = [{}]
    if token:
        attempts.append({"data": {"__RequestVerificationToken": token}})
        attempts.append({"headers": {"RequestVerificationToken": token}})
    last = None
    for extra in attempts:
        kwargs = {"params": params, "timeout": 60}
        if "data" in extra:
            kwargs["data"] = extra["data"]
        if "headers" in extra:
            kwargs["headers"] = {**session.headers, **extra["headers"]}
        r = session.post(url, **kwargs)
        last = r
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                pass
    raise RuntimeError(f"POST {url} a eșuat (status {last.status_code}): {last.text[:200]}")


def fetch_all_operators(session, token):
    clase = post_json(session, URL_CLASE, token)["Data"]
    print(f"Clase API: {len(clase)}")
    toti = []
    first_keys_printed = False
    for c in clase:
        clasa_id = c.get("ClasaID") or c.get("ClasaId") or c.get("Id")
        ops = post_json(session, URL_OPERATORI, token, params={"clasaId": clasa_id})["Data"]
        print(f"  clasaId={clasa_id} ({c.get('Denumire','?')}): {len(ops)} operatori")
        for op in ops:
            if not first_keys_printed:
                print("  [info] chei JSON operator:", list(op.keys()))
                first_keys_printed = True
            den = pick(op, "denumire", "nume")
            cf = pick(op, "fiscal", "cui", "cod")
            loc = pick(op, "localit", "oras", "judet")
            veh_raw = pick(op, "vehicul", "camioan", "nrvehic")
            try:
                veh = int(re.sub(r"[^\d]", "", str(veh_raw)) or 0)
            except Exception:
                veh = 0
            toti.append({
                "den": str(den or "").strip(),
                "cf": str(cf or "").strip(),
                "loc": str(loc or "").strip(),
                "veh": veh,
            })
    return toti


# ---------------------------------------------------------------------------

def main():
    out = Path("public")
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "transport-data.json"

    luna_cod, luna_label = luna_export(date.today())
    print(f"Lună export: {luna_cod} ({luna_label})")

    session, token = build_session()
    print("Sesiune deschisă; token anti-forgery:", "DA" if token else "nu (probabil nu e necesar)")
    toti = fetch_all_operators(session, token)

    if not toti:
        print("[EROARE] niciun operator preluat — NU suprascriu datele existente.", file=sys.stderr)
        sys.exit(1)

    # Atribuie clasa (bucket) după Nr.Vehicule
    for o in toti:
        o["clasa"] = bucket_for(o["veh"])
    toti = [o for o in toti if o["clasa"] and o["den"]]
    print(f"Total operatori valizi: {len(toti)}")

    # --- CSV lunar + istoric cumulat (format sheet 'data') ---
    cols = ["Denumire Operator", "Cod Fiscal", "Localitate", "Nr.Vehicule", "Export data", "Clase Transportator"]
    rows_csv = [[o["den"], o["cf"], o["loc"], o["veh"], luna_cod, o["clasa"]] for o in toti]

    luna_csv = out / f"operatori-{luna_cod}.csv"
    with open(luna_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows_csv)

    istoric = out / "operatori-istoric.csv"
    exists = istoric.exists()
    # Evită duplicarea lunii dacă jobul rulează de două ori
    already = set()
    if exists:
        with open(istoric, encoding="utf-8-sig") as f:
            for r in csv.reader(f):
                if len(r) >= 5:
                    already.add(r[4])
    if luna_cod not in already:
        with open(istoric, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(cols)
            w.writerows(rows_csv)
    print(f"CSV: {luna_csv.name} (+ istoric)")

    # --- Actualizează transport-data.json ---
    existing = {}
    if json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    # 1) evolutie: adaugă/actualizează luna curentă
    evolutie = existing.get("evolutie") or {"luni": [], "clase": []}
    if luna_cod not in evolutie["luni"]:
        evolutie["luni"].append(luna_cod)
        evolutie["luni"].sort()
    # reconstruiește structura claselor păstrând istoricul lunilor
    prev = {c["nume"]: c for c in evolutie.get("clase", [])}
    new_clase = []
    for b in BUCKETS:
        grp = [o for o in toti if o["clasa"] == b["nume"]]
        op_by = (prev.get(b["nume"], {}).get("operatori") or {}).copy()
        cam_by = (prev.get(b["nume"], {}).get("camioane") or {}).copy()
        op_by[luna_cod] = len(grp)
        cam_by[luna_cod] = sum(o["veh"] for o in grp)
        new_clase.append({"nume": b["nume"], "min": b["min"], "max": b["max"],
                          "operatori": op_by, "camioane": cam_by})
    evolutie["clase"] = new_clase

    # 2) tab-urile „ultimele date" = luna curentă
    clase = []
    tot_op = tot_cam = 0
    for i, b in enumerate(BUCKETS):
        grp = [o for o in toti if o["clasa"] == b["nume"]]
        op_n = len(grp); cam_n = sum(o["veh"] for o in grp)
        tot_op += op_n; tot_cam += cam_n
        interval = f"{b['min']} – {b['max']} camioane" if b["max"] else f"{b['min']}+ camioane"
        clase.append({"nr": i + 1, "nume": b["nume"], "interval": interval,
                      "min": b["min"], "max": b["max"] or 0,
                      "operatori": op_n, "camioane": cam_n, "pondere": 0.0, "color": b["color"]})
    for c in clase:
        c["pondere"] = round(c["operatori"] / tot_op * 100, 1) if tot_op else 0.0

    mari = sorted([o for o in toti if o["clasa"] == "Operatori mari"],
                  key=lambda o: o["veh"], reverse=True)
    operatori_mari = [{"nr": i + 1, "den": o["den"], "cf": o["cf"], "loc": o["loc"], "veh": o["veh"]}
                      for i, o in enumerate(mari)]

    metrics = {"totalOperatori": tot_op, "totalCamioane": tot_cam,
               "flotaMedie": round(tot_cam / tot_op, 1) if tot_op else 0,
               "flotaMaxima": max((o["veh"] for o in toti), default=0)}

    existing.update({
        "lastUpdate": luna_label,
        "generatedAt": date.today().isoformat(),
        "metrics": metrics, "clase": clase,
        "operatoriMari": operatori_mari, "evolutie": evolutie,
    })
    existing.setdefault("dieselData", [])
    existing.setdefault("countryNames", {})

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, separators=(",", ":"))

    print(f"✅ transport-data.json: {luna_label} | {metrics['totalOperatori']} operatori, "
          f"{metrics['totalCamioane']} camioane | evolutie luni: {evolutie['luni']}")


if __name__ == "__main__":
    main()
