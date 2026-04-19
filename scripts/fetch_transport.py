import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

CLASE = [
    {"id": 1, "nume": "operatori_mici"},
    {"id": 2, "nume": "operatori_medii_1"},
    {"id": 3, "nume": "operatori_medii_2"},
    {"id": 4, "nume": "operatori_mari"},
]

def fetch_clasa(context, clasa_id, clasa_nume):
    print(f"Fetch {clasa_nume} (clasaId={clasa_id})...")

    # Obtine sesiune vizitand pagina principala
    page = context.new_page()
    page.goto("https://www.autorizatiiauto.ro/Marfa/ListaClase", wait_until="networkidle", timeout=60000)

    # Obtine cookies din sesiune
    cookies = context.cookies()
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    # Extrage requestVerificationToken din pagina
    token = page.evaluate("""
        () => {
            const el = document.querySelector('input[name="__RequestVerificationToken"]');
            return el ? el.value : '';
        }
    """)
    print(f"  Token: {token[:20] if token else 'N/A'}...")
    page.close()

    all_data = []
    page_num = 1

    while True:
        # Folosim API request direct cu sesiunea
        response = context.request.post(
            f"https://www.autorizatiiauto.ro/Marfa/ListaClase/GetListaClaseOperator?clasaId={clasa_id}",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.autorizatiiauto.ro/Marfa/ListaClase/Detail",
            },
            form={
                "sort": "DenumireOperator-asc",
                "page": str(page_num),
                "pageSize": "100",
                "group": "",
                "filter": "",
            }
        )

        print(f"  Status pagina {page_num}: {response.status}")

        if response.status != 200:
            print(f"  Eroare: {response.text()[:200]}")
            break

        result = response.json()
        items = result.get("Data", [])

        if not items:
            print(f"  Pagina {page_num}: 0 items, stop.")
            break

        all_data.extend(items)
        total = result.get("Total", 0)
        print(f"  Pagina {page_num}: {len(items)} items (total: {total})")

        if len(all_data) >= total:
            break
        page_num += 1

    return all_data

def save():
    os.makedirs("src/data/transport", exist_ok=True)
    toate_datele = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )

        for clasa in CLASE:
            data = fetch_clasa(context, clasa["id"], clasa["nume"])
            toate_datele[clasa["nume"]] = data
            print(f"Total {clasa['nume']}: {len(data)} operatori")

        browser.close()

    output = {
        "sursa": "autorizatiiauto.ro",
        "actualizat": datetime.now().strftime("%Y-%m-%d"),
        "date": toate_datele
    }

    with open("src/data/transport/clase_transportatori.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in toate_datele.values())
    print(f"Salvat {total} operatori in total")

if __name__ == "__main__":
    save()
