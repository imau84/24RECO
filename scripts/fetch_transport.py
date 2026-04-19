pythonimport requests
import json
import os
from datetime import datetime

def fetch_clase_transportatori():
    url = "https://www.autorizatiiauto.ro/Marfa/ListaClase/GetListaClase"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.autorizatiiauto.ro/Marfa/ListaClase"
    }
    
    all_data = []
    page = 1
    
    while True:
        params = {
            "ListaClaseTransportator-page": page,
            "ListaClaseTransportator-pageSize": 100,
        }
        r = requests.get(url, params=params, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        items = data.get("Data", [])
        if not items:
            break
        all_data.extend(items)
        
        total = data.get("Total", 0)
        print(f"Pagina {page}: {len(items)} items (total: {total})")
        
        if len(all_data) >= total:
            break
        page += 1
    
    return all_data, data.get("Total", 0)

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
    
    print(f"Salvat {len(data)} inregistrari in src/data/transport/clase_transportatori.json")

if __name__ == "__main__":
    save()
