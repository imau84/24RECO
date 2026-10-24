#!/usr/bin/env python3
"""
dezarhiveaza.py
===============
Dezarhivează arhivele din data/parc-auto/raw/ în data/parc-auto/extracted/<AAAA>/.
.7z cu py7zr, .zip cu zipfile. Arhivele din arhive (zip în zip) se desfac și ele.
Excelurile nearhivate (2012–2017, de pe data.gov.ro) se copiază ca atare.
Un an deja dezarhivat (folder nevid) se sare; --refa îl reface.

Rulare:  python scripts/parc-auto/dezarhiveaza.py [--refa]
"""

import shutil
import sys
import zipfile
from pathlib import Path

import py7zr

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "parc-auto" / "raw"
OUT_DIR = ROOT / "data" / "parc-auto" / "extracted"


def _sigur(dest: Path, nume: str) -> Path:
    """Refuză căile care ies din folderul destinație (../, căi absolute)."""
    tinta = (dest / nume).resolve()
    if dest.resolve() not in tinta.parents and tinta != dest.resolve():
        raise ValueError(f"Cale nesigură în arhivă: {nume}")
    return tinta


def desface(arhiva: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    ext = arhiva.suffix.lower()
    if ext == ".7z":
        with py7zr.SevenZipFile(arhiva, "r") as z:
            for nume in z.getnames():
                _sigur(dest, nume)
            z.extractall(dest)
    elif ext == ".zip":
        with zipfile.ZipFile(arhiva) as z:
            for info in z.infolist():
                # Arhivele vechi au nume în cp437 sau cp852 (diacritice); le lăsăm cum vin.
                _sigur(dest, info.filename)
            z.extractall(dest)
    elif ext in (".xls", ".xlsx"):
        shutil.copy2(arhiva, dest / arhiva.name)
        return
    else:
        return
    # arhive imbricate
    for inner in list(dest.rglob("*")):
        if inner.is_file() and inner.suffix.lower() in (".7z", ".zip") and inner != arhiva:
            desface(inner, inner.parent)
            inner.unlink()


def main():
    refa = "--refa" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for arhiva in sorted(RAW_DIR.iterdir()):
        if arhiva.suffix.lower() not in (".7z", ".zip", ".xls", ".xlsx"):
            continue
        an = arhiva.name[:4]
        dest = OUT_DIR / an
        if dest.exists() and any(dest.iterdir()):
            if not refa:
                print(f"  {an}: deja dezarhivat")
                continue
            shutil.rmtree(dest)
        print(f"  {an}: {'copiez' if arhiva.suffix.lower() in ('.xls', '.xlsx') else 'dezarhivez'} {arhiva.name}")
        desface(arhiva, dest)
        for f in sorted(dest.rglob("*")):
            if f.is_file():
                print(f"      {f.relative_to(dest)}  ({f.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
