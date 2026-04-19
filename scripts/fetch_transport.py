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

def fetch_clasa(page, clasa_id, clasa_nume):
    print(f"Fetch {clasa_nume} (clasaId={clasa_id})...")

    # Navigam la pagina Detail pentru aceasta clasa
    page.goto("https://www.autorizatiiauto.ro/Marfa/ListaClase", wait_until="networkidle", timeout=60000)

    # Submit form pentru a obtine sesiunea cu clasa corecta
    page.evaluate(f"""
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/Marfa/ListaClase/Detail';
        const input = document.createElement('input');
        input.name = 'clasaId';
        input.value = '{clasa_id}';
        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
    """)
    page.wait_for_load_state("networkidle", timeout=30000)

    all_data = []
    page_num = 1

    while True:
        result = page.evaluate(f"""
            async () => {{
                const formData = new URLSearchParams();
                formData.append('sort', 'DenumireOperator-asc');
                formData.append('page', '{page_num}');
                formData.append('pageSize', '100');
                formData.append('group', '');
                formData.append('filter', '');

                const r = await fetch('/Marfa/ListaClase/GetListaClaseOperator?clasaId={clasa_id}', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest'
                    }},
                    body: formData.toString()
                }});
                return await r.json();
            }}
        """)

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
        page = context.new_page()

        for clasa in CLASE:
            data = fetch_clasa(page, clasa["id"], clasa["nume"])
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
