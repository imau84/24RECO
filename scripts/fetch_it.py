#!/usr/bin/env python3
"""
IT & Comunicații — 6 statistici pentru România → src/data/it/date.json

Tab-ul „Eurostat”:
  1. Cifra de afaceri în IT și telecom (J61/J62/J63)       sts_setu_m
  2. Angajați, ore lucrate și salarii în secțiunea J        sts_selb_m
  3. Exportul de servicii IT și telecom (trimestrial)       bop_c6_q
  4. Prețurile serviciilor de comunicații (IAPC)            prc_hicp_minr
Tab-ul „Infrastructură”:
  5. Infrastructura de internet (prefixe IP, ASN)           RIPE NCC — RIPEstat country-resource-stats
  6. Adopția IPv6 la utilizatori                            APNIC Labs — v6economy

Rulează lunar din GitHub Actions (.github/workflows/update-it.yml).
Bazat pe scripturile „it-0X-….py”. Aceleași reguli ca la industrie/turism: flag-urile p/e se păstrează,
perioadele goale de la coadă se taie, iar dacă un set nu poate fi descărcat se păstrează versiunea veche.

Rulare: pip install requests pandas ; python scripts/fetch_it.py
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

import fetch_eurostat_industrie as ind
from fetch_eurostat_industrie import eurostat, iesire
from fetch_eurostat_transport import HEADERS

OUT = Path("src/data/it/date.json")
ind.MIN_LUNI = 40  # exportul e trimestrial: 2015-T1 → azi are ~46 de perioade, nu 48+

RIPE = "https://stat.ripe.net/data/country-resource-stats/data.json"
APNIC = "https://data1.labs.apnic.net/v6stats/v6economy/{}.json"
TARI_RIPE = {"BG": "Bulgaria", "HU": "Ungaria", "PL": "Polonia", "CZ": "Cehia", "GR": "Grecia", "AT": "Austria"}
TARI_APNIC = {"BG": "Bulgaria", "HU": "Ungaria", "PL": "Polonia", "CZ": "Cehia", "GR": "Grecia", "DE": "Germania", "FR": "Franța"}
APNIC_START = "2017-01"   # înainte de 2017 eșantionul zilnic pentru România e prea mic
PRAG_ESANTION = 10_000    # eșantion mediu zilnic minim ca o lună să fie publicată
PRAG_ZILE = 14            # zile minime cu măsurători într-o lună

EUROSTAT = [
    {
        "key": "cifra", "scurt": "Cifra de afaceri",
        "titlu": "Cifra de afaceri în IT și telecomunicații",
        "descriere": "Câți bani încasează firmele de software, de servicii IT și de telecomunicații, ca indice: 100 = media lunară din 2021. "
                     "220 înseamnă de 2,2 ori mai mult decât în 2021. Sunt lei curenți, deci creșterea include și scumpirile.",
        "cod": "sts_setu_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_setu_m", "M.NETTUR.J+J61+J62+J63.CA.I21.RO"),
                  ("sts_setu_m", "M.NETTUR.J62.CA.I21.EU27_2020+BG+PL+HU+CZ")],
        "serii": {
            "M,NETTUR,J62,CA,I21,RO": "Programare și consultanță IT",
            "M,NETTUR,J63,CA,I21,RO": "Servicii informatice (date, hosting, portaluri)",
            "M,NETTUR,J61,CA,I21,RO": "Telecomunicații",
            "M,NETTUR,J,CA,I21,RO": "Informații și comunicații (total)",
            "M,NETTUR,J62,CA,I21,EU27_2020": "IT — media UE",
            "M,NETTUR,J62,CA,I21,BG": "IT — Bulgaria",
            "M,NETTUR,J62,CA,I21,PL": "IT — Polonia",
            "M,NETTUR,J62,CA,I21,HU": "IT — Ungaria",
            "M,NETTUR,J62,CA,I21,CZ": "IT — Cehia",
        },
        "note": ["Indice de valoare (lei/euro curenți), nu de volum: o parte din creștere vine din inflație.",
                 "Ajustat doar pentru numărul de zile lucrătoare, nu și sezonier: decembrie e mereu vârf. Compară cu aceeași lună din anul trecut.",
                 "Fiecare țară are propriul indice (2021 = 100): comparația arată cine a crescut mai repede din 2021, nu cine are piața mai mare.",
                 "Ultimele 2–3 luni sunt provizorii; Eurostat le revizuiește la fiecare publicare."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_setu_m/default/table?lang=en",
    },
    {
        "key": "munca", "scurt": "Angajați și salarii",
        "titlu": "Angajați, ore lucrate și salarii în IT și comunicații",
        "descriere": "Câți oameni lucrează în IT, telecom, edituri și media, câte ore lucrează și cât primesc în total ca salarii — ca indice, 100 = media din 2021. "
                     "„Salariul mediu” e fondul de salarii împărțit la numărul de angajați.",
        "cod": "sts_selb_m", "freq": "M", "unitate": "indice, 2021 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("sts_selb_m", "M.EMP+HW+WAGE.J.SCA.I21.RO"),
                  ("sts_selb_m", "M.EMP.J.SCA.I21.DE+ES+PT")],
        "serii": {
            "M,EMP,J,SCA,I21,RO": "Număr de angajați",
            "M,HW,J,SCA,I21,RO": "Ore lucrate",
            "M,WAGE,J,SCA,I21,RO": "Fondul total de salarii",
            "M,EMP,J,SCA,I21,DE": "Angajați — Germania",
            "M,EMP,J,SCA,I21,ES": "Angajați — Spania",
            "M,EMP,J,SCA,I21,PT": "Angajați — Portugalia",
        },
        "derivat": ("Salariul mediu (fond / angajat)", "M,WAGE,J,SCA,I21,RO", "M,EMP,J,SCA,I21,RO"),
        "note": ["România raportează doar pentru toată secțiunea J (IT + telecom + edituri + radio-TV), nu separat pentru IT.",
                 "Fondul de salarii e în lei curenți: în 2022–2023 inflația a fost peste 10%, deci o parte din creștere nu e câștig real.",
                 "„Salariul mediu” e un raport de indici (100 = 2021), nu o sumă în lei.",
                 "Serii ajustate sezonier: se pot compara direct două luni la rând.",
                 "Doar câteva țări UE publică această serie lunară, de aceea comparația e cu Germania, Spania și Portugalia."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/sts_selb_m/default/table?lang=en",
    },
    {
        "key": "export", "scurt": "Export de servicii IT",
        "titlu": "Exportul de servicii IT și telecom",
        "descriere": "Câte milioane de euro încasează România din servicii IT, telecom și informații vândute în străinătate, pe trimestru. "
                     "Soldul = export minus import: cât rămâne în țară net.",
        "cod": "bop_c6_q", "freq": "Q", "unitate": "mil. euro", "zecimale": 1, "agregare": "suma",
        "parti": [("bop_c6_q", "Q.MIO_EUR.SI+S.S1.S1.CRE+DEB+BAL.WRL_REST.RO"),
                  ("bop_c6_q", "Q.MIO_EUR.SI.S1.S1.CRE.WRL_REST.BG+PL+HU+CZ")],
        "serii": {
            "Q,MIO_EUR,SI,S1,S1,CRE,WRL_REST,RO": "Export servicii IT și telecom",
            "Q,MIO_EUR,SI,S1,S1,DEB,WRL_REST,RO": "Import servicii IT și telecom",
            "Q,MIO_EUR,SI,S1,S1,BAL,WRL_REST,RO": "Sold (export − import)",
            "Q,MIO_EUR,S,S1,S1,CRE,WRL_REST,RO": "Export total de servicii (toate tipurile)",
            "Q,MIO_EUR,SI,S1,S1,CRE,WRL_REST,BG": "Export IT — Bulgaria",
            "Q,MIO_EUR,SI,S1,S1,CRE,WRL_REST,PL": "Export IT — Polonia",
            "Q,MIO_EUR,SI,S1,S1,CRE,WRL_REST,HU": "Export IT — Ungaria",
            "Q,MIO_EUR,SI,S1,S1,CRE,WRL_REST,CZ": "Export IT — Cehia",
        },
        "derivat": ("Ponderea IT în exportul de servicii", "Q,MIO_EUR,SI,S1,S1,CRE,WRL_REST,RO", "Q,MIO_EUR,S,S1,S1,CRE,WRL_REST,RO"),
        "derivat_meta": {"unitate": "%", "agregare": "medie"},
        "note": ["Date trimestriale: balanța de plăți nu are detaliu lunar pentru serviciile IT.",
                 "Se publică cu circa un trimestru întârziere, iar BNR revizuiește retroactiv seriile, uneori cu câțiva ani în urmă.",
                 "Euro curenți, fără ajustare sezonieră: trimestrul I e de obicei mai slab, compară cu același trimestru din anul trecut.",
                 "„Ponderea IT” = cât din tot exportul de servicii al României (transport, turism, IT etc.) vine din IT și telecom."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/bop_c6_q/default/table?lang=en",
    },
    {
        "key": "preturi", "scurt": "Prețuri telefon și internet",
        "titlu": "Prețurile serviciilor de comunicații",
        "descriere": "Cât de scumpe sunt abonamentele de mobil, internetul, telefonia fixă și telefoanele/laptopurile pentru români. "
                     "Indice: 100 = prețurile medii din 2025; 90 înseamnă cu 10% mai ieftin decât în 2025.",
        "cod": "prc_hicp_minr", "freq": "M", "unitate": "indice, 2025 = 100", "zecimale": 1, "agregare": "medie",
        "parti": [("prc_hicp_minr", "M.I25.TOTAL+CP08+CP081+CP082+CP083+CP0831+CP0832+CP0833+CP0834.RO"),
                  ("prc_hicp_minr", "M.I25.TOTAL+CP083.EU27_2020")],
        "serii": {
            "M,I25,CP083,RO": "Servicii de comunicații (total)",
            "M,I25,CP0832,RO": "Telefonie mobilă",
            "M,I25,CP0833,RO": "Internet și stocare online",
            "M,I25,CP0831,RO": "Telefonie fixă",
            "M,I25,CP0834,RO": "Pachete (TV + internet + telefon)",
            "M,I25,CP081,RO": "Telefoane, laptopuri și alte echipamente",
            "M,I25,CP082,RO": "Software",
            "M,I25,CP08,RO": "Informații și comunicații (total)",
            "M,I25,TOTAL,RO": "Toate prețurile (pentru comparație)",
            "M,I25,CP083,EU27_2020": "Servicii de comunicații — media UE",
            "M,I25,TOTAL,EU27_2020": "Toate prețurile — media UE",
        },
        "note": ["Compară cu „Toate prețurile”: dacă o linie urcă mai încet, serviciul s-a ieftinit în termeni reali.",
                 "Prețurile echipamentelor sunt ajustate pentru calitate (un telefon nou mai performant la același preț contează ca o ieftinire).",
                 "Clasificarea nouă COICOP 2018 (setul prc_hicp_minr), bază 2025 = 100; seriile vechi (prc_hicp_midx) s-au oprit în decembrie 2025.",
                 "Pachetele și software-ul au serii scurte sau cu salturi în primii ani."],
        "url": "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table?lang=en",
    },
]

RIPE_CFG = {
    "key": "ripe", "scurt": "Infrastructura de internet",
    "titlu": "Infrastructura de internet a României",
    "descriere": "Câte rețele are România pe internet și câte blocuri de adrese IP anunță în lume. "
                 "Un „sistem autonom” (ASN) e o rețea independentă — un operator, o firmă mare, o universitate. "
                 "Un „prefix” e un bloc de adrese IP; IPv6 e noua generație de adrese, care o înlocuiește treptat pe IPv4.",
    "cod": "country-resource-stats", "freq": "M", "unitate": "prefixe", "zecimale": 0, "agregare": "medie",
    "sursa": "RIPE NCC — RIPEstat",
    "note": ["Valoarea lunii = ultima măsurătoare săptămânală din lună (o fotografie la sfârșitul lunii).",
             "„Vizibile” = anunțate efectiv în rutarea globală a internetului; „alocate” = înregistrate pe România la RIPE, chiar dacă nu sunt folosite.",
             "Raportul IPv6/IPv4 arată cât de departe e trecerea la IPv6 (comparabil între țări de mărimi diferite).",
             "Nu măsoară viteza sau acoperirea internetului, doar resursele de adresare ale operatorilor.",
             "Ultima lună e provizorie cât timp nu s-a încheiat."],
    "url": "https://stat.ripe.net/app/RO",
}

APNIC_CFG = {
    "key": "ipv6", "scurt": "Adopția IPv6",
    "titlu": "Adopția IPv6 în România",
    "descriere": "Ce procent dintre utilizatorii de internet din România pot folosi IPv6, noua generație de adrese de internet. "
                 "30% înseamnă că 3 din 10 oameni măsurați au o conexiune care merge și pe IPv6.",
    "cod": "v6economy/RO", "freq": "M", "unitate": "% din utilizatori", "zecimale": 1, "agregare": "medie", "rata": True,
    "sursa": "APNIC Labs",
    "note": ["Măsurat prin reclame afișate în browser: un test mic verifică dacă se poate încărca o resursă prin IPv6.",
             "„Capabil” = poate folosi IPv6; „preferat” = îl folosește efectiv când are de ales.",
             "Valoarea lunii = media măsurătorilor zilnice. Lunile cu eșantion mic (sub 10.000 de teste pe zi) sau cu sub 14 zile măsurate nu sunt afișate.",
             "Depinde mult de câțiva operatori mari: când unul activează sau oprește IPv6, procentul sare brusc.",
             "Ultima lună e provizorie cât timp APNIC n-a publicat măsurătorile până la sfârșitul ei."],
    "url": "https://stats.labs.apnic.net/ipv6/RO",
}


def get_json(url: str, **kw):
    for i in range(4):
        try:
            r = requests.get(url, headers=HEADERS, timeout=600, **kw)
            if r.ok:
                return r.json()
            print(f"  încercarea {i + 1}: HTTP {r.status_code} {r.text[:120]!r}")
        except (requests.RequestException, ValueError) as e:
            print(f"  încercarea {i + 1}: {e}")
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"nu am putut descărca {url}")


def eurostat_it(cfg: dict) -> dict:
    s = eurostat(cfg)
    if "derivat_meta" in cfg:
        for r in s["serii"]:
            if r["nume"] == cfg["derivat"][0]:
                r.update(cfg["derivat_meta"])
    return s


# ── RIPE NCC ────────────────────────────────────────────────────────────────

def ripe_lunar(cc: str) -> pd.DataFrame:
    """Săptămânal → lunar (ultima observație din lună). RIPEstat marchează cu -1 câmpurile indisponibile."""
    d = get_json(RIPE, params={"resource": cc, "starttime": f"{ind.START}-01", "resolution": "1w"})
    stats = d.get("data", {}).get("stats", [])
    if len(stats) < 100:
        raise RuntimeError(f"doar {len(stats)} observații săptămânale pentru {cc}")
    df = pd.DataFrame(stats)
    df["luna"] = df.stats_date.str[:7]
    for k in ("v4_prefixes_ris", "v6_prefixes_ris", "asns_ris", "asns_stats"):
        df[k] = pd.to_numeric(df[k], errors="coerce").where(lambda x: x >= 0)
    return df.sort_values("stats_date").groupby("luna").last()


def ripe(cfg: dict) -> dict:
    ro = ripe_lunar("RO")
    tari = {}
    for cc, nume in TARI_RIPE.items():
        try:
            tari[nume] = ripe_lunar(cc)
        except Exception as e:
            print(f"  ATENȚIE: {cc}: {e}")
    perioade = list(ro.index)
    # luna e incompletă dacă după ultima măsurătoare mai urmează încă o săptămână în aceeași lună
    ultima = pd.Timestamp(ro.stats_date.iloc[-1])
    prov = {len(perioade) - 1} if (ultima + pd.Timedelta(days=7)).month == ultima.month else set()
    col = lambda df, k: [None if pd.isna(v) else float(v) for v in df[k].reindex(perioade)]
    raport = lambda df: [None if pd.isna(a) or pd.isna(b) or not b else a / b * 100
                         for a, b in zip(df.v6_prefixes_ris.reindex(perioade), df.v4_prefixes_ris.reindex(perioade))]
    serii = [
        {"nume": "Prefixe IPv4 vizibile", "valori": col(ro, "v4_prefixes_ris"), "provizorii": prov},
        {"nume": "Prefixe IPv6 vizibile", "valori": col(ro, "v6_prefixes_ris"), "provizorii": prov},
        {"nume": "Rețele (ASN) alocate României", "valori": col(ro, "asns_stats"), "provizorii": prov, "unitate": "rețele (ASN)"},
        {"nume": "Rețele (ASN) vizibile pe internet", "valori": col(ro, "asns_ris"), "provizorii": prov, "unitate": "rețele (ASN)"},
        {"nume": "Raport IPv6 / IPv4 — România", "valori": raport(ro), "provizorii": prov, "unitate": "% (prefixe IPv6 la 100 IPv4)", "zecimale": 1},
    ] + [{"nume": f"Raport IPv6 / IPv4 — {nume}", "valori": raport(df), "provizorii": prov,
          "unitate": "% (prefixe IPv6 la 100 IPv4)", "zecimale": 1} for nume, df in tari.items()]
    v4 = serii[0]["valori"][-1]
    if not v4 or not 1000 < v4 < 100000:
        raise RuntimeError(f"număr implauzibil de prefixe IPv4: {v4}")
    return iesire(cfg, perioade, serii)


# ── APNIC Labs ──────────────────────────────────────────────────────────────

def apnic_lunar(cc: str) -> pd.DataFrame:
    """Zilnic → media lunară, doar lunile cu eșantion suficient."""
    d = get_json(APNIC.format(cc))
    rows = [{"luna": x["date"][:7], "data": x["date"], "capabil": x["raw"].get("capable_pc"),
             "preferat": x["raw"].get("preferred_pc"), "esantion": x["raw"].get("seen")}
            for x in d.get("data", []) if x.get("raw")]
    if len(rows) < 500:
        raise RuntimeError(f"doar {len(rows)} observații zilnice pentru {cc}")
    m = pd.DataFrame(rows).groupby("luna").agg(capabil=("capabil", "mean"), preferat=("preferat", "mean"),
                                               esantion=("esantion", "mean"), zile=("capabil", "size"),
                                               ultima_zi=("data", "max"))
    return m[(m.index >= APNIC_START) & (m.esantion >= PRAG_ESANTION) & (m.zile >= PRAG_ZILE)]


def apnic(cfg: dict) -> dict:
    ro = apnic_lunar("RO")
    tari = {}
    for cc, nume in TARI_APNIC.items():
        try:
            tari[nume] = apnic_lunar(cc)
        except Exception as e:
            print(f"  ATENȚIE: {cc}: {e}")
    # grilă lunară completă: lunile excluse la filtrul de calitate rămân goale (null), nu sunt sărite
    perioade = [str(p) for p in pd.period_range(ro.index.min(), ro.index.max(), freq="M")]
    col = lambda df, k: [None if pd.isna(v) else float(v) for v in df[k].reindex(perioade)]
    # luna curentă (încă nu s-a terminat sau APNIC n-a publicat ultimele zile) e provizorie
    ultima = pd.Timestamp(ro.ultima_zi.iloc[-1])
    prov = {len(perioade) - 1} if ultima.day < ultima.days_in_month else set()
    serii = [{"nume": "Capabil IPv6 — România", "valori": col(ro, "capabil"), "provizorii": prov},
             {"nume": "Preferă IPv6 — România", "valori": col(ro, "preferat"), "provizorii": prov}] + \
            [{"nume": f"Capabil IPv6 — {nume}", "valori": col(df, "capabil"), "provizorii": prov} for nume, df in tari.items()]
    ult = ro.capabil.iloc[-1]
    if not 0 < ult < 100:
        raise RuntimeError(f"procent IPv6 implauzibil: {ult}")
    return iesire(cfg, perioade, serii)


GRUPE = {"eurostat": [(c, eurostat_it) for c in EUROSTAT],
         "infrastructura": [(RIPE_CFG, ripe), (APNIC_CFG, apnic)]}


def main():
    vechi = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    rezultat, erori = {}, []
    for grupa, lista in GRUPE.items():
        v_grupa = {s["key"]: s for s in vechi.get(grupa, [])}
        rezultat[grupa] = []
        for cfg, fn in lista:
            print(f"[{grupa}/{cfg['key']}] {cfg['cod']}")
            try:
                s = fn(cfg)
                v = v_grupa.get(cfg["key"])
                if v and v["perioade"] == s["perioade"] and v["serii"] == s["serii"]:
                    s["actualizat"] = v["actualizat"]  # date neschimbate → fără commit inutil
                print(f"  ok: {len(s['perioade'])} perioade, {s['perioade'][0]} → {s['perioade'][-1]}, {len(s['serii'])} serii")
                rezultat[grupa].append(s)
            except Exception as e:  # păstrăm datele vechi ale setului
                erori.append(f"{cfg['key']}: {e}")
                print(f"  EROARE: {e}")
                if cfg["key"] in v_grupa:
                    rezultat[grupa].append(v_grupa[cfg["key"]])
    if not any(rezultat.values()):
        sys.exit("::error::Niciun set nu a putut fi descărcat.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rezultat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Scris {OUT} ({OUT.stat().st_size // 1024} KB)")
    if erori:
        print("::warning::Seturi nedescărcate (s-au păstrat datele vechi): " + "; ".join(erori))


if __name__ == "__main__":
    main()
