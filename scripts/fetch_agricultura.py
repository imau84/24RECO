#!/usr/bin/env python3
"""
Script: fetch_agricultura.py - v3 cu debug complet
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
    text = text.strip().replace('\xa0', '').replace(' ', '').replace(',', '')
    # Eliminăm punctele ca separator mii
    text = re.sub(r'(\d)\.(\d{3})', r'\1\2', text)
    m = re.search(r'\b(\d{3,4})\b', text)
    if m:
        v = int(m.group(1))
        if 500 <= v <= 5000:
            return v
    return None

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
        page.wait_for_timeout(4000)

        # DEBUG: printăm tot textul paginii pentru primele 3000 chars
        full_text = page.inner_text("body")
        print("=== PREVIEW TEXT PAGINA (primele 2000 chars) ===")
        print(full_text[:2000])
        print("=== END PREVIEW ===")

        # Căutăm toate elementele care conțin "SAPTAMANA"
        elements = page.query_selector_all("*")
        saptamana_elements = []
        for el in elements:
            try:
                txt = el.inner_text()
                if re.search(r'SAPTAMANA\s+\d+', txt, re.IGNORECASE) and len(txt) < 500:
                    saptamana_elements.append(txt.strip())
            except:
                pass

        print(f"\n=== ELEMENTE CU 'SAPTAMANA' ({len(saptamana_elements)}) ===")
        for e in saptamana_elements[:10]:
            print(f"  >> {e[:200]}")
        print("=== END ===\n")

        # Extragem toate tabelele și printăm conținutul
        tables = page.query_selector_all("table")
        print(f"📊 Tabele găsite: {len(tables)}")

        for ti, table in enumerate(tables):
            rows = table.query_selector_all("tr")
            print(f"\n--- TABEL {ti+1} ({len(rows)} rânduri) ---")
            for ri, row in enumerate(rows[:30]):
                cells = [c.inner_text().strip() for c in row.query_selector_all("td, th")]
                if any(cells):
                    print(f"  R{ri+1}: {cells}")

        # Acum parsăm efectiv
        # Strategie: căutăm în tot textul paginii pattern-ul săptămânilor
        # BRM folosește format: "SAPTAMANA XX/YYYY" urmat de date
        
        # Găsim toate săptămânile din textul complet
        week_matches = list(re.finditer(
            r'SAPTAMANA\s+(\d+)/(\d+)\s*\(?([^)]*)\)?',
            full_text, re.IGNORECASE
        ))
        print(f"\n📅 Săptămâni găsite în text: {[(m.group(1), m.group(3)[:20]) for m in week_matches]}")

        # Parsăm tabelele cu strategie îmbunătățită
        for table in tables:
            rows = table.query_selector_all("tr")
            current_nr = None
            current_label = None
            current_grau = {}
            current_porumb = {}

            for row in rows:
                cells = [c.inner_text().strip().replace('\n', ' ') for c in row.query_selector_all("td, th")]
                if not cells:
                    continue
                full = " ".join(cells)

                # Header săptămână
                m = re.search(r'SAPTAMANA\s+(\d+)/\d+', full, re.IGNORECASE)
                if m:
                    if current_nr and (current_grau or current_porumb):
                        results.append({"nr": current_nr, "label": current_label or "", "grau": current_grau, "porumb": current_porumb})
                    current_nr = int(m.group(1))
                    m2 = re.search(r'\(([^)]+)\)', full)
                    current_label = m2.group(1).strip() if m2 else f"S{current_nr}"
                    current_grau = {}
                    current_porumb = {}
                    continue

                if not current_nr:
                    continue

                # Grâu
                if re.search(r'gr[aâ]u', full, re.IGNORECASE):
                    vals = [parse_value(c) for c in cells]
                    vals = [v for v in vals if v]
                    print(f"  Grâu row: {cells} -> vals: {vals}")
                    if len(vals) >= 3:
                        current_grau = {"VEST": vals[0], "EST": vals[1], "SUD": vals[2]}

                # Porumb
                if re.search(r'porumb', full, re.IGNORECASE):
                    vals = [parse_value(c) for c in cells]
                    vals = [v for v in vals if v]
                    print(f"  Porumb row: {cells} -> vals: {vals}")
                    if len(vals) >= 3:
                        current_porumb = {"VEST": vals[0], "EST": vals[1], "SUD": vals[2]}

            if current_nr and (current_grau or current_porumb):
                results.append({"nr": current_nr, "label": current_label or "", "grau": current_grau, "porumb": current_porumb})

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
            print(f"✅ Adăugat S{s['nr']}: {s}")
        else:
            idx = existing_nrs[s["nr"]]
            if result[idx].get("grau") != s.get("grau") or result[idx].get("porumb") != s.get("porumb"):
                result[idx] = s
                changed = True
                print(f"🔄 Actualizat S{s['nr']}")
    result.sort(key=lambda x: x["nr"])
    return result, changed

def main():
    print(f"🌾 fetch_agricultura.py v3 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if JSON_PATH.exists():
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        existing = data.get("saptamani", [])
        meta = data.get("meta", {})
    else:
        existing = []
        meta = {}

    print(f"📂 Date existente: {len(existing)} săptămâni")

    try:
        new_data = scrape_with_playwright()
    except Exception as e:
        print(f"❌ Eroare: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"\n📊 Săptămâni parsate: {[s['nr'] for s in new_data]}")

    if not new_data:
        print("⚠️  Nu s-au găsit date.")
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

    print(f"💾 Salvat: {len(merged)} săptămâni, ultima: S{latest['nr']}")

if __name__ == "__main__":
    main()
