#!/usr/bin/env python3
"""
ETL: date.gov.ro (ANAF/MF) -> Neon PostgreSQL
Importa:
  1. Date de identificare platitori (2 fisiere, separator ^)
  2. Situatii financiare (3 fisiere: BL_BS_SL, IR, UU; CSV cu virgula)

Ruleaza pe GitHub Actions (workflow_dispatch), o data pe an.
Necesita env: DATABASE_URL (conexiunea unpooled Neon).

Descarcarea foloseste API-ul CKAN al data.gov.ro:
  https://data.gov.ro/api/3/action/resource_show?id=<uuid>
"""

import csv
import io
import os
import re
import sys
import time
import zipfile
from datetime import datetime

import psycopg
import requests

# ---------------------------------------------------------------- configurare

CKAN_API = "https://data.gov.ro/api/3/action/resource_show?id={}"

# UUID-urile resurselor de pe data.gov.ro (se schimba la fiecare editie anuala)
RESOURCES_IDENTIFICARE = [
    "c39fee6e-810e-46fe-9020-72057fa89192",  # fisier a
    "6335ce42-7fd9-4532-b4a8-2929dcb65a21",  # fisier b
]
RESOURCES_SITUATII = [
    # eticheta "sursa" se detecteaza automat din numele fisierului descarcat
    "38a8cc80-3470-49a0-9335-7ae020d8239d",
    "eeecc692-d914-4d3b-b7f5-d1a8a9791979",
    "3540a9ce-6a4d-4e29-9aa1-ac909fe28ac1",
]
AN_BILANT = 2025

# coloanele pastrate din fisierul de identificare (numele din header-ul sursa)
KEEP_COLS = [
    "COD_FISCAL", "DENUMIRE", "TIP_UNITATE", "LOCALITATE", "STRADA", "NR",
    "DATA_INREGISTRARE", "TELEFON", "JUDET_COMERT", "NR_COMERT", "AN_COMERT",
    "COD_POSTAL", "DATA_STARE", "STARE", "JUDET",
]

DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
BATCH = 50_000

# ------------------------------------------------------------------- utilitare


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def get_with_retry(url: str, attempts: int = 6, timeout: int = 120, **kw):
    """GET cu retry si backoff exponential; data.gov.ro e instabil."""
    last = None
    for attempt in range(attempts):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            wait = 2 ** attempt * 10
            log(f"  eroare la {url} ({type(e).__name__}); reincerc in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Cerere esuata definitiv: {url} ({last})")


def download_resource(uuid: str, dest_dir: str = "downloads") -> str:
    """Afla URL-ul real prin API-ul CKAN si descarca fisierul, cu retry."""
    os.makedirs(dest_dir, exist_ok=True)
    meta = get_with_retry(CKAN_API.format(uuid)).json()
    if not meta.get("success"):
        raise RuntimeError(f"CKAN resource_show a esuat pentru {uuid}")
    url = meta["result"]["url"]
    name = meta["result"].get("name") or url.rsplit("/", 1)[-1]
    path = os.path.join(dest_dir, url.rsplit("/", 1)[-1])
    log(f"Descarc: {name} <- {url}")

    for attempt in range(6):
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            size_mb = os.path.getsize(path) / 1e6
            log(f"  salvat {path} ({size_mb:.1f} MB)")
            return path
        except requests.RequestException as e:
            wait = 2 ** attempt * 10
            log(f"  eroare ({type(e).__name__}: {e}); reincerc in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Descarcarea a esuat definitiv: {url}")


def iter_text_files(path: str):
    """Intoarce (nume, stream text) pentru fisierul dat; dezarhiveaza zip-uri."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if info.filename.lower().endswith((".txt", ".csv")):
                    yield info.filename, io.BytesIO(z.read(info))
    else:
        with open(path, "rb") as f:
            yield os.path.basename(path), io.BytesIO(f.read())


def decode_stream(raw: io.BytesIO) -> io.StringIO:
    """Detecteaza encoding-ul: utf-8(-sig) -> cp1250 -> latin-1."""
    data = raw.getvalue()
    for enc in ("utf-8-sig", "utf-8", "cp1250", "latin-1"):
        try:
            return io.StringIO(data.decode(enc))
        except UnicodeDecodeError:
            continue
    return io.StringIO(data.decode("utf-8", errors="replace"))


def parse_date(s):
    if not s or not DATE_RE.match(s):
        return None
    try:
        return datetime.strptime(s, "%d.%m.%Y").date()
    except ValueError:
        return None


def to_int(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def detect_sursa(fname: str) -> str:
    """Detecteaza tipul formularului din numele fisierului."""
    f = fname.lower()
    if "bl_bs_sl" in f:
        return "BL_BS_SL"
    if "_ir_" in f or f.startswith("web_ir") or "ir_an" in f:
        return "IR"
    if "_uu_" in f or f.startswith("web_uu") or "uu_an" in f:
        return "UU"
    raise RuntimeError(f"Nu pot detecta tipul formularului din numele: {fname}")


# ---------------------------------------------------------------------- schema

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS platitori (
    cui               BIGINT PRIMARY KEY,
    denumire          TEXT NOT NULL,
    tip_unitate       TEXT,
    localitate        TEXT,
    strada            TEXT,
    nr                TEXT,
    data_inregistrare DATE,
    telefon           TEXT,
    judet_comert      TEXT,
    nr_comert         TEXT,
    an_comert         TEXT,
    cod_postal        TEXT,
    data_stare        DATE,
    stare             TEXT,
    judet             TEXT
);
CREATE INDEX IF NOT EXISTS idx_platitori_judet    ON platitori (judet);
CREATE INDEX IF NOT EXISTS idx_platitori_denumire ON platitori (denumire);

CREATE TABLE IF NOT EXISTS situatii_financiare (
    cui                  BIGINT NOT NULL,
    an                   SMALLINT NOT NULL,
    sursa                TEXT NOT NULL,      -- BL_BS_SL / IR / UU
    caen                 INTEGER,
    active_imobilizate   BIGINT,             -- I1
    active_circulante    BIGINT,             -- I2
    stocuri              BIGINT,             -- I3
    creante              BIGINT,             -- I4
    casa_conturi         BIGINT,             -- I5
    cheltuieli_in_avans  BIGINT,             -- I6
    datorii              BIGINT,             -- I7
    venituri_in_avans    BIGINT,             -- I8
    provizioane          BIGINT,             -- I9
    capitaluri_total     BIGINT,             -- I10
    capital_subscris     BIGINT,             -- I11
    patrimoniul_regiei   BIGINT,             -- I12
    cifra_afaceri_neta   BIGINT,             -- I13
    venituri_totale      BIGINT,             -- I14
    cheltuieli_totale    BIGINT,             -- I15
    profit_brut          BIGINT,             -- I16
    pierdere_bruta       BIGINT,             -- I17
    profit_net           BIGINT,             -- I18
    pierdere_neta        BIGINT,             -- I19
    numar_salariati      INTEGER,            -- I20
    PRIMARY KEY (cui, an, sursa)
);
CREATE INDEX IF NOT EXISTS idx_sf_caen ON situatii_financiare (caen);
CREATE INDEX IF NOT EXISTS idx_sf_ca   ON situatii_financiare (cifra_afaceri_neta DESC NULLS LAST);
"""

# ------------------------------------------------------------- import platitori


def load_platitori(conn, paths, cui_filter):
    """Incarca doar platitorii al caror CUI e in cui_filter
    (firmele cu situatii financiare depuse) - limita 512MB Neon Free."""
    total, skipped = 0, 0
    with conn.cursor() as cur:
        cur.execute("TRUNCATE platitori")
        copy_sql = (
            "COPY platitori (cui, denumire, tip_unitate, localitate, strada, nr,"
            " data_inregistrare, telefon, judet_comert, nr_comert, an_comert,"
            " cod_postal, data_stare, stare, judet) FROM STDIN"
        )
        seen = set()
        with cur.copy(copy_sql) as copy:
            for path in paths:
                for fname, raw in iter_text_files(path):
                    log(f"Procesez identificare: {fname}")
                    text = decode_stream(raw)
                    header = text.readline().rstrip("\r\n").split("^")
                    ncols = len(header)
                    idx = {c: header.index(c) for c in KEEP_COLS}
                    for line in text:
                        parts = line.rstrip("\r\n").split("^")
                        if len(parts) == ncols + 1 and parts[-1] == "":
                            parts = parts[:-1]
                        if len(parts) != ncols:
                            skipped += 1
                            continue
                        cui = to_int(parts[idx["COD_FISCAL"]])
                        d_inreg = parse_date(parts[idx["DATA_INREGISTRARE"]].strip())
                        denumire = parts[idx["DENUMIRE"]].strip()
                        # sanity check: rand corupt de encoding -> campuri decalate
                        if cui is None or not denumire:
                            skipped += 1
                            continue
                        if cui not in cui_filter:  # fara bilant depus -> nu intra
                            skipped += 1
                            continue
                        if cui in seen:  # dubluri intre fisierele a si b
                            skipped += 1
                            continue
                        seen.add(cui)
                        g = lambda c: (parts[idx[c]].strip() or None)
                        copy.write_row((
                            cui, denumire, g("TIP_UNITATE"), g("LOCALITATE"),
                            g("STRADA"), g("NR"), d_inreg, g("TELEFON"),
                            g("JUDET_COMERT"), g("NR_COMERT"), g("AN_COMERT"),
                            g("COD_POSTAL"), parse_date((g("DATA_STARE") or "")),
                            g("STARE"), g("JUDET"),
                        ))
                        total += 1
                        if total % 200_000 == 0:
                            log(f"  ...{total:,} randuri")
    conn.commit()
    log(f"platitori: {total:,} inserate, {skipped:,} sarite")


# ----------------------------------------------------- import situatii financiare


def load_situatii(conn, paths):
    total, skipped = 0, 0
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM situatii_financiare WHERE an = %s", (AN_BILANT,)
        )
        copy_sql = (
            "COPY situatii_financiare (cui, an, sursa, caen,"
            " active_imobilizate, active_circulante, stocuri, creante,"
            " casa_conturi, cheltuieli_in_avans, datorii, venituri_in_avans,"
            " provizioane, capitaluri_total, capital_subscris, patrimoniul_regiei,"
            " cifra_afaceri_neta, venituri_totale, cheltuieli_totale,"
            " profit_brut, pierdere_bruta, profit_net, pierdere_neta,"
            " numar_salariati) FROM STDIN"
        )
        seen = set()
        with cur.copy(copy_sql) as copy:
            for path in paths:
                for fname, raw in iter_text_files(path):
                    sursa = detect_sursa(fname)
                    log(f"Procesez situatii [{sursa}]: {fname}")
                    reader = csv.reader(decode_stream(raw))
                    header = next(reader)
                    expected = 22  # CUI, CAEN, I1..I20
                    if len(header) != expected:
                        raise RuntimeError(
                            f"{fname}: astept {expected} coloane, gasit {len(header)}: {header}"
                        )
                    for row in reader:
                        if len(row) != expected:
                            skipped += 1
                            continue
                        cui = to_int(row[0])
                        if cui is None:
                            skipped += 1
                            continue
                        key = (cui, sursa)
                        if key in seen:
                            skipped += 1
                            continue
                        seen.add(key)
                        vals = [to_int(v) for v in row[1:]]
                        copy.write_row((cui, AN_BILANT, sursa, *vals))
                        total += 1
                        if total % 200_000 == 0:
                            log(f"  ...{total:,} randuri")
    conn.commit()
    log(f"situatii_financiare: {total:,} inserate, {skipped:,} sarite")
    return {cui for cui, _ in seen}


# ------------------------------------------------------------------------ main


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("Lipseste env DATABASE_URL")

    log("Descarc fisierele de pe data.gov.ro (API CKAN)...")
    paths_ident = [download_resource(u) for u in RESOURCES_IDENTIFICARE]
    paths_sit = [download_resource(u) for u in RESOURCES_SITUATII]

    log("Conectare la Neon...")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()
        # ordinea conteaza: intai situatiile (colectam CUI-urile firmelor
        # cu bilant depus), apoi platitorii filtrati dupa acele CUI-uri
        cui_set = load_situatii(conn, paths_sit)
        log(f"CUI-uri cu bilant depus: {len(cui_set):,}")
        load_platitori(conn, paths_ident, cui_set)

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM platitori")
            log(f"TOTAL platitori in DB: {cur.fetchone()[0]:,}")
            cur.execute("SELECT count(*) FROM situatii_financiare")
            log(f"TOTAL situatii in DB: {cur.fetchone()[0]:,}")
            cur.execute("ANALYZE platitori; ANALYZE situatii_financiare;")
        conn.commit()
    log("Gata.")


if __name__ == "__main__":
    main()
