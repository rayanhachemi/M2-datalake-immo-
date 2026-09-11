"""Bronze Ile-de-France - découpage par département x catégorie.

Pourquoi découpé : IdF entière en 1 requête = timeout/429 (testé).
Ecoles seules = 14643 objets. Shops = centaines de milliers.
Donc 8 depts x 4 cats = 32 petites requêtes, sleep 15s, reprise auto.
"""
import json
import time
from pathlib import Path
import requests

HEADERS = {"User-Agent": "TP-DL-Student-Project/1.0 (uni coursework)", "Accept": "application/json"}
URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
BRONZE = Path(__file__).resolve().parent.parent.parent / "bronze" / "idf"
BRONZE.mkdir(parents=True, exist_ok=True)

# requêtes par zone area INSEE (pas de doublons frontières comme BBOX)
DEPTS = ["75", "77", "78", "91", "92", "93", "94", "95"]
CATS = {
    "ecoles": 'nwr["amenity"~"school|college|university|kindergarten"]',
    "sante": 'nwr["amenity"~"pharmacy|hospital|clinic|doctors"]',
    "shops": 'nwr["shop"]',
    "transport": 'nwr["public_transport"="stop_position"]',
}


def fetch_one(dept, cat, timeout=120, retries=4):
    dest = BRONZE / f"osm_idf_{dept}_{cat}.json"
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"skip {dept}/{cat}, déjà {dest.stat().st_size/1e6:.2f} Mo")
        return dest
    filt = CATS[cat]
    q = f'[out:json][timeout:{timeout}];area["ref:INSEE"="{dept}"]["boundary"="administrative"]->.a;({filt}(area.a););out center;'
    last = None
    for att in range(retries):
        url = URLS[(att) % len(URLS)]
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=timeout + 30)
            if r.status_code in (406, 429, 502, 503, 504):
                last = f"{r.status_code} via {url}"
                print(f"  {dept}/{cat} {last} retry {att+1}/{retries}")
                time.sleep(15 * (att + 1))
                continue
            r.raise_for_status()
            dest.write_text(r.text, encoding="utf-8")
            n = len(r.json().get("elements", []))
            print(f"OK {dept}/{cat}: {n} objets, {dest.stat().st_size/1e6:.2f} Mo")
            return dest
        except Exception as e:
            last = str(e)
            print(f"  {dept}/{cat} ERR {e} retry {att+1}")
            time.sleep(15 * (att + 1))
    raise SystemExit(f"Echec {dept}/{cat}: {last}")


if __name__ == "__main__":
    import sys
    only = sys.argv[1:]  # ex: python main_idf.py 75 ecoles
    if len(only) == 2:
        depts, cats = [only[0]], [only[1]]
    elif len(only) == 1 and only[0] in CATS:
        depts, cats = DEPTS, [only[0]]  # ex: python main_idf.py ecoles
    else:
        depts, cats = DEPTS, list(CATS)
    for d in depts:
        for c in cats:
            fetch_one(d, c)
            time.sleep(15)  # politesse Overpass
