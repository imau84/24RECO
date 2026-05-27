#!/usr/bin/env python3
"""Script debug v8 - cauta in div-uri si salveaza HTML complet"""

import sys
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://brm.ro/cotatii-cereale/"

def main():
    print(f"debug v8 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        try:
            page.get_by_text("Cotații săptămânale").first.click()
            page.wait_for_timeout(2000)
        except:
            pass

        # Salvam HTML-ul complet al paginii
        html = page.content()
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML salvat: {len(html)} chars")

        # Cautam SAPTAMANA in tot HTML-ul
        import re
        matches = re.findall(r'.{0,50}SAPTAMANA.{0,100}', html, re.IGNORECASE)
        print(f"Aparitii 'SAPTAMANA' in HTML: {len(matches)}")
        for m in matches[:5]:
            print(f"  >> {m}")

        # Cautam VEST/EST/SUD
        matches2 = re.findall(r'.{0,20}(?:VEST|EST|SUD).{0,100}', html)
        print(f"\nAparitii VEST/EST/SUD in HTML: {len(matches2)}")
        for m in matches2[:5]:
            print(f"  >> {m}")

        # Text complet
        full_text = page.inner_text("body")
        with open("debug_text.txt", "w", encoding="utf-8") as f:
            f.write(full_text)
        
        # Cautam in text
        lines_with_sap = [l for l in full_text.split('\n') if 'SAPTAMANA' in l.upper() or 'VEST' in l.upper() or 'EST' in l.upper()]
        print(f"\nLinii relevante din text ({len(lines_with_sap)}):")
        for l in lines_with_sap[:20]:
            print(f"  {repr(l)}")

        browser.close()
    
    # Salvam debug compact
    with open("debug_brm.json", "w", encoding="utf-8") as f:
        json.dump({"lines": lines_with_sap[:50]}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
