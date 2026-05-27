#!/usr/bin/env python3
"""
fetch_agricultura.py - versiunea finală
Extrage Grâu Panificație + Porumb din tablepress-16 de pe brm.ro
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

JSON_PATH = Path("src/data/agricultura/agricultura_data.json")
URL = "https://brm.ro/cotatii-cereale/"

def parse_val(text: str):
    text = text.strip().replace('\xa0', '').replace(',', '')
    m = re.search(r'\b(\d{3,4})\b', text)
    if m:
        v = int(m.group(1))
        if 500 <= v <= 5000:
            return v
    return None

def get_html() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
    return html

def parse_data(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tablepress-16")
    if not table:
        print("❌ Tabelul tablepress-16 nu a fost găsit!")
        return []

    rows = table.find_all("tr")
    print(f"📊 Rânduri în tabel: {len(rows)}")

    results = []
    current_nr = None
    current_label = None
    grau = {}
    porumb = {}
    in_grau_section = False

    for row in rows:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if not cells or not any(cells):
            continue

        full = cells[0]

        # Header săptămână: "SAPTAMANA 19/2026 (Saptamana 07 - 13 mai 2026)"
        m = re.match(r'SAPTAMANA\s+(\d+)/\d+\s*\(([^)]+)\)', full, re.IGNORECASE)
        if m:
            # Salvăm săptămâna precedentă
            if current_nr and len(grau) == 3 and len(porumb) == 3:
                results.append({"nr": current_nr, "label": current_label, "grau": grau, "porumb": porumb})
                print(f"  ✅ S{current_nr}: grâu={grau}, porumb={porumb}")

            current_nr = int(m.group(1))
            raw = m.group(2).strip()
            # "Saptamana 07 - 13 mai 2026" → "07-13 mai 2026"
            current_label = re.sub(r'^[Ss]aptamana\s+', '', raw).replace(' - ', '-')
            grau = {}
            porumb = {}
            in_grau_section = False
            continue

        if not current_nr:
            continue

        # Header subgrup
        if re.search(r'ZONA DE LIVRARE', full, re.IGNORECASE):
            # Prima apariție cu GRAU PT PANIFICATIE = secțiunea noastră
            if len(cells) > 1 and re.search(r'GRAU PT PANIFICATIE', cells[1], re.IGNORECASE):
                in_grau_section = True
            else:
                in_grau_section = False
            continue

        if not in_grau_section:
            continue

        # Rânduri VEST/EST/SUD
        zona_m = re.match(r'^(VEST|EST|SUD)\b', full, re.IGNORECASE)
        if zona_m and len(cells) >= 6:
            zona = zona_m.group(1).upper()
            # cols: [Zona, GrauPanif, Var%, GrauFurajer, Var%, Porumb, Var%]
            v_grau = parse_val(cells[1])    # coloana 2 = Grâu Panificație
            v_porumb = parse_val(cells[5])  # coloana 6 = Porumb
            if v_grau:
                grau[zona] = v_grau
            if v_porumb:
                porumb[zona] = v_porumb

    # Ultima săptămână
    if current_nr and len(grau) == 3 and len(porumb) == 3:
        results.append({"nr": current_nr, "label": current_label, "grau": grau, "porumb": porumb})
        print(f"  ✅ S{current_nr}: grâu={grau}, porumb={porumb}")

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
    print(f"🌾 fetch_agricultura.py final — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

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
        html = get_html()
        print(f"✅ HTML descărcat: {len(html)} chars")
    except Exception as e:
        print(f"❌ Eroare fetch: {e}")
        sys.exit(1)

    new_data = parse_data(html)
    print(f"📊 Săptămâni găsite: {[s['nr'] for s in new_data]}")

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
