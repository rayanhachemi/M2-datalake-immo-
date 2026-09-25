"""Bronze OSM — découpage par région x département x catégorie.

Pourquoi découpé : une région entière en 1 requête = timeout/429 (testé sur IdF).
Donc région > dept > catégorie = petites requêtes, sleep 15s, reprise auto.

4 régions cibles : idf (8 depts), occitanie (13), bretagne (4), ara (12) → 37 depts × 4 cats = 148 requêtes.
"""
import time
from pathlib import Path
import requests

HEADERS = {"User-Agent": "TP-DL-Student-Project/1.0 (uni coursework)", "Accept": "application/json"}
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
BRONZE = Path(__file__).resolve().parent.parent.parent / "bronze" / "osm"

REGIONS = {
    "idf":       ["75", "77", "78", "91", "92", "93", "94", "95"],
    "occitanie": ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"],
    "bretagne":  ["22", "29", "35", "56"],
    "ara":       ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"],
}

CATS = {
    "ecoles":    'nwr["amenity"~"school|college|university|kindergarten"]',
    "sante":     'nwr["amenity"~"pharmacy|hospital|clinic|doctors"]',
    "shops":     'nwr["shop"]',
    "transport": 'nwr["public_transport"="stop_position"]',
}


def fetch_one(region: str, dept: str, cat: str, timeout: int = 120, retries: int = 4) -> Path:
    dest = BRONZE / region / f"osm_{region}_{dept}_{cat}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"skip {region}/{dept}/{cat}, déjà {dest.stat().st_size/1e6:.2f} Mo")
        return dest
    filt = CATS[cat]
    q = f'[out:json][timeout:{timeout}];area["ref:INSEE"="{dept}"]["boundary"="administrative"]->.a;({filt}(area.a););out center;'
    last = None
    for att in range(retries):
        url = URLS[att % len(URLS)]
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=timeout + 30)
            if r.status_code in (406, 429, 502, 503, 504):
                last = f"{r.status_code} via {url}"
                print(f"  {region}/{dept}/{cat} {last} retry {att+1}/{retries}")
                time.sleep(15 * (att + 1))
                continue
            r.raise_for_status()
            dest.write_text(r.text, encoding="utf-8")
            n = len(r.json().get("elements", []))
            print(f"OK {region}/{dept}/{cat}: {n} objets, {dest.stat().st_size/1e6:.2f} Mo")
            return dest
        except Exception as e:
            last = str(e)
            print(f"  {region}/{dept}/{cat} ERR {e} retry {att+1}")
            time.sleep(15 * (att + 1))
    raise SystemExit(f"Echec {region}/{dept}/{cat}: {last}")


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]  # ex: python main_idf.py idf 75 ecoles

    if len(args) == 3:
        regions_run = {args[0]: REGIONS[args[0]]}
        depts_run   = [args[1]]
        cats_run    = [args[2]]
    elif len(args) == 1 and args[0] in REGIONS:
        regions_run = {args[0]: REGIONS[args[0]]}
        depts_run   = None
        cats_run    = list(CATS)
    else:
        regions_run = REGIONS
        depts_run   = None
        cats_run    = list(CATS)

    for region, depts in regions_run.items():
        for dept in (depts_run or depts):
            for cat in cats_run:
                fetch_one(region, dept, cat)
                time.sleep(15)  # politesse Overpass
