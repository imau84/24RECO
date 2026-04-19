import requests
import json
import os
from datetime import datetime

def fetch_clase_transportatori():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    })

    # Obtine cookie de sesiune
    session.get("https://www.autorizatiiauto.ro/Marfa/ListaClase", timeout=30)

    url = "https://www.autorizatiiauto.ro/Marfa/ListaClase/GetListaClase"
    all_data = []
    page = 1

    while True:
        params = {
            "ListaClaseTransportator-page": page,
            "ListaClaseTransportator-pageSize": 100,
        }
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.autorizatiiauto.ro/Marfa/ListaClase",
        }
        r = session.get(url, params=params, headers=headers, timeout=30)
        print(f"Status pagina {page}: {r.status_code}")

        if r.status_code != 200:
            print(f"Eroare: {r.text[:500]}")
            break

        data = r.json()
        items = data.get("Data", [])
        if not items:
            print("Nu mai sunt date.")
            break

        all_data.extend(items)
        total = data.get("Total", 0)
        print(f"Pagina {page}: {len(items)} items (total: {total})")

        if len(all_data) >= total:
            break
        page += 1

    return all_data, data.get("Total", 0) if all_data else ([], 0)

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
