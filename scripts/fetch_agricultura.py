#!/usr/bin/env python3
"""Script debug v9 - interceptam request-urile de retea"""

import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://brm.ro/cotatii-cereale/"

def main():
    print(f"debug v9 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    network_requests = []
    response_bodies = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        page = context.new_page()

        # Interceptam toate request-urile
        def on_request(request):
            url = request.url
            if any(x in url.lower() for x in ['cereale', 'cotatii', 'ajax', 'api', 'data', 'json', 'wp-admin', 'wp-content']):
                network_requests.append({"url": url, "method": request.method})
                print(f"REQ: {request.method} {url[:120]}")

        def on_response(response):
            url = response.url
            if any(x in url.lower() for x in ['cereale', 'cotatii', 'ajax', 'api', 'json']):
                try:
                    body = response.text()
                    if len(body) > 100:
                        response_bodies[url] = body[:2000]
                        print(f"RESP ({len(body)} chars): {url[:100]}")
                        print(f"  BODY: {body[:300]}")
                except:
                    pass

        page.on("request", on_request)
        page.on("response", on_response)

        print(f"📡 Navigare la {URL}")
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)

        # Click pe tab
        try:
            page.get_by_text("Cotații săptămânale").first.click()
            page.wait_for_timeout(3000)
            print("✅ click tab")
        except Exception as e:
            print(f"no tab: {e}")

        # Toate URL-urile
        print(f"\n=== TOATE REQUEST-URILE ({len(network_requests)}) ===")
        for r in network_requests:
            print(f"  {r['method']} {r['url']}")

        # Salvam
        debug = {
            "requests": network_requests,
            "responses": {k: v[:500] for k, v in response_bodies.items()}
        }
        with open("debug_brm.json", "w", encoding="utf-8") as f:
            json.dump(debug, f, ensure_ascii=False, indent=2)

        # Incercam si iframe-uri
        frames = page.frames
        print(f"\n=== FRAMES ({len(frames)}) ===")
        for i, frame in enumerate(frames):
            print(f"  Frame {i}: {frame.url}")
            try:
                txt = frame.inner_text("body")
                if 'SAPTAMANA' in txt.upper() or 'VEST' in txt.upper():
                    print(f"    *** DATE GASITE IN FRAME {i}! ***")
                    print(txt[:1000])
                    with open(f"debug_frame_{i}.txt", "w", encoding="utf-8") as f:
                        f.write(txt)
            except:
                pass

        browser.close()

if __name__ == "__main__":
    main()
