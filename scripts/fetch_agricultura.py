#!/usr/bin/env python3
"""
Script: fetch_agricultura.py
Folosește Playwright pentru a încărca pagina BRM (JavaScript dinamic).
Rulează în fiecare Luni prin GitHub Actions.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

JSON_PATH = Path("src/data/agricultura/agricultura_data.json")
URL = "https://brm.ro/cotatii-cereale/"

def parse_value(text: str):
    if not text:
        return None
    text = text.strip().replace('\xa0', '').replace(' ', '').replace(',', '').replace('.', '')
    m = re.search(r'\d{3,4}', text)
    return int(m.group()) if m else None

def scrape_with_playwright() -> list[dict]:
    from playwright.sync_api import sync_playwright

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        print(f"📡 Navigare la {URL}")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Extragem toate tabelele
        tables = page.query_selector_all("table")
        print(f"📊 Tabele găsite: {len(tables)}")

        current_nr = None
        current_label = None
        current_grau = {}
        current_porumb = {}

        for table in tables:
            html = table.inner_html()
            rows = table.query_selector_all("tr")

            for row in rows:
                cells = [c.inner_text().strip() for c in row.query_selector_all("td, th")]
                if not cells:
                    continue

                full = " ".join(cells)

                # Detectăm header săptămână
                m = re.search(r'SAPTAMANA\s+(\d+)/(\d+)', full, re.IGNORECASE)
                if m:
                    # Salvăm săptămâna precedentă
                    if current_nr and (current_grau or current_porumb):
                        results.append({
                            "nr": current_nr,
                            "label": current_label or "",
                            "grau": current_grau,
                            "porumb": current_porumb,
                        })
                    current_nr = int(m.group(1))
                    # Extragem intervalul de date
                    m2 = re.search(r'\(([^)]+)\)', full)
                    current_label = m2.group(1).strip() if m2 else f"S{current_nr}"
                    # Scurtăm label-ul
                    current_label = re.sub(r'[Ss]aptamana\s+\d+\s*[-–]\s*', '', current_label).strip()
                    current_grau = {}
                    current_porumb = {}
                    print(f"  📅 S{current_nr}: {current_label}")
                    continue

                # Rând cu date grâu
                if current_nr and re.search(r'gr[aâ]u', full, re.IGNORECASE):
                    vals = [parse_value(c) for c in cells]
                    vals = [v for v in vals if v and 500 <= v <= 3000]
                    if len(vals) >= 3:
                        current_grau = {"VEST": vals[0], "EST": vals[1], "SUD": vals[2]}

                # Rând cu date porumb
                if current_nr and re.search(r'porumb', full, re.IGNORECASE):
                    vals = [parse_value(c) for c in cells]
                    vals = [v for v in vals if v and 500 <= v <= 3000]
                    if len(vals) >= 3:
                        current_porumb = {"VEST": vals[0], "EST": vals[1], "SUD": vals[2]}

        # Ultima săptămână
        if current_nr and (current_grau or current_porumb):
            results.append({
                "nr": current_nr,
                "label": current_label or "",
                "grau": current_grau,
                "porumb": current_porumb,
            })

        browser.close()

    return results

def merge(existing: list, new_data: list) -> tuple[list, bool]:
    existing_nrs = {s["nr"]: i for i, s in enumerate(existing)}
    result = list(existing)
    changed = False

    for s in new_data:
        if s["nr"] not in existing_nrs:
            result.append(s)
            changed = True
            print(f"✅ Adăugat S{s['nr']}: grâu={s['grau']}, porumb={s['porumb']}")
        else:
            idx = existing_nrs[s["nr"]]
            if result[idx].get("grau") != s["grau"] or result[idx].get("porumb") != s["porumb"]:
                result[idx] = s
                changed = True
                print(f"🔄 Actualizat S{s['nr']}")

    result.sort(key=lambda x: x["nr"])
    return result, changed

def main():
    print(f"🌾 fetch_agricultura.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Citim JSON existent
    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        existing = data.get("saptamani", [])
        meta = data.get("meta", {})
    else:
        existing = []
        meta = {}

    print(f"📂 Date existente: {len(existing)} săptămâni (S{existing[0]['nr'] if existing else '?'}–S{existing[-1]['nr'] if existing else '?'})")

    # Scrape cu Playwright
    try:
        new_data = scrape_with_playwright()
    except Exception as e:
        print(f"❌ Eroare Playwright: {e}")
        sys.exit(1)

    print(f"📊 Săptămâni găsite pe BRM: {[s['nr'] for s in new_data]}")

    if not new_data:
        print("⚠️  Nu s-au găsit date. Verifică structura paginii BRM.")
        sys.exit(0)

    merged, changed = merge(existing, new_data)

    if not changed:
        print("ℹ️  Nicio modificare.")
        sys.exit(0)

    latest = merged[-1]
    meta.update({
        "actualizat": f"S{latest['nr']} {latest['label']}",
        "sursa": "Bursa Română de Mărfuri (BRM)",
        "url": URL,
        "frecventa": "saptamanal",
        "ultima_rulare": datetime.now().strftime("%Y-%m-%d"),
    })

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "saptamani": merged}, f, ensure_ascii=False, indent=2)

    print(f"💾 Salvat: {len(merged)} săptămâni, ultima: S{latest['nr']} — {latest['label']}")

if __name__ == "__main__":
    main()
