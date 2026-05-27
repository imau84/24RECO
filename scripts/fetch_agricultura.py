#!/usr/bin/env python3
"""Script debug v7 - salveaza rândurile în fișier"""

import sys
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://brm.ro/cotatii-cereale/"

def main():
    print(f"debug v7 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        try:
            page.get_by_text("Cotații săptămânale").first.click()
            page.wait_for_timeout(2000)
        except:
            pass

        tables = page.query_selector_all("table")
        
        debug_rows = []
        for ti, table in enumerate(tables):
            rows = table.query_selector_all("tr")
            for ri, row in enumerate(rows[:100]):
                cells = [c.inner_text().strip() for c in row.query_selector_all("td,th")]
                if any(c for c in cells if c.strip()):
                    debug_rows.append({"t": ti+1, "r": ri+1, "cells": cells})

        browser.close()

    # Salvam în fișier
    with open("debug_brm.json", "w", encoding="utf-8") as f:
        json.dump(debug_rows, f, ensure_ascii=False, indent=2)
    
    print(f"Salvat {len(debug_rows)} randuri in debug_brm.json")
    
    # Printam primele 30 compact
    for row in debug_rows[:30]:
        print(f"T{row['t']} R{row['r']}: {row['cells']}")

if __name__ == "__main__":
    main()
