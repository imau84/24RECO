"""
normalizare.py — unifică mărcile și modelele din fișierele DGPCI.

Marca:  curățată la capete (spații, . , ~ ` * - /), cratimele fără spații în jur,
        variantele cu aceleași litere puse la un loc („MERCEDES - BENZ” = „MERCEDES BENZ”),
        apoi tabelul ALIAS_MARCI (greșeli de scriere, sub-mărci, nume vechi).
Model:  model_norm  = aceeași denumire fără spații/semne, fără marca la început;
        model_familie = familia (Seria 1, Clasa C, A4, Astra, Logan, Model 3, ...).

Corecturile manuale se fac în data/parc-auto/marca_mapping.csv și model_mapping.csv;
vezi Corecturi mai jos.
"""

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

NESPECIFICAT = "nespecificat"

# Semne parazite tăiate de la capetele mărcilor/modelelor
_CAPETE = " \t\xa0.,;:~`'\"*-_/\\|!?+#"

# cheie (doar litere și cifre) -> marca canonică
ALIAS_MARCI = {
    "VW": "VOLKSWAGEN", "VOLKSWAGENVW": "VOLKSWAGEN", "VOLKSVAGEN": "VOLKSWAGEN",
    "VOLKSKWAGEN": "VOLKSWAGEN", "VOLKWAGEN": "VOLKSWAGEN", "VOLSKWAGEN": "VOLKSWAGEN",
    "DAIMLERBENZ": "MERCEDES-BENZ",
    "DACA": "DACIA", "DACAIA": "DACIA", "DACIO": "DACIA", "DAXCIA": "DACIA", "SACIA": "DACIA",
    "DACIAOKURA": "DACIA", "DACIAROMTURINGIA": "DACIA",
    "BMWI": "BMW",
    "CITROIEN": "CITROEN", "CITROENDS": "CITROEN", "DSAUTOMOBILES": "DS",
    "HYUNDAY": "HYUNDAI", "HYUNDAIGENESIS": "HYUNDAI",
    "NISSANINFINITI": "NISSAN",
    "SUZUKY": "SUZUKI", "SZUKI": "SUZUKI",
    "MITSUBISI": "MITSUBISHI", "MITSUBISHIGLX": "MITSUBISHI",
    "LANDROVER": "LAND ROVER",
    "LADAVAZ": "LADA", "VAZ": "LADA", "JIGULI": "LADA", "NIVALADAVAZ": "LADA",
    "OLCIT": "OLTCIT", "MOSKVITCH": "MOSKVICH",
    "SSANGYOUNG": "SSANGYONG", "SSANGYONGDAEWOO": "SSANGYONG",
    "TESLAMOTORS": "TESLA",
    "AUTOMOBILILAMBORGHINISPA": "LAMBORGHINI", "BRABUSGMBH": "BRABUS",
    "MCC": "SMART", "MICROCOMPACTCAR": "SMART",
    "MAZDAFORD": "MAZDA",
    "FORDCNGTECHNIK": "FORD", "FORDCNGTECHNIC": "FORD", "FORDGNCTECHNIK": "FORD", "FORDBENTINA": "FORD",
    "MERCURYFORD": "MERCURY",
    "VAUXALL": "VAUXHALL", "WAUXHALL": "VAUXHALL", "VAUXHALLOPEL": "VAUXHALL",
    "STUDEBACKER": "STUDEBAKER", "WILLIS": "WILLYS",
    "MGROEWE": "MG", "BAICBEIJING": "BAIC", "LYNKCO": "LYNK & CO",
    "QUATTRO": "AUDI", "H3": "HUMMER", "TALBOTSIMCA": "TALBOT", "ZASTAVAIVECO": "ZASTAVA",
    "GENERALMOTORSIT": "GENERAL MOTORS ITALIA",
}
# mărci scrise prin prefix (zeci de variante greșite)
PREFIX_MARCI = [
    (("MERCEDES", "MERCEDE", "MECEDES", "MERCSDES"), "MERCEDES-BENZ"),
]
# „mărci” care sunt de fapt modele: cheie -> (marca, prefix pus în fața modelului)
MARCI_MODEL = {
    "RANGEROVER": ("LAND ROVER", "RANGE ROVER"),
    "MONDEOTURNIER": ("FORD", "MONDEO"),
    "WRANGLER": ("JEEP", "WRANGLER"),
}

# familii pe două cuvinte, când primul nu ajunge
DOUA_CUVINTE = {"GRAND", "LAND", "RANGE", "MODEL", "SANTA", "NEW", "SUPER", "URBAN", "SPACE"}
# modele de 2 litere care stau singure (nu se lipesc de cuvântul următor)
SINGURE = {"KA", "TT", "CC", "UP", "LT", "IQ", "GT"}
# cuvinte de 3 litere care rămân cu majuscule (restul: „Rio”, „Fox”, „Zoe”)
ACRONIME = {"ASX", "MPV", "FTO", "HST", "GTV", "GTC", "GTI", "NSX", "RCZ", "MDX", "RDX", "TSX", "CTS",
            "SRX", "STS", "BRZ", "WRX", "AMG", "SUV", "CRX", "MGB", "MGF", "XJS", "XJR", "XKR", "UAZ", "BZ"}

_CLASE_MERCEDES = ["CLA", "CLS", "CLK", "CLC", "GLA", "GLB", "GLC", "GLE", "GLK", "GLS", "SLK", "SLC",
                   "SLR", "SLS", "EQA", "EQB", "EQC", "EQE", "EQS", "EQV", "EQT", "CL", "GL", "SL", "ML",
                   "A", "B", "C", "E", "G", "R", "S", "V", "X"]


def cheie(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def _zero_in_o(s: str) -> str:
    """„T0YOTA”, „P0L0”, „L0DGY” -> O: în cuvintele cu ≥2 litere unde singura cifră e 0."""
    def fix(m):
        w = m.group(0)
        if "0" in w and not re.search(r"[1-9]", w) and len(re.findall(r"[A-Z]", w)) >= 2:
            return w.replace("0", "O")
        return w
    return re.sub(r"[A-Z0-9]+", fix, s)


def curata(s: str) -> str:
    s = (s or "").upper().replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip(_CAPETE)
    s = re.sub(r"\s*-\s*", "-", s)
    return _zero_in_o(s)


def este_nespecificat(model: str) -> bool:
    m = curata(model)
    return m == "" or m == "NESPECIFICAT" or not re.search(r"[A-Z0-9]", m)


# ---------------------------------------------------------------- mărci

class Marci:
    """Construită din toate variantele brute (cu numărul de mașini), ca să aleagă
    scrierea cea mai frecventă pentru variantele cu aceeași cheie."""

    def __init__(self, numar_brute: Counter):
        pe_cheie = defaultdict(Counter)
        for bruta, n in numar_brute.items():
            c = curata(bruta)
            pe_cheie[cheie(c)][c] += n
        self._afisare = {k: v.most_common(1)[0][0] for k, v in pe_cheie.items()}

    def auto(self, bruta: str) -> tuple:
        """(marca, prefix_model) pentru o marcă brută."""
        c = curata(bruta)
        k = cheie(c)
        if k in MARCI_MODEL:
            return MARCI_MODEL[k]
        if k in ALIAS_MARCI:
            return ALIAS_MARCI[k], ""
        for prefixe, marca in PREFIX_MARCI:
            if k.startswith(prefixe):
                return marca, ""
        return self._afisare.get(k, c), ""


# ---------------------------------------------------------------- modele

def variante_marca(marca: str, brute: set) -> list:
    # „brute”: doar variantele brute care sunt chiar marca (nu „RANGE ROVER” -> LAND ROVER)
    """Scrierile mărcii care pot apărea la începutul modelului („VW GOLF”, „MERCEDES C 200”)."""
    v = {marca, marca.replace("-", " "), marca.split("-")[0], marca.split(" ")[0]}
    v |= {curata(b) for b in brute}
    if marca == "VOLKSWAGEN":
        v.add("VW")
    return sorted((x for x in v if len(cheie(x)) >= 2), key=len, reverse=True)


def fara_marca(model: str, marca: str, variante: list) -> str:
    m = curata(model)
    for v in variante:
        if len(cheie(v)) <= 2 and v == marca:   # DS 3, MG 5: marca face parte din nume
            continue
        if m.startswith(v) and len(m) > len(v) and not m[len(v)].isalnum():
            return m[len(v):].strip(_CAPETE)
        if m == v:
            return ""
        if len(v) >= 4 and m.startswith(v) and m[len(v):].isdigit():   # MAZDA3 -> 3
            return m[len(v):]
    return m


def model_norm(model_curat: str) -> str:
    return cheie(model_curat) or NESPECIFICAT


def _afisare(t: str) -> str:
    """Forma afișată: „Astra”, „C-Max”, „X3”, „CR-V”, „Rio”, „Santa Fe”."""
    doua = " " in t

    def bucata(p, cuv):
        if re.search(r"\d", p) or cuv in ACRONIME:
            return p
        if len(p) <= 2 and not (doua and len(cuv) == 2):
            return p
        if len(cuv) == 3 and not re.search(r"[AEIOUY]", cuv):
            return p
        return p.capitalize()
    return " ".join("-".join(bucata(p, cuv) for p in cuv.split("-")) for cuv in t.split(" "))


def _unitate(tok: list, i: int):
    """Primul „cuvânt” începând de la i: lipește prefixele scurte (C MAX, CR V, RAV 4)."""
    t = tok[i]
    if i + 1 < len(tok):
        u = tok[i + 1]
        litere = t.isalpha()
        if litere and len(t) <= 2 and t not in SINGURE and (u.isalpha() or (u.isdigit() and len(u) <= 2)):
            # C 3 -> C3, CX 5 -> CX-5, C MAX -> C-MAX
            return (t + u if u.isdigit() and len(t) == 1 else f"{t}-{u}"), i + 2
        if litere and len(t) <= 3 and u.isdigit() and len(u) == 1:
            return t + u, i + 2
        if t.isdigit() and len(t) == 1 and u.isalpha():                 # 4 RUNNER
            return t + u, i + 2
    return t, i + 1


def _generic(model_curat: str) -> str:
    tok = [t for t in re.split(r"[^A-Z0-9]+", re.sub(r"['`´’]", "", model_curat)) if t]
    if not tok:
        return NESPECIFICAT
    cap, i = _unitate(tok, 0)
    if cap in DOUA_CUVINTE and i < len(tok):
        urm, _ = _unitate(tok, i)
        cap = f"{cap} {urm}"
    else:
        m = re.fullmatch(r"(\d{3,4})[A-Z]{1,4}", cap)     # 307SW, 1310L, 200D
        if m:
            cap = m.group(1)
        m = re.fullmatch(r"([A-Z]{4,})\d", cap)            # GOLF4, CLIO2
        if m:
            cap = m.group(1)
    return _afisare(cap)


def _bmw(n: str):
    m = re.match(r"(?:SERIA|SERIE)(\d)|(\d)(?:ER|SERIES)", n)
    if m:
        return f"Seria {m.group(1) or m.group(2)}"
    m = re.match(r"M?(\d)\d{2}", n)
    if m:
        return f"Seria {m.group(1)}"
    m = re.match(r"M(\d)(?!\d)", n)
    if m:
        return f"Seria {m.group(1)}"
    m = re.match(r"I?X(\d)", n)
    if m:
        return ("iX" if n.startswith("I") else "X") + m.group(1)
    if n.startswith("IX"):
        return "iX"
    m = re.match(r"([ZI])(\d)", n)
    if m:
        return ("i" if m.group(1) == "I" else "Z") + m.group(2)
    return None


def _mercedes(n: str):
    m = re.fullmatch(r"([A-Z]{1,3})(?:KLASSE|CLASS|CLASA)", n) or re.fullmatch(r"(?:KLASSE|CLASA|CLASS)([A-Z]{1,3})", n)
    if m:
        return "Clasa M" if m.group(1) == "ML" else f"Clasa {m.group(1)}"
    if n.startswith("AMGGT"):
        return "AMG GT"
    for c in _CLASE_MERCEDES:
        if n.startswith(c) and (len(n) == len(c) or n[len(c)].isdigit()):
            if c.startswith("EQ"):
                return c
            return "Clasa M" if c == "ML" else f"Clasa {c}"
    return None


def _audi(n: str):
    m = re.match(r"(RSQ|RS|SQ|A|Q|S)(\d)", n)
    return m.group(1) + m.group(2) if m else None


def _tesla(n: str):
    m = re.match(r"MODEL([A-Z0-9])", n)
    if m:
        return f"Model {m.group(1)}"
    if n in ("S", "3", "X", "Y"):
        return f"Model {n}"
    return None


def _vw(n: str):
    m = re.match(r"ID(\d)", n)
    return f"ID.{m.group(1)}" if m else None


def _hyundai(n: str):
    m = re.match(r"(IX|I)(\d{2})", n)
    return m.group(1).lower() + m.group(2) if m else None


REGULI_MARCA = {"BMW": _bmw, "MERCEDES-BENZ": _mercedes, "AUDI": _audi, "TESLA": _tesla,
                "VOLKSWAGEN": _vw, "HYUNDAI": _hyundai}


def _distanta(a: str, b: str) -> int:
    """Levenshtein, pentru cuvinte scurte."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _greseala(f: str, g: str) -> bool:
    """f e o scriere greșită a lui g? Un singur cuvânt diferă, de minim 5 litere, la 1 literă
    distanță (2 de la 8 litere în sus). Fără cifre, cratime, „Clasa”/„Seria”."""
    if re.search(r"[\d-]", f + g) or f.startswith(("Clasa ", "Seria ")) or g.startswith(("Clasa ", "Seria ")):
        return False
    cf, cg = f.upper().split(" "), g.upper().split(" ")
    if len(cf) != len(cg):
        return False
    dif = [(a, b) for a, b in zip(cf, cg) if a != b]
    if len(dif) != 1:
        return False
    a, b = dif[0]
    prag = 2 if min(len(a), len(b)) >= 8 else 1
    return min(len(a), len(b)) >= 5 and abs(len(a) - len(b)) <= prag and _distanta(a, b) <= prag


def uneste_greseli(numar_familii: Counter) -> dict:
    """{familie_greșită: familie} în cadrul aceleiași mărci („Evogue” -> „Evoque”), doar când
    familia țintă are de cel puțin 20 de ori mai multe mașini."""
    fam = sorted(((f, n) for f, n in numar_familii.items() if f != NESPECIFICAT), key=lambda x: -x[1])
    rez = {}
    for i, (f, n) in enumerate(fam):
        for g, ng in fam[:i]:
            if ng >= 20 * n and g not in rez and _greseala(f, g):
                rez[f] = g
                break
    return rez


def model_familie(marca: str, model_curat: str) -> str:
    n = cheie(model_curat)
    if not n:
        return NESPECIFICAT
    regula = REGULI_MARCA.get(marca)
    return (regula(n) if regula else None) or _generic(model_curat)


# ---------------------------------------------------------------- corecturi manuale

class Corecturi:
    """Fișierul de verificare (editabil) + o copie cu valorile automate scrise ultima oară.
    O valoare din fișier diferită de cea automată de atunci e o corectură manuală și se
    păstrează; restul se recalculează (ca să prindă îmbunătățirile regulilor)."""

    def __init__(self, cale: Path, chei: list, campuri: list):
        self.cale = cale
        self.cale_auto = cale.with_name(cale.stem + ".auto.csv")
        self.chei, self.campuri = chei, campuri
        self.manual = self._citeste(cale)
        self.auto_vechi = self._citeste(self.cale_auto)

    def _citeste(self, cale):
        if not cale.exists():
            return {}
        with open(cale, encoding="utf-8-sig", newline="") as fh:
            return {tuple(r[k] for k in self.chei): r for r in csv.DictReader(fh)}

    def aplica(self, k: tuple, auto: dict) -> dict:
        rez = dict(auto)
        rand = self.manual.get(k)
        if not rand:
            return rez
        vechi = self.auto_vechi.get(k, auto)
        for c in self.campuri:
            if rand.get(c) not in (None, "") and rand[c] != vechi.get(c):
                rez[c] = rand[c]
        return rez

    def scrie(self, randuri: list, auto: dict):
        """randuri: [dict cu chei + campuri + 'numar'], auto: {cheie: {campuri}}"""
        coloane = self.chei + self.campuri + ["numar"]
        for cale, sursa in ((self.cale, None), (self.cale_auto, auto)):
            with open(cale, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=coloane)
                w.writeheader()
                for r in randuri:
                    if sursa is not None:
                        k = tuple(r[c] for c in self.chei)
                        r = {**r, **sursa[k]}
                    w.writerow({c: r[c] for c in coloane})
