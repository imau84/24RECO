#!/usr/bin/env python3
"""
Script: fetch_cnpp_asigurati.py (v2 - parser corectat pe structura reală CNPP)
Descarcă fișierele "Asigurați" de la CNPP și generează JSON pentru 24reco.com

Structura Excel reală:
  Sheet "CNPP_pilon_tip_asigurati_transe":
    - header multi-rând, datele încep după rândul cu "(1)" în coloana 0
    - col 0: numărul grupei | col 1: tranșa de venit | col 2: număr (normă întreagă)
    - col 3: venit mediu | col 4: timp parțial | col 6: fără contract
    - col 8: șomaj | col 12: contract individual
    - rând "Total" la final
  Sheet "cnpp_pilon1_salariu_mediu_judet":
    - datele încep după rândul cu "(1)" în coloana 1
    - col 1: cod județ | col 2: denumire | col 3: nr angajatori
    - col 4: fond salarii | col 5: nr asigurați | col 6: salariu mediu

Utilizare:
  python fetch_cnpp_asigurati.py                          # ultima lună disponibilă
  python fetch_cnpp_asigurati.py --year 2026 --month 4    # lună specifică
  python fetch_cnpp_asigurati.py --year 2025 --all        # tot anul 2025
  python fetch_cnpp_asigurati.py --all-years              # 2025 + 2026 complet
  python fetch_cnpp_asigurati.py --all-years --force      # regenerează totul
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ─── Configurare ───────────────────────────────────────────────────────────────

BASE_URL = "https://www.cnpp.ro"
PAGE_URL_CURRENT = f"{BASE_URL}/ro/indicatori-statistici-pilon-i"
PAGE_URL_ARCHIVE = (
    f"{BASE_URL}/indicatori-statistici-pilon-i"
    "?p_p_id=101_INSTANCE_svWpDmJy1qVq"
    "&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
    "&p_p_col_id=column-1&p_p_col_count=2"
    "&p_r_p_564233524_tag={year}"
)

OUTPUT_JSON = Path(__file__).parent.parent / "public" / "cnpp_asigurati.json"
CACHE_DIR = Path(__file__).parent / "_cache_cnpp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": PAGE_URL_CURRENT,
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}

LUNA_RO = {
    1: "Ianuarie", 2: "Februarie", 3: "Martie", 4: "Aprilie",
    5: "Mai", 6: "Iunie", 7: "Iulie", 8: "August",
    9: "Septembrie", 10: "Octombrie", 11: "Noiembrie", 12: "Decembrie",
}

CURRENT_YEAR = 2026  # Anul afișat pe pagina principală (fără parametru de arhivă)


# ─── Scraping linkuri CNPP ─────────────────────────────────────────────────────

def get_page(url: str) -> BeautifulSoup:
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.content, "html.parser")
        except Exception as e:
            print(f"  [!] Retry {attempt+1}/3 pentru pagină: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Nu s-a putut descărca pagina: {url}")


def find_asigurati_links(year: int) -> dict:
    """Returnează dict: (year, month) -> url pentru fișierele Asigurați."""
    url = PAGE_URL_CURRENT if year == CURRENT_YEAR else PAGE_URL_ARCHIVE.format(year=year)
    print(f"  Scanez pagina pentru {year}...")
    soup = get_page(url)

    links = {}
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        m = re.search(r"(\d{4})\.(\d{2})\s*[-–]\s*(\w+)\s+Asigura", text, re.UNICODE)
        if m:
            yr, mo = int(m.group(1)), int(m.group(2))
            href = a["href"]
            if not href.startswith("http"):
                href = BASE_URL + href
            href = re.sub(r";jsessionid=[^?&]*", "", href)
            links[(yr, mo)] = href
            print(f"    ✓ Găsit: {yr}.{mo:02d} - {m.group(3)}")
    return links


# ─── Descărcare ────────────────────────────────────────────────────────────────

def download_excel(year: int, month: int, url: str) -> Path | None:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"cnpp_{year}_{month:02d}_asigurati.xls"
    if cache_file.exists():
        print(f"    → Folosesc cache: {cache_file.name}")
        return cache_file

    print(f"    → Descarc de la CNPP...")
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            resp.raise_for_status()
            if len(resp.content) < 5000:
                print(f"    [!] Fișier prea mic ({len(resp.content)} bytes)")
                return None
            cache_file.write_bytes(resp.content)
            print(f"    ✓ Descărcat: {len(resp.content)/1024:.1f} KB")
            time.sleep(1.5)
            return cache_file
        except Exception as e:
            print(f"    [!] Retry {attempt+1}/3: {e}")
            time.sleep(3 * (attempt + 1))
    return None


# ─── Parsare Excel (structură fixă CNPP) ───────────────────────────────────────

def _to_int(val) -> int:
    try:
        if pd.isna(val):
            return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def parse_salarii(filepath: Path) -> tuple[list[dict], int | None]:
    """
    Parsează sheet-ul CNPP_pilon_tip_asigurati_transe.
    Returnează (rânduri, total_asigurati).
    """
    df = pd.read_excel(
        filepath, sheet_name="CNPP_pilon_tip_asigurati_transe",
        header=None, engine="xlrd"
    )
    # Găsim rândul cu "(1)" în coloana 0 — datele încep imediat după
    start_row = None
    for i in range(len(df)):
        if str(df.iloc[i, 0]).strip() == "(1)":
            start_row = i + 1
            break
    if start_row is None:
        raise ValueError("Sheet tranșe: nu am găsit rândul de start '(1)'")

    rows = []
    total = None
    for i in range(start_row, len(df)):
        c0 = str(df.iloc[i, 0]).strip()
        if c0.lower() == "total":
            total = _to_int(df.iloc[i, 2])
            break
        if c0 in ("nan", ""):
            break
        transa = str(df.iloc[i, 1]).strip()
        if c0 == "0 (*)":
            transa = "Fără venit"
        rows.append({
            "grupa": c0,
            "transa": transa,
            "numar": _to_int(df.iloc[i, 2]),               # normă întreagă
            "venit_mediu": _to_int(df.iloc[i, 3]),
            "timp_partial": _to_int(df.iloc[i, 4]),
            "fara_contract": _to_int(df.iloc[i, 6]),
            "somaj": _to_int(df.iloc[i, 8]),
            "contract_individual": _to_int(df.iloc[i, 12]),
        })
    return rows, total


def parse_judete(filepath: Path) -> list[dict]:
    """Parsează sheet-ul cnpp_pilon1_salariu_mediu_judet."""
    df = pd.read_excel(
        filepath, sheet_name="cnpp_pilon1_salariu_mediu_judet",
        header=None, engine="xlrd"
    )
    start_row = None
    for i in range(len(df)):
        if str(df.iloc[i, 1]).strip() == "(1)":
            start_row = i + 1
            break
    if start_row is None:
        raise ValueError("Sheet județe: nu am găsit rândul de start '(1)'")

    rows = []
    for i in range(start_row, len(df)):
        c1 = str(df.iloc[i, 1]).strip()
        if c1.lower() == "total" or c1 in ("nan", ""):
            break
        rows.append({
            "cod": c1,
            "judet": str(df.iloc[i, 2]).strip(),
            "angajatori": _to_int(df.iloc[i, 3]),
            "fond_salarii": _to_int(df.iloc[i, 4]),
            "asigurati": _to_int(df.iloc[i, 5]),
            "salariu_mediu": _to_int(df.iloc[i, 6]),
        })
    return rows


def parse_excel_file(filepath: Path, year: int, month: int) -> dict | None:
    print(f"    → Parsez: {filepath.name}")
    try:
        salarii, total = parse_salarii(filepath)
        judete = parse_judete(filepath)
    except Exception as e:
        print(f"    [!] Eroare parsare: {e}")
        import traceback
        traceback.print_exc()
        return None

    print(f"    ✓ Salarii: {len(salarii)} tranșe, total asigurați: {total}")
    print(f"    ✓ Județe: {len(judete)} rânduri")

    return {
        "year": year,
        "month": month,
        "luna": LUNA_RO.get(month, f"Luna {month}"),
        "period": f"{year}.{month:02d}",
        "total_asigurati": total,
        "salarii": salarii,
        "judete": judete,
    }


# ─── Logica principală ─────────────────────────────────────────────────────────

def load_existing_json() -> dict:
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"updated_at": "", "periods": []}


def save_json(data: dict):
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)
    print(f"\n✅ JSON salvat: {OUTPUT_JSON}")
    print(f"   Perioade totale: {len(data['periods'])}")


def main():
    parser = argparse.ArgumentParser(description="Fetch CNPP Asigurați Pilon I")
    parser.add_argument("--year", type=int)
    parser.add_argument("--month", type=int)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--all-years", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.all_years:
        tasks = [(2025, None), (2026, None)]
    elif args.year and args.month:
        tasks = [(args.year, args.month)]
    elif args.year:
        tasks = [(args.year, None)]
    else:
        print("🔍 Mod auto: verifică luni noi pe pagina 2026...")
        tasks = [(CURRENT_YEAR, None)]

    existing = load_existing_json()
    if args.force:
        # La --force, elimină doar perioadele care vor fi re-procesate
        years_forced = {y for (y, _) in tasks}
        if args.month:
            existing["periods"] = [
                p for p in existing["periods"]
                if not (p["year"] == args.year and p["month"] == args.month)
            ]
        else:
            existing["periods"] = [
                p for p in existing["periods"] if p["year"] not in years_forced
            ]
        print(f"⚠️  --force: perioadele pentru {sorted(years_forced)} vor fi regenerate")

    existing_periods = {p["period"] for p in existing.get("periods", [])}
    new_count = 0

    for (year, month_target) in tasks:
        print(f"\n{'='*60}\n📋 Procesez: {year}" +
              (f" luna {month_target}" if month_target else " (toate lunile)") +
              f"\n{'='*60}")
        try:
            links = find_asigurati_links(year)
        except Exception as e:
            print(f"[!] Eroare scraping {year}: {e}")
            continue
        if not links:
            print(f"[!] Nu s-au găsit linkuri Asigurați pentru {year}")
            continue

        months = [month_target] if month_target else sorted(
            m for (y, m) in links if y == year
        )

        for month in months:
            key = f"{year}.{month:02d}"
            if key in existing_periods:
                print(f"  → {key} deja în JSON, skip.")
                continue
            url = links.get((year, month))
            if not url:
                print(f"  → {key}: link negăsit.")
                continue

            print(f"\n📥 Procesez {key} - {LUNA_RO.get(month)} {year}")
            filepath = download_excel(year, month, url)
            if not filepath:
                continue
            result = parse_excel_file(filepath, year, month)
            if result:
                existing["periods"] = [
                    p for p in existing["periods"] if p["period"] != key
                ]
                existing["periods"].append(result)
                existing_periods.add(key)
                new_count += 1

    existing["periods"].sort(key=lambda p: p.get("period", ""))
    save_json(existing)
    print(f"\n{'✅ ' + str(new_count) + ' perioadă(e) noi' if new_count else 'ℹ️  Nicio perioadă nouă'}")


if __name__ == "__main__":
    main()
