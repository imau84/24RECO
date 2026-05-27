#!/usr/bin/env python3
"""Script debug v11 - cautam TablePress in HTML raw"""

import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://brm.ro/cotatii-cereale/"

def main():
    print(f"debug v11 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        # Scroll pe toata pagina sa triggeram lazy load
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # Luam HTML-ul complet
        html = page.content()

        # Cautam tablepress
        tp_matches = re.findall(r'tablepress[^>]{0,200}', html, re.IGNORECASE)
        print(f"TablePress mentions: {len(tp_matches)}")
        for m in tp_matches[:5]:
            print(f"  {m[:150]}")

        # Cautam SAPTAMANA in HTML
        sap_matches = re.findall(r'.{0,100}SAPTAMANA.{0,200}', html, re.IGNORECASE)
        print(f"\nSAPTAMANA in HTML: {len(sap_matches)}")
        for m in sap_matches[:5]:
            print(f"  {m[:200]}")

        # Cautam numerele de cotatie (ex: 957, 1079) in context
        price_matches = re.findall(r'<td[^>]*>\s*(\d{3,4})\s*</td>', html)
        print(f"\nNumerice in <td>: {price_matches[:30]}")

        # Salvam o portiune din HTML cu tabele
        table_section = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL | re.IGNORECASE)
        print(f"\nTabele in HTML: {len(table_section)}")
        for i, t in enumerate(table_section[:3]):
            print(f"\n--- Tabel {i+1} (primele 500 chars) ---")
            print(t[:500])

        # Salvam tot HTML-ul pentru analiza
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        with open("debug_brm.json", "w", encoding="utf-8") as f:
            json.dump({
                "tablepress": tp_matches[:10],
                "saptamana": sap_matches[:10],
                "prices_in_td": price_matches[:50],
                "nr_tables": len(table_section),
                "table_previews": [t[:300] for t in table_section[:5]]
            }, f, ensure_ascii=False, indent=2)

        print(f"\nHTML total: {len(html)} chars")
        browser.close()

if __name__ == "__main__":
    main()
