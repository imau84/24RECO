#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Navigare exacta confirmata:
1. tempo-online → B. STATISTICA ECONOMICA → LOCUINTE → LOC108A
2. Selecteaza: toate categoriile, Total mediu, TOTAL regiune, luna noua, Metri patrati suprafata utila
3. CAUTA → captura raspuns API sau DOM
"""

import json
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUTPUT_PATH = "src/data/constructii/constructii_data.json"
TEMPO_URL = "http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table"

LUNI_RO = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
    "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
    "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
}

def parse_luna_option(label):
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            an = int(parts[2])
            lp = parts[1]
            return (an, LUNI_RO.get(lp, 0))
        elif parts[0] in ("anul", "an"):
            return (int(parts[1]), 0)
    except: pass
    return (0, 0)

def parse_luna_json(label):
    # "Luna 3 2026" → (2026, 3)
    parts = label.strip().split()
    try: return (int(parts[2]), int(parts[1]))
    except: return (0, 0)

def to_float(v):
    if not v or str(v).strip() in ["-", ":", "...", ""]: return None
    try: return float(str(v).replace(".", "").replace(",", ".").strip())
    except: return None

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_ultima_luna(existing):
    ultima_key = (0, 0)
    for vals in existing.get("date", {}).values():
        for d in vals:
            k = parse_luna_json(d.get("luna", ""))
            if k > ultima_key:
                ultima_key = k
    return ultima_key

def main():
    print(f"[{datetime.now().isoformat()}] Start LOC108A cu Playwright...")
    existing = load_existing()
    ultima_key = get_ultima_luna(existing)
    print(f"  Ultima luna in JSON: an={ultima_key[0]}, luna={ultima_key[1]}")

    date_out = existing.get("date", {})
    cats_out = existing.get("categorii", [])
    adaugat = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ro-RO",
            viewport={"width": 1280, "height": 900}
        )
        page = context.new_page()

        # Capturam raspunsurile API
        api_data = {}  # {luna_label: raw_response}

        def on_response(response):
            url = response.url
            if "dataSet" in url and "LOC108A" in url:
                try:
                    data = response.json()
                    print(f"  [API] Capturat: {url[-50:]}")
                    api_data["last"] = data
                except:
                    pass

        page.on("response", on_response)

        # PASUL 1: Deschide TEMPO-Online
        print("  → Pas 1: Deschid TEMPO-Online...")
        page.goto(TEMPO_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # PASUL 2: Click pe "B. STATISTICA ECONOMICA"
        print("  → Pas 2: Click B. STATISTICA ECONOMICA...")
        try:
            page.click("text=B. STATISTICA ECONOMICA", timeout=10000)
            page.wait_for_timeout(2000)
        except PWTimeout:
            # Incearca varianta cu spatiu diferit
            try:
                page.click("text=STATISTICA ECONOMICA", timeout=5000)
                page.wait_for_timeout(2000)
            except:
                print("  ✗ Nu am gasit B. STATISTICA ECONOMICA")
                page.screenshot(path="debug1.png")

        # PASUL 3: Click pe "LOCUINTE"
        print("  → Pas 3: Click LOCUINTE...")
        try:
            # Gasim link-ul "LOCUINTE" din meniu (nu "CONSTRUCTII" ci sectiunea 10)
            page.click("text=LOCUINTE", timeout=10000)
            page.wait_for_timeout(2000)
        except PWTimeout:
            print("  ✗ Nu am gasit LOCUINTE")
            page.screenshot(path="debug2.png")

        # PASUL 4: Click pe LOC108A
        print("  → Pas 4: Click LOC108A...")
        try:
            page.click("text=LOC108A", timeout=10000)
            page.wait_for_timeout(3000)
        except PWTimeout:
            print("  ✗ Nu am gasit LOC108A")
            page.screenshot(path="debug3.png")
            browser.close()
            return

        # Asteptam sa apara filtrele
        print("  → Astept filtrele LOC108A...")
        try:
            page.wait_for_selector("text=CATEGORII DE CONSTRUCTII", timeout=15000)
            print("  ✓ Filtrele LOC108A sunt vizibile")
        except PWTimeout:
            print("  ✗ Filtrele nu au aparut")
            page.screenshot(path="debug4.png")
            browser.close()
            return

        # Gasim lunile disponibile si le comparam cu ce avem
        print("  → Verific lunile disponibile...")
        
        # Gasim toate checkbox-urile din sectiunea Perioade
        # Dupa structura din screenshot: lista cu "Luna ianuarie 2025", etc.
        luna_checkboxes = page.locator("text=/^Luna (ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie) \\d{4}$/").all()
        
        luni_disponibile = []
        for cb_text in luna_checkboxes:
            label = cb_text.inner_text().strip()
            key = parse_luna_option(label)
            if key[1] > 0:
                luni_disponibile.append((key, label))
        
        print(f"  → {len(luni_disponibile)} luni gasite in UI")
        
        # Luni noi = disponibile la INSSE dar nu in JSON-ul nostru
        luni_noi = [(k, l) for k, l in luni_disponibile if k > ultima_key]
        print(f"  → Luni noi de adaugat: {[l for _, l in luni_noi]}")

        if not luni_noi:
            print("  ✅ Datele sunt la zi. Modificat: false")
            browser.close()
            return

        # Procesam fiecare luna noua
        for luna_key, luna_label in luni_noi:
            print(f"\n  === Procesez: {luna_label} ===")
            api_data.clear()

            # Asiguram selectia corecta:
            # - Toate categoriile (sunt deja bifate implicit)
            # - Medii: Total
            # - Regiuni: TOTAL
            # - Perioade: DOAR luna curenta
            # - UM: Metri patrati suprafata utila

            # 1. Debifam toate lunile bifate si bifam doar luna noua
            print("  → Selectez luna...")
            
            # Debifam "Anul X" daca e bifat
            try:
                an = luna_key[0]
                an_loc = page.locator(f"label:has-text('Anul {an}'), span:has-text('Anul {an}')").first
                parent = an_loc.locator("xpath=../input[@type='checkbox']")
                if parent.count() > 0 and parent.is_checked():
                    parent.uncheck()
                    page.wait_for_timeout(300)
            except: pass

            # Bifam luna noua
            try:
                # Gasim checkbox-ul langa text-ul lunii
                luna_loc = page.locator(f"label:has-text('{luna_label}')").first
                checkbox = luna_loc.locator("xpath=../input[@type='checkbox']")
                if checkbox.count() == 0:
                    # Incearca alt selector
                    checkbox = page.locator(f"input[type='checkbox']").filter(
                        has=page.locator(f"text={luna_label}")
                    ).first
                
                if not checkbox.is_checked():
                    checkbox.check()
                    page.wait_for_timeout(500)
                print(f"  ✓ Bifat: {luna_label}")
            except Exception as e:
                print(f"  ✗ Eroare bifat luna: {e}")
                # Incercam click direct pe text
                try:
                    page.locator(f"text={luna_label}").first.click()
                    page.wait_for_timeout(500)
                    print(f"  ✓ Click direct pe: {luna_label}")
                except Exception as e2:
                    print(f"  ✗ Si click direct a esuat: {e2}")
                    continue

            # 2. UM: Metri patrati suprafata utila (debifam Numar, bifam mp)
            try:
                # Debifam "Numar"
                numar_cb = page.locator("label:has-text('Numar')").locator("xpath=../input[@type='checkbox']").first
                if numar_cb.count() > 0 and numar_cb.is_checked():
                    numar_cb.uncheck()
                    page.wait_for_timeout(200)
                
                # Bifam "Metri patrati suprafata utila"
                mp_cb = page.locator("label:has-text('Metri patrati suprafata utila')").locator("xpath=../input[@type='checkbox']").first
                if mp_cb.count() > 0 and not mp_cb.is_checked():
                    mp_cb.check()
                    page.wait_for_timeout(200)
            except Exception as e:
                print(f"  ⚠ UM selectie: {e}")

            # 3. CAUTA
            print("  → Click CAUTA...")
            try:
                page.click("button:has-text('CAUTA')", timeout=5000)
                page.wait_for_timeout(6000)  # Asteptam raspunsul
            except Exception as e:
                print(f"  ✗ CAUTA: {e}")
                try:
                    page.locator("text=CAUTA").first.click()
                    page.wait_for_timeout(6000)
                except: pass

            # 4. Extragem datele
            if "last" in api_data:
                print("  ✓ Date capturate din API!")
                raw = api_data["last"]
                if isinstance(raw, dict):
                    raw = raw.get("data", raw.get("matrixData", []))
                
                print(f"  Raw tip: {type(raw).__name__}, len={len(raw) if hasattr(raw,'__len__') else '?'}")
                
                # Categoriile din LOC108A (ordinea din UI):
                # 0: Cladiri rezidentiale (exclusiv cele pentru colectivitati)
                # 1: Cladiri rezidentiale pentru colectivitati  
                # 2: Cladiri administrative
                # 3: Alte cladiri (hoteluri si cladiri similare, cladiri ptr comert...)
                # 4: Hoteluri si cladiri similare
                # 5: Cladiri pentru comert cu ridicata si cu amanuntul
                # 6: Alte cladiri
                categorii_insse = [
                    "Cladiri rezidentiale (exclusiv cele pentru colectivitati)",
                    "Cladiri rezidentiale pentru colectivitati",
                    "Cladiri administrative",
                    "Alte cladiri (hoteluri, comert, etc)",
                    "Hoteluri si cladiri similare",
                    "Cladiri pentru comert cu ridicata si cu amanuntul",
                    "Alte cladiri"
                ]

                if isinstance(raw, list):
                    first = raw[0] if raw else None
                    if isinstance(first, list):
                        for ci, row in enumerate(raw):
                            cat = categorii_insse[ci] if ci < len(categorii_insse) else f"Cat{ci}"
                            val_raw = row[0] if row else None
                            val = to_float(val_raw)
                            if cat not in date_out: date_out[cat] = []
                            if cat not in cats_out: cats_out.append(cat)
                            if luna_label not in [d["luna"] for d in date_out[cat]]:
                                date_out[cat].append({"luna": luna_label, "valoare": val})
                                adaugat = True
                                print(f"     + {cat[:45]}: {val}")
                    elif isinstance(first, (int, float, str, type(None))):
                        for ci, val_raw in enumerate(raw):
                            cat = categorii_insse[ci] if ci < len(categorii_insse) else f"Cat{ci}"
                            val = to_float(val_raw)
                            if cat not in date_out: date_out[cat] = []
                            if cat not in cats_out: cats_out.append(cat)
                            if luna_label not in [d["luna"] for d in date_out[cat]]:
                                date_out[cat].append({"luna": luna_label, "valoare": val})
                                adaugat = True
                                print(f"     + {cat[:45]}: {val}")
            else:
                # Fallback: extragem din tabelul DOM
                print("  → API nu capturat, extrag din tabel DOM...")
                try:
                    page.wait_for_selector("table", timeout=5000)
                    rows = page.locator("table tr").all()
                    print(f"  → {len(rows)} randuri in tabel")
                    
                    for ri, row in enumerate(rows):
                        cells = row.locator("td").all()
                        if len(cells) < 2: continue
                        cat_text = cells[0].inner_text().strip()
                        # Ultima coloana = Metri patrati
                        val_text = cells[-1].inner_text().strip()
                        val = to_float(val_text)
                        
                        if not cat_text or cat_text == "-": continue
                        if "MACROREGIUNEA" in cat_text or "Regiunea" in cat_text: continue
                        if cat_text in ["Categorii de constructii", "Medii de rezidenta"]: continue
                        
                        if cat_text not in date_out: date_out[cat_text] = []
                        if cat_text not in cats_out: cats_out.append(cat_text)
                        if luna_label not in [d["luna"] for d in date_out[cat_text]]:
                            date_out[cat_text].append({"luna": luna_label, "valoare": val})
                            adaugat = True
                            print(f"     + {cat_text[:45]}: {val}")
                except Exception as e:
                    print(f"  ✗ Eroare extragere DOM: {e}")

        browser.close()

    if not adaugat:
        print("\n⚠ Nu s-a adaugat nimic nou. Modificat: false")
        return

    # Sortam si salvam
    for cat in date_out:
        date_out[cat].sort(key=lambda d: parse_luna_option(d.get("luna", "")))

    toate = sorted(
        {d["luna"] for v in date_out.values() for d in v},
        key=parse_luna_option
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
