#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pensii_asf.py — utilitare LOCALE pentru secțiunea "05 Pensii private".

Nu modifică fin_common.py. Conține doar logica de parsare a fișierelor
statistice ASF (`p2-date_statistice.xlsx`, `p3-date_statistice.xlsx`), care au
o structură proprie: fiecare foaie ("Table N.") conține unul sau mai multe
BLOCURI, fiecare bloc având un rând-antet care începe cu celula "Nr. crt.",
urmat de coloane cu date calendaristice (o coloană = o lună).
"""
from __future__ import annotations

import datetime as _dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fin_common import fetch  # noqa: E402

BAZA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CACHE = os.path.join(BAZA, "cache", "pensii")
OUT = os.path.join(BAZA, "out")

URL = {
    "p2": "https://data.asfromania.ro/pensii/p2-date_statistice.xlsx",
    "p3": "https://data.asfromania.ro/pensii/p3-date_statistice.xlsx",
}
SECTIUNE = "05 Pensii private"
LICENTA = ("Autoritatea de Supraveghere Financiară — date publice, reutilizabile "
           "cu indicarea sursei (ASF, date statistice pensii private).")


def descarca(pilon: str, *, forta: bool = False) -> str:
    """Descarcă fișierul ASF (sau folosește copia din cache) și întoarce calea."""
    os.makedirs(CACHE, exist_ok=True)
    cale = os.path.join(CACHE, f"{pilon}.xlsx")
    if forta or not os.path.exists(cale) or os.path.getsize(cale) < 500_000:
        r = fetch(URL[pilon], expect="xlsx", timeout=120)
        with open(cale, "wb") as f:
            f.write(r.content)
    if os.path.getsize(cale) < 500_000:
        raise SystemExit(f"EȘEC: {URL[pilon]} a întors un fișier prea mic. Nu suprascriu datele bune.")
    return cale


def foaie(pilon: str, sheet: str) -> pd.DataFrame:
    return pd.read_excel(descarca(pilon), sheet_name=sheet, header=None)


def _per(v) -> str | None:
    """Antet de coloană -> 'YYYY-MM'. Acceptă doar date calendaristice reale."""
    if isinstance(v, (_dt.datetime, _dt.date, pd.Timestamp)):
        return f"{v.year:04d}-{v.month:02d}"
    return None


def _txt(v) -> str:
    return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v).strip()


def blocuri(df: pd.DataFrame) -> list[dict]:
    """Detectează blocurile dintr-o foaie ASF.

    Întoarce [{titlu, rand_antet, col_nume, perioade: {per: col}, randuri: [(nume, rand)]}].
    """
    out = []
    n = len(df)
    antete = []
    for i in range(n):
        for j in range(df.shape[1]):
            if _txt(df.iat[i, j]).lower().startswith("nr. crt"):
                antete.append((i, j))
                break
    for k, (i, j) in enumerate(antete):
        col_nume = j + 1
        per = {}
        for j2 in range(col_nume + 1, df.shape[1]):
            p = _per(df.iat[i, j2])
            if p:
                per[p] = j2
        if not per:
            continue
        # titlu: primul rând de text lung deasupra antetului
        titlu = ""
        for i2 in range(i - 1, max(-1, i - 6), -1):
            cand = [_txt(v) for v in df.iloc[i2].tolist() if len(_txt(v)) > 15]
            if cand:
                titlu = cand[0]
                break
        stop = antete[k + 1][0] if k + 1 < len(antete) else n
        randuri = []
        goale = 0
        for i2 in range(i + 1, stop):
            nume = _txt(df.iat[i2, col_nume])
            crt = df.iat[i2, j]
            e_index = isinstance(crt, (int, float)) and not pd.isna(crt)
            if not nume:
                goale += 1
                if goale >= 2 and randuri:
                    break
                continue
            if not e_index and nume.upper() not in ("TOTAL",):
                continue  # rânduri de note / sub-antete ("Luna de referinţă…")
            goale = 0
            randuri.append((nume, i2))
        if randuri:
            out.append({"titlu": titlu, "rand_antet": i, "col_nume": col_nume,
                        "perioade": per, "randuri": randuri})
    return out


def bloc_lung(df: pd.DataFrame, bloc: dict, *, indicator: str,
              exclude_total: bool = False) -> pd.DataFrame:
    """Un bloc -> format lung: perioada × entitate × indicator × valoare."""
    rows = []
    for nume, i2 in bloc["randuri"]:
        if exclude_total and nume.upper() == "TOTAL":
            continue
        for p, j2 in bloc["perioade"].items():
            v = df.iat[i2, j2]
            if v is None or (isinstance(v, float) and pd.isna(v)) or _txt(v) == "":
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            rows.append({"perioada": p, "entitate": nume, "indicator": indicator, "valoare": fv})
    return pd.DataFrame(rows)


def bloc_wide(df: pd.DataFrame, bloc: dict, *, exclude_total: bool = True) -> pd.DataFrame:
    """Un bloc -> tabel perioade (index) × entități (coloane)."""
    lg = bloc_lung(df, bloc, indicator="x", exclude_total=exclude_total)
    if lg.empty:
        return pd.DataFrame()
    return lg.pivot_table(index="perioada", columns="entitate", values="valoare",
                          aggfunc="last").sort_index()


def gaseste_bloc(bl: list[dict], *chei: str) -> dict:
    """Primul bloc al cărui titlu conține TOATE fragmentele date (fără diacritice-sensibilitate)."""
    def norm(s: str) -> str:
        tr = str.maketrans("ăâîșşțţĂÂÎȘŞȚŢ", "aaissttAAISSTT")
        return s.translate(tr).lower()
    for b in bl:
        t = norm(b["titlu"])
        if all(norm(c) in t for c in chei):
            return b
    raise SystemExit("EȘEC: nu am găsit blocul cu cheile " + repr(chei) +
                     ". Titluri disponibile: " + repr([b["titlu"][:70] for b in bl]))


def lung_din_matrice(df: pd.DataFrame, *, rand_antet: int, col_data: int, col_nume: int,
                     col_valori: dict[int, str], data_fmt: str | None = None) -> pd.DataFrame:
    """Foi deja în format lung (Data | Fond | col1 | col2 | …) -> perioada × fond × indicator."""
    rows = []
    for i in range(rand_antet + 1, len(df)):
        d = df.iat[i, col_data]
        p = _per(d)
        if p is None:
            s = _txt(d)
            try:
                p = _per(pd.to_datetime(s, format=data_fmt, dayfirst=True))
            except Exception:  # noqa: BLE001
                p = None
        if p is None:
            continue
        nume = _txt(df.iat[i, col_nume])
        if not nume:
            continue
        for j, eticheta in col_valori.items():
            v = df.iat[i, j]
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if pd.isna(fv):
                continue
            rows.append({"perioada": p, "entitate": nume, "indicator": eticheta, "valoare": fv})
    return pd.DataFrame(rows)


def cagr(v0: float, v1: float, ani: float) -> float | None:
    if not v0 or v0 <= 0 or v1 is None or v1 <= 0 or ani <= 0:
        return None
    return ((v1 / v0) ** (1 / ani) - 1) * 100
