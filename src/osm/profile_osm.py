"""Profilage bronze OSM IdF - diag qualité avant silver."""
import json
import sys
from collections import Counter
from pathlib import Path

BRONZE = Path(__file__).resolve().parent.parent.parent / "bronze" / "idf"


def profile(path: Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    els = d.get("elements", [])
    types = Counter(e.get("type") for e in els)
    no_name = sum(1 for e in els if not e.get("tags", {}).get("name"))
    no_tags = sum(1 for e in els if not e.get("tags"))
    vacant = sum(1 for e in els if e.get("tags", {}).get("shop") == "vacant")
    no_geo = sum(1 for e in els if "lat" not in e and "center" not in e)
    sous = Counter()
    for e in els:
        t = e.get("tags", {})
        sous[t.get("amenity", t.get("shop", t.get("public_transport", "?")))] += 1
    print(f"\n== {path.name} ==")
    print(f"total: {len(els)}, types: {dict(types)}")
    print(f"sans name: {no_name} ({no_name/max(len(els),1):.1%}), sans tags: {no_tags}, shop=vacant: {vacant}, sans geo: {no_geo}")
    print(f"top sous-types: {sous.most_common(10)}")
    print(f"version OSM: {d.get('osm3s', {}).get('timestamp_osm_base')}")


if __name__ == "__main__":
    files = sorted(BRONZE.glob("*.json"))
    if not files:
        print(f"aucun JSON dans {BRONZE}. Lance: python3 Scrape/main_idf.py 75 ecoles")
        sys.exit(1)
    for f in files:
        profile(f)
