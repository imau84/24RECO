#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Actualizează datele de înmatriculări autoturisme pentru pagina Comerț.

Flux:
  1. POST https://dgpci.mai.gov.ro/drpciv-api/readNewsMedia  (category=statistica)
  2. Selectează articolele "Înmatriculări <luna> <an>" și descarcă arhiva atașată
     din https://dgpci.mai.gov.ro/assets/uploads/stiri-comunicate/<urlFileName>
     (formatul variază lunar: .rar sau .zip)
  3. Dezarhivează, ia fișierul *Autoturisme*.xls(x), citește sheet-ul "Lista_Detaliata"
  4. Agregă pe marcă / județ / combustibil / deținător, separat nou vs. uzat
  5. Scrie/actualizează public/comert_data.json (chei YYYY_MM)

Utilizare:
  python scripts/fetch_comert.py                # luna cea mai recentă (rulare lunară)
  python scripts/fetch_comert.py --backfill 2026 # toate lunile din 2026 (rulare unică)
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

import pandas as pd

API_URL = "https://dgpci.mai.gov.ro/drpciv-api/readNewsMedia"
DL_BASE = "https://dgpci.mai.gov.ro/assets/uploads/stiri-comunicate/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "public", "comert_data.json")

SHEET = "Lista_Detaliata"
COL_JUDET, COL_MARCA, COL_COMB = "Judet", "Marca", "Combustibil"
COL_DET, COL_MOTIV, COL_TOTAL = "Detinator", "Motiv de inmatriculare", "Total"
MOTIV_NOU, MOTIV_UZAT = "INSCRIERE VEHICUL NOU", "INSCRIERE VEHICUL UZAT"

LABELS = ["", "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
          "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"]
YYYYMM_RE = re.compile(r"(20\d{2})(\d{2})")


# ----------------------------------------------------------------- HTTP --
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://dgpci.mai.gov.ro",
    "Referer": "https://dgpci.mai.gov.ro/news-and-media/statistica",
}


def _request_with_retry(req, timeout, attempts=4):
    """Serverul DGPCI răspunde uneori 403 (WAF/rate-limit) pe runnerele GitHub.
    Reîncercăm cu pauze crescătoare; de regulă a 2-a/3-a încercare trece."""
    delay = 8
    last = None
    for i in range(attempts):
        try:
            return urllib.request.urlopen(req, timeout=timeout).read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429, 500, 502, 503) and i < attempts - 1:
                print(f"    … HTTP {e.code}, reîncerc în {delay}s "
                      f"(încercarea {i + 2}/{attempts})")
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except urllib.error.URLError as e:
            last = e
            if i < attempts - 1:
                print(f"    … eroare rețea ({e.reason}), reîncerc în {delay}s")
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise last


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={**HEADERS, "Content-Type": "application/json"})
    return json.loads(_request_with_retry(req, timeout=120).decode("utf-8"))


def download(url_file_name):
    url = DL_BASE + url_file_name
    req = urllib.request.Request(url, headers=HEADERS)
    return _request_with_retry(req, timeout=300)


def list_news(year):
    payload = {"language": "RO", "page": 1, "maxrows": 100,
               "category": "statistica", "year": year}
    data = post_json(API_URL, payload)
    return (data.get("data") or {}).get("news") or []


def is_inmatriculari(title):
    t = (title or "").strip().lower()
    return t.startswith("înmatricul") or t.startswith("inmatricul")


def news_files(item):
    i18n = item.get("i18n") or []
    if not i18n:
        return []
    return i18n[0].get("files") or []


# -------------------------------------------------------------- ARCHIVE --
def _try_extract(cmd):
    """Rulează o comandă de dezarhivare; întoarce True dacă unealta există.
    Nu validăm codul de retur (unele arhive au fișiere stricate irelevante);
    validarea reală e pe fișierul Autoturisme extras."""
    if not shutil.which(cmd[0]):
        return False
    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    return True


def _is_valid_excel(path):
    try:
        with open(path, "rb") as f:
            magic = f.read(8)
    except OSError:
        return False
    if magic[:2] == b"PK":
        # containerul zip al unui .xlsx trebuie să fie complet, nu trunchiat
        try:
            with zipfile.ZipFile(path) as z:
                return z.testzip() is None
        except zipfile.BadZipFile:
            return False
    return magic[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # .xls OLE2


def _find_autoturisme(out_dir):
    return [p for p in glob.glob(os.path.join(out_dir, "**", "*"), recursive=True)
            if re.search(r"autoturisme", os.path.basename(p), re.I)
            and p.lower().endswith((".xlsx", ".xls"))]


def extract_autoturisme(archive_bytes, file_name, workdir):
    """Scrie arhiva și extrage fișierul *Autoturisme*.xls(x), încercând pe rând
    mai multe unelte. `unar` trunchiază unele RAR-uri DRPCIV, deci preferăm
    `unrar` (oficial, compatibil WinRAR), apoi `7z`, apoi `unar`."""
    arc_path = os.path.join(workdir, file_name)
    with open(arc_path, "wb") as f:
        f.write(archive_bytes)

    tools = [
        ["unrar", "x", "-y", "-o+", arc_path],            # rulează cu cwd=out_dir
        ["7z", "x", "-y", arc_path],                       # idem
        ["unar", "-quiet", "-force-overwrite", arc_path],  # idem
    ]
    if file_name.lower().endswith(".zip"):
        tools.append(None)  # fallback: zipfile nativ

    for n, tool in enumerate(tools):
        out_dir = os.path.join(workdir, f"extracted_{n}")
        os.makedirs(out_dir, exist_ok=True)
        if tool is None:
            try:
                with zipfile.ZipFile(arc_path) as z:
                    z.extractall(out_dir)
            except zipfile.BadZipFile:
                continue
        else:
            cmd = tool[:]
            if not shutil.which(cmd[0]):
                continue
            subprocess.run(cmd, check=False, cwd=out_dir,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for cand in _find_autoturisme(out_dir):
            if _is_valid_excel(cand):
                print(f"    ✓ extras valid cu "
                      f"{'zipfile' if tool is None else tool[0]}: "
                      f"{os.path.basename(cand)}")
                return cand
        print(f"    ✗ {'zipfile' if tool is None else tool[0]}: "
              f"fișier Autoturisme lipsă sau trunchiat, încerc următoarea unealtă")

    raise FileNotFoundError(
        "Fișierul *Autoturisme*.xls(x) nu a putut fi extras intact din arhivă "
        "cu nicio unealtă (unrar/7z/unar)")


# ---------------------------------------------------------------- PARSE --
def _pick_engine(path):
    """Alege motorul după conținutul real al fișierului, nu după extensie.
    DRPCIV livrează uneori .xls (BIFF/OLE2) cu extensia .xlsx și invers."""
    with open(path, "rb") as f:
        magic = f.read(8)
    if magic[:2] == b"PK":                      # zip container -> xlsx
        return "openpyxl"
    if magic[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":  # OLE2 -> xls vechi
        return "xlrd"
    raise ValueError(
        f"Format Excel nerecunoscut (primii bytes: {magic!r}) — fișier corupt?")


def _find_header_row(path, engine):
    probe = pd.read_excel(path, sheet_name=SHEET, header=None, nrows=20, engine=engine)
    for i in range(len(probe)):
        vals = [str(v).strip() for v in probe.iloc[i].tolist()]
        if COL_JUDET in vals and COL_MARCA in vals and COL_TOTAL in vals:
            return i
    raise ValueError("Rândul de antet (Judet/Marca/Total) nu a fost găsit")


def load_detaliata(path):
    engine = _pick_engine(path)
    hdr = _find_header_row(path, engine)
    df = pd.read_excel(path, sheet_name=SHEET, header=hdr, engine=engine)
    df.columns = [str(c).strip() for c in df.columns]
    if len(df) and str(df.iloc[0].get(COL_JUDET, "")).strip().lower() in ("county", "judet"):
        df = df.iloc[1:].copy()
    df = df[df[COL_JUDET].notna() & (df[COL_JUDET].astype(str).str.strip() != "")]
    df[COL_TOTAL] = pd.to_numeric(df.get(COL_TOTAL), errors="coerce").fillna(1).astype(int)
    for c in (COL_JUDET, COL_MARCA, COL_COMB, COL_DET, COL_MOTIV):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    if COL_MARCA in df.columns:
        m = df[COL_MARCA].str.split(",").str[0]
        m = m.str.replace(r"[`'\"]", "", regex=True)
        m = m.str.replace(r"\s+", " ", regex=True).str.strip()
        df[COL_MARCA] = m
    return df


def _agg(df, col):
    s = df.groupby(col)[COL_TOTAL].sum().sort_values(ascending=False)
    return [[k, int(v)] for k, v in s.items()]


def aggregate(df):
    parts = {"nou": df[df[COL_MOTIV] == MOTIV_NOU], "uzat": df[df[COL_MOTIV] == MOTIV_UZAT]}
    out = {"total": int(df[COL_TOTAL].sum()),
           "nou": int(parts["nou"][COL_TOTAL].sum()),
           "uzat": int(parts["uzat"][COL_TOTAL].sum())}
    for dim, col in (("marca", COL_MARCA), ("judet", COL_JUDET),
                     ("combustibil", COL_COMB), ("detinator", COL_DET)):
        out[dim] = {k: _agg(v, col) for k, v in parts.items()}
    return out


# --------------------------------------------------------------- DRIVER --
def process_item(item):
    """Download + parse one news item. Returns (month_key, entry) or None."""
    files = news_files(item)
    arc = next((f for f in files
                if (f.get("urlFileName") or "").lower().endswith((".rar", ".zip"))), None)
    if not arc:
        return None
    title = (item.get("i18n") or [{}])[0].get("titleDescription", "")
    print(f"  → {title}  ({arc.get('name')})")
    blob = download(arc["urlFileName"])
    with tempfile.TemporaryDirectory() as tmp:
        # name the saved archive by its real display name to keep the right extension
        xls = extract_autoturisme(blob, os.path.basename(arc.get("name") or arc["urlFileName"]), tmp)
        yyyy, mm = YYYYMM_RE.search(os.path.basename(xls)).groups() \
            if YYYYMM_RE.search(os.path.basename(xls)) else (None, None)
        if not yyyy:
            print("    ! Nu pot determina luna din numele fișierului, sar peste.")
            return None
        df = load_detaliata(xls)
        if df.empty:
            raise RuntimeError(f"0 rânduri în {title} — nu suprascriu datele bune.")
        agg = aggregate(df)
        entry = {"label": f"{LABELS[int(mm)]} {yyyy}", **agg}
        return f"{yyyy}_{mm}", entry


def load_existing():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "months": {}}


def save(data):
    data["meta"] = {"source": "DGPCI / DRPCIV",
                    "category": "Autoturisme (M1, M1G)",
                    "updated": dt.date.today().isoformat()}
    data["months"] = dict(sorted(data["months"].items(), reverse=True))
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"✓ Scris {OUT_PATH} ({len(data['months'])} luni)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, metavar="AN",
                    help="Procesează toate lunile din anul dat (ex. 2026)")
    args = ap.parse_args()

    data = load_existing()
    updated = 0

    if args.backfill:
        year = args.backfill
        items = [it for it in list_news(year)
                 if is_inmatriculari((it.get("i18n") or [{}])[0].get("titleDescription"))]
        print(f"Backfill {year}: {len(items)} articole de înmatriculări")
        failed = []
        for n, it in enumerate(items):
            if n:
                time.sleep(6)   # pauză între luni, să nu declanșăm WAF-ul
            title = (it.get("i18n") or [{}])[0].get("titleDescription", "?")
            try:
                res = process_item(it)
                if res and res[0].startswith(str(year)):
                    data["months"][res[0]] = res[1]
                    updated += 1
            except Exception as e:
                # O lună cu arhivă/fișier corupt nu trebuie să blocheze restul.
                print(f"  ✗ EȘUAT: {title} — {type(e).__name__}: {e}")
                failed.append(title)
        if failed:
            print(f"\nAtenție: {len(failed)} luni au eșuat și au fost sărite: "
                  + "; ".join(failed))
    else:
        # rulare lunară: cel mai recent articol de înmatriculări (caut în anul curent,
        # cu fallback pe anul precedent pentru ianuarie)
        now = dt.date.today()
        items = []
        for y in (now.year, now.year - 1):
            items = [it for it in list_news(y)
                     if is_inmatriculari((it.get("i18n") or [{}])[0].get("titleDescription"))]
            if items:
                break
        if not items:
            print("Niciun articol de înmatriculări găsit.")
            sys.exit(1)
        res = process_item(items[0])      # lista vine sortată descrescător (cel mai nou primul)
        if not res:
            print("Articolul nu are arhivă utilizabilă.")
            sys.exit(1)
        data["months"][res[0]] = res[1]
        updated += 1

    if updated == 0:
        print("Nimic de actualizat — nu suprascriu fișierul existent.")
        sys.exit(1)
    save(data)


if __name__ == "__main__":
    main()
