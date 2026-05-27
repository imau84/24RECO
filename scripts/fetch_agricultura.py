#!/usr/bin/env python3
"""Script debug v6 - printam primele 80 randuri din tabel"""

import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://brm.ro/cotatii-cereale/"

def main():
    print(f"🌾 debug v6 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        print(f"📡 {URL}")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Click tab daca exista
        try:
            page.get_by_text("Cotații săptămânale").first.click()
            page.wait_for_timeout(2000)
            print("✅ click tab")
        except:
            print("⚠️ no tab click")

        tables = page.query_selector_all("table")
        print(f"tabele: {len(tables)}")

        for ti, table in enumerate(tables):
            rows = table.query_selector_all("tr")
            print(f"\n=== TABEL {ti+1} ({len(rows)} randuri) ===")
            for ri, row in enumerate(rows[:80]):
                cells = [c.inner_text().strip() for c in row.query_selector_all("td,th")]
                if any(c for c in cells if c.strip()):
                    print(f"R{ri+1}: {cells}")

        browser.close()

if __name__ == "__main__":
    main()
