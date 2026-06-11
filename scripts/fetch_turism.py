#!/usr/bin/env python3
"""
fetch_turism.py
===============
Actualizare automata a datelor pentru pagina "Turism" (Sosiri).

Sursa : INS TEMPO-Online, matricele TUR104* :
  - national  : sosiri pe tipuri de structuri x categorii de clasificare x tipuri de turisti (lunar)
  - judete    : sosiri pe tipuri de structuri x tipuri de turisti x judete (lunar)
  - localitati: sosiri pe tipuri de structuri x localitati (lunar)

Strategie (incrementala — descarca DOAR lunile lipsa):
  1. Citeste public/turism_data.json existent -> determina ultima luna prezenta
     in fiecare bloc (CHART_DATA / CAT_DATA, COUNTY_DATA, LOC_DATA).
  2. Pentru fiecare matrice candidata: GET metadata -> identifica dimensiunile
     dupa eticheta (structuri / categorii / turisti / judete / localitati / perioade).
     Rolul matricei (NATIONAL / COUNTY / LOC) se decide automat din dimensiuni,
     deci nu conteaza daca INS redenumeste codurile.
  3. Pentru fiecare luna lipsa: POST /tempo-ins/pivot cu encQuery restrans la
     luna respectiva (si la o singura structura pentru localitati, ca sa stam
     mereu sub pragul de 30.000 celule).
  4. Parseaza CSV-ul (detectie coloane pe baza continutului, robust la reordonare)
     si actualizeaza JSON-ul existent. Cheile de an sunt generice ("2025","2026",
     "2027"...) — pagina alege automat ultimii doi ani.
  5. Scrie public/turism_data.json doar daca s-a schimbat ceva.

Nota migrare: vechiul format LOC_DATA folosea {y25:[...], y26:[...]}.
La prima rulare scriptul il converteste automat in {"2025":[...], "2026":[...]}.

Ruleaza fara browser (doar HTTP) -> rapid si stabil in GitHub Actions.
"""

import copy
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

import requests

# ─── Config ──────────────────────────────────────────────────────────────────
BASE      = "http://statistici.insse.ro:8077/tempo-ins"
PIVOT_URL = f"{BASE}/pivot"

# Candidate, in ordinea preferintei. Rolul fiecareia se detecteaza din metadata.
MATRICES = ["TUR104F", "TUR104G", "TUR104H", "TUR104E", "TUR104D", "TUR104B"]

OUTPUT_PATH = "public/turism_data.json"
MIN_YEAR    = 2025          # nu coboram sub anul deja acoperit de site
MAX_CELLS   = 28000         # marja de siguranta sub pragul INS de 30.000
SLEEP_SEC   = 2.0           # pauza intre request-uri (politete + stabilitate)
RETRIES     = 4

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

JUDETE_RO = {
    "alba", "arad", "arges", "bacau", "bihor", "bistrita-nasaud", "botosani",
    "brasov", "braila", "buzau", "caras-severin", "calarasi", "cluj",
    "constanta", "covasna", "dambovita", "dolj", "galati", "giurgiu", "gorj",
    "harghita", "hunedoara", "ialomita", "iasi", "ilfov", "maramures",
    "mehedinti", "mures", "neamt", "olt", "prahova", "satu mare", "salaj",
    "sibiu", "suceava", "teleorman", "timis", "tulcea", "vaslui", "valcea",
    "vrancea", "bucuresti", "municipiul bucuresti",
}
TURISTI_SET = {"total", "romani", "straini"}

DEBUG = "--debug" in sys.argv
DRY   = "--dry-run" in sys.argv


def log(*a):
    print(*a, flush=True)


# ─── Helpers generale ────────────────────────────────────────────────────────
def strip_diac(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    return strip_diac((s or "").strip().lower())


def parse_luna(label: str):
    """'Luna aprilie 2026' -> (2026, 4). Altfel None."""
    parts = norm(label).split()
    try:
        if parts and parts[0] == "luna" and len(parts) >= 3:
            m = LUNI_RO.get(parts[1], 0)
            if m:
                return (int(parts[2]), m)
    except (ValueError, IndexError):
        pass
    return None


def to_number(s: str):
    s = (s or "").strip().strip('"').replace("\xa0", "").replace(" ", "")
    if s in ("", "-", ":", "...", "c", "*"):
        return None
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        f = float(s)
        return int(f) if f == int(f) else round(f, 1)
    except ValueError:
        return None


def http_get_json(url: str):
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            return r.json()
        except Exception as e:               # noqa: BLE001
            last = e
            log(f"    ! GET esuat (incercarea {attempt}/{RETRIES}): {e}")
            time.sleep(4 * attempt)
    raise RuntimeError(f"GET {url} a esuat definitiv: {last}")


def http_post_pivot(payload: dict) -> str:
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.post(PIVOT_URL, json=payload, headers=HEADERS, timeout=120)
            r.raise_for_status()
            text = r.content.decode("utf-8", errors="ignore")
            low = text.lower()
            if "celule" in low and ("30000" in text or "pragul" in low):
                raise RuntimeError("INS a respins cererea: depasire prag 30.000 celule.")
            return text
        except Exception as e:               # noqa: BLE001
            last = e
            log(f"    ! POST esuat (incercarea {attempt}/{RETRIES}): {e}")
            time.sleep(5 * attempt)
    raise RuntimeError(f"POST pivot a esuat definitiv: {last}")


# ─── Metadata & detectia rolurilor ───────────────────────────────────────────
def classify_dims(meta: dict) -> dict:
    """Mapare rol_dimensiune -> dict dimensiune, pe baza etichetelor + optiunilor."""
    roles = {}
    for d in meta.get("dimensionsMap", []):
        label = norm(d.get("label", ""))
        opts = d.get("options", [])
        if "localitati" in label:
            roles["loc"] = d
        elif "judet" in label or "macroregiuni" in label:
            roles["judet"] = d
        elif "structuri" in label:
            roles["structura"] = d
        elif "categorii" in label:
            roles["categorie"] = d
        elif "turisti" in label:
            roles["turisti"] = d
        elif "perioade" in label or (opts and parse_luna(opts[0].get("label", ""))):
            roles["luna"] = d
        elif label.startswith("um") or "unitati de masura" in label:
            roles["um"] = d
        else:
            # fallback: dimensiune de timp nedetectata dupa eticheta
            if opts and any(parse_luna(o.get("label", "")) for o in opts[:5]):
                roles["luna"] = d
            else:
                roles.setdefault("_altele", []).append(d)
    return roles


def matrix_role(dims: dict):
    if "loc" in dims and "structura" in dims and "luna" in dims:
        return "LOC"
    if "judet" in dims and "structura" in dims and "turisti" in dims and "luna" in dims:
        return "COUNTY"
    if "categorie" in dims and "structura" in dims and "turisti" in dims and "luna" in dims:
        return "NATIONAL"
    return None


def discover_matrices() -> dict:
    """Returneaza {rol: (cod_matrice, meta, dims)} pentru NATIONAL/COUNTY/LOC."""
    found = {}
    for code in MATRICES:
        if len(found) == 3:
            break
        url = f"{BASE}/matrix/{code}"
        log(f"  GET {url}")
        try:
            meta = http_get_json(url)
        except Exception as e:                # noqa: BLE001
            log(f"    ! sar peste {code}: {e}")
            continue
        dims = classify_dims(meta)
        role = matrix_role(dims)
        name = (meta.get("matrixName") or code).strip()[:90]
        log(f"    -> {code}: rol={role or 'necunoscut'} | {name}")
        if DEBUG:
            for d in meta.get("dimensionsMap", []):
                log(f"       · {d.get('label','?').strip()} ({len(d.get('options',[]))} optiuni)")
        if role and role not in found:
            found[role] = (code, meta, dims)
        time.sleep(1.0)
    return found


def month_options(dims: dict) -> dict:
    """{(an, luna): nomItemId} pentru toate lunile >= MIN_YEAR."""
    out = {}
    for o in dims["luna"]["options"]:
        ym = parse_luna(o.get("label", ""))
        if ym and ym[0] >= MIN_YEAR:
            out[ym] = str(o["nomItemId"])
    return out


def all_ids(dim: dict) -> list:
    return [str(o["nomItemId"]) for o in dim["options"]]


def find_option(dim: dict, label_norm: str):
    for o in dim["options"]:
        if norm(o.get("label", "")) == label_norm:
            return str(o["nomItemId"])
    return None


def build_enc_query(meta: dict, selection: dict) -> str:
    """selection: {dim_label_norm: [ids]} ; dimensiunile nespecificate -> toate optiunile.
    Ordinea dimensiunilor trebuie pastrata exact ca in metadata."""
    parts = []
    for d in meta["dimensionsMap"]:
        key = norm(d.get("label", ""))
        ids = selection.get(key)
        if ids is None:
            ids = [str(o["nomItemId"]) for o in d["options"]]
        parts.append(",".join(ids))
    return ":".join(parts)


def pivot_payload(code: str, meta: dict, enc: str) -> dict:
    det = meta["details"]
    return {
        "language": "ro",
        "encQuery": enc,
        "matCode": code,
        "matMaxDim": det["matMaxDim"],
        "matUMSpec": det["matUMSpec"],
        "matRegJ": det.get("matRegJ", 0),
    }


# ─── Parsare CSV ─────────────────────────────────────────────────────────────
def csv_rows(text: str) -> list:
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if r and any(c.strip() for c in r):
            rows.append([c.strip().strip('"') for c in r])
    return rows


def classify_columns(rows: list, structuri_norm: set) -> dict:
    """Detecteaza indecsi de coloane dupa continut (praguri majoritare,
    robust la randuri de header/titlu/footer)."""
    ncols = max(len(r) for r in rows)
    cols = [[(r[i] if i < len(r) else "") for r in rows] for i in range(ncols)]
    idx = {"structura": None, "categorie": None, "turisti": None,
           "geo": None, "luna": None, "um": None, "val": None}

    def ratio(vals, pred):
        return (sum(1 for v in vals if pred(v)) / len(vals)) if vals else 0.0

    scored = []
    for i, c in enumerate(cols):
        vals = [v for v in c if v]
        if not vals:
            continue
        nv = [norm(v) for v in vals]
        scored.append((i, {
            "luna":      ratio(vals, lambda v: parse_luna(v) is not None),
            "turisti":   ratio(nv, lambda v: v in TURISTI_SET)
                         if any(v in ("romani", "straini") for v in nv) else 0.0,
            "categorie": ratio(nv, lambda v: ("stele" in v) or ("flori" in v)
                               or v.endswith("stea") or ("floare" in v)),
            "geo":       ratio(vals, lambda v: bool(re.match(r"^\d{3,}\s", v))
                               or norm(v) in JUDETE_RO),
            "um":        ratio(nv, lambda v: ("numar" in v) or ("persoane" in v)),
            "val":       ratio(vals, lambda v: to_number(v) is not None),
            "structura": ratio(nv, lambda v: v in structuri_norm),
        }))

    # asignare in ordinea specificitatii; o coloana primeste un singur rol
    thresholds = [("luna", 0.6), ("val", 0.6), ("um", 0.8), ("turisti", 0.6),
                  ("categorie", 0.3), ("geo", 0.3), ("structura", 0.5)]
    used = set()
    for role, th in thresholds:
        best, best_r = None, th
        for i, sc in scored:
            if i in used:
                continue
            if sc[role] >= best_r:
                best, best_r = i, sc[role]
        if best is not None:
            idx[role] = best
            used.add(best)

    if idx["val"] is None:
        idx["val"] = ncols - 1
    if idx["structura"] is None:
        # prima coloana textuala ramasa
        for i, sc in scored:
            if i not in used and sc["val"] < 0.5:
                idx["structura"] = i
                break
    return idx


# ─── JSON existent ───────────────────────────────────────────────────────────
def load_existing() -> dict:
    if not os.path.exists(OUTPUT_PATH):
        raise SystemExit(f"Nu gasesc {OUTPUT_PATH} — ruleaza din radacina repo-ului.")
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_loc_years(data: dict):
    """LOC_DATA: {y25:[..], y26:[..]} -> {'2025':[..], '2026':[..]} (o singura data)."""
    loc = data.get("LOC_DATA", {})
    changed = False
    for s in loc.values():
        for jud in s.values():
            for k, vals in jud.items():
                if isinstance(vals, dict) and ("y25" in vals or "y26" in vals):
                    nv = {}
                    if "y25" in vals:
                        nv["2025"] = vals["y25"]
                    if "y26" in vals:
                        nv["2026"] = vals["y26"]
                    jud[k] = nv
                    changed = True
    if changed:
        log("  Migrare LOC_DATA: y25/y26 -> chei de an ('2025','2026')")


def year_arr(container: dict, year: int, month: int) -> list:
    """Asigura existenta listei pentru anul dat, extinsa pana la luna `month`."""
    y = str(year)
    arr = container.get(y)
    if not isinstance(arr, list):
        arr = []
        container[y] = arr
    while len(arr) < month:
        arr.append(None)
    return arr


def months_present(yearmap) -> set:
    """Set de (an, luna) deja prezente (valoare non-None) intr-un dict {an: [..]}."""
    out = set()
    if not isinstance(yearmap, dict):
        return out
    for y, arr in yearmap.items():
        if not re.match(r"^\d{4}$", str(y)) or not isinstance(arr, list):
            continue
        for i, v in enumerate(arr):
            if v is not None:
                out.add((int(y), i + 1))
    return out


# ─── Actualizari pe blocuri ──────────────────────────────────────────────────
def update_national(data: dict, code: str, meta: dict, dims: dict, missing: list) -> int:
    """Actualizeaza CHART_DATA + CAT_DATA pentru lunile lipsa. Returneaza nr. valori scrise."""
    months = month_options(dims)
    sel_months = [m for m in missing if m in months]
    if not sel_months:
        return 0
    structuri_norm = {norm(o["label"]) for o in dims["structura"]["options"]}
    written = 0

    # toate lunile lipsa intr-un singur request daca incape sub prag
    n_cells = (len(dims["structura"]["options"]) * len(dims["categorie"]["options"])
               * len(dims["turisti"]["options"]) * len(sel_months))
    chunks = [sel_months] if n_cells <= MAX_CELLS else [[m] for m in sel_months]

    for chunk in chunks:
        sel = {norm(dims["luna"]["label"]): [months[m] for m in chunk]}
        enc = build_enc_query(meta, sel)
        log(f"  [NATIONAL {code}] POST pivot pentru lunile {chunk}")
        text = http_post_pivot(pivot_payload(code, meta, enc))
        rows = csv_rows(text)
        if not rows:
            log("    ! CSV gol")
            continue
        idx = classify_columns(rows, structuri_norm)
        if DEBUG:
            log(f"    coloane detectate: {idx}")
        for r in rows:
            try:
                ym = parse_luna(r[idx["luna"]]) if idx["luna"] is not None else None
                val = to_number(r[idx["val"]])
                if not ym or val is None:
                    continue
                y, m = ym
                stru = r[idx["structura"]].strip() if idx["structura"] is not None else "Total"
                cat = r[idx["categorie"]].strip() if idx["categorie"] is not None else "Total"
                tur = r[idx["turisti"]].strip() if idx["turisti"] is not None else "Total"

                # CHART_DATA (doar categorie Total)
                if norm(cat) == "total":
                    node = data.setdefault("CHART_DATA", {}).setdefault(stru, {}).setdefault(tur, {})
                    arr = year_arr(node, y, m)
                    arr[m - 1] = val
                    written += 1

                # CAT_DATA: [structura][categorie][turisti][an]
                node = (data.setdefault("CAT_DATA", {})
                        .setdefault(stru, {}).setdefault(cat, {}).setdefault(tur, {}))
                year_arr(node, y, m)[m - 1] = val

                # STRUCTURI_DISPLAY: adauga structuri noi cu eticheta verbatim
                disp = data.setdefault("STRUCTURI_DISPLAY", {})
                if stru not in disp:
                    disp[stru] = stru
            except (IndexError, KeyError):
                continue
        time.sleep(SLEEP_SEC)
    return written


def update_county(data: dict, code: str, meta: dict, dims: dict, missing: list) -> int:
    months = month_options(dims)
    sel_months = [m for m in missing if m in months]
    if not sel_months:
        return 0
    structuri_norm = {norm(o["label"]) for o in dims["structura"]["options"]}
    written = 0

    base_cells = (len(dims["structura"]["options"]) * len(dims["turisti"]["options"])
                  * len(dims["judet"]["options"]))
    sel_extra = {}
    if "categorie" in dims:   # daca matricea are si categorii, luam doar 'Total'
        tid = find_option(dims["categorie"], "total")
        if tid:
            sel_extra[norm(dims["categorie"]["label"])] = [tid]
        else:
            base_cells *= len(dims["categorie"]["options"])

    per_req = max(1, MAX_CELLS // max(base_cells, 1))
    chunks = [sel_months[i:i + per_req] for i in range(0, len(sel_months), per_req)]

    for chunk in chunks:
        sel = dict(sel_extra)
        sel[norm(dims["luna"]["label"])] = [months[m] for m in chunk]
        enc = build_enc_query(meta, sel)
        log(f"  [JUDETE {code}] POST pivot pentru lunile {chunk}")
        text = http_post_pivot(pivot_payload(code, meta, enc))
        rows = csv_rows(text)
        if not rows:
            log("    ! CSV gol")
            continue
        idx = classify_columns(rows, structuri_norm)
        if DEBUG:
            log(f"    coloane detectate: {idx}")
        for r in rows:
            try:
                ym = parse_luna(r[idx["luna"]]) if idx["luna"] is not None else None
                val = to_number(r[idx["val"]])
                if not ym or val is None or idx["geo"] is None:
                    continue
                geo = r[idx["geo"]].strip()
                g = norm(geo)
                if g not in JUDETE_RO:        # sarim macroregiuni/regiuni/total tara
                    continue
                y, m = ym
                stru = r[idx["structura"]].strip() if idx["structura"] is not None else "Total"
                tur = r[idx["turisti"]].strip() if idx["turisti"] is not None else "Total"
                node = (data.setdefault("COUNTY_DATA", {})
                        .setdefault(stru, {}).setdefault(tur, {}).setdefault(geo, {}))
                year_arr(node, y, m)[m - 1] = val
                written += 1
            except (IndexError, KeyError):
                continue
        time.sleep(SLEEP_SEC)
    return written


def build_loc_to_judet(dim_loc: dict) -> dict:
    """Parcurge optiunile in ordine: judet curent -> localitatile care urmeaza."""
    mapping = {}
    current = None
    for o in dim_loc["options"]:
        label = (o.get("label") or "").strip()
        g = norm(label)
        if re.match(r"^\d{3,}\s", label):
            if current:
                mapping[label] = (current, label)          # localitate
        elif g in JUDETE_RO:
            current = label
            mapping[label] = (current, "TOTAL")            # randul de total al judetului
        # macroregiuni / regiuni / TOTAL tara -> ignorate
    return mapping


def update_loc(data: dict, code: str, meta: dict, dims: dict, missing: list) -> int:
    months = month_options(dims)
    sel_months = [m for m in missing if m in months]
    if not sel_months:
        return 0
    loc_map = build_loc_to_judet(dims["loc"])
    structuri_norm = {norm(o["label"]) for o in dims["structura"]["options"]}
    written = 0

    sel_base = {}
    if "turisti" in dims:                      # LOC_DATA nu are split pe turisti -> doar Total
        tid = find_option(dims["turisti"], "total")
        if tid:
            sel_base[norm(dims["turisti"]["label"])] = [tid]

    n_loc = len(dims["loc"]["options"])
    for (y, m) in sel_months:
        for s_opt in dims["structura"]["options"]:
            s_label = (s_opt.get("label") or "").strip()
            sel = dict(sel_base)
            sel[norm(dims["luna"]["label"])] = [months[(y, m)]]
            sel[norm(dims["structura"]["label"])] = [str(s_opt["nomItemId"])]
            if n_loc > MAX_CELLS:
                raise RuntimeError("Prea multe localitati pentru un singur request.")
            enc = build_enc_query(meta, sel)
            log(f"  [LOCALITATI {code}] {y}-{m:02d} · {s_label}")
            text = http_post_pivot(pivot_payload(code, meta, enc))
            rows = csv_rows(text)
            if not rows:
                time.sleep(SLEEP_SEC)
                continue
            idx = classify_columns(rows, structuri_norm)
            for r in rows:
                try:
                    val = to_number(r[idx["val"]])
                    if val is None or idx["geo"] is None:
                        continue
                    geo = r[idx["geo"]].strip()
                    hit = loc_map.get(geo)
                    if not hit:
                        continue
                    judet, key = hit
                    node = (data.setdefault("LOC_DATA", {})
                            .setdefault(s_label, {}).setdefault(judet, {})
                            .setdefault(key, {}))
                    year_arr(node, y, m)[m - 1] = val
                    written += 1
                except (IndexError, KeyError):
                    continue
            time.sleep(SLEEP_SEC)
    return written


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    log("════════════════════════════════════════════════")
    log(" Actualizare date Turism (INS TEMPO, sosiri)")
    log("════════════════════════════════════════════════")

    data = load_existing()
    before = copy.deepcopy(data)
    migrate_loc_years(data)

    # lunile deja prezente in fiecare bloc
    have_chart = months_present(data.get("CHART_DATA", {}).get("Total", {}).get("Total", {}))
    have_county = set()
    cd = data.get("COUNTY_DATA", {})
    if cd:
        s0 = next(iter(cd.values()), {})
        t0 = next(iter(s0.values()), {}) if s0 else {}
        j0 = next(iter(t0.values()), {}) if t0 else {}
        have_county = months_present(j0)
    have_loc = set()
    ld = data.get("LOC_DATA", {}).get("Total", {})
    if ld:
        j0 = next(iter(ld.values()), {})
        have_loc = months_present(j0.get("TOTAL", {}) if isinstance(j0, dict) else {})

    log(f"  Luni prezente — national: {sorted(have_chart)[-1] if have_chart else '—'} | "
        f"judete: {sorted(have_county)[-1] if have_county else '—'} | "
        f"localitati: {sorted(have_loc)[-1] if have_loc else '—'}")

    log("\nPas 1: identificare matrice TEMPO")
    found = discover_matrices()
    if not found:
        raise SystemExit("Nu am putut identifica nicio matrice TEMPO de turism.")

    total_written = 0
    summary = []

    if "NATIONAL" in found:
        code, meta, dims = found["NATIONAL"]
        avail = set(month_options(dims).keys())
        missing = sorted(avail - have_chart)
        log(f"\nPas 2: national ({code}) — luni lipsa: {missing or 'niciuna'}")
        if missing and not DRY:
            w = update_national(data, code, meta, dims, missing)
            total_written += w
            summary.append(f"national: {len(missing)} luni, {w} valori")

    if "COUNTY" in found:
        code, meta, dims = found["COUNTY"]
        avail = set(month_options(dims).keys())
        missing = sorted(avail - have_county)
        log(f"\nPas 3: judete ({code}) — luni lipsa: {missing or 'niciuna'}")
        if missing and not DRY:
            w = update_county(data, code, meta, dims, missing)
            total_written += w
            summary.append(f"judete: {len(missing)} luni, {w} valori")

    if "LOC" in found:
        code, meta, dims = found["LOC"]
        avail = set(month_options(dims).keys())
        missing = sorted(avail - have_loc)
        log(f"\nPas 4: localitati ({code}) — luni lipsa: {missing or 'niciuna'}")
        if missing and not DRY:
            w = update_loc(data, code, meta, dims, missing)
            total_written += w
            summary.append(f"localitati: {len(missing)} luni, {w} valori")

    # META
    all_have = months_present(data.get("CHART_DATA", {}).get("Total", {}).get("Total", {}))
    if all_have:
        y, m = max(all_have)
        data["META"] = {
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "lastMonth": f"{y}-{m:02d}",
            "source": "INS TEMPO-Online (statistici.insse.ro)",
        }

    if DRY:
        log("\n--dry-run: nu scriu nimic.")
        return

    if json.dumps(data, sort_keys=True) == json.dumps(before, sort_keys=True):
        log("\nNicio modificare — fisierul ramane neschimbat.")
        return

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    log(f"\n✅ Scris {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)//1024} KB) — "
        f"{total_written} valori noi ({'; '.join(summary) if summary else 'doar migrare format'})")


if __name__ == "__main__":
    main()
