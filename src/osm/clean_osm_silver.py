"""Silver OSM IdF : fusion 32 JSON bronze -> 1 Parquet nettoyé.

Traitements (issus du profilage) :
- bruit éducation : garde school/kindergarten/college/university -> reste en 'autre' exclu
- bruit santé : garde pharmacy/hospital/clinic/doctors (gère 'pharmacy;...' composés)
- vacant : shop=vacant -> is_vacant=True, exclu du comptage commerce
- noms manquants : gardés, flag name_missing=True
- doublons frontières : dedup sur id_osm
- ways/relations : lat/lon via 'center' (out center)
Sortie : silver/osm_idf_poi.parquet + stats JSON pour le rapport.
"""
import json
from collections import Counter
from pathlib import Path
import pandas as pd

BRONZE = Path(__file__).resolve().parent.parent.parent / "bronze" / "idf"
SILVER = Path(__file__).resolve().parent.parent.parent / "silver"
SILVER.mkdir(parents=True, exist_ok=True)

CAT_OF_FILE = {"ecoles": "education", "sante": "sante", "shops": "commerce", "transport": "transport"}
KEEP_EDU = {"school", "kindergarten", "college", "university"}
KEEP_SANTE = {"pharmacy", "hospital", "clinic", "doctors"}


def split_multi(v: str):
    return [x.strip() for x in str(v).split(";") if x.strip()]


def process():
    rows, stats = [], Counter(brut=0)
    files = sorted(BRONZE.glob("osm_idf_*.json"))
    assert files, f"aucun JSON dans {BRONZE}"
    for fp in files:
        parts = fp.stem.split("_")  # osm_idf_75_ecoles
        dept, filecat = parts[2], parts[3]
        cat = CAT_OF_FILE[filecat]
        d = json.loads(fp.read_text(encoding="utf-8"))
        version = d.get("osm3s", {}).get("timestamp_osm_base", "?")
        for e in d.get("elements", []):
            stats["brut"] += 1
            tags = e.get("tags", {})
            lat = e.get("lat", (e.get("center") or {}).get("lat"))
            lon = e.get("lon", (e.get("center") or {}).get("lon"))
            if lat is None or lon is None:
                stats["sans_geo_drop"] += 1
                continue
            sous = tags.get("amenity", tags.get("shop", tags.get("public_transport", "?")))
            sous_main = split_multi(sous)[0] if sous != "?" else "?"
            # filtre bruit
            if cat == "education" and sous_main not in KEEP_EDU:
                stats["bruit_edu_drop"] += 1
                continue
            if cat == "sante" and not (set(split_multi(sous)) & KEEP_SANTE):
                stats["bruit_sante_drop"] += 1
                continue
            is_vacant = (tags.get("shop") == "vacant")
            name = tags.get("name")
            rows.append({
                "id_osm": f"{e.get('type')}/{e.get('id')}",
                "nom": name,
                "lat": float(lat), "lon": float(lon),
                "categorie": cat,
                "sous_type": sous_main,
                "dept": dept,
                "is_vacant": bool(is_vacant),
                "name_missing": name is None,
                "date_extract": version,
            })
    df = pd.DataFrame(rows)
    avant_dedup = len(df)
    df = df.drop_duplicates(subset=["id_osm"], keep="first")
    stats["apres_dedup"] = len(df)
    stats["doublons_drop"] = avant_dedup - len(df)
    stats["vacant_flag"] = int(df["is_vacant"].sum())
    stats["name_missing"] = int(df["name_missing"].sum())
    out = SILVER / "osm_idf_poi.parquet"
    df.to_parquet(out, index=False)
    (SILVER / "osm_idf_silver_stats.json").write_text(json.dumps(dict(stats), indent=2), encoding="utf-8")
    print(f"brut: {stats['brut']} -> silver: {len(df)}")
    print(f"par catégorie:\n{df['categorie'].value_counts()}")
    print(f"vacant: {stats['vacant_flag']}, name_missing: {stats['name_missing']}, doublons: {stats['doublons_drop']}")
    print(f"OK {out} ({out.stat().st_size/1e6:.1f} Mo)")


if __name__ == "__main__":
    process()
