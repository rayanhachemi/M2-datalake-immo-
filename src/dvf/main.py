"""Téléchargement DVF bronze depuis data.gouv.fr, filtré sur les 4 régions cibles.

Usage:
    python src/dvf/main.py
    python src/dvf/main.py --year 2024
"""

import argparse
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

BRONZE = Path(__file__).resolve().parents[2] / "bronze" / "dvf"
BRONZE.mkdir(parents=True, exist_ok=True)

MILLÉSIMES_FALLBACK = {
    2021: "9085adb3-473a-4265-ae9f-af72b8df39b6",
    2022: "330aead3-b527-4c0f-8c9a-a82a9b928816",
    2023: "ddbd3eff-2d18-420c-a1d6-37f14a2fcc2c",
    2024: "24d0313f-8f07-4514-bf7d-e1d274e61ecc",
    2025: "63c368e8-72b9-4f35-8315-80c21fcc575d",
}

DATASET_ID = "5c4ae55a634f4117716d5656"
BASE_URL = "https://www.data.gouv.fr/api/1/datasets/r/{}"


def get_millésimes() -> dict:
    """Récupère les resource IDs depuis l'API data.gouv.fr (fallback sur les IDs codés en dur)."""
    try:
        url = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_ID}/"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        result = {}
        for resource in data.get("resources", []):
            title = resource.get("title", "")
            rid = resource.get("id", "")
            for year in MILLÉSIMES_FALLBACK:
                if str(year) in title:
                    result[year] = rid
                    break
        if len(result) >= 3:
            print(f"Resource IDs récupérés depuis l'API : {result}")
            return result
    except Exception as e:
        print(f"API data.gouv.fr inaccessible ({e}), utilisation des IDs de secours")
    return MILLÉSIMES_FALLBACK

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
        dept_idx = 19

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
    parser.add_argument("--year", type=int, choices=list(MILLÉSIMES_FALLBACK))
    args = parser.parse_args()

    millésimes = get_millésimes()
    years = {args.year: millésimes[args.year]} if args.year else millésimes

    for year, rid in sorted(years.items()):
        fetch_year(year, rid)
        time.sleep(3)


if __name__ == "__main__":
    main()
