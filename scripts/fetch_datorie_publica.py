"""
Fetch automat pentru pagina "Datorie Publică" (Ministerul Finanțelor / Trezorerie).

Descarcă fișierul Excel "Evoluția datoriei guvernamentale conform metodologiei UE"
(EvdatguvconformUERo<MM><YYYY>.xls), publicat lunar la:
https://mfinante.gov.ro/ro/web/trezor/datorie-guvernamentala

Fișierul conține istoricul complet 2020–prezent (coloane = ani / luni curente),
deci scriptul rescrie integral secțiunea 2020+ a JSON-ului, păstrând neschimbat
istoricul 2010–2019 (extras din buletinele PDF mai vechi, care nu se mai
republică).

Rulează săptămânal prin GitHub Actions (vezi update-datorie-publica.yml).
"""

import json
import sys
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://mfinante.gov.ro/static/10/Mfp/buletin/executii/EvdatguvconformUERo{month:02d}{year}.xls"
DATA_PATH = Path("public/datorie-publica_data.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; 24reco-bot/1.0)"}


def candidate_urls(max_months_back: int = 3):
    today = date.today()
    y, m = today.year, today.month
    for _ in range(max_months_back):
        yield y, m, BASE_URL.format(month=m, year=y)
        m -= 1
        if m == 0:
            m = 12
            y -= 1


def download(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.content) > 1000:
            return r.content
    except requests.RequestException:
        pass
    return None


def first_numeric_after(rows, header_idx, max_lookahead=5):
    for i in range(header_idx + 1, min(header_idx + 1 + max_lookahead, len(rows))):
        label = (rows[i][0] or "").strip() if rows[i][0] else ""
        vals = rows[i][1:10]
        if label == "" and any(isinstance(v, (int, float)) for v in vals):
            return [round(v, 2) if isinstance(v, (int, float)) else None for v in vals]
    return None


def find_row(rows, start, end, predicate):
    for i in range(start, min(end, len(rows))):
        label = (rows[i][0] or "")
        label = " ".join(str(label).split()).strip()
        if predicate(label):
            vals = rows[i][1:10]
            return [round(v, 2) if isinstance(v, (int, float)) else None for v in vals]
    return None


def parse_section(rows, start, end):
    return {
        "pctPIB": find_row(rows, start, end, lambda l: l == "% PIB"),
        "termenScurt": find_row(rows, start, end, lambda l: l == "- termen scurt"),
        "termenMediuLung": find_row(rows, start, end, lambda l: l == "- termen mediu si lung"),
        "numerarDepozite": find_row(rows, start, end, lambda l: l == "- numerar si depozite"),
        "titluriStat": find_row(rows, start, end, lambda l: l == "- titluri de stat"),
        "imprumuturi": find_row(rows, start, end, lambda l: l == "- imprumuturi"),
        "lei": find_row(rows, start, end, lambda l: l == "- Lei"),
        "euro": find_row(rows, start, end, lambda l: l == "- Euro"),
        "usd": find_row(rows, start, end, lambda l: l == "- USD"),
        "altii": find_row(rows, start, end, lambda l: l == "- altii"),
    }


def parse_workbook(xls_bytes: bytes) -> dict:
    import xlrd
    from io import BytesIO

    book = xlrd.open_workbook(file_contents=xls_bytes)
    sheet = book.sheet_by_index(0)
    rows = [sheet.row_values(r) for r in range(sheet.nrows)]

    def find_idx(predicate, frm=0):
        for i in range(frm, len(rows)):
            label = " ".join(str(rows[i][0] or "").split()).strip()
            if predicate(label):
                return i
        return -1

    # rândul de header conține anii / lunile pe coloane (ex: 2020 2021 ... Martie 2026)
    header_idx = find_idx(lambda l: l.startswith("Datoria administratiei publice") and "conform" not in l)
    periods_row = rows[header_idx]
    periods = []
    for v in periods_row[1:10]:
        if v == "" or v is None:
            continue
        periods.append(str(v).strip())

    int_idx = find_idx(lambda l: l.startswith("I. Datoria interna"))
    ext_idx = find_idx(lambda l: l.startswith("II. Datoria externa"))
    end_idx = len(rows)

    total = parse_section(rows, header_idx, int_idx)
    total["total"] = find_row(rows, header_idx, int_idx, lambda l: l == "total (I+II)")
    pib = find_row(rows, header_idx, int_idx, lambda l: l == "PIB")

    interna = parse_section(rows, int_idx, ext_idx)
    interna["total"] = first_numeric_after(rows, int_idx)

    externa = parse_section(rows, ext_idx, end_idx)
    externa["total"] = first_numeric_after(rows, ext_idx)

    return {
        "periods": periods,
        "pib": pib,
        "total": total,
        "interna": interna,
        "externa": externa,
    }


def normalize_period(p: str) -> str:
    """'2020' -> '2020'; 'Ianuarie 2026' / 'Martie 2026**)' -> '2026-01' etc."""
    p = p.replace("**)", "").replace("*)", "").strip()
    luni = {
        "ianuarie": "01", "februarie": "02", "martie": "03", "aprilie": "04",
        "mai": "05", "iunie": "06", "iulie": "07", "august": "08",
        "septembrie": "09", "octombrie": "10", "noiembrie": "11", "decembrie": "12",
    }
    parts = p.lower().split()
    if len(parts) == 2 and parts[0] in luni:
        return f"{parts[1]}-{luni[parts[0]]}"
    return p


def main():
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} nu există. Rulează inițial cu fișierul JSON de bootstrap.")
        sys.exit(1)

    store = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    parsed = None
    for year, month, url in candidate_urls(max_months_back=3):
        content = download(url)
        if content is None:
            continue
        try:
            parsed = parse_workbook(content)
        except Exception as e:
            print(f"Nu am putut parsa {url}: {e}")
            continue
        print(f"Descărcat și parsat: {url}")
        break

    if parsed is None:
        print("Niciun fișier nou disponibil / accesibil. Nu modific nimic.")
        return

    norm_periods = [normalize_period(p) for p in parsed["periods"]]

    # păstrăm istoricul 2010-2019 din JSON existent, înlocuim 2020+ cu datele noi
    keep_until = store.get("detailed_from", "2020")
    old_periods = store["periods"]
    cut = old_periods.index(keep_until) if keep_until in old_periods else 10
    pre = {
        "periods": old_periods[:cut],
        "pib": store["pib"][:cut],
        "total": store["total"][:cut],
        "pctPIB": store["pctPIB"][:cut],
        "interna": store["interna"][:cut],
        "externa": store["externa"][:cut],
    }

    store["periods"] = pre["periods"] + norm_periods
    store["pib"] = pre["pib"] + (parsed["pib"] or [])
    store["total"] = pre["total"] + (parsed["total"]["total"] or [])
    store["pctPIB"] = pre["pctPIB"] + (parsed["total"]["pctPIB"] or [])
    store["interna"] = pre["interna"] + (parsed["interna"]["total"] or [])
    store["externa"] = pre["externa"] + (parsed["externa"]["total"] or [])
    store["total_detail"] = parsed["total"]
    store["interna_detail"] = parsed["interna"]
    store["externa_detail"] = parsed["externa"]
    store["lastUpdated"] = date.today().isoformat()[:7]

    DATA_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Actualizat:", DATA_PATH)


if __name__ == "__main__":
    main()
