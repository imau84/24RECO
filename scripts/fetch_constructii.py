#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Foloseste Playwright pentru a accesa INSSE TEMPO-Online ca un browser real,
selecteaza LOC108A cu filtrele corecte si extrage datele din tabel.
"""

import json
import os
import sys
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

OUTPUT_PATH = "src/data/constructii/constructii_data.json"
INSSE_URL = "http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table"

LUNI_RO = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
}

def parse_luna(label):
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            an = int(parts[2])
            lp = parts[1]
            return (an, LUNI_RO.get(lp, int(lp) if lp.isdigit() else 0))
        elif parts[0] in ("anul", "an"):
            return (int(parts[1]), 0)
    except:
        pass
    return (0, 0)

def parse_luna_json(label):
    parts = label.strip().split()
    try:
        return (int(parts[2]), int(parts[1]))
    except:
        return (0, 0)

def to_float(v):
    if not v or str(v).strip() in ["-", ":", "..."]:
        return None
    try:
        return float(str(v).replace(".", "").replace(",", ".").strip())
    except:
        return None

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_new_months(existing):
    """Returneaza lista de luni lipsa fata de JSON-ul existent."""
    ultima_key = (0, 0)
    for vals in existing.get("date", {}).values():
        for d in vals:
            k = parse_luna_json(d.get("luna", ""))
            if k > ultima_key:
                ultima_key = k
    return ultima_key

def scrape_with_playwright(missing_months_keys):
    """
    Deschide TEMPO-Online, selecteaza LOC108A, selecteaza lunile lipsa
    una cate una si extrage datele din tabel.
    Returneaza dict: {luna_label: {categorie: valoare}}
    """
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ro-RO"
        )
        page = context.new_page()

        # Interceptam request-urile API pentru a captura datele JSON direct
        api_responses = []

        def handle_response(response):
            if "dataSet/LOC108A" in response.url or "matrix/dataSet" in response.url:
                try:
                    data = response.json()
                    api_responses.append(data)
                    print(f"  [API] Capturat raspuns de la: {response.url[:80]}")
                except:
                    pass

        page.on("response", handle_response)

        print(f"  → Deschid TEMPO-Online...")
        page.goto(INSSE_URL, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Cauta LOC108A
        print(f"  → Caut LOC108A...")
        try:
            search_input = page.locator("input[placeholder*='auta'], input[type='search'], input[placeholder*='earch']").first
            search_input.fill("LOC108A")
            page.wait_for_timeout(1000)

            # Apasa Enter sau buton search
            search_input.press("Enter")
            page.wait_for_timeout(2000)
        except:
            print("  → Input cautare negasit, incerc navigare directa...")

        # Incearca sa gaseasca si sa clickeze pe LOC108A
        try:
            loc_link = page.locator("text=LOC108A").first
            loc_link.click(timeout=10000)
            page.wait_for_timeout(3000)
        except:
            print("  → Link LOC108A negasit direct")

        print(f"  → URL curent: {page.url[:80]}")

        # Asteapta sa apara filtrele (checkboxuri cu categorii)
        try:
            page.wait_for_selector("text=Categorii de constructii", timeout=15000)
            print("  ✓ Pagina LOC108A incarcata")
        except PlaywrightTimeout:
            print("  ✗ Timeout asteptand pagina LOC108A")
            # Screenshot pentru debug
            page.screenshot(path="/tmp/debug_screenshot.png")
            browser.close()
            return {}

        # Procesam fiecare luna lipsa
        for luna_key in missing_months_keys:
            an, luna_nr = luna_key
            # Gasim label-ul lunii in romana
            luna_ro = {v: k for k, v in LUNI_RO.items()}.get(luna_nr, str(luna_nr))
            luna_label = f"Luna {luna_ro} {an}"
            print(f"\n  === Procesez: {luna_label} ===")

            # Debifam toate lunile selectate
            try:
                # Gasim checkboxurile din coloana Perioade
                perioade_section = page.locator("text=Perioade").locator("..")
                checked_boxes = page.locator("input[type='checkbox']:checked")
                count = checked_boxes.count()
                print(f"  → {count} checkboxuri bifate")
            except:
                pass

            # Selectam: toate categoriile, Total mediu, TOTAL regiune, luna noua, mp suprafata
            # Mai intai deselect tot si reselect ce vrem
            try:
                # Bifam luna dorita
                luna_checkbox = page.locator(f"text={luna_label}").locator("..").locator("input[type='checkbox']")
                if luna_checkbox.count() > 0:
                    # Debifam Anul curent daca e bifat
                    an_checkbox = page.locator(f"text=Anul {an}").locator("..").locator("input[type='checkbox']")
                    if an_checkbox.is_checked():
                        an_checkbox.uncheck()

                    luna_checkbox.check()
                    print(f"  ✓ Bifat: {luna_label}")
                else:
                    print(f"  ✗ Checkbox negasit pentru {luna_label}")
                    continue
            except Exception as e:
                print(f"  ✗ Eroare bifat luna: {e}")
                continue

            # Apasam CAUTA
            api_responses.clear()
            try:
                cauta_btn = page.locator("button:has-text('CAUTA'), button:has-text('Cauta'), button:has-text('CĂUTA')").first
                cauta_btn.click()
                print("  → Apasam CAUTA...")

                # Asteptam raspunsul API
                page.wait_for_timeout(5000)
            except Exception as e:
                print(f"  ✗ Eroare CAUTA: {e}")
                continue

            # Extragem datele din tabel sau din API response capturat
            if api_responses:
                print(f"  ✓ {len(api_responses)} raspunsuri API capturate")
                raw = api_responses[-1]
                if isinstance(raw, dict):
                    raw = raw.get("data", raw.get("matrixData", []))

                results[luna_label] = {}
                # raw[0] = prima categorie, raw[1] = a doua, etc.
                # Categoriile sunt in ordinea din tabel
                print(f"  Raw sample: {str(raw)[:200]}")
            else:
                # Extragem din DOM
                print("  → Nu s-a capturat API, extrag din DOM...")
                try:
                    rows = page.locator("table tbody tr").all()
                    print(f"  → {len(rows)} randuri in tabel")
                    results[luna_label] = {}
                    for row in rows[:10]:
                        cells = row.locator("td").all()
                        if len(cells) >= 2:
                            cat = cells[0].inner_text().strip()
                            val_text = cells[-1].inner_text().strip()
                            val = to_float(val_text)
                            if cat and val is not None:
                                results[luna_label][cat] = val
                                print(f"     {cat[:40]}: {val}")
                except Exception as e:
                    print(f"  ✗ Eroare extragere DOM: {e}")

        browser.close()

    return results

def main():
    print(f"[{datetime.now().isoformat()}] Start LOC108A cu Playwright...")
    existing = load_existing()
    ultima_key = get_new_months(existing)
    print(f"  Ultima luna JSON: an={ultima_key[0]}, luna={ultima_key[1]}")

    # Calculam ce luni sunt lipsa (maxim ultimele 3 luni ca sa nu fie prea lung)
    now = datetime.now()
    missing_keys = []
    for an in range(ultima_key[0], now.year + 1):
        start_luna = ultima_key[1] + 1 if an == ultima_key[0] else 1
        end_luna = now.month if an == now.year else 12
        for luna in range(start_luna, end_luna + 1):
            missing_keys.append((an, luna))

    # Limitam la 3 luni per rulare
    missing_keys = missing_keys[:3]
    print(f"  Luni de verificat: {missing_keys}")

    if not missing_keys:
        print("Datele sunt la zi. Modificat: false")
        return

    results = scrape_with_playwright(missing_keys)

    if not results:
        print("Nu s-au obtinut date noi. Modificat: false")
        return

    date_out = existing.get("date", {})
    cats_out = existing.get("categorii", [])
    adaugat = False

    for luna_label, cat_vals in results.items():
        for cat, val in cat_vals.items():
            if cat not in date_out:
                date_out[cat] = []
            if cat not in cats_out:
                cats_out.append(cat)
            existing_luni = [d["luna"] for d in date_out[cat]]
            if luna_label not in existing_luni:
                date_out[cat].append({"luna": luna_label, "valoare": val})
                adaugat = True
                print(f"  + {cat[:40]}: {val} ({luna_label})")

    if not adaugat:
        print("Nu s-au adaugat date noi. Modificat: false")
        return

    for cat in date_out:
        date_out[cat].sort(key=lambda d: parse_luna(d.get("luna", "")))

    toate = sorted(
        {d["luna"] for v in date_out.values() for d in v},
        key=parse_luna
    )

    save_json({
        **existing,
        "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
        "categorii": cats_out,
        "perioade": toate,
        "date": date_out
    })
    print(f"\n✅ Salvat! Ultima luna: {toate[-1] if toate else '?'}")
    print("Modificat: true")

if __name__ == "__main__":
    main()
