#!/usr/bin/env python3
"""
fetch_transport.py
Scraping lunar: autorizatiiauto.ro (operatori autorizați) + EU Weekly Oil Bulletin
Output: public/transport-data.json
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ── EU Oil Bulletin — date directe din CSV/API Europa ──
EU_OIL_URL = "https://ec.europa.eu/energy/observatory/reports/Oil_Bulletin_Prices_History.xlsx"
# Alternativă JSON dacă XLSX nu e disponibil:
EU_OIL_FALLBACK = "https://energy.ec.europa.eu/system/files/2023-12/weekly_oil_bulletin.csv"

AUTORIZ_URL = "https://autorizatiiauto.ro"

# Mapare coduri țări → flag emoji
FLAGS = {
    "AT": "🇦🇹", "BE": "🇧🇪", "BG": "🇧🇬", "CY": "🇨🇾", "CZ": "🇨🇿",
    "DE": "🇩🇪", "DK": "🇩🇰", "EE": "🇪🇪", "ES": "🇪🇸", "FI": "🇫🇮",
    "FR": "🇫🇷", "GR": "🇬🇷", "HR": "🇭🇷", "HU": "🇭🇺", "IE": "🇮🇪",
    "IT": "🇮🇹", "LT": "🇱🇹", "LU": "🇱🇺", "LV": "🇱🇻", "MT": "🇲🇹",
    "NL": "🇳🇱", "PL": "🇵🇱", "PT": "🇵🇹", "RO": "🇷🇴", "SE": "🇸🇪",
    "SI": "🇸🇮", "SK": "🇸🇰",
}

# Judete fallback pentru normalizare
JUDETE_MAP = {
    "ALBA": "Alba", "ARAD": "Arad", "ARGES": "Argeș", "ARGEȘ": "Argeș",
    "BACAU": "Bacău", "BACĂU": "Bacău", "BIHOR": "Bihor",
    "BISTRITA-NASAUD": "Bistrița-Năsăud", "BOTOSANI": "Botoșani",
    "BRAILA": "Brăila", "BRASOV": "Brașov", "BRAȘOV": "Brașov",
    "BUZAU": "Buzău", "CALARASI": "Călărași", "CARAS-SEVERIN": "Caraș-Severin",
    "CLUJ": "Cluj", "CONSTANTA": "Constanța", "CONSTANȚA": "Constanța",
    "COVASNA": "Covasna", "DAMBOVITA": "Dâmbovița", "DOLJ": "Dolj",
    "GALATI": "Galați", "GALAȚI": "Galați", "GIURGIU": "Giurgiu",
    "GORJ": "Gorj", "HARGHITA": "Harghita", "HUNEDOARA": "Hunedoara",
    "IALOMITA": "Ialomița", "IASI": "Iași", "IAȘI": "Iași",
    "ILFOV": "Ilfov", "MARAMURES": "Maramureș", "MEHEDINTI": "Mehedinți",
    "MURES": "Mureș", "MUREȘ": "Mureș", "NEAMT": "Neamț",
    "OLT": "Olt", "PRAHOVA": "Prahova", "SALAJ": "Sălaj",
    "SATU-MARE": "Satu Mare", "SIBIU": "Sibiu", "SUCEAVA": "Suceava",
    "TELEORMAN": "Teleorman", "TIMIS": "Timiș", "TIMIȘ": "Timiș",
    "TULCEA": "Tulcea", "VALCEA": "Vâlcea", "VASLUI": "Vaslui",
    "VRANCEA": "Vrancea", "BUCURESTI": "București", "BUCUREȘTI": "București",
    "MUNICIPIUL BUCURESTI": "București",
}


def normalize_judet(raw: str) -> str:
    if not raw:
        return raw
    key = raw.strip().upper().replace("-", "-")
    return JUDETE_MAP.get(key, raw.strip().title())


async def fetch_operatori(playwright):
    """Scrape autorizatiiauto.ro — necesită sesiune ASP.NET activă."""
    print("→ Conectare autorizatiiauto.ro...")
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"
    )
    page = await context.new_page()

    operatori = []
    try:
        await page.goto(AUTORIZ_URL, timeout=60000, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Navigare la lista operatori — adaptezi selector-ul după structura reală a site-ului
        # Structura tipică: formular căutare → submit → tabel rezultate
        # Caută link-ul spre lista completă sau export
        
        # Încearcă să găsim un link de tip "Căutare" sau "Lista operatori"
        links = await page.eval_on_selector_all(
            "a",
            "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
        )
        
        search_link = None
        for lnk in links:
            if any(w in lnk.get("text", "").lower() for w in ["căutare", "cautare", "operatori", "lista"]):
                search_link = lnk["href"]
                break

        if search_link:
            await page.goto(search_link, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(1500)

        # Submit formular de căutare (câmpuri goale = toate rezultatele)
        try:
            btn = page.locator("input[type=submit], button[type=submit]").first
            await btn.click()
            await page.wait_for_timeout(3000)
        except Exception:
            pass

        # Parcurge toate paginile din tabel
        page_num = 0
        max_pages = 500  # limită de siguranță

        while page_num < max_pages:
            rows = await page.eval_on_selector_all(
                "table tr",
                """rows => rows.slice(1).map(r => {
                    const cells = Array.from(r.querySelectorAll('td'));
                    return cells.map(c => c.textContent.trim());
                }).filter(r => r.length >= 3)"""
            )

            if not rows:
                break

            for row in rows:
                if len(row) >= 3:
                    operatori.append({
                        "denumire": row[0] if len(row) > 0 else "",
                        "judet": normalize_judet(row[1] if len(row) > 1 else ""),
                        "tip": row[2] if len(row) > 2 else "",
                        "vehicule": _parse_int(row[3] if len(row) > 3 else "0"),
                        "status": "Activ",
                    })

            # Paginare — caută butonul "Următor"
            next_btns = await page.eval_on_selector_all(
                "a, input[type=submit]",
                "els => els.filter(e => /urm[aă]t|next|>/i.test(e.textContent || e.value)).map(e => e.textContent || e.value)"
            )

            if not next_btns:
                break

            try:
                nxt = page.locator("a:has-text('Următor'), a:has-text('Next'), a:has-text('>')").first
                await nxt.click()
                await page.wait_for_timeout(2000)
                page_num += 1
            except Exception:
                break

    except Exception as e:
        print(f"  Eroare scraping operatori: {e}", file=sys.stderr)
    finally:
        await browser.close()

    print(f"  → {len(operatori)} operatori colectați")
    return operatori


def _parse_int(s: str) -> int:
    try:
        return int(re.sub(r"[^\d]", "", s))
    except Exception:
        return 0


def fetch_oil_bulletin() -> dict:
    """
    Descarcă datele Oil Bulletin din API-ul Europa.
    Returnează dict cu prețuri diesel/benzină per țară + media UE.
    """
    import urllib.request
    import csv
    import io

    print("→ Descărcare EU Oil Bulletin...")
    
    # URL CSV direct (săptămânal actualizat de DG ENER)
    csv_urls = [
        "https://ec.europa.eu/energy/observatory/reports/Oil_Bulletin_Prices_History.csv",
        "https://energy.ec.europa.eu/system/files/2024-01/oil_bulletin.csv",
    ]
    
    tari_data = {}
    
    for url in csv_urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            
            reader = csv.DictReader(io.StringIO(content), delimiter=";")
            rows = list(reader)
            if not rows:
                continue
            
            # Ia ultimul set de date disponibil
            # Format tipic: Country, Date, Diesel (EUR), Petrol (EUR), ...
            last_week = {}
            for row in rows:
                ctry = (row.get("Country") or row.get("country") or "").strip().upper()[:2]
                if not ctry or len(ctry) != 2:
                    continue
                # Diesel fără taxe (col "Diesel") sau cu taxe ("Diesel incl. taxes")
                diesel_raw = row.get("Diesel") or row.get("diesel") or row.get("Gas oil") or "0"
                petrol_raw = row.get("Petrol") or row.get("petrol") or row.get("Motor gasoline") or "0"
                
                try:
                    diesel = float(diesel_raw.replace(",", ".").strip()) / 1000  # EUR/L (datele vin în EUR/1000L)
                    petrol = float(petrol_raw.replace(",", ".").strip()) / 1000
                    if diesel > 0:
                        last_week[ctry] = {"diesel": diesel, "benzina": petrol}
                except Exception:
                    pass
            
            if last_week:
                tari_data = last_week
                break
        except Exception as e:
            print(f"  OilBulletin URL failed ({url}): {e}", file=sys.stderr)
            continue
    
    # Dacă n-am reușit, returnăm date hardcodate recente
    if not tari_data:
        print("  → Folosim prețuri estimate (Oil Bulletin indisponibil)")
        tari_data = {
            "RO": {"diesel": 1.285, "benzina": 1.310},
            "BG": {"diesel": 1.218, "benzina": 1.280},
            "HU": {"diesel": 1.356, "benzina": 1.398},
            "PL": {"diesel": 1.290, "benzina": 1.342},
            "DE": {"diesel": 1.521, "benzina": 1.678},
            "FR": {"diesel": 1.489, "benzina": 1.610},
            "NL": {"diesel": 1.562, "benzina": 1.720},
            "ES": {"diesel": 1.388, "benzina": 1.490},
            "IT": {"diesel": 1.451, "benzina": 1.598},
            "AT": {"diesel": 1.412, "benzina": 1.524},
            "CZ": {"diesel": 1.326, "benzina": 1.388},
            "SK": {"diesel": 1.318, "benzina": 1.375},
        }

    # Construiește lista pentru frontend
    tari_list = []
    for code, vals in sorted(tari_data.items()):
        if code in FLAGS:
            tari_list.append({
                "tara": code,
                "flag": FLAGS[code],
                "diesel": round(vals["diesel"], 3),
                "benzina": round(vals.get("benzina", 0), 3),
            })

    ro_data = tari_data.get("RO", {})
    diesel_ro = ro_data.get("diesel", 0)
    
    # Media UE ponderată (simplificată)
    diesel_vals = [v["diesel"] for v in tari_data.values() if v["diesel"] > 0]
    eu_avg = round(sum(diesel_vals) / len(diesel_vals), 3) if diesel_vals else 0

    print(f"  → {len(tari_list)} țări procesate, RO diesel: {diesel_ro}")
    return {
        "dieselRO": {"pret": round(diesel_ro, 3), "varPct": None},
        "dieselEUMediu": eu_avg,
        "tariUE": tari_list,
    }


def load_existing_history(output_path: Path) -> list:
    """Citește istoricul lunar din fișierul existent."""
    if not output_path.exists():
        return []
    try:
        with open(output_path) as f:
            existing = json.load(f)
        return existing.get("evolutieLunara", [])
    except Exception:
        return []


async def main():
    from playwright.async_api import async_playwright

    output_path = Path("public/transport-data.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    luna_str = now.strftime("%-m %Y")  # ex: "6 2025"
    # Format frumos în română
    luni_ro = ["", "Ian", "Feb", "Mar", "Apr", "Mai", "Iun",
               "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    luna_display = f"{luni_ro[now.month]} {now.year}"

    # 1. Scraping operatori
    async with async_playwright() as p:
        operatori = await fetch_operatori(p)

    # 2. Oil Bulletin
    carburanti = fetch_oil_bulletin()

    # 3. Calculează variație diesel față de luna trecută
    history = load_existing_history(output_path)
    if history:
        last = history[-1]
        old_diesel = last.get("dieselRO", carburanti["dieselRO"]["pret"])
        cur_diesel = carburanti["dieselRO"]["pret"]
        if old_diesel and cur_diesel:
            var_pct = round((cur_diesel - old_diesel) / old_diesel * 100, 1)
            carburanti["dieselRO"]["varPct"] = var_pct

    # 4. Adaugă luna curentă în istoric
    total_ops = len(operatori)
    total_vehs = sum(o.get("vehicule", 0) for o in operatori)
    
    # Evita duplicate
    if not history or history[-1].get("luna") != luna_display:
        history.append({
            "luna": luna_display,
            "operatori": total_ops,
            "vehicule": total_vehs,
            "dieselRO": carburanti["dieselRO"]["pret"],
        })
    else:
        # Update ultima intrare
        history[-1] = {
            "luna": luna_display,
            "operatori": total_ops,
            "vehicule": total_vehs,
            "dieselRO": carburanti["dieselRO"]["pret"],
        }

    # Păstrăm max 24 luni de istoric
    history = history[-24:]

    # 5. Construiește output final
    result = {
        "lastUpdate": luna_display,
        "generatedAt": now.isoformat(),
        "operatori": operatori,
        "evolutieLunara": history,
        "carburanti": carburanti,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Salvat: {output_path}")
    print(f"   Operatori: {total_ops}")
    print(f"   Vehicule: {total_vehs}")
    print(f"   Diesel RO: {carburanti['dieselRO']['pret']} EUR/L")
    print(f"   Țări combustibil: {len(carburanti['tariUE'])}")


if __name__ == "__main__":
    asyncio.run(main())
