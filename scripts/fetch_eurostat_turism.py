#!/usr/bin/env python3
"""
Turism — 4 statistici Eurostat lunare pentru România → src/data/turism/eurostat.json

  1. Cifra de afaceri în hoteluri, restaurante și agenții   sts_setu_m
  2. Pasageri pe aeroporturile din România                   avia_paoc
  3. Prețurile din turism (IAPC)                             prc_hicp_minr
  4. Gradul de ocupare a hotelurilor, România vs. UE         tour_occ_mnor

Rulează lunar din GitHub Actions (.github/workflows/update-eurostat-turism.yml).
Bazat pe scripturile „turism-0X-….py”. Folosește aceleași funcții ca scripts/fetch_eurostat_industrie.py
(flag-uri p/e păstrate, perioadele goale tăiate, setul vechi păstrat dacă descărcarea eșuează).

Rulare: pip install requests pandas ; python scripts/fetch_eurostat_turism.py
"""
import json
import sys
from pathlib import Path

from fetch_eurostat_industrie import eurostat

OUT = Path("src/data/turism/eurostat.json")

TARI = "EU27_2020+BG+HU+PL+CZ+HR+AT+IT+ES"
SETURI = [
    {
        "key": "horeca", "scurt": "Hoteluri și restaurante",
        "titlu": "Cifra de afaceri în hoteluri, restaurante și agenții de turism",
        "descriere": "Câți bani încasează hotelurile, restaurantele și agențiile de turism, ca indice: 100 = media lunară din 2021. "
                     "Atenție: sunt lei curenți, deci creșterea include și scumpirile, nu doar mai mulți clienți.",
        "cod": "sts_setu_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_setu_m", "M.NETTUR.I+I55+I56+N79.NSA.I21.RO")],
        "serii": {
            "M,NETTUR,I,NSA,I21,RO": "Hoteluri și restaurante (total)",
            "M,NETTUR,I55,NSA,I21,RO": "Cazare (hoteluri, pensiuni)",
            "M,NETTUR,I56,NSA,I21,RO": "Restaurante, baruri, catering",
            "M,NETTUR,N79,NSA,I21,RO": "Agenții de turism și tur-operatori",
        },
        "note": ["Valori în lei curenți: în 2022–2024 o bună parte din creștere vine din scumpiri (vezi „Prețuri în turism”).",
                 "Serie neajustată sezonier: vara e mereu vârf la cazare. Compară cu aceeași lună din anul trecut.",
                 "2020–2021: restaurantele și hotelurile au fost închise sau cu restricții; agențiile au căzut sub 10% din nivelul de dinainte.",
                 "Ultimele 2–3 luni sunt provizorii; la agenții revizuirile pot fi mari (sunt puține firme raportoare)."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_setu_m/default/table?lang=en",
    },
    {
        "key": "aerian", "scurt": "Pasageri aerieni",
        "titlu": "Pasageri pe aeroporturile din România",
        "descriere": "Câți pasageri au plecat sau au sosit cu avionul în România, în fiecare lună. "
                     "Nu sunt doar turiști: intră și oamenii de afaceri și românii care lucrează în străinătate.",
        "cod": "avia_paoc", "freq": "M", "unitate": "pasageri", "zecimale": 0, "agregare": "suma",
        "parti": [("avia_paoc", "M.PAS.PAS_CRD.TOTAL+NAT+INTL.TOTAL.RO")],
        "serii": {
            "M,PAS,PAS_CRD,TOTAL,TOTAL,RO": "Total pasageri",
            "M,PAS,PAS_CRD,INTL,TOTAL,RO": "Zboruri internaționale",
            "M,PAS,PAS_CRD,NAT,TOTAL,RO": "Zboruri interne",
        },
        "note": ["Se numără fiecare îmbarcare și debarcare: un zbor intern dus-întors apare de patru ori. Nu sunt „turiști unici”.",
                 "Aprilie–mai 2020: trafic aproape oprit (−95% față de 2019).",
                 "Serie neajustată sezonier: iulie–august sunt mereu vârf, februarie minim.",
                 "Eurostat publică aceste date cu 3–5 luni întârziere; ultimele luni sunt provizorii."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/avia_paoc/default/table?lang=en",
    },
    {
        "key": "preturi", "scurt": "Prețuri în turism",
        "titlu": "Prețurile din turism",
        "descriere": "Cât de scumpe sunt cazarea, masa la restaurant, pachetele de vacanță și biletele de avion pentru români. "
                     "Indice: 100 = prețurile medii din 2015; 185 înseamnă de 1,85 ori mai scump. Variația față de anul trecut = inflația pe acel produs.",
        "cod": "prc_hicp_minr", "freq": "M", "unitate": "indice, 2015 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("prc_hicp_minr", "M.I15.CP112+CP1111+CP098+CP0733+CP11+TOTAL.RO")],
        "serii": {
            "M,I15,CP112,RO": "Cazare",
            "M,I15,CP1111,RO": "Restaurante și cafenele",
            "M,I15,CP098,RO": "Pachete de vacanță",
            "M,I15,CP0733,RO": "Bilete de avion",
            "M,I15,CP11,RO": "Restaurante și cazare (total)",
            "M,I15,TOTAL,RO": "Toate prețurile (pentru comparație)",
        },
        "note": ["Compară fiecare grupă cu „Toate prețurile”: dacă urcă mai repede, turismul s-a scumpit peste medie.",
                 "Pachetele de vacanță și biletele de avion se schimbă mult de la o lună la alta (oferte sezoniere); uită-te la variația față de anul trecut.",
                 "Aprilie–mai 2020 o parte din prețuri au fost estimate (unități închise).",
                 "Indicele armonizat (IAPC), clasificarea COICOP 2018 (setul prc_hicp_minr)."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table?lang=en",
    },
    {
        "key": "ocupare", "scurt": "Grad de ocupare",
        "titlu": "Cât de pline sunt hotelurile: România față de alte țări",
        "descriere": "Ce procent din paturile (și camerele) din hoteluri au fost ocupate în fiecare lună. "
                     "40% înseamnă că din 10 paturi disponibile, 4 au avut pe cineva în ele, în medie.",
        "cod": "tour_occ_mnor", "freq": "M", "unitate": "% din paturi ocupate", "zecimale": 1, "agregare": "medie",
        "rata": True,
        "parti": [("tour_occ_mnor", "M.BEDPL+BEDRM.PC.RO"), ("tour_occ_mnor", f"M.BEDPL.PC.{TARI}")],
        "serii": {
            "M,BEDPL,PC,RO": "România — paturi",
            "M,BEDRM,PC,RO": "România — camere",
            "M,BEDPL,PC,EU27_2020": "Media UE",
            "M,BEDPL,PC,BG": "Bulgaria",
            "M,BEDPL,PC,HU": "Ungaria",
            "M,BEDPL,PC,PL": "Polonia",
            "M,BEDPL,PC,CZ": "Cehia",
            "M,BEDPL,PC,HR": "Croația",
            "M,BEDPL,PC,AT": "Austria",
            "M,BEDPL,PC,IT": "Italia",
            "M,BEDPL,PC,ES": "Spania",
        },
        "note": ["Gradul „net”: zilele în care hotelul e închis nu se numără.",
                 "România raportează doar hotelurile și unitățile similare; pensiunile nu intră aici.",
                 "Seria României pe camere are luni lipsă și, vara, valori sub cea pe paturi — așa o publică Eurostat; pentru comparații folosește „România — paturi”.",
                 "Media UE lipsește în unele luni (Eurostat nu o publică dacă prea multe țări n-au trimis datele); golurile nu sunt completate.",
                 "Comparațiile din 2020–2021 nu sunt sigure: capacitatea „disponibilă” s-a definit diferit în perioada închiderilor."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/tour_occ_mnor/default/table?lang=en",
    },
]


def main():
    vechi = {}
    if OUT.exists():
        vechi = {s["key"]: s for s in json.loads(OUT.read_text(encoding="utf-8"))["seturi"]}
    seturi, erori = [], []
    for cfg in SETURI:
        print(f"[{cfg['key']}] {cfg['cod']}")
        try:
            s = eurostat(cfg)
            v = vechi.get(cfg["key"])
            if v and v["perioade"] == s["perioade"] and v["serii"] == s["serii"]:
                s["actualizat"] = v["actualizat"]  # date neschimbate → fără commit inutil
            print(f"  ok: {len(s['perioade'])} luni, {s['perioade'][0]} → {s['perioade'][-1]}")
            seturi.append(s)
        except Exception as e:  # păstrăm datele vechi ale setului
            erori.append(f"{cfg['key']}: {e}")
            print(f"  EROARE: {e}")
            if cfg["key"] in vechi:
                seturi.append(vechi[cfg["key"]])
    if not seturi:
        sys.exit("::error::Niciun set nu a putut fi descărcat.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"seturi": seturi}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scris {OUT} ({OUT.stat().st_size // 1024} KB)")
    if erori:
        print("::warning::Seturi nedescărcate (s-au păstrat datele vechi): " + "; ".join(erori))


if __name__ == "__main__":
    main()
