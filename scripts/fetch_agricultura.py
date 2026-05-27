#!/usr/bin/env python3
"""Script debug v10 - interceptam body-ul request-urilor admin-ajax.php"""

import json
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://brm.ro/cotatii-cereale/"

def main():
    print(f"debug v10 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    ajax_responses = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
        page = context.new_page()

        # Interceptam TOATE response-urile de la admin-ajax.php
        def on_response(response):
            if "admin-ajax" in response.url:
                try:
                    body = response.text()
                    print(f"\n=== AJAX RESPONSE ({len(body)} chars) ===")
                    print(body[:3000])
                    ajax_responses.append({"url": response.url, "body": body[:5000]})
                except Exception as e:
                    print(f"Err reading response: {e}")

        page.on("response", on_response)

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        # Click pe tab
        try:
            page.get_by_text("Cotații săptămânale").first.click()
            page.wait_for_timeout(3000)
            print("✅ click tab")
        except Exception as e:
            print(f"no tab: {e}")

        browser.close()

    with open("debug_brm.json", "w", encoding="utf-8") as f:
        json.dump(ajax_responses, f, ensure_ascii=False, indent=2)
    
    print(f"\nSalvat {len(ajax_responses)} raspunsuri AJAX")

if __name__ == "__main__":
    main()
