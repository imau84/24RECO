"""
comun.py — căi, citirea Excelurilor DGPCI și recunoașterea rândurilor.

Structura fișierelor „Parc auto la 31.12.AAAA” (verificată 2012–2025):
  - o foaie TOTAL (2012: „TOTAL_FISIER_verificat”, 2017: „total”, 2018: „Total”) + câte o
    foaie per județ (cod auto: AB, B, ...); 2021 mai are 19 foi goale „FoaieNN”, ignorate.
  - antet pe rândurile 3–6: Numar | Vechime 0--2 ... >20 | Carburant | Vechime 0--4 ... peste 12
    (2012–2017: „0-2” cu o cratimă; 2012 nu are grupele 0-4 ... peste 12)
  - un bloc de rezumat (ex. „Autoturisme (M1, M1G)”, în 2012–2019 „AUTOTURISM”),
    apoi ierarhia:
        total categorie <cod>       (2020+: „total categorie   AUTOTRACTOARE   N1”)
         total marca <MARCA>        (1 spațiu fix în față)
           model <MODEL>            (3 spații fixe în față)
"""

import pickle
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "parc-auto"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
CACHE_DIR = DATA_DIR / "cache"
CSV_DIR = DATA_DIR / "csv"
MAPPING_CSV = DATA_DIR / "model_mapping.csv"
MARCI_CSV = DATA_DIR / "marca_mapping.csv"
JSON_OUT = ROOT / "public" / "parc_auto_autoturisme.json"

# Categoriile de autoturisme. Până în 2019 fișierul are „categoria de folosință”
# (AUTOTURISM), din 2020 categoriile europene M1/M1G (+ M1S din 2022, M1GS din 2025).
CATEGORII_M1 = {"M1", "M1G", "M1S", "M1GS"}
CATEGORII_VECHI = {"AUTOTURISM"}
CATEGORII_AUTOTURISME = CATEGORII_M1 | CATEGORII_VECHI

NBSP = "\xa0"
PREFIX_CATEGORIE = "total categorie"
PREFIX_MARCA = NBSP + "total marca"
PREFIX_MODEL = NBSP * 3 + "model"

# Coloane, în forma normalizată din CSV
VECHIME_1 = ["v_0_2", "v_3_5", "v_6_10", "v_11_15", "v_16_20", "v_peste_20"]
VECHIME_2 = ["v_0_4", "v_5_8", "v_9_12", "v_peste_12"]
COMBUSTIBIL = ["benzina", "motorina", "electric", "hibrid"]

_ANTET_VECHIME_1 = {"0--2": "v_0_2", "3--5": "v_3_5", "6--10": "v_6_10",
                    "11--15": "v_11_15", "16--20": "v_16_20", ">20": "v_peste_20"}
_ANTET_VECHIME_2 = {"0--4": "v_0_4", "5--8": "v_5_8", "9--12": "v_9_12", "peste 12": "v_peste_12"}


def ani_disponibili():
    return sorted(int(p.name) for p in EXTRACTED_DIR.iterdir() if p.is_dir() and p.name.isdigit())


def fisier_excel(an: int) -> Path:
    fisiere = [f for f in (EXTRACTED_DIR / str(an)).rglob("*") if f.suffix.lower() in (".xls", ".xlsx")]
    if len(fisiere) != 1:
        raise RuntimeError(f"{an}: aștept un singur Excel, am găsit {fisiere}")
    return fisiere[0]


def citeste_excel(an: int) -> dict:
    """{nume_foaie: [rânduri ca liste]}; păstrat în cache (citirea .xls durează minute)."""
    sursa = fisier_excel(an)
    cache = CACHE_DIR / f"{an}.pkl"
    if cache.exists() and cache.stat().st_mtime >= sursa.stat().st_mtime:
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    foi = {}
    if sursa.suffix.lower() == ".xls":
        import xlrd
        wb = xlrd.open_workbook(sursa, on_demand=True)
        for nume in wb.sheet_names():
            sh = wb.sheet_by_name(nume)
            foi[nume] = [sh.row_values(r) for r in range(sh.nrows)]
            wb.unload_sheet(nume)
    else:
        import openpyxl
        wb = openpyxl.load_workbook(sursa, read_only=True)
        for nume in wb.sheetnames:
            foi[nume] = [list(r) for r in wb[nume].iter_rows(values_only=True)]
        wb.close()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(cache, "wb") as fh:
        pickle.dump(foi, fh)
    return foi


def este_foaie_judet(nume: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{1,2}", nume.strip()))


def foaie_total(foi: dict) -> str:
    return next(n for n in foi if n.strip().upper().startswith("TOTAL"))


def numar(v) -> int:
    if isinstance(v, (int, float)):
        return int(round(v))
    if isinstance(v, str) and v.strip().replace(".", "", 1).isdigit():
        return int(float(v))
    return 0


def text(v) -> str:
    return v if isinstance(v, str) else ""


def harta_coloane(randuri: list) -> dict:
    """Găsește rândul de antet (cel cu „0--2”) și întoarce {nume_normalizat: index_coloană}."""
    for i, rand in enumerate(randuri[:15]):
        # 2012–2017 scriu „0-2”, din 2018 „0--2”
        celule = [re.sub(r"(?<=\d)-+(?=\d)", "--", text(c).strip()) for c in rand]
        if "0--2" not in celule:
            continue
        col = {"numar": 1}
        for j, c in enumerate(celule):
            cl = c.lower()
            if c in _ANTET_VECHIME_1:
                col[_ANTET_VECHIME_1[c]] = j
            elif c in _ANTET_VECHIME_2:
                col[_ANTET_VECHIME_2[c]] = j
            elif cl == "benzina":
                col["benzina"] = j
            elif cl == "motorina":
                col["motorina"] = j
            elif cl == "electric":
                col["electric"] = j
            elif cl.startswith("hibrid"):
                col["hibrid"] = j
        # „Numar” e în rândul de deasupra
        sus = [text(c).strip().lower() for c in randuri[i - 1]]
        if "numar" in sus:
            col["numar"] = sus.index("numar")
        col["_rand_antet"] = i
        return col
    raise RuntimeError("Nu găsesc rândul de antet (0--2)")


def tip_rand(eticheta: str):
    """('categorie', cod) | ('marca', nume) | ('model', nume) | (None, None)."""
    if eticheta.startswith(PREFIX_CATEGORIE):
        rest = eticheta[len(PREFIX_CATEGORIE):]
        bucati = [b.strip() for b in rest.split(NBSP) if b.strip()]
        return "categorie", (bucati[-1] if bucati else rest.strip())
    if eticheta.startswith(PREFIX_MARCA):
        return "marca", eticheta[len(PREFIX_MARCA):]
    if eticheta.startswith(PREFIX_MODEL):
        return "model", eticheta[len(PREFIX_MODEL):]
    return None, None


def rand_rezumat_autoturisme(randuri: list):
    """Rândul „Autoturisme (M1, M1G)” (2018–2019: „AUTOTURISM”) din blocul de rezumat."""
    for rand in randuri[:60]:
        e = text(rand[0] if rand else None).replace(NBSP, " ").strip()
        if e.startswith(PREFIX_CATEGORIE):
            break
        if e.startswith("Autoturisme (M1") or e == "AUTOTURISM":
            return e, rand
    return None, None


def parcurge_autoturisme(randuri: list):
    """Generează (categorie, marca_brută, model_brut, rând) pentru rândurile „model”
    din categoriile de autoturisme."""
    categorie = marca = None
    for rand in randuri:
        e = text(rand[0] if rand else None)
        tip, val = tip_rand(e)
        if tip == "categorie":
            categorie = val if val in CATEGORII_AUTOTURISME else None
            marca = None
        elif categorie is None:
            continue
        elif tip == "marca":
            marca = val
        elif tip == "model":
            yield categorie, marca, val, rand
