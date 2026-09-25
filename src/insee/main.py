"""Télécharge des données INSEE via l'API Melodi dans bronze/insee/.

Source : API Melodi de l'INSEE — gratuite, sans authentification, limitée à 30 requêtes/minute.
Jeu utilisé par défaut : DS_FILOSOFI_CC (niveau de vie, taux de pauvreté, revenu disponible, 2023).

Les réponses sont du JSON imbriqué (format statistique SDMX) :
    observations[] > dimensions{GEO, TIME_PERIOD, FILOSOFI_MEASURE…} + attributes{} + measures{OBS_VALUE_NIVEAU{value}}
Elles sont conservées telles quelles, une observation par ligne (JSON Lines), pour la zone bronze.

⚠ Piège de l'API : la PREMIÈRE page ne contient pas de lien `next`, contrairement aux suivantes.
   On numérote donc les pages nous-mêmes et on s'arrête sur `isLast` ou sur une page vide.

Usage :
    python src/insee/main.py                                           # MED_SL et PR_MD60
    python src/insee/main.py --measures MED_SL                        # un seul indicateur
    python src/insee/main.py --dataset DS_FILOSOFI_CC --catalog       # liste les jeux disponibles
"""

import argparse
import json
import time
import urllib.request
from collections import Counter
from pathlib import Path

API = "https://api.insee.fr/melodi"
BRONZE = Path(__file__).resolve().parents[2] / "bronze" / "insee"
PAGE_SIZE = 5000
PAUSE = 2.0  # secondes entre deux requêtes (limite : 30 requêtes/minute)

REGIONS = {
    "idf":       {"75", "77", "78", "91", "92", "93", "94", "95"},
    "occitanie": {"09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"},
    "bretagne":  {"22", "29", "35", "56"},
    "ara":       {"01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"},
}
DEPTS_CIBLES = {d for depts in REGIONS.values() for d in depts}


def http_json(url: str, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                return json.load(r)
        except Exception as exc:
            wait = min(120, 5 * 2 ** attempt)
            print(f"  ! {exc} — nouvel essai dans {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"échec après {retries} essais : {url}")


def show_catalog() -> None:
    """Affiche les jeux de données disponibles (identifiant, titre, nombre d'observations)."""
    for ds in http_json(f"{API}/catalog/all"):
        titre = " ".join(t["content"] for t in ds.get("title", []) if t.get("lang") == "fr")
        print(f"{ds.get('identifier', ''):35} | {ds.get('numObservations', ''):>10} obs | {titre[:80]}")


def download(dataset: str, measures: list[str], out_file: Path) -> None:
    total, pages = 0, 0
    avec_valeur, sans_valeur = Counter(), Counter()

    with open(out_file, "w", encoding="utf-8") as out:
        for mesure in measures:
            page = 1
            while True:
                url = f"{API}/data/{dataset}?FILOSOFI_MEASURE={mesure}&maxResult={PAGE_SIZE}&page={page}"
                d = http_json(url)

                observations = d.get("observations", [])
                if not observations:
                    break

                for o in observations:
                    geo = o["dimensions"]["GEO"]
                    # filtre : garder uniquement les communes des 4 régions cibles
                    if "-COM-" not in geo:
                        continue
                    dept = geo.split("-COM-")[1][:2]
                    if dept not in DEPTS_CIBLES:
                        continue
                    val = o["measures"].get("OBS_VALUE_NIVEAU", {}).get("value")
                    cible = avec_valeur if val is not None else sans_valeur
                    cible[mesure] += 1
                    out.write(json.dumps(o, ensure_ascii=False) + "\n")
                    total += 1

                pages += 1
                print(f"  {mesure} : page {page}, {total:,} observations", flush=True)

                if d.get("paging", {}).get("isLast"):
                    break

                page += 1
                time.sleep(PAUSE)

    print(f"✔ {total:,} observations, {pages} pages -> {out_file}")
    print(f"  communes avec valeur : {dict(avec_valeur)}")
    print(f"  communes sans valeur (secret statistique) : {dict(sans_valeur)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="DS_FILOSOFI_CC")
    parser.add_argument("--measures", nargs="*", default=["MED_SL", "PR_MD60"],
                        help="MED_SL = niveau de vie médian, PR_MD60 = taux de pauvreté")
    parser.add_argument("--catalog", action="store_true", help="liste les jeux de données et quitte")
    args = parser.parse_args()

    if args.catalog:
        show_catalog()
        return

    BRONZE.mkdir(parents=True, exist_ok=True)
    out_file = BRONZE / f"{args.dataset.lower()}_2023.jsonl"
    print(f"{args.dataset} | indicateurs : {', '.join(args.measures)}", flush=True)
    download(args.dataset, args.measures, out_file)


if __name__ == "__main__":
    main()
