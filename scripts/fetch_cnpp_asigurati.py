#!/usr/bin/env python3
"""
Script: fetch_cnpp_asigurati.py
Descarcă fișierele "Asigurați" de la CNPP și generează JSON pentru 24reco.com
Poate rula manual (cu argumente) sau automat via GitHub Actions (săptămânal)

Utilizare:
  python fetch_cnpp_asigurati.py                   # verifică ultima lună disponibilă
  python fetch_cnpp_asigurati.py --year 2026 --month 3   # martie 2026 explicit
  python fetch_cnpp_asigurati.py --year 2025 --all        # toate lunile din 2025
  python fetch_cnpp_asigurati.py --year 2026 --all        # toate lunile din 2026
  python fetch_cnpp_asigurati.py --all-years              # 2025 + 2026 complet
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ─── Configurare ───────────────────────────────────────────────────────────────

BASE_URL = "https://www.cnpp.ro"
PAGE_URL_CURRENT = f"{BASE_URL}/ro/indicatori-statistici-pilon-i"
PAGE_URL_ARCHIVE  = (
    f"{BASE_URL}/indicatori-statistici-pilon-i"
    "?p_p_id=101_INSTANCE_svWpDmJy1qVq"
    "&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
    "&p_p_col_id=column-1&p_p_col_count=2"
    "&p_r_p_564233524_tag={year}"
)

OUTPUT_JSON = Path(__file__).parent.parent / "public" / "cnpp_asigurati.json"
CACHE_DIR   = Path(__file__).parent / "_cache_cnpp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": PAGE_URL_CURRENT,
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}

LUNA_MAP = {
    "Ianuarie": 1, "Februarie": 2, "Martie": 3, "Aprilie": 4,
    "Mai": 5, "Iunie": 6, "Iulie": 7, "August": 8,
    "Septembrie": 9, "Octombrie": 10, "Noiembrie": 11, "Decembrie": 12,
}
LUNA_RO = {v: k for k, v in LUNA_MAP.items()}


# ─── Scraping linkuri CNPP ─────────────────────────────────────────────────────

def get_page(url: str) -> BeautifulSoup:
    """Descarcă și parsează o pagina CNPP cu retry."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, "html.parser")
        except Exception as e:
            print(f"  [!] Retry {attempt+1}/3 pentru {url}: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Nu s-a putut descărca pagina: {url}")


def find_asigurati_links(year: int) -> dict[tuple, str]:
    """
    Returnează dict: (year, month_int) -> url_fisier
    Caută pe pagina anuală toate linkurile "Asigurați".
    """
    if year == 2026:
        url = PAGE_URL_CURRENT
    else:
        url = PAGE_URL_ARCHIVE.format(year=year)

    print(f"  Scanez pagina pentru {year}: {url}")
    soup = get_page(url)

    links = {}
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        # Caută linkuri de tipul "2026.03 - Martie Asigurați"
        m = re.search(
            r"(\d{4})\.(\d{2})\s*[-–]\s*(\w+)\s+Asigura", 
            text, re.UNICODE
        )
        if m:
            yr, mo, luna_text = int(m.group(1)), int(m.group(2)), m.group(3)
            href = a["href"]
            if not href.startswith("http"):
                href = BASE_URL + href
            # Curăță jsessionid din URL
            href = re.sub(r";jsessionid=[^?&]*", "", href)
            links[(yr, mo)] = href
            print(f"    ✓ Găsit: {yr}.{mo:02d} - {luna_text}")

    return links


# ─── Descărcare și cache ───────────────────────────────────────────────────────

def download_excel(year: int, month: int, url: str) -> Path | None:
    """Descarcă fișierul Excel în cache local. Returnează path-ul sau None."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"cnpp_{year}_{month:02d}_asigurati.xls"

    if cache_file.exists():
        print(f"    → Folosesc cache: {cache_file.name}")
        return cache_file

    print(f"    → Descarc: {url[:80]}...")
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, stream=True)
            resp.raise_for_status()
            content = resp.content
            if len(content) < 5000:
                print(f"    [!] Fișier prea mic ({len(content)} bytes) - posibil eroare")
                return None
            cache_file.write_bytes(content)
            print(f"    ✓ Descărcat: {len(content)/1024:.1f} KB")
            time.sleep(1.5)
            return cache_file
        except Exception as e:
            print(f"    [!] Retry {attempt+1}/3: {e}")
            time.sleep(3 * (attempt + 1))

    return None


# ─── Parsare Excel ─────────────────────────────────────────────────────────────

def parse_sheet_salarii(df_raw: pd.DataFrame) -> list[dict]:
    """
    Parsează sheet-ul CNPP_pilon_tip_asigurati_transe.
    Structura: tranșe salariale pe tip asigurat.
    """
    rows = []
    # Găsim headerul căutând o coloană cu text despre "salariu" sau "transe"
    header_row = None
    for i, row in df_raw.iterrows():
        row_str = " ".join(str(v).lower() for v in row.values if pd.notna(v))
        if "transa" in row_str or "tranșă" in row_str or "interval" in row_str or "grupa" in row_str:
            header_row = i
            break

    if header_row is None:
        # Fallback: folosim primele rânduri ca header
        header_row = 0

    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() for c in df_raw.iloc[header_row].values]
    df = df.dropna(how="all").reset_index(drop=True)

    for _, row in df.iterrows():
        row_dict = {}
        for col, val in row.items():
            if pd.notna(val):
                row_dict[str(col).strip()] = val
        if row_dict:
            rows.append(row_dict)

    return rows


def parse_sheet_judete(df_raw: pd.DataFrame) -> list[dict]:
    """
    Parsează sheet-ul cnpp_pilon1_salariu_mediu_judet.
    Structura: județ, salariu mediu, număr asigurați.
    """
    rows = []
    header_row = None
    for i, row in df_raw.iterrows():
        row_str = " ".join(str(v).lower() for v in row.values if pd.notna(v))
        if "judet" in row_str or "județ" in row_str or "judetul" in row_str:
            header_row = i
            break

    if header_row is None:
        header_row = 0

    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() for c in df_raw.iloc[header_row].values]
    df = df.dropna(how="all").reset_index(drop=True)

    for _, row in df.iterrows():
        row_dict = {}
        for col, val in row.items():
            if pd.notna(val) and str(val).strip() not in ("", "nan"):
                row_dict[str(col).strip()] = val
        if row_dict and len(row_dict) >= 2:
            rows.append(row_dict)

    return rows


def parse_excel_file(filepath: Path, year: int, month: int) -> dict | None:
    """Parsează un fișier Excel CNPP și returnează datele structurate."""
    print(f"    → Parsez: {filepath.name}")
    try:
        xl = pd.ExcelFile(filepath, engine="xlrd")
        sheets = xl.sheet_names
        print(f"    → Sheet-uri găsite: {sheets}")
    except Exception as e:
        # Încearcă cu openpyxl (format xlsx)
        try:
            xl = pd.ExcelFile(filepath, engine="openpyxl")
            sheets = xl.sheet_names
            print(f"    → Sheet-uri (openpyxl): {sheets}")
        except Exception as e2:
            print(f"    [!] Nu s-a putut deschide Excel: {e} / {e2}")
            return None

    result = {
        "year": year,
        "month": month,
        "luna": LUNA_RO.get(month, f"Luna {month}"),
        "period": f"{year}.{month:02d}",
        "sheets_found": sheets,
        "salarii": [],
        "judete": [],
    }

    # Găsim sheet-ul de salarii (primul sheet sau cel cu "transe"/"tip")
    sheet_salarii = None
    sheet_judete = None

    for s in sheets:
        sl = s.lower()
        if "transe" in sl or "tip_asig" in sl or "tip asig" in sl or sl == sheets[0].lower():
            if sheet_salarii is None:
                sheet_salarii = s
        if "judet" in sl or "județ" in sl:
            sheet_judete = s

    # Fallback: primul = salarii, ultimul = judete
    if sheet_salarii is None and len(sheets) >= 1:
        sheet_salarii = sheets[0]
    if sheet_judete is None and len(sheets) >= 2:
        sheet_judete = sheets[-1]

    print(f"    → Sheet salarii: {sheet_salarii}")
    print(f"    → Sheet județe: {sheet_judete}")

    try:
        engine = "xlrd" if str(filepath).endswith(".xls") else "openpyxl"
        if sheet_salarii:
            df_sal = pd.read_excel(filepath, sheet_name=sheet_salarii, header=None, engine=engine)
            result["salarii"] = parse_sheet_salarii(df_sal)
            print(f"    ✓ Salarii: {len(result['salarii'])} rânduri")

        if sheet_judete:
            df_jud = pd.read_excel(filepath, sheet_name=sheet_judete, header=None, engine=engine)
            result["judete"] = parse_sheet_judete(df_jud)
            print(f"    ✓ Județe: {len(result['judete'])} rânduri")
    except Exception as e:
        print(f"    [!] Eroare parsare: {e}")
        import traceback
        traceback.print_exc()

    return result


# ─── Logica principală ─────────────────────────────────────────────────────────

def load_existing_json() -> dict:
    """Încarcă JSON-ul existent sau returnează structură goală."""
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"updated_at": "", "periods": []}


def save_json(data: dict):
    """Salvează JSON-ul actualizat."""
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    data["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✅ JSON salvat: {OUTPUT_JSON}")
    print(f"   Perioade totale: {len(data['periods'])}")


def process_period(year: int, month: int, links: dict, existing_periods: set) -> dict | None:
    """Procesează o perioadă (an+lună) și returnează datele."""
    key = f"{year}.{month:02d}"
    if key in existing_periods:
        print(f"  → {key} deja în JSON, skip.")
        return None

    url = links.get((year, month))
    if not url:
        print(f"  → {key}: link negăsit pe pagina CNPP.")
        return None

    print(f"\n📥 Procesez {key} - {LUNA_RO.get(month, 'Luna?')} {year}")
    filepath = download_excel(year, month, url)
    if not filepath:
        return None

    data = parse_excel_file(filepath, year, month)
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Descarcă și procesează datele CNPP Asigurați Pilon I"
    )
    parser.add_argument("--year", type=int, help="Anul dorit (2025 sau 2026)")
    parser.add_argument("--month", type=int, help="Luna dorită (1-12)")
    parser.add_argument("--all", action="store_true", 
                        help="Descarcă toate lunile disponibile pentru --year")
    parser.add_argument("--all-years", action="store_true",
                        help="Descarcă 2025 + 2026 complet")
    parser.add_argument("--force", action="store_true",
                        help="Suprascrie și perioadele deja existente în JSON")
    args = parser.parse_args()

    # Determină ce ani/luni trebuie procesate
    tasks: list[tuple[int, int | None]] = []  # (year, month_or_None)

    if args.all_years:
        tasks = [(2025, None), (2026, None)]
    elif args.year and args.all:
        tasks = [(args.year, None)]
    elif args.year and args.month:
        tasks = [(args.year, args.month)]
    elif args.year:
        # Auto-detectare lune disponibile din pagina
        tasks = [(args.year, None)]
    else:
        # Default: verifică ultima lună disponibilă din 2026
        print("🔍 Mod auto: verifică ultima lună disponibilă din 2026...")
        tasks = [(2026, None)]

    # Încarcă JSON existent
    existing = load_existing_json()
    existing_periods = {p["period"] for p in existing.get("periods", [])}

    if args.force:
        existing_periods = set()
        existing["periods"] = []
        print("⚠️  --force: suprascrie toate perioadele existente")

    new_count = 0

    for (year, month_target) in tasks:
        print(f"\n{'='*60}")
        print(f"📋 Procesez: {year}" + (f" Luna {month_target}" if month_target else " (toate lunile)"))
        print('='*60)

        # Obține linkurile disponibile de pe pagina CNPP
        try:
            links = find_asigurati_links(year)
        except Exception as e:
            print(f"[!] Eroare scraping pagina {year}: {e}")
            continue

        if not links:
            print(f"[!] Nu s-au găsit linkuri pentru {year}")
            continue

        # Decide ce luni să proceseze
        if month_target is not None:
            months_to_process = [month_target]
        else:
            months_to_process = sorted(m for (y, m) in links if y == year)

        for month in months_to_process:
            result = process_period(year, month, links, existing_periods)
            if result:
                # Adaugă sau actualizează în lista de perioade
                existing["periods"] = [
                    p for p in existing["periods"] 
                    if p.get("period") != result["period"]
                ]
                existing["periods"].append(result)
                existing_periods.add(result["period"])
                new_count += 1

    # Sortează perioadele cronologic
    existing["periods"].sort(key=lambda p: p.get("period", ""))

    if new_count > 0:
        save_json(existing)
        print(f"\n✅ {new_count} perioadă(e) noi adăugate.")
    else:
        print("\nℹ️  Nicio perioadă nouă de adăugat.")
        # Salvăm oricum pentru a actualiza updated_at
        save_json(existing)


if __name__ == "__main__":
    main()
