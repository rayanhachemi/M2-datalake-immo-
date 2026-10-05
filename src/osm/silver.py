"""Silver OSM — POI nettoyés, rattachés à leur commune (clé de jointure avec DVF / INSEE).

Lit bronze/osm/{region}/osm_{region}_{dept}_{cat}.json et écrit :
    silver/osm_poi.parquet           une ligne par objet OSM retenu
    silver/osm_silver_stats.json     volumes avant / après chaque règle (traçabilité)

Règles (cf. docs/osm/qualite.md) :
    - commune par jointure spatiale sur les contours communaux (adresses absentes à ~80 %),
      plus proche commune à moins de 1 km pour les points en bord de côte / frontière
    - dédoublonnage id_osm (objets présents dans deux départements)
    - sous-type multi-valeurs a;b;c → première valeur
    - écoles / santé : liste blanche (exclut driving_school, music_school...)
    - shop=vacant / shop=yes : gardés et flagués
    - transport : mode (inconnu si absent) + id_arret, regroupement des stop_position
      de même nom à moins de 100 m → compter nunique(id_arret), pas les lignes
    - objets sans nom : gardés et flagués

Contours : geo.api.gouv.fr (communes actuelles, Paris = 75056 comme dans INSEE), mis en cache
dans bronze/contours/communes_{dept}.geojson.

Usage :
    python src/osm/silver.py
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from main import BRONZE, CATS, HEADERS, REGIONS
from profiling import MODES_TRANSPORT, PERIMETRE, SOUS_TYPE_TAG

ROOT = Path(__file__).resolve().parents[2]
CONTOURS = ROOT / "bronze" / "contours"
SILVER = ROOT / "silver"
GEO_API = "https://geo.api.gouv.fr/departements/{dept}/communes"

CATEGORIE = {"ecoles": "education", "sante": "sante", "shops": "commerce", "transport": "transport"}
SEUIL_ARRET_M = 100      # stop_position de même nom plus proches que ça = un seul arrêt
SEUIL_NEAREST_M = 1000   # au-delà, un point hors contours est considéré hors zone
CRS_METRIQUE = "EPSG:2154"  # Lambert-93


def contours_dept(dept: str) -> gpd.GeoDataFrame:
    """Contours communaux d'un département (téléchargés une fois puis lus depuis le cache)."""
    dest = CONTOURS / f"communes_{dept}.geojson"
    if not dest.exists():
        CONTOURS.mkdir(parents=True, exist_ok=True)
        r = requests.get(GEO_API.format(dept=dept), headers=HEADERS, timeout=120,
                         params={"format": "geojson", "geometry": "contour", "fields": "code,nom,codeDepartement"})
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"  contours {dept} téléchargés ({dest.stat().st_size / 1e6:.1f} Mo)", flush=True)
    g = gpd.read_file(dest)
    return g.rename(columns={"code": "code_commune", "nom": "nom_commune", "codeDepartement": "dept"})[
        ["code_commune", "nom_commune", "dept", "geometry"]]


def load_bronze(region: str, depts: list[str]) -> pd.DataFrame:
    """Aplatit les JSON Overpass d'une région (un objet = une ligne)."""
    rows = []
    for dept in depts:
        for cat in CATS:
            path = BRONZE / region / f"osm_{region}_{dept}_{cat}.json"
            if not path.exists():
                print(f"  ⚠ manquant : {path.name}", flush=True)
                continue
            d = json.loads(path.read_text(encoding="utf-8"))
            date_extract = d.get("osm3s", {}).get("timestamp_osm_base")
            for e in d.get("elements", []):
                tags = e.get("tags", {})
                geo = e if "lat" in e else e.get("center", {})
                nom = (tags.get("name") or "").strip() or None
                rows.append({
                    "id_osm": f"{e['type']}/{e['id']}", "type_osm": e["type"],
                    "nom": nom, "lat": geo.get("lat"), "lon": geo.get("lon"),
                    "categorie": CATEGORIE[cat], "cat": cat,
                    "sous_type_brut": tags.get(SOUS_TYPE_TAG[cat]),
                    "mode": next((m for m in MODES_TRANSPORT if tags.get(m) == "yes"), None)
                            if cat == "transport" else None,
                    "region": region, "dept_extract": dept, "date_extract": date_extract,
                })
    return pd.DataFrame(rows)


def rattacher_communes(df: pd.DataFrame, communes: gpd.GeoDataFrame, stats: dict) -> gpd.GeoDataFrame:
    """Jointure spatiale point-dans-polygone, puis plus proche commune (< SEUIL_NEAREST_M) pour le reste."""
    pts = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs="EPSG:4326")
    j = gpd.sjoin(pts, communes, how="left", predicate="within").drop(columns="index_right")
    j = j[~j.index.duplicated()]  # point pile sur une limite → 2 communes, on garde la 1re

    orphelins = j["code_commune"].isna()
    stats["commune_par_contour"] += int((~orphelins).sum())
    if orphelins.any():
        o = j.loc[orphelins, df.columns.tolist() + ["geometry"]].to_crs(CRS_METRIQUE)
        near = gpd.sjoin_nearest(o, communes.to_crs(CRS_METRIQUE), how="left",
                                 max_distance=SEUIL_NEAREST_M, distance_col="dist_m")
        near = near[~near.index.duplicated()]
        ok = near["code_commune"].notna()
        stats["commune_par_proximite"] += int(ok.sum())
        stats["drop_hors_communes"] += int((~ok).sum())
        for c in ["code_commune", "nom_commune", "dept"]:
            j.loc[near.index[ok], c] = near.loc[ok, c]
        j = j[j["code_commune"].notna()]
    return j.drop(columns="geometry")


def _norm_nom(s: pd.Series) -> pd.Series:
    """Nom comparable : minuscules, sans accents ni ponctuation."""
    def f(x):
        x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()
        return re.sub(r"[^a-z0-9]+", " ", x).strip()
    return s.map(f, na_action="ignore")


def _composantes(xy: np.ndarray, seuil: float) -> np.ndarray:
    """Composantes connexes (lien simple) des points à moins de `seuil` mètres."""
    n = len(xy)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n - 1):
        d = np.hypot(*(xy[i + 1:] - xy[i]).T)
        for k in np.nonzero(d < seuil)[0]:
            a, b = find(i), find(i + 1 + k)
            if a != b:
                parent[b] = a
    return np.array([find(i) for i in range(n)])


def regrouper_arrets(tr: pd.DataFrame) -> pd.Series:
    """id_arret : id_osm du représentant du groupe (même nom, chaîne de points < SEUIL_ARRET_M)."""
    id_arret = tr["id_osm"].copy()
    xy = gpd.GeoSeries(gpd.points_from_xy(tr["lon"], tr["lat"]), crs="EPSG:4326").to_crs(CRS_METRIQUE)
    xy = np.column_stack([xy.x.values, xy.y.values])
    pos = pd.Series(np.arange(len(tr)), index=tr.index)
    cle = _norm_nom(tr["nom"])
    # sans nom : impossible de distinguer deux arrêts voisins → chaque objet reste un arrêt
    for _, idx in cle.dropna().groupby(cle.dropna()).groups.items():
        if len(idx) < 2:
            continue
        p = pos[idx].values
        comp = _composantes(xy[p], SEUIL_ARRET_M)
        rep = pd.Series(idx).groupby(comp).transform("first").values
        id_arret.loc[idx] = tr.loc[rep, "id_osm"].values
    return id_arret


def build_region(region: str, depts: list[str], stats: dict) -> pd.DataFrame:
    df = load_bronze(region, depts)
    stats["brut"] += len(df)
    stats["par_region_brut"][region] = len(df)

    # sous-type : première valeur des listes a;b;c
    multi = df["sous_type_brut"].str.contains(";", na=False)
    stats["sous_type_multi_valeurs"] += int(multi.sum())
    df["sous_type"] = df["sous_type_brut"].str.split(";").str[0].str.strip()

    # liste blanche écoles / santé
    hors = pd.Series(False, index=df.index)
    for cat, ok in PERIMETRE.items():
        hors |= (df["cat"] == cat) & ~df["sous_type"].isin(ok)
    stats["drop_hors_perimetre"] += int(hors.sum())
    df = df[~hors]

    communes = pd.concat([contours_dept(d) for d in depts], ignore_index=True)
    df = rattacher_communes(df, communes, stats)
    return df


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows cp1252
    try:  # réseau d'entreprise avec inspection SSL
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass

    stats = {k: 0 for k in ["brut", "sous_type_multi_valeurs", "drop_hors_perimetre", "commune_par_contour",
                            "commune_par_proximite", "drop_hors_communes"]}
    stats["par_region_brut"] = {}
    parts = []
    for region, depts in REGIONS.items():
        print(f"== {region} ({len(depts)} depts)", flush=True)
        parts.append(build_region(region, depts, stats))
    df = pd.concat(parts, ignore_index=True)
    del parts

    # doublons : même objet extrait par deux départements (frontière) — la commune vient
    # de la jointure spatiale, donc les deux copies sont identiques sauf dept_extract
    dup = df.duplicated(["categorie", "id_osm"])
    stats["drop_doublons_id_osm"] = int(dup.sum())
    df = df[~dup].reset_index(drop=True)

    # flags
    df["name_missing"] = df["nom"].isna()
    df["is_vacant"] = (df["cat"] == "shops") & (df["sous_type"] == "vacant")
    df["is_untyped"] = (df["cat"] == "shops") & (df["sous_type"] == "yes")

    # transport : mode + regroupement des stop_position en arrêts
    tr = df["categorie"] == "transport"
    df.loc[tr, "mode"] = df.loc[tr, "mode"].fillna("inconnu")
    df["id_arret"] = pd.Series(pd.NA, index=df.index, dtype="string")
    for region in REGIONS:
        m = tr & (df["region"] == region)
        df.loc[m, "id_arret"] = regrouper_arrets(df[m]).values
    stats["transport_stop_positions"] = int(tr.sum())
    stats["transport_arrets"] = int(df.loc[tr, "id_arret"].nunique())
    stats["transport_mode_inconnu"] = int((df.loc[tr, "mode"] == "inconnu").sum())

    stats["name_missing"] = int(df["name_missing"].sum())
    stats["vacant_flag"] = int(df["is_vacant"].sum())
    stats["untyped_flag"] = int(df["is_untyped"].sum())
    stats["silver"] = len(df)
    stats["communes_couvertes"] = int(df["code_commune"].nunique())
    stats["par_categorie"] = df["categorie"].value_counts().to_dict()
    stats["par_region"] = df["region"].value_counts().to_dict()

    cols = ["id_osm", "type_osm", "nom", "lat", "lon", "categorie", "sous_type", "mode", "id_arret",
            "code_commune", "nom_commune", "dept", "region", "is_vacant", "is_untyped", "name_missing",
            "date_extract"]
    df = df[cols].astype({"code_commune": "string", "nom_commune": "string", "dept": "string",
                          "date_extract": "string"})
    SILVER.mkdir(exist_ok=True)
    df.to_parquet(SILVER / "osm_poi.parquet", index=False)
    (SILVER / "osm_silver_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False),
                                                  encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\n✔ {len(df):,} POI → {SILVER / 'osm_poi.parquet'}")


if __name__ == "__main__":
    main()
