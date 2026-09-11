"""Pivot commune OSM IdF : ajoute code_commune à chaque POI silver.

Correctifs qualité (profilage pivot) :
- fuite area Overpass : requêtes 75/93/94 ont ramené des objets hors IdF
  (ex node/250381713 école à Bordeaux dans fichier 75). Clip bbox IdF strict.
- collision 'nom' POI vs 'nom' commune : renommage avant jointure.
Méthode : clip bbox -> sjoin 'within' -> repli 'nearest' < 2 km -> drop hors-zone.
Sortie : silver/osm_idf_poi_geo.parquet (+ code_commune, nom_commune).
"""
from pathlib import Path
import pandas as pd
import geopandas as gpd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
BRONZE = ROOT / "bronze"
SILVER = ROOT / "silver"
GEOJSON = BRONZE / "communes_idf.geojson"
HEADERS = {"User-Agent": "TP-DL-Student-Project/1.0 (uni coursework)"}

# bbox IdF + marge
LON0, LAT0, LON1, LAT1 = 1.40, 48.08, 3.60, 49.28


def fetch_contours():
    if GEOJSON.exists() and GEOJSON.stat().st_size > 1e6:
        print(f"contours déjà là ({GEOJSON.stat().st_size/1e6:.1f} Mo)")
        return
    print("DL contours communes IdF...")
    with requests.get("https://geo.api.gouv.fr/communes",
                       params={"codeRegion": "11", "format": "geojson", "geometry": "contour"},
                       headers=HEADERS, timeout=300, stream=True) as r:
        r.raise_for_status()
        with open(GEOJSON, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    print(f"OK ({GEOJSON.stat().st_size/1e6:.1f} Mo)")


def pivot():
    fetch_contours()
    poi = pd.read_parquet(SILVER / "osm_idf_poi.parquet")
    print(f"silver entrée: {len(poi)}")
    inbbox = poi[(poi["lon"] >= LON0) & (poi["lon"] <= LON1)
                 & (poi["lat"] >= LAT0) & (poi["lat"] <= LAT1)]
    print(f"clip bbox IdF: {len(inbbox)} gardés, {len(poi)-len(inbbox)} hors-zone droppés")
    print(inbbox.groupby("dept").size().to_string())
    gpoi = gpd.GeoDataFrame(inbbox, geometry=gpd.points_from_xy(inbbox["lon"], inbbox["lat"]), crs="EPSG:4326")
    com = gpd.read_file(GEOJSON).to_crs("EPSG:4326")[["code", "nom", "geometry"]]
    com = com.rename(columns={"code": "code_commune", "nom": "nom_commune"})
    joined = gpd.sjoin(gpoi, com, how="left", predicate="within")
    miss = joined["code_commune"].isna().sum()
    print(f"within: {len(joined)-miss} appariés, {miss} frontières")
    if miss:
        un = gpoi[joined["code_commune"].isna()].to_crs("EPSG:2154")
        com2154 = com.to_crs("EPSG:2154")
        near = gpd.sjoin_nearest(un, com2154, how="left", max_distance=2000)
        ok = near["code_commune"].notna().sum()
        joined.loc[joined["code_commune"].isna(), ["code_commune", "nom_commune"]] = \
            near[["code_commune", "nom_commune"]].values
        print(f"nearest<2km: {ok} récupérés, {miss-ok} droppés")
        joined = joined[joined["code_commune"].notna()]
    out = SILVER / "osm_idf_poi_geo.parquet"
    pd.DataFrame(joined.drop(columns=["geometry", "index_right"])).to_parquet(out, index=False)
    final = pd.read_parquet(out)
    print(f"communes couvertes: {final['code_commune'].nunique()}")
    print(f"top communes:\n{final['nom_commune'].value_counts().head(8).to_string()}")
    print(f"OK {out} ({out.stat().st_size/1e6:.1f} Mo, {len(final)} lignes)")


if __name__ == "__main__":
    pivot()
