"""Bronze OSM — découpage par région x département x catégorie.

Pourquoi découpé : une région entière en 1 requête = timeout/429 (testé sur IdF).
Donc région > dept > catégorie = petites requêtes, MAX_WORKERS requêtes parallèles max (politesse Overpass).

4 régions cibles : idf (8 depts), occitanie (13), bretagne (4), ara (12) → 37 depts × 4 cats = 148 requêtes.
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

try:  # réseau d'entreprise avec inspection SSL : utilise le magasin de certificats de l'OS
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

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

MAX_WORKERS = 5  # max simultané — au-delà Overpass throttle/ban
_url_lock = threading.Lock()
_url_idx = 0


def _next_url() -> str:
    global _url_idx
    with _url_lock:
        url = URLS[_url_idx % len(URLS)]
        _url_idx += 1
        return url


def fetch_one(region: str, dept: str, cat: str, timeout: int = 180, retries: int = 4) -> Path:
    dest = BRONZE / region / f"osm_{region}_{dept}_{cat}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"skip {region}/{dept}/{cat}, déjà {dest.stat().st_size/1e6:.2f} Mo", flush=True)
        return dest
    filt = CATS[cat]
    # admin_level=6 obligatoire : les régions ont aussi un ref:INSEE à 2 chiffres (11 = IdF, 01 = Guadeloupe...)
    # map_to_area : zone calculée depuis la relation, sans dépendre de la base "areas" du miroir (parfois incomplète)
    q = (f'[out:json][timeout:{timeout}];'
         f'rel["ref:INSEE"="{dept}"]["boundary"="administrative"]["admin_level"="6"];map_to_area->.a;'
         f'({filt}(area.a););out center;')
    last = None
    for att in range(retries):
        url = _next_url()
        try:
            r = requests.post(url, data={"data": q}, headers=HEADERS, timeout=timeout + 30)
            if r.status_code in (406, 429, 502, 503, 504):
                last = f"{r.status_code} via {url}"
                print(f"  {region}/{dept}/{cat} {last} retry {att+1}/{retries}", flush=True)
                time.sleep(20 * (att + 1))
                continue
            r.raise_for_status()
            data = r.json()
            n = len(data.get("elements", []))
            # 0 objet ou "remark" = zone introuvable / timeout côté serveur, jamais un vrai résultat ici
            if n == 0 or "remark" in data:
                last = f"réponse invalide ({n} objets, remark={data.get('remark')!r}) via {url}"
                print(f"  {region}/{dept}/{cat} {last} retry {att+1}/{retries}", flush=True)
                time.sleep(20 * (att + 1))
                continue
            dest.write_text(r.text, encoding="utf-8")
            print(f"OK {region}/{dept}/{cat}: {n} objets, {dest.stat().st_size/1e6:.2f} Mo", flush=True)
            return dest
        except Exception as e:
            last = str(e)
            print(f"  {region}/{dept}/{cat} ERR {e} retry {att+1}", flush=True)
            time.sleep(20 * (att + 1))
    print(f"ECHEC {region}/{dept}/{cat}: {last}", flush=True)
    return None  # on ne crash plus, on continue les autres


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]

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

    tasks = [
        (region, dept, cat)
        for region, depts in regions_run.items()
        for dept in (depts_run or depts)
        for cat in cats_run
    ]

    echecs = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_one, r, d, c): (r, d, c) for r, d, c in tasks}
        for fut in as_completed(futures):
            r, d, c = futures[fut]
            if fut.result() is None:
                echecs.append(f"{r}/{d}/{c}")

    if echecs:
        print(f"\n⚠ Echecs ({len(echecs)}) : {', '.join(echecs)}")
        print("Relance : python src/osm/main.py (les fichiers déjà présents sont sautés)")
    else:
        print(f"\n✔ {len(tasks)} requêtes terminées.")
