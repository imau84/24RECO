"""
Fetch automat pentru pagina "Execuție Bugetară" (Ministerul Finanțelor).

Descarcă lunar fișierul "Sinteza" (Anexa2_bgc<DDMM><YYYY>.xlsx), publicat de
mfinante.gov.ro, extrage valorile cumulate (an curent vs. an precedent,
aceeași perioadă) și calculează valoarea lunii respective prin diferență
față de luna anterioară deja stocată în JSON.

Rulează săptămânal prin GitHub Actions (vezi update-executie-bugetara.yml).
Dacă nu există o lună nouă publicată, scriptul nu modifică nimic.
"""

import json
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://mfinante.gov.ro/static/10/Mfp/buletin/executii/Anexa2_bgc{day:02d}{month:02d}{year}.xlsx"
DATA_PATH = Path("public/executie-bugetara_data.json")
MONTH_KEYS = ["ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct", "nov", "dec"]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"}


def candidate_urls(max_months_back: int = 3):
    """Generează URL-uri candidate pentru ultimele luni (cea mai recentă întâi)."""
    today = date.today()
    y, m = today.year, today.month
    for _ in range(max_months_back):
        last_day = monthrange(y, m)[1]
        yield y, m, BASE_URL.format(day=last_day, month=m, year=y)
        m -= 1
        if m == 0:
            m = 12
            y -= 1


def download_xlsx(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and r.content[:2] == b"PK":  # xlsx = zip
            return r.content
    except requests.RequestException:
        pass
    return None


def parse_sinteza(xlsx_bytes: bytes) -> dict:
    """Returnează {label: (prevYearLei, curYearLei)} din foaia 'Sinteza - An 2'."""
    import openpyxl
    from io import BytesIO

    wb = openpyxl.load_workbook(BytesIO(xlsx_bytes), data_only=True)
    ws = wb["Sinteza - An 2"]
    out = {}
    for row in ws.iter_rows(values_only=True):
        if not row or not row[0]:
            continue
        label = str(row[0]).replace("\r", " ").replace("\n", " ")
        label = " ".join(label.split()).strip()
        if not label or label == "PIB" or label.startswith("Realiz"):
            continue
        prev_lei = row[1] if isinstance(row[1], (int, float)) else None
        cur_lei = row[6] if len(row) > 6 and isinstance(row[6], (int, float)) else None
        if prev_lei is None and cur_lei is None:
            continue
        out[label] = (round(prev_lei, 2) if prev_lei is not None else None,
                       round(cur_lei, 2) if cur_lei is not None else None)
    return out


# Mapare etichetă curată (folosită în JSON-ul site-ului) -> etichetă(e) brute din Excel.
# Etichetele cu mai multe surse (ex. "Alte sume UE") se însumează.
LABEL_MAP = {
    "VENITURI TOTALE": ["VENITURI TOTALE"],
    "Venituri curente": ["Venituri curente"],
    "Venituri fiscale": ["Venituri fiscale"],
    "Impozit profit, salarii, venit": ["Impozitul pe profit, salarii, venit si castiguri din capital"],
    "Impozitul pe profit": ["Impozitul pe profit"],
    "Impozitul pe salarii și venit": ["Impozitul pe salarii si venit"],
    "Alte impozite pe venit/profit": ["Alte impozite pe venit, profit si castiguri din capital"],
    "Impozite și taxe pe proprietate": ["Impozite si taxe pe proprietate"],
    "Impozite și taxe bunuri și servicii": ["Impozite si taxe pe bunuri si servicii"],
    "TVA": ["TVA"],
    "Accize": ["Accize"],
    "Alte impozite bunuri și servicii": ["Alte impozite si taxe pe bunuri si servicii"],
    "Taxe utilizare bunuri": ["Taxe pe utilizarea bunurilor, autorizarea utilizarii bunurilor sau pe desfasurarea de activitati"],
    "Taxe vamale": ["Impozit pe comertul exterior si tranzactiile internationale (taxe vamale)"],
    "Alte impozite și taxe fiscale": ["Alte impozite si taxe fiscale"],
    "Contribuții de asigurări": ["Contributii de asigurari"],
    "Venituri nefiscale": ["Venituri nefiscale"],
    "Venituri din capital": ["Venituri din capital"],
    "Donații": ["Donatii"],
    "Sume primite UE (prefinanțări)": ["Sume primite de la UE/alti donatori in contul platilor efectuate si prefinantari"],
    "Sume în curs de distribuire": ["Sume in curs de distribuire"],
    "Alte sume UE (incl. 2014–2020)": [
        "Alte sume primite de la UE",
        "Sume primite de la UE/alti donatori in contul platilor efectuate si prefinantari aferente cadrului financiar 2014-2020",
    ],
    "PNRR nerambursabil": ["Sume aferente asistentei financiare nerambursabile alocate pentru PNRR"],
    "CHELTUIELI TOTALE": ["CHELTUIELI TOTALE"],
    "Cheltuieli curente": ["Cheltuieli curente"],
    "Cheltuieli de personal": ["Cheltuieli de personal"],
    "Bunuri și servicii": ["Bunuri si servicii"],
    "Dobânzi": ["Dobanzi"],
    "Subvenții": ["Subventii cheltuieli", "Subventii"],  # numele poate apărea fără sufix in unele fișiere
    "Transferuri între unități adm. pub.": ["Transferuri intre unitati ale administratiei publice"],
    "Alte transferuri": ["Alte transferuri"],
    "Proiecte fonduri externe nerambursabile": ["Proiecte cu finantare din fonduri externe nerambursabile"],
    "Asistență socială": ["Asistenta sociala"],
    "Proiecte FEN 2014–2020": [
        "Proiecte cu finantare din fonduri externe nerambursabile aferente cadrului financiar 2014-2020 si din fondul de modernizare"
    ],
    "Alte cheltuieli": ["Alte cheltuieli"],
    "Proiecte PNRR nerambursabil": ["Proiecte cu finantare din sumele reprezentand asistenta financiara nerambursabila aferenta PNRR"],
    "Proiecte PNRR împrumut": ["Proiecte cu finantare din sumele aferente componentei de imprumut a PNRR"],
    "Programe finanțare rambursabilă": ["Cheltuieli aferente programelor cu finantare rambursabila"],
    "Cheltuieli de capital": ["Cheltuieli de capital"],
    "Plăți recuperate ani precedenți": ["Plati efectuate in anii precedenti si recuperate in anul curent"],
    "EXCEDENT / DEFICIT": ["EXCEDENT(+) / DEFICIT(-)"],
}


def sum_raw(raw: dict, labels: list[str], idx: int) -> float:
    total = 0.0
    found = False
    for l in labels:
        if l in raw and raw[l][idx] is not None:
            total += raw[l][idx]
            found = True
    return total if found else None


def main():
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} nu există. Rulează inițial cu fișierul JSON de bootstrap.")
        sys.exit(1)

    store = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing_months = set(store["months"])

    found_new = False
    for year, month, url in candidate_urls(max_months_back=3):
        month_key = MONTH_KEYS[month - 1]
        if month_key in existing_months and year == date.today().year:
            continue  # deja avem luna asta
        content = download_xlsx(url)
        if content is None:
            continue
        print(f"Descărcat: {url}")
        raw = parse_sinteza(content)

        # cumulat pentru luna anterioară (deja stocat) -- necesar pentru diferență
        prev_month_idx = MONTH_KEYS.index(month_key) - 1
        for row in store["rows"]:
            labels = LABEL_MAP.get(row["label"], [row["label"]])
            cum_cur_26 = sum_raw(raw, labels, 1)  # col index 1 = an curent (.xlsx col G == idx6 in 0-based all cols, dar in parse_sinteza am pus index 1 pt cur in tuple)
            cum_cur_25 = sum_raw(raw, labels, 0)
            if cum_cur_26 is None:
                continue
            # cumulat pana luna precedenta = suma valorilor lunare deja existente
            prev_cum_26 = sum(row.get(f"{MONTH_KEYS[i]}26", 0) or 0 for i in range(prev_month_idx + 1)) if prev_month_idx >= 0 else 0
            prev_cum_25 = sum(row.get(f"{MONTH_KEYS[i]}25", 0) or 0 for i in range(prev_month_idx + 1)) if prev_month_idx >= 0 else 0
            row[f"{month_key}26"] = round(cum_cur_26 - prev_cum_26, 2)
            if cum_cur_25 is not None:
                row[f"{month_key}25"] = round(cum_cur_25 - prev_cum_25, 2)
            row["cum26"] = round(cum_cur_26, 2)
            if cum_cur_25 is not None:
                row["cum25"] = round(cum_cur_25, 2)
                row["var"] = round((cum_cur_26 - cum_cur_25) / abs(cum_cur_25) * 100, 2) if cum_cur_25 else None

        store["months"] = [m for m in MONTH_KEYS if any(f"{m}26" in r for r in store["rows"])]
        store["lastUpdated"] = date.today().isoformat()
        found_new = True
        break  # cea mai recentă lună găsită e suficientă pentru acest run

    if found_new:
        DATA_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
        print("Actualizat:", DATA_PATH)
    else:
        print("Nicio lună nouă disponibilă încă.")


if __name__ == "__main__":
    main()
