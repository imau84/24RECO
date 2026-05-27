#!/usr/bin/env python3
"""
Script: fetch_agricultura.py - v5 final
Extrage Grâu Panificație + Porumb din tabelele BRM Cereale.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

JSON_PATH = Path("src/data/agricultura/agricultura_data.json")
URL = "https://brm.ro/cotatii-cereale/"

def parse_value(text: str):
    """Extrage valoare numerică validă (500-5000) din text."""
    if not text:
        return None
    text = text.strip().replace('\xa0', '').replace(' ', '').replace(',', '')
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
        page.wait_for_timeout(3000)

        # Click pe tab "Cotații săptămânale" dacă există
        try:
            tab = page.get_by_text("Cotații săptămânale", exact=False)
            tab.first.click()
            page.wait_for_timeout(2000)
            print("✅ Click tab săptămânal")
        except:
            pass

        tables = page.query_selector_all("table")
        print(f"📊 Tabele găsite: {len(tables)}")

        for table in tables:
            rows = table.query_selector_all("tr")
            current_nr = None
            current_label = None
            grau = {}
            porumb = {}
            in_first_subtable = False  # Prima subtabelă = Grâu + Porumb

            for row in rows:
                cells = [c.inner_text().strip().replace('\n', ' ') for c in row.query_selector_all("td, th")]
                if not cells or not any(cells):
                    continue

                full = " ".join(cells)

                # Header săptămână: "SAPTAMANA 19/2026 (Saptamana 07 - 13 mai 2026)"
                m = re.search(r'SAPTAMANA\s+(\d+)/(\d+)', full, re.IGNORECASE)
                if m:
                    # Salvăm săptămâna precedentă
                    if current_nr and grau and porumb:
                        results.append({
                            "nr": current_nr,
                            "label": current_label or "",
                            "grau": grau,
                            "porumb": porumb,
                        })
                        print(f"  ✅ S{current_nr}: grâu={grau}, porumb={porumb}")

                    current_nr = int(m.group(1))
                    m2 = re.search(r'\(([^)]+)\)', full)
                    raw_label = m2.group(1).strip() if m2 else ""
                    # Scurtăm: "Saptamana 07 - 13 mai 2026" -> "07-13 mai 2026"
                    raw_label = re.sub(r'[Ss]aptamana\s+', '', raw_label)
                    current_label = raw_label.strip()
                    grau = {}
                    porumb = {}
                    in_first_subtable = True
                    continue

                if not current_nr:
                    continue

                # Header subgrup: "ZONA DE LIVRARE/PRODUSUL  GRAU PT PANIFICATIE  Var.%  GRAU FURAJER..."
                # Prima apariție = grâu+porumb, a doua = orz+floarea — ignorăm a doua
                if re.search(r'ZONA DE LIVRARE', full, re.IGNORECASE):
                    # Dacă avem deja grâu, înseamnă că e al doilea subgrup — îl ignorăm
                    if grau:
                        in_first_subtable = False
                    continue

                if not in_first_subtable:
                    continue

                # Rânduri cu date: VEST / EST / SUD
                zone_match = re.match(r'^(VEST|EST|SUD)\b', full, re.IGNORECASE)
                if zone_match:
                    zona = zone_match.group(1).upper()
                    vals = [parse_value(c) for c in cells[1:]]  # Sărim coloana zonei
                    vals = [v for v in vals if v]
                    print(f"    {zona}: cells={cells}, vals={vals}")

                    # Structura coloane: [Grâu Panif, Var%, Grâu Furajer, Var%, Porumb, Var%]
                    # Valorile numerice valide în ordine: grâu_panif, grâu_furajer, porumb
                    if len(vals) >= 3:
                        grau[zona] = vals[0]   # Grâu Panificație
                        porumb[zona] = vals[2]  # Porumb (poziția 3)
                    elif len(vals) == 2:
                        grau[zona] = vals[0]
                        porumb[zona] = vals[1]
                    elif len(vals) == 1:
                        grau[zona] = vals[0]

            # Ultima săptămână
            if current_nr and grau and porumb:
                results.append({
                    "nr": current_nr,
                    "label": current_label or "",
                    "grau": grau,
                    "porumb": porumb,
                })
                print(f"  ✅ S{current_nr}: grâu={grau}, porumb={porumb}")

        browser.close()

    return results

def merge(existing: list, new_data: list) -> tuple[list, bool]:
    existing_map = {s["nr"]: i for i, s in enumerate(existing)}
    result = list(existing)
    changed = False
    for s in new_data:
        if s["nr"] not in existing_map:
            result.append(s)
            changed = True
            print(f"✅ Adăugat S{s['nr']}")
        else:
            idx = existing_map[s["nr"]]
            if result[idx].get("grau") != s.get("grau") or result[idx].get("porumb") != s.get("porumb"):
                result[idx] = s
                changed = True
                print(f"🔄 Actualizat S{s['nr']}")
    result.sort(key=lambda x: x["nr"])
    return result, changed

def main():
    print(f"🌾 fetch_agricultura.py v5 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

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

    print(f"📊 Săptămâni parsate: {[s['nr'] for s in new_data]}")

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

    print(f"💾 Salvat: {len(merged)} săptămâni, ultima: S{latest['nr']} — {latest['label']}")

if __name__ == "__main__":
    main()
