#!/usr/bin/env python3
"""
Script: fetch_agricultura.py
Rulează în fiecare Luni prin GitHub Actions.
Extrage cotațiile BRM Cereale și actualizează src/data/agricultura/agricultura_data.json
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://brm.ro/cotatii-cereale/"
JSON_PATH = Path("src/data/agricultura/agricultura_data.json")

ZONE = ["VEST", "EST", "SUD"]

def fetch_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    }
    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def parse_value(text: str) -> int | None:
    """Extrage valoare numerică din text (ex: '952 lei/t' → 952)"""
    if not text:
        return None
    text = text.strip().replace('\xa0', '').replace(',', '').replace('.', '')
    m = re.search(r'\d{3,4}', text)
    return int(m.group()) if m else None

def parse_week_header(text: str) -> tuple[int, str] | None:
    """Extrage numărul săptămânii și intervalul de date din header"""
    # Format: "SAPTAMANA 19/2026 (Saptamana 07 - 13 mai 2026)"
    m = re.search(r'SAPTAMANA\s+(\d+)/\d+.*?\(.*?(\d+\s*[-–]\s*\d+\s+\w+\s+\d+)\)', text, re.IGNORECASE)
    if m:
        nr = int(m.group(1))
        label = m.group(2).strip()
        return nr, label
    # Format alternativ
    m2 = re.search(r'[Ss][Aa][Pp][Tt]\w*\s*\.?\s*(\d+)', text)
    if m2:
        return int(m2.group(1)), text.strip()[:20]
    return None

def scrape_data(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    
    saptamani = []
    current_week = None
    current_label = None
    current_grau = {}
    current_porumb = {}

    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if not cells:
                continue

            full_text = " ".join(cells)

            # Detectăm header săptămână
            week_info = parse_week_header(full_text)
            if week_info:
                # Salvăm săptămâna precedentă dacă există
                if current_week and (current_grau or current_porumb):
                    saptamani.append({
                        "nr": current_week,
                        "label": current_label,
                        "grau": current_grau,
                        "porumb": current_porumb,
                    })
                current_week, current_label = week_info
                current_grau = {}
                current_porumb = {}
                continue

            # Detectăm rânduri cu date pentru grâu
            if current_week and re.search(r'gr[aâ]u', full_text, re.IGNORECASE):
                # Căutăm valori numerice
                vals = [parse_value(c) for c in cells if parse_value(c)]
                if len(vals) >= 3:
                    current_grau = {"VEST": vals[0], "EST": vals[1], "SUD": vals[2]}

            # Detectăm rânduri cu date pentru porumb
            if current_week and re.search(r'porumb', full_text, re.IGNORECASE):
                vals = [parse_value(c) for c in cells if parse_value(c)]
                if len(vals) >= 3:
                    current_porumb = {"VEST": vals[0], "EST": vals[1], "SUD": vals[2]}

    # Adăugăm ultima săptămână
    if current_week and (current_grau or current_porumb):
        saptamani.append({
            "nr": current_week,
            "label": current_label or "",
            "grau": current_grau,
            "porumb": current_porumb,
        })

    return saptamani

def merge_with_existing(existing: list, new_data: list) -> tuple[list, bool]:
    """Adaugă săptămânile noi la datele existente. Returnează (date_finale, a_fost_modificat)"""
    existing_nrs = {s["nr"] for s in existing}
    added = False
    result = list(existing)

    for s in new_data:
        if s["nr"] not in existing_nrs:
            result.append(s)
            added = True
            print(f"✅ Adăugat S{s['nr']}: grâu={s['grau']}, porumb={s['porumb']}")
        else:
            # Actualizăm dacă există date noi/corecte
            idx = next(i for i, x in enumerate(result) if x["nr"] == s["nr"])
            if result[idx] != s:
                result[idx] = s
                added = True
                print(f"🔄 Actualizat S{s['nr']}")

    result.sort(key=lambda x: x["nr"])
    return result, added

def main():
    print(f"🌾 fetch_agricultura.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📡 Fetch: {URL}")

    # Citim JSON existent
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        existing = data.get("saptamani", [])
        meta = data.get("meta", {})
    else:
        print("⚠️  Fișier JSON inexistent, creăm unul nou")
        existing = []
        meta = {}

    # Scrape BRM
    try:
        html = fetch_page()
        print(f"✅ Pagina descărcată ({len(html)} chars)")
    except Exception as e:
        print(f"❌ Eroare fetch: {e}")
        sys.exit(1)

    new_data = scrape_data(html)
    print(f"📊 Săptămâni găsite pe BRM: {[s['nr'] for s in new_data]}")

    if not new_data:
        print("⚠️  Nu s-au găsit date noi. Verifică structura HTML a paginii BRM.")
        sys.exit(0)

    merged, changed = merge_with_existing(existing, new_data)

    if not changed:
        print("ℹ️  Nicio modificare față de datele existente.")
        sys.exit(0)

    # Actualizăm meta
    latest = merged[-1]
    meta["actualizat"] = f"S{latest['nr']} {latest['label']}"
    meta["sursa"] = "Bursa Română de Mărfuri (BRM)"
    meta["url"] = URL
    meta["frecventa"] = "saptamanal"
    meta["ultima_rulare"] = datetime.now().strftime("%Y-%m-%d")

    output = {"meta": meta, "saptamani": merged}

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"💾 Salvat: {JSON_PATH} ({len(merged)} săptămâni)")
    print(f"📅 Ultima săptămână: S{latest['nr']} — {latest['label']}")

if __name__ == "__main__":
    main()
