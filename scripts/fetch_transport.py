import requests
import json
import os
from datetime import datetime

def fetch_clase_transportatori():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    })

    print("Obtin sesiune...")
    resp = session.get("https://www.autorizatiiauto.ro/Marfa/ListaClase", timeout=30)
    print(f"Sesiune status: {resp.status_code}")
    print(f"Cookies: {dict(session.cookies)}")

    url = "https://www.autorizatiiauto.ro/Marfa/ListaClase/GetListaClase"
    params = {
        "ListaClaseTransportator-page": 1,
        "ListaClaseTransportator-pageSize": 100,
    }
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.autorizatiiauto.ro/Marfa/ListaClase",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

    r = session.get(url, params=params, headers=headers, timeout=30)
    print(f"API status: {r.status_code}")
    print(f"Raspuns raw (primii 1000 chars): {r.text[:1000]}")

    data = r.json()
    print(f"Keys in raspuns: {list(data.keys())}")
    print(f"Total: {data.get('Total')}")
    print(f"Nr items in Data: {len(data.get('Data', []))}")

    return data.get("Data", []), data.get("Total", 0)

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
