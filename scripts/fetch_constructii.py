#!/usr/bin/env python3
"""
Script: fetch_constructii.py
Navigare robusta cu debug screenshots + fallback URL direct.
"""

import json, os, sys, base64
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUTPUT_PATH = "src/data/constructii/constructii_data.json"

# URL direct la pagina LOC108A - evita navigarea prin meniuri
# Structura URL: #/pages/tables/insse-table cu starea matricei in localStorage
TEMPO_URL   = "http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table"
LOC108A_URL = "http://statistici.insse.ro:8077/tempo-online/#/pages/tables/insse-table"

LUNI_RO = {
    "ianuarie":1,"februarie":2,"martie":3,"aprilie":4,
    "mai":5,"iunie":6,"iulie":7,"august":8,
    "septembrie":9,"octombrie":10,"noiembrie":11,"decembrie":12
}

def parse_luna_option(label):
    parts = label.strip().lower().split()
    try:
        if parts[0] == "luna":
            return (int(parts[2]), LUNI_RO.get(parts[1], 0))
        elif parts[0] in ("anul","an"):
            return (int(parts[1]), 0)
    except: pass
    return (0, 0)

def parse_luna_json(label):
    parts = label.strip().split()
    try: return (int(parts[2]), int(parts[1]))
    except: return (0, 0)

def to_float(v):
    if not v or str(v).strip() in ["-",":",""]: return None
    try: return float(str(v).replace(".","").replace(",",".").strip())
    except: return None

def load_existing():
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def screenshot(page, name):
    try:
        path = f"/tmp/debug_{name}.png"
        page.screenshot(path=path, full_page=False)
        print(f"  [screenshot] {path}")
    except: pass

def click_text(page, text, timeout=8000):
    """Incearca mai multe strategii de click pe un text."""
    strategies = [
        lambda: page.click(f"text={text}", timeout=timeout),
        lambda: page.locator(f"span:has-text('{text}')").first.click(timeout=timeout),
        lambda: page.locator(f"a:has-text('{text}')").first.click(timeout=timeout),
        lambda: page.locator(f"li:has-text('{text}')").first.click(timeout=timeout),
        lambda: page.locator(f"div:has-text('{text}')").last.click(timeout=timeout),
    ]
    for i, strategy in enumerate(strategies):
        try:
            strategy()
            return True
        except:
            pass
    return False

def main():
    print(f"[{datetime.now().isoformat()}] Start LOC108A cu Playwright...")
    existing = load_existing()

    ultima_key = (0,0)
    for vals in existing.get("date",{}).values():
        for d in vals:
            k = parse_luna_json(d.get("luna",""))
            if k > ultima_key: ultima_key = k
    print(f"  Ultima luna JSON: an={ultima_key[0]}, luna={ultima_key[1]}")

    date_out = existing.get("date", {})
    cats_out = existing.get("categorii", [])
    adaugat = False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-gpu"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="ro-RO",
            viewport={"width":1400,"height":900}
        )
        page = context.new_page()

        # Capturam API responses
        api_data = {}
        def on_response(response):
            if "dataSet" in response.url:
                try:
                    api_data["last"] = response.json()
                    print(f"  [API] {response.url[-60:]}")
                except: pass
        page.on("response", on_response)

        # PASUL 1: Incarca pagina principala
        print("  → Incarc TEMPO-Online...")
        page.goto(TEMPO_URL, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(2000)
        screenshot(page, "01_home")

        # Analizam DOM-ul pentru a gasi elementele corecte
        print("  → Analizez structura paginii...")
        visible_text = page.evaluate("""() => {
            const els = document.querySelectorAll('a, span, li, div');
            const texts = [];
            for (const el of els) {
                const t = el.innerText?.trim();
                if (t && t.length > 3 && t.length < 50 && !texts.includes(t)) {
                    texts.push(t);
                }
            }
            return texts.slice(0, 50);
        }""")
        print(f"  Texte vizibile: {visible_text[:20]}")

        # PASUL 2: Navigam la LOC108A
        # Strategia 1: Click pe "B. STATISTICA ECONOMICA" sau variante
        print("  → Navigare spre LOC108A...")
        
        navigat = False
        
        # Incercam sa gasim si sa clickam pe "B. STATISTICA ECONOMICA"
        stat_eco_texts = [
            "B. STATISTICA ECONOMICA",
            "B.STATISTICA ECONOMICA", 
            "STATISTICA ECONOMICA",
            "B. Statistica Economica",
            "Statistica economica"
        ]
        
        for text in stat_eco_texts:
            try:
                el = page.locator(f"text='{text}'").first
                if el.count() > 0:
                    el.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    print(f"  ✓ Click pe: {text}")
                    navigat = True
                    break
            except: pass

        if not navigat:
            # Incercam JavaScript click pe elementul care contine textul
            result = page.evaluate("""() => {
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    if (el.childNodes.length === 1 && 
                        el.textContent?.includes('STATISTICA ECONOMICA')) {
                        el.click();
                        return el.tagName + ': ' + el.textContent?.trim().substring(0, 50);
                    }
                }
                return 'not found';
            }""")
            print(f"  → JS click result: {result}")
            page.wait_for_timeout(2000)

        screenshot(page, "02_after_stat_eco")

        # PASUL 3: Click pe LOCUINTE
        locuinte_texts = ["LOCUINTE", "Locuinte", "B.10 LOCUINTE", "10. LOCUINTE"]
        for text in locuinte_texts:
            try:
                el = page.locator(f"text='{text}'").first
                if el.count() > 0:
                    el.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    print(f"  ✓ Click pe: {text}")
                    break
            except: pass

        # JS fallback pentru LOCUINTE
        result = page.evaluate("""() => {
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                const t = el.textContent?.trim();
                if (t === 'LOCUINTE' || t === '1. LOCUINTE') {
                    el.click();
                    return 'clicked: ' + t;
                }
            }
            return 'not found';
        }""")
        print(f"  → LOCUINTE JS: {result}")
        page.wait_for_timeout(2000)
        screenshot(page, "03_after_locuinte")

        # PASUL 4: Click pe LOC108A
        result = page.evaluate("""() => {
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                if (el.textContent?.startsWith('LOC108A')) {
                    el.click();
                    return 'clicked: ' + el.textContent?.trim().substring(0, 80);
                }
            }
            return 'not found';
        }""")
        print(f"  → LOC108A JS: {result}")
        page.wait_for_timeout(4000)
        screenshot(page, "04_after_loc108a")

        # Verificam daca suntem pe pagina cu filtre
        page_text = page.evaluate("() => document.body.innerText?.substring(0, 500)")
        print(f"  Pagina curenta (primele 300 chars): {page_text[:300]}")

        # Asteptam filtrele
        try:
            page.wait_for_selector("text=CATEGORII DE CONSTRUCTII", timeout=10000)
            print("  ✓ Filtrele LOC108A sunt vizibile!")
        except PWTimeout:
            # Incercam URL direct cu hash navigation
            print("  ✗ Filtrele nu apar, incerc navigare alternativa...")
            
            # Poate pagina foloseste un alt pattern - incercam sa vedem toate link-urile
            links = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a, [ng-click], [onclick]'))
                    .map(el => ({
                        tag: el.tagName,
                        text: el.textContent?.trim().substring(0, 60),
                        href: el.href || el.getAttribute('ng-click') || ''
                    }))
                    .filter(l => l.text?.length > 2)
                    .slice(0, 30);
            }""")
            print(f"  Linkuri gasite: {links[:10]}")
            screenshot(page, "05_debug_links")
            browser.close()
            return

        # PASUL 5: Selectam filtrele
        print("\n  → Selectez filtrele...")

        # Gasim toate luna-labels disponibile
        all_luna_labels = page.evaluate("""() => {
            const labels = [];
            document.querySelectorAll('label, span, div').forEach(el => {
                const t = el.textContent?.trim();
                if (t?.startsWith('Luna ') && t.split(' ').length === 3) {
                    labels.push(t);
                }
            });
            return [...new Set(labels)];
        }""")
        print(f"  Luni gasite in UI: {len(all_luna_labels)}, ultimele 3: {all_luna_labels[-3:] if all_luna_labels else []}")

        luni_noi = [l for l in all_luna_labels if parse_luna_option(l) > ultima_key and parse_luna_option(l)[1] > 0]
        print(f"  Luni noi: {luni_noi}")

        if not luni_noi:
            print("  ✅ Datele sunt la zi.")
            browser.close()
            return

        for luna_label in luni_noi:
            print(f"\n  === {luna_label} ===")
            api_data.clear()

            # Deselectam orice luna bifata si selectam luna noua
            # Folosim JavaScript pentru robustete
            result = page.evaluate(f"""() => {{
                const target = '{luna_label}';
                // Debifam toate lunile
                document.querySelectorAll('input[type=checkbox]').forEach(cb => {{
                    const label = cb.closest('label') || cb.parentElement;
                    const text = label?.textContent?.trim() || '';
                    if (text.startsWith('Luna ') || text.startsWith('Anul ')) {{
                        if (cb.checked) cb.click();
                    }}
                }});
                // Bifam luna dorita
                let found = false;
                document.querySelectorAll('input[type=checkbox]').forEach(cb => {{
                    const label = cb.closest('label') || cb.parentElement;
                    const text = label?.textContent?.trim() || '';
                    if (text === target && !cb.checked) {{
                        cb.click();
                        found = true;
                    }}
                }});
                return found ? 'bifat: ' + target : 'negasit: ' + target;
            }}""")
            print(f"  Luna: {result}")
            page.wait_for_timeout(500)

            # UM: Metri patrati
            result = page.evaluate("""() => {
                let ok = '';
                document.querySelectorAll('input[type=checkbox]').forEach(cb => {
                    const label = cb.closest('label') || cb.parentElement;
                    const text = label?.textContent?.trim() || '';
                    if (text.includes('Numar') && !text.includes('Metri') && cb.checked) {
                        cb.click();
                        ok += 'debifat Numar; ';
                    }
                    if (text.includes('Metri patrati') && !cb.checked) {
                        cb.click();
                        ok += 'bifat Metri patrati; ';
                    }
                });
                return ok || 'UM neschimbat';
            }""")
            print(f"  UM: {result}")
            page.wait_for_timeout(300)

            # CAUTA
            result = page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent?.trim().toUpperCase().includes('CAUTA')) {
                        btn.click();
                        return 'click CAUTA';
                    }
                }
                return 'buton negasit';
            }""")
            print(f"  CAUTA: {result}")
            page.wait_for_timeout(6000)
            screenshot(page, f"06_results_{luna_label.replace(' ','_')}")

            # Extragem date
            if "last" in api_data:
                print("  ✓ Date din API!")
                raw = api_data["last"]
                if isinstance(raw, dict):
                    raw = raw.get("data", raw.get("matrixData", []))
                print(f"  Raw: {type(raw).__name__}, len={len(raw) if hasattr(raw,'__len__') else '?'}")
                if raw: print(f"  Sample[0]: {str(raw[0])[:150]}")

                categorii_insse = [
                    "Cladiri rezidentiale (exclusiv cele pentru colectivitati)",
                    "Cladiri rezidentiale pentru colectivitati",
                    "Cladiri administrative",
                    "Alte cladiri (hoteluri, comert, etc)",
                    "Hoteluri si cladiri similare",
                    "Cladiri pentru comert cu ridicata si cu amanuntul",
                    "Alte cladiri"
                ]

                if isinstance(raw, list) and raw:
                    items = raw[0] if isinstance(raw[0], list) else raw
                    for ci, val_raw in enumerate(items):
                        cat = categorii_insse[ci] if ci < len(categorii_insse) else f"Cat{ci}"
                        val = to_float(val_raw)
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            adaugat = True
                            print(f"     + {cat[:45]}: {val}")
            else:
                # DOM fallback
                print("  → Extrag din tabel DOM...")
                try:
                    rows_data = page.evaluate("""() => {
                        const rows = [];
                        document.querySelectorAll('table tr').forEach(tr => {
                            const cells = Array.from(tr.querySelectorAll('td'));
                            if (cells.length >= 2) {
                                rows.push(cells.map(c => c.innerText?.trim()));
                            }
                        });
                        return rows.slice(0, 20);
                    }""")
                    print(f"  Randuri tabel: {rows_data[:5]}")
                    
                    for row in rows_data:
                        if len(row) < 2: continue
                        cat = row[0]
                        val = to_float(row[-1])
                        if not cat or cat == "-" or "MACROREGIUNEA" in cat: continue
                        if cat not in date_out: date_out[cat] = []
                        if cat not in cats_out: cats_out.append(cat)
                        if luna_label not in [d["luna"] for d in date_out[cat]]:
                            date_out[cat].append({"luna": luna_label, "valoare": val})
                            adaugat = True
                            print(f"     + {cat[:45]}: {val}")
                except Exception as e:
                    print(f"  ✗ DOM: {e}")

        browser.close()

    if not adaugat:
        print("\n⚠ Nu s-a adaugat nimic. Modificat: false")
        return

    for cat in date_out:
        date_out[cat].sort(key=lambda d: parse_luna_option(d.get("luna","")))

    toate = sorted(
        {d["luna"] for v in date_out.values() for d in v},
        key=parse_luna_option
    )

    save_json({**existing,
        "ultima_actualizare": datetime.now().strftime("%Y-%m-%d"),
        "categorii": cats_out,
        "perioade": toate,
        "date": date_out
    })
    print(f"\n✅ Salvat! Ultima luna: {toate[-1] if toate else '?'}")
    print("Modificat: true")

if __name__ == "__main__":
    main()
