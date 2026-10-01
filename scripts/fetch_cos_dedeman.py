# -*- coding: utf-8 -*-
"""Construcții — Coșul de materiale Dedeman (indice propriu 24reco).

O dată pe lună (ziua 1) citește prețul de raft al celor 21 de produse din coș, direct din
paginile publice de produs dedeman.ro (permise de robots.txt; NU folosim /api/, /xapiv2 sau
/catalogsearch/), și adaugă observația lunii în `src/data/constructii/cos_dedeman_data.json`.

Indicele (medie geometrică pe grupă, ponderi fixe) se calculează în pagină, din observații —
vezi src/app/industrii/constructii/cos-materiale.ts. Pe site se publică doar indicii și
variațiile pe grupe, nu prețul fiecărui produs.

HTML-ul brut al fiecărei pagini se salvează în ARHIVA_DIR (în GitHub Actions e urcat ca
artifact), ca observația să poată fi verificată ulterior.

Rulare:   python scripts/fetch_cos_dedeman.py [--luna YYYY-MM] [--force]
"""
import argparse
import gzip
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "src" / "data" / "constructii" / "cos_dedeman_data.json"
ARHIVA_DIR = Path(os.environ.get("ARHIVA_DIR", ROOT / ".arhiva-dedeman"))
BAZA_URL = "https://www.dedeman.ro"
UA = "24reco.com bot - contact@24reco.com"
PAUZA = 4  # secunde între cereri, fără paralelism

GRUPE = [
    {"key": "ciment", "nume": "Ciment și lianți", "pondere": 22},
    {"key": "zidarie", "nume": "Zidărie (BCA, cărămidă)", "pondere": 15},
    {"key": "termo", "nume": "Termoizolație", "pondere": 18},
    {"key": "otel", "nume": "Oțel-beton și armături", "pondere": 20},
    {"key": "adezivi", "nume": "Adezivi și mortare", "pondere": 15},
    {"key": "gips", "nume": "Gips-carton", "pondere": 10},
]

# (cod produs — cheia stabilă, grupă, denumire, URL relativ)
# Doar produse cu preț afișat public pe pagină. Produsele „doar în magazin” (oțel-beton PC52 în bare,
# BCA Ytong, ciment Structo/Cemrom) își încarcă prețul prin API-ul intern, pe care nu îl folosim —
# au fost înlocuite la T0 (oct. 2026) cu echivalente din aceeași grupă.
COS = [
    ("6044033", "ciment", "Ciment Holcim SapaBet 22.5X, 40 kg", "/ro/ciment-holcim-sapabet-22-5x-sac-40-kg/p/6044033"),
    ("6062991", "ciment", "Ciment Holcim Ecoplanet Plus 42.5 N, 40 kg", "/ro/ciment-compozit-pentru-structuri-din-beton-holcim-ecoplanet-plus-42-5-n-40-kg/p/6062991"),
    ("6011034", "ciment", "Ciment Romcim Ultra 42,5, 40 kg", "/ro/ciment-romcim-ultra-42-5-40-kg/p/6011034"),
    ("6061564", "ciment", "Ciment Heidelberg Evobuild CEM II 42,5R, 20 kg", "/ro/ciment-portland-heidelberg-materials-cem-ii-b-m-s-ll-42-5-r-evobuild-20-kg/p/6061564"),
    ("6059766", "ciment", "Ciment zidărie Heidelberg Evobuild Z-100, 20 kg", "/ro/ciment-pentru-zidarie-heidelberg-materials-evobuild-z-100-20-kg/p/6059766"),
    ("6065094", "zidarie", "BCA Performo Clasic 650×100×250 mm", "/ro/bca-performo-clasic-650-x-100-x-250-mm-lxgxh/p/6065094"),
    ("6065096", "zidarie", "BCA Performo Clasic 650×200×250 mm", "/ro/bca-performo-clasic-650-x-200-x-250-mm-lxgxh/p/6065096"),
    ("6006574", "zidarie", "Cărămidă plină Helios P63A 230×115×63 mm", "/ro/caramida-interior/-exterior-helios-plina-rosu-p63a-230-x-115-x-63-mm/p/6006574"),
    ("6025878", "termo", "Polistiren Baudeman EPS 80, 3 cm", "/ro/polistiren-expandat-pentru-fatada-baudeman-eps-80-3-cm/p/6025878"),
    ("6025880", "termo", "Polistiren Baudeman EPS 80, 5 cm", "/ro/polistiren-expandat-pentru-fatada-baudeman-eps-80-5-cm/p/6025880"),
    ("6046746", "termo", "Polistiren Baudeman EPS 100, 10 cm", "/ro/polistiren-expandat-pentru-fatada-baudeman-eps-100-10-cm/p/6046746"),
    ("6016677", "otel", "Etrier fier beton B500A 200×200×8 mm", "/ro/etrier-fier-beton-b500a-200-x-200-x-8-mm/p/6016677"),
    ("6037924", "otel", "Etrier fier beton B500A 150×150×6 mm", "/ro/etrier-fier-beton-b500a-150-x-150-x-6-mm/p/6037924"),
    ("6029542", "otel", "Plasă sudată zincată Edilplan D3, 1×2 m", "/ro/panou-zincat-edilplan-diametru-3-mm-1000-x-2000-mm-ochi-50-x-50-mm/p/6029542"),
    ("6050575", "otel", "Sârmă neagră de legat 3 mm, rolă 10 kg", "/ro/sarma-neagra-3-mm-rola-10-kg/p/6050575"),
    ("5009135", "adezivi", "Adeziv gresie/faianță Adeplast AF-E, 25 kg", "/ro/adeziv-pentru-gresie-si-faianta-adeplast-af-e-exterior-gri-25-kg/p/5009135"),
    ("6068692", "adezivi", "Adeziv gresie/faianță Etalon, 25 kg", "/ro/adeziv-standard-pentru-gresie-si-faianta-etalon-interior-25-kg/p/6068692"),
    ("6012314", "adezivi", "Adeziv BCA Ytong Fix N220, 25 kg", "/ro/adeziv-bca-ytong-fix-n220-sac-25-kg/p/6012314"),
    ("5008952", "adezivi", "Mortar tencuială Adeplast Klasiko, 30 kg", "/ro/mortar-de-tencuiala-adeplast-klasiko-gri-interior/-exterior-30-kg/p/5008952"),
    ("5006960", "gips", "Placă gips-carton Rigips RBI 12.5×1200×2000 mm", "/ro/placa-gips-carton-tip-h-protectie-umiditate-rigips-rbi-12-5-x-1200-x-2000-mm/p/5006960"),
    ("5009550", "gips", "Placă gips-carton + polistiren Rigitherm 20PS", "/ro/placa-gips-carton-si-polistiren-termoizolare-rigitherm-20ps-9-5-x-1200-x-2600-mm-rigips/p/5009550"),
]

RE_UNIT_TXT = re.compile(r"([\d.,]+)\s*lei\s*/\s*(kg|sac|mp|m2|mc|buc|ml|m)\b", re.I)


def descarca(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ro-RO,ro;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def extrage(html: str, cod: str) -> dict:
    """Prețul produsului principal (după cod), prețul pe unitate și eventuala promoție."""
    fin = re.search(r'id="product-price-(\d+)"\s+data-price-amount="([\d.]+)"\s+data-price-type="finalPrice"\s+data-product-id="%s"' % cod, html)
    if not fin:
        # fallback: microdata schema.org/Offer din blocul principal
        m = re.search(r'itemprop="offers".{0,400}?itemprop="price"\s+content="([\d.]+)"', html, re.S)
        if not m:
            return {}
        intern, pret = None, float(m.group(1))
    else:
        intern, pret = fin.group(1), float(fin.group(2))

    out = {"pret": pret}
    alt = re.search(r'data-price-amount="([\d.]+)"\s+data-price-type="alternativePrice"\s+data-product-id="%s"[^>]*>.*?price-sale-unit">\s*/\s*([^<\s]+)' % cod, html, re.S)
    if alt:
        out["pret_unitar"], out["unitate"] = float(alt.group(1)), alt.group(2).lower()
    # unitatea de vânzare a pachetului (/sac, /buc, /bara…) — după prețul final
    if intern:
        u = re.search(r'id="product-price-%s".{0,600}?price-sale-unit">\s*/\s*([^<\s]+)' % intern, html, re.S)
        if u:
            out["unitate_pachet"] = u.group(1).lower()
        old = re.search(r'id="old-price-%s"[^>]*data-price-amount="([\d.]+)"' % intern, html) or \
              re.search(r'id="old-price-%s".{0,200}?class="price">([\d.]+)<span class="decimals">(\d+)' % intern, html, re.S)
        if old:
            vechi = float(old.group(1)) if old.lastindex == 1 else float(f"{old.group(1).rstrip('.')}.{old.group(2)}")
            if vechi > pret:
                out["promo"], out["pret_vechi"] = True, vechi
    if "pret_unitar" not in out:
        m = RE_UNIT_TXT.search(html)
        if m and m.group(2).lower() not in ("sac", "buc"):
            out["pret_unitar"], out["unitate"] = float(m.group(1).replace(",", ".")), m.group(2).lower()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--luna", help="luna observației (YYYY-MM); implicit luna curentă, ora României")
    ap.add_argument("--force", action="store_true", help="rescrie observația lunii dacă există deja")
    a = ap.parse_args()

    acum = datetime.now(timezone.utc)
    ro = acum + timedelta(hours=3)  # aproximare suficientă pentru a alege luna
    luna = a.luna or ro.strftime("%Y-%m")

    data = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"observatii": []}
    if any(o["luna"] == luna for o in data["observatii"]) and not a.force:
        print(f"Observația pentru {luna} există deja — nimic de făcut (folosiți --force pentru a o reface).")
        return 0

    arhiva = ARHIVA_DIR / luna
    arhiva.mkdir(parents=True, exist_ok=True)
    produse, erori = {}, []
    for i, (cod, grupa, nume, url) in enumerate(COS):
        if i:
            time.sleep(PAUZA)
        try:
            html = descarca(BAZA_URL + url)
        except Exception as e:  # noqa: BLE001
            erori.append(f"{cod} {nume}: {e}")
            print(f"  ✗ {cod} {nume}: {e}")
            continue
        with gzip.open(arhiva / f"{cod}.html.gz", "wt", encoding="utf-8") as f:
            f.write(html)
        p = extrage(html, cod)
        if not p:
            erori.append(f"{cod} {nume}: preț negăsit în pagină")
            print(f"  ✗ {cod} {nume}: preț negăsit")
            continue
        produse[cod] = p
        u = f" · {p['pret_unitar']} lei/{p['unitate']}" if "pret_unitar" in p else ""
        print(f"  ✓ {cod} {nume}: {p['pret']} lei{u}{' · PROMO' if p.get('promo') else ''}")

    if len(produse) < len(COS) * 0.6:
        print(f"EROARE: doar {len(produse)}/{len(COS)} produse citite — nu salvez observația.", file=sys.stderr)
        return 1

    data["meta"] = {
        "titlu": "Coșul de materiale de construcții — indice 24reco",
        "sursa": "Prețuri de raft publicate pe dedeman.ro, colectate de 24reco.com",
        "url": "https://www.dedeman.ro",
        "metoda": "Prețul pe unitate (lei/kg, lei/mp…) al fiecărui produs, la data de 1 a lunii. Indice de grupă = media geometrică a raporturilor de preț față de prima observație; indice general = media ponderată a grupelor.",
        "frecventa": "lunar, ziua 1",
    }
    data["grupe"] = GRUPE
    data["cos"] = [{"cod": c, "grupa": g, "nume": n, "url": BAZA_URL + u} for c, g, n, u in COS]
    obs = {"luna": luna, "data": ro.strftime("%Y-%m-%d"), "produse": produse}
    if erori:
        obs["erori"] = erori
    data["observatii"] = sorted([o for o in data["observatii"] if o["luna"] != luna] + [obs], key=lambda o: o["luna"])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scris {OUTPUT} — {luna}: {len(produse)}/{len(COS)} produse, {len(erori)} erori")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
