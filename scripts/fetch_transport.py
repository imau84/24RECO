import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

def fetch_clase_transportatori():
    all_data = []
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        responses = []

        def handle_response(response):
            if "GetListaClase" in response.url:
                try:
                    data = response.json()
                    responses.append(data)
                except:
                    pass

        page.on("response", handle_response)

        print("Deschid pagina...")
        page.goto("https://www.autorizatiiauto.ro/Marfa/ListaClase", wait_until="networkidle", timeout=60000)
        print("Pagina incarcata.")

        if responses:
            data = responses[0]
            all_data = data.get("Data", [])
            total = data.get("Total", 0)
            print(f"Date gasite: {len(all_data)} (total: {total})")
        else:
            print("Nu s-au prins raspunsuri API.")

        browser.close()

    return all_data, total

def save():
    os.makedirs("src/data/transport", exist_ok=True)
    data, total = fetch_clase_transportatori()
    output = {
        "sursa": "autorizatiiauto.ro",
        "actualizat": datetime.now().strftime("%Y-%m-%d"),
        "total": total,
        "date": data
    }
    with open("src/data/transport/clase_transportatori.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Salvat {len(data)} inregistrari")

if __name__ == "__main__":
    save()
