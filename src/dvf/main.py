"""Ingestion DVF bronze — télécharge et filtre sur les 4 régions cibles.

Source : data.gouv.fr (DGFiP) — fichiers .txt pipe-séparés, un par millésime.
Filtre appliqué dès l'ingestion : uniquement les départements des 4 régions cibles.
Justification : les fichiers source sont partitionnés par millésime (grain natif),
le filtrage géographique est une sélection de lignes, pas une transformation métier.

Contrainte légale : données à caractère personnel — ne pas exposer publiquement
ni permettre la ré-identification indirecte (CGU DGFiP).

Usage :
    python src/dvf/main.py              # télécharge les 5 millésimes
    python src/dvf/main.py --year 2024  # un seul millésime
"""

import argparse
import io
import time
import urllib.request
import zipfile
from pathlib import Path

BRONZE = Path(__file__).resolve().parents[2] / "bronze" / "dvf"
BRONZE.mkdir(parents=True, exist_ok=True)

MILLÉSIMES = {
    2021: "947677ab-ad21-48f4-a9ac-ad217c99cf39",
    2022: "be6e092d-292a-4568-90bf-4254a261ff3b",
    2023: "025b9d29-8efb-40bb-8ce6-5bddf97a4e51",
    2024: "99a26050-b94f-4ffc-9eb0-73ed28a895d1",
    2025: "902db087-b0eb-4cbb-a968-0b499bde5bc4",
}

BASE_URL = "https://www.data.gouv.fr/api/1/datasets/r/{}"

REGIONS = {
    "idf":       {"75", "77", "78", "91", "92", "93", "94", "95"},
    "occitanie": {"09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"},
    "bretagne":  {"22", "29", "35", "56"},
    "ara":       {"01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"},
}

DEPTS_CIBLES = {d for depts in REGIONS.values() for d in depts}

HEADERS = {
    "User-Agent": "TP-DL-Student-Project/1.0 (uni coursework)",
}


def fetch_year(year: int, resource_id: str, retries: int = 4) -> Path:
    dest = BRONZE / f"dvf_{year}_cibles.txt"
    if dest.exists() and dest.stat().st_size > 10_000:
        print(f"skip {year}, déjà {dest.stat().st_size / 1e6:.2f} Mo")
        return dest

    url = BASE_URL.format(resource_id)
    print(f"{year} : téléchargement depuis {url}", flush=True)

    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
            break
        except Exception as exc:
            last_err = exc
            wait = min(120, 10 * 2 ** attempt)
            print(f"  ! {exc} — retry {attempt + 1}/{retries} dans {wait}s")
            time.sleep(wait)
    else:
        raise RuntimeError(f"Echec {year} après {retries} essais : {last_err}")

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        txt_name = next(n for n in zf.namelist() if n.endswith(".txt"))
        content = zf.read(txt_name).decode("latin-1")

    lines = content.splitlines()
    header, rows = lines[0], lines[1:]

    cols = header.split("|")
    try:
        dept_idx = cols.index("Code departement")
    except ValueError:
        dept_idx = 19  # position standard dans le fichier DVF

    kept_rows = [r for r in rows if r.split("|")[dept_idx].strip() in DEPTS_CIBLES]

    with open(dest, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(kept_rows))

    total = len(rows)
    kept = len(kept_rows)
    print(f"✔ {year} : {kept:,} lignes / {total:,} total ({kept/total*100:.1f}%) → {dest.stat().st_size/1e6:.2f} Mo")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, choices=list(MILLÉSIMES), help="millésime unique à télécharger")
    args = parser.parse_args()

    years = {args.year: MILLÉSIMES[args.year]} if args.year else MILLÉSIMES

    for year, rid in sorted(years.items()):
        fetch_year(year, rid)
        time.sleep(3)


if __name__ == "__main__":
    main()
