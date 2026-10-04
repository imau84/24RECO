#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bvb_buletin.py — parser pentru buletinele lunare ale Bursei de Valori București.

Sursa: https://bvb.ro/info/Rapoarte/Lunare/{LUNA}{AN}.pdf  (LUNA = majuscule, fără
diacritice; AN pe 4 cifre; ex. AUGUST2026.pdf).

Extrage exclusiv secțiunea „A. Indicatori bursieri de baza / Main market indicators",
singura parte a buletinului cu structură stabilă pe toată perioada 2011–2026.

Modul auxiliar folosit de scripturile `financiara_01_02.py` și `financiara_01_03.py`.
NU face parte din fin_common.py (care e partajat cu alte fluxuri de lucru).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import fetch  # noqa: E402

BAZA = "https://bvb.ro/info/Rapoarte/Lunare"
LUNI_URL = ["IANUARIE", "FEBRUARIE", "MARTIE", "APRILIE", "MAI", "IUNIE",
            "IULIE", "AUGUST", "SEPTEMBRIE", "OCTOMBRIE", "NOIEMBRIE", "DECEMBRIE"]

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "bvb")

# ---------------------------------------------------------------------------
# Etichetele indicatorilor din secțiunea A. Ordinea contează: se testează
# variantele lungi înaintea celor scurte (BET-XT-TRN înainte de BET-XT etc.).
# ---------------------------------------------------------------------------
ETICHETE = [
    ("valoarea totala tranzactionata", "valoare_tranzactionata"),
    ("valoarea medie zilnica", "valoare_medie_zilnica"),
    ("capitalizarea bursiera", "capitalizare"),
    ("nr de titluri tranzactionate", "nr_titluri"),
    ("nr tranzactiilor", "nr_tranzactii"),
    ("nr. tranzactiilor", "nr_tranzactii"),
    ("indicele bet-xt-trn", "BET-XT-TRN"),
    ("indicele bet-xt-tr", "BET-XT-TR"),
    ("indicele bet-xt", "BET-XT"),
    ("indicele bet-trn", "BET-TRN"),
    ("indicele bet-tr", "BET-TR"),
    ("indicele bet-fi", "BET-FI"),
    ("indicele bet-ng", "BET-NG"),
    ("indicele bet-bk", "BET-BK"),
    ("indicele bet-ef", "BET-EF"),
    ("indicele bet-c", "BET-C"),
    ("indicele betplus", "BETPlus"),
    ("indicele bet plus", "BETPlus"),
    ("indicele rotx", "ROTX"),
    ("indicele bet", "BET"),
]

_RE_UNIT = re.compile(
    r"(puncte\s*/\s*index\s*points\s*-?\s*(ron|eur|usd)"
    r"|mil\.*\s*(ron|eur|usd)"
    r"|nr\.\s*/\s*no\.)", re.I)
_RE_NUM = re.compile(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:,\d+)?")


def _norm(s: str) -> str:
    """minuscule, fără diacritice, spații colapsate."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def _ro_float(t: str):
    t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def descarca_text(an: int, luna: int, *, timeout: int = 90) -> str | None:
    """Descarcă buletinul și întoarce textul primelor pagini. None dacă lipsește."""
    os.makedirs(CACHE, exist_ok=True)
    cale_txt = os.path.join(CACHE, f"{an}-{luna:02d}.txt")
    if os.path.exists(cale_txt) and os.path.getsize(cale_txt) > 500:
        with open(cale_txt, encoding="utf-8", errors="replace") as f:
            return f.read()
    url = f"{BAZA}/{LUNI_URL[luna - 1]}{an}.pdf"
    try:
        r = fetch(url, expect="pdf", tries=2, timeout=timeout)
    except Exception:  # noqa: BLE001 — luna lipsește din arhivă
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(r.content)
        tmp = tf.name
    try:
        # secțiunea A e mereu în primele pagini; limităm ca să fie rapid
        out = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "7", tmp, "-"],
                             capture_output=True, timeout=120)
        txt = out.stdout.decode("utf-8", errors="replace")
    finally:
        os.unlink(tmp)
    if len(txt) < 500:
        return None
    with open(cale_txt, "w", encoding="utf-8") as f:
        f.write(txt)
    return txt


def _sectiune_a(txt: str) -> list[str]:
    """Liniile secțiunii A (fără cuprins)."""
    linii = txt.splitlines()
    start = None
    for i, l in enumerate(linii):
        n = _norm(l)
        if n.startswith("a. indicatori bursieri de baza") and "....." not in l:
            start = i + 1
            break
    if start is None:
        return []
    for j in range(start, len(linii)):
        n = _norm(linii[j])
        if n.startswith("b. indicatori bursieri pentru"):
            return linii[start:j]
    return linii[start:start + 90]


def parseaza(txt: str) -> dict:
    """Întoarce {cheie_indicator: {'RON': x, 'EUR': y, 'USD': z, 'var_RON': p}}."""
    rez: dict[str, dict] = {}
    linii = _sectiune_a(txt)
    if not linii:
        return rez

    # Pasul 1: transformă liniile într-o secvență de evenimente ordonate.
    evenimente = []  # ('label', cheie) | ('unit', valuta, valoare, variatie)
    nn = [_norm(x) for x in linii]
    for i, l in enumerate(linii):
        n = nn[i]
        if not n:
            continue
        m = _RE_UNIT.search(n)
        if m:
            valuta = (m.group(2) or m.group(3) or "NR").upper()
            rest = n[m.end():]
            nums = _RE_NUM.findall(rest)
            if not nums:
                # Formatul din 2010: unitatea stă pe linia etichetei, iar cifrele
                # pe linia următoare (fără unitate și fără etichetă). Preluăm doar
                # în acest caz strict, ca să nu atribuim greșit valori.
                for j in range(i + 1, min(i + 3, len(nn))):
                    urm = nn[j]
                    if not urm:
                        continue
                    if _RE_UNIT.search(urm) or any(t in urm for t, _ in ETICHETE):
                        break
                    cand = _RE_NUM.findall(urm)
                    if cand:
                        nums = cand
                    break
            val = _ro_float(nums[0]) if nums else None
            var = _ro_float(nums[1]) if len(nums) > 1 else None
            evenimente.append(("unit", valuta, val, var))
            # eticheta poate fi pe aceeași linie (formatul 2010–2013)
            cap = n[:m.start()]
            for tipar, cheie in ETICHETE:
                if tipar in cap:
                    evenimente.append(("label", cheie))
                    break
            continue
        for tipar, cheie in ETICHETE:
            if tipar in n:
                evenimente.append(("label", cheie))
                break

    # Pasul 2: grupează. Un grup începe la prima unitate RON/NR și ține până la
    # următoarea. Eticheta grupului e labelul care apare în interiorul lui —
    # în formatele noi eticheta stă între linia RON și linia EUR.
    grupuri = []
    curent = None
    for ev in evenimente:
        if ev[0] == "unit" and ev[1] in ("RON", "NR"):
            if curent and curent["unitati"]:
                grupuri.append(curent)
                curent = {"label": None, "unitati": [ev]}
            elif curent:  # grup deschis de o etichetă, încă fără unități
                curent["unitati"].append(ev)
            else:
                curent = {"label": None, "unitati": [ev]}
        elif curent is None:
            if ev[0] == "label":
                curent = {"label": ev[1], "unitati": []}
        else:
            if ev[0] == "label":
                if curent["label"] is None:
                    curent["label"] = ev[1]
                else:  # etichetă nouă fără unitate RON — deschide grup nou
                    grupuri.append(curent)
                    curent = {"label": ev[1], "unitati": []}
            else:
                curent["unitati"].append(ev)
    if curent:
        grupuri.append(curent)

    for g in grupuri:
        if not g["label"]:
            continue
        d = rez.setdefault(g["label"], {})
        for _, valuta, val, var in g["unitati"]:
            if val is None:
                continue
            d.setdefault(valuta, val)
            if var is not None:
                d.setdefault(f"var_{valuta}", var)
    return rez


def luna_bvb(an: int, luna: int) -> dict | None:
    txt = descarca_text(an, luna)
    if txt is None:
        return None
    d = parseaza(txt)
    return d or None


def serie(an_start: int, luna_start: int, an_stop: int, luna_stop: int,
          *, lucratori: int = 6) -> dict[str, dict]:
    """Descarcă și parsează tot intervalul. Cheie: 'AAAA-LL'."""
    perioade = []
    a, m = an_start, luna_start
    while (a, m) <= (an_stop, luna_stop):
        perioade.append((a, m))
        m += 1
        if m == 13:
            a, m = a + 1, 1
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=lucratori) as ex:
        for (a, m), d in zip(perioade, ex.map(lambda p: luna_bvb(*p), perioade)):
            if d:
                out[f"{a}-{m:02d}"] = d
    return out


if __name__ == "__main__":
    for a, m in [(2026, 8), (2020, 1), (2015, 6), (2011, 3)]:
        d = luna_bvb(a, m) or {}
        print(f"--- {a}-{m:02d}: {len(d)} indicatori")
        for k in sorted(d):
            print(f"    {k:26s} {d[k]}")


# ---------------------------------------------------------------------------
# Secțiunea D.1 — indicatori pe sectoare de activitate
# ---------------------------------------------------------------------------
_N = r"\d{1,3}(?:\.\d{3})*,\d+"
_RE_RAND_SECTOR = re.compile(
    rf"({_N})\s+({_N})\s+({_N}|-)\s+({_N}|-)\s+({_N}|-)\s*$")
_RE_DATA = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")

SECTOARE = [
    ("intermedieri financiare", "Intermedieri financiare și asigurări"),
    ("industria extractiva", "Industria extractivă"),
    ("furnizarea de energie", "Energie electrică, termică și gaze"),
    ("industria prelucratoare", "Industria prelucrătoare"),
    ("transport si depozitare", "Transport și depozitare"),
    ("activitati profesionale", "Activități profesionale, științifice și tehnice"),
    ("sanatate si asistenta", "Sănătate și asistență socială"),
    ("cu ridicata si cu amanuntul", "Comerț cu ridicata și cu amănuntul"),
    ("informatii si comunicatii", "Informații și comunicații"),
    ("constructii", "Construcții"),
    ("hoteluri si restaurante", "Hoteluri și restaurante"),
    ("agricultura", "Agricultură, silvicultură și pescuit"),
    ("distributia apei", "Distribuția apei și salubritate"),
    ("tranzactii imobiliare", "Tranzacții imobiliare"),
    ("activitati de servicii administrative", "Servicii administrative și suport"),
    ("invatamant", "Învățământ"),
    ("activitati de spectacole", "Spectacole, activități culturale și recreative"),
    ("alte sectoare", "Alte sectoare"),
]


def parseaza_sectoare(txt: str) -> list[dict]:
    """Secțiunea D.1: capitalizare, valoare tranzacționată, PER, PBV, DIVY pe sector."""
    linii = txt.splitlines()
    nn = [_norm(x) for x in linii]
    start = None
    for i, n in enumerate(nn):
        if "sector de activitate" in n and "....." not in linii[i]:
            start = i
            break
    if start is None:
        return []
    out, vazute = [], set()
    for i in range(start, min(start + 80, len(linii))):
        n = nn[i]
        if n.startswith("d.2.") or "evolutia zilnica" in n or _RE_DATA.search(linii[i]):
            break
        m = _RE_RAND_SECTOR.search(linii[i].strip())
        if not m:
            continue
        sector = None
        for off in (0, -1, 1, -2, 2, -3, 3):
            j = i + off
            if 0 <= j < len(nn):
                for tipar, nume in SECTOARE:
                    if tipar in nn[j] and nume not in vazute:
                        sector = nume
                        break
            if sector:
                break
        if not sector:
            continue
        vazute.add(sector)
        out.append({
            "sector": sector,
            "capitalizare_ron": _ro_float(m.group(1)),
            "valoare_tranzactionata_ron": _ro_float(m.group(2)),
            "per": _ro_float(m.group(3)) if m.group(3) != "-" else None,
            "pbv": _ro_float(m.group(4)) if m.group(4) != "-" else None,
            "divy": _ro_float(m.group(5)) if m.group(5) != "-" else None,
        })
    return out


def serie_sectoare(an_start: int, luna_start: int, an_stop: int, luna_stop: int,
                   *, lucratori: int = 6) -> list[dict]:
    """Lista de rânduri {perioada, sector, ...} pentru tot intervalul."""
    perioade = []
    a, m = an_start, luna_start
    while (a, m) <= (an_stop, luna_stop):
        perioade.append((a, m))
        m += 1
        if m == 13:
            a, m = a + 1, 1

    def _unu(p):
        t = descarca_text(*p)
        return parseaza_sectoare(t) if t else []

    randuri = []
    with ThreadPoolExecutor(max_workers=lucratori) as ex:
        for (a, m), rows in zip(perioade, ex.map(_unu, perioade)):
            for r in rows:
                randuri.append({"perioada": f"{a}-{m:02d}", **r})
    return randuri
