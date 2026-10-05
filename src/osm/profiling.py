"""Profiling des fichiers bronze OSM : volumétrie, complétude, doublons, anomalies.

Lit bronze/osm/{region}/osm_{region}_{dept}_{cat}.json (produits par main.py) et écrit
dans docs/osm/profiling/ :
    fichiers.csv              une ligne par fichier (volumes, types, nuls, fraîcheur)
    sous_types.csv            effectifs par région × catégorie × sous-type
    completude_tags.csv       % de renseignement des tags utiles par région × catégorie

Usage :
    python src/osm/profiling.py               # les 4 régions
    python src/osm/profiling.py --region idf  # une seule région
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from main import BRONZE, CATS, REGIONS

PROFILING = Path(__file__).resolve().parents[2] / "docs" / "osm" / "profiling"

# tag portant le sous-type selon la catégorie
SOUS_TYPE_TAG = {"ecoles": "amenity", "sante": "amenity", "shops": "shop", "transport": "public_transport"}
# sous-types réellement visés : la regex Overpass "school" capte aussi driving_school, music_school...
PERIMETRE = {
    "ecoles": {"school", "college", "university", "kindergarten"},
    "sante": {"pharmacy", "hospital", "clinic", "doctors"},
}
MODES_TRANSPORT = ["bus", "tram", "train", "subway", "light_rail", "trolleybus", "ferry", "monorail"]
# tags dont on mesure la complétude (utiles pour le silver / l'analyse)
TAGS_UTILES = ["name", "opening_hours", "addr:street", "addr:housenumber", "addr:postcode",
               "addr:city", "wheelchair", "website", "phone", "operator", "brand"]
# emprise large France métropolitaine (lat_min, lat_max, lon_min, lon_max)
BBOX_FR = (41.0, 51.5, -5.5, 10.0)


def _transport_mode(tags: dict) -> str | None:
    return next((m for m in MODES_TRANSPORT if tags.get(m) == "yes"), None)


def load_file(path: Path, region: str, dept: str, cat: str) -> tuple[dict, list[dict]]:
    """Charge un JSON Overpass → (métadonnées fichier, liste d'objets aplatis)."""
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for e in d.get("elements", []):
        tags = e.get("tags", {})
        geo = e if "lat" in e else e.get("center", {})
        rows.append({
            "region": region, "dept": dept, "cat": cat,
            "type": e.get("type"), "id_osm": f"{e.get('type')}/{e.get('id')}",
            "lat": geo.get("lat"), "lon": geo.get("lon"),
            "sous_type": tags.get(SOUS_TYPE_TAG[cat]),
            "mode": _transport_mode(tags) if cat == "transport" else None,
            "nb_tags": len(tags),
            **{f"tag:{t}": t in tags and tags[t].strip() != "" for t in TAGS_UTILES},
        })
    meta = {
        "region": region, "dept": dept, "cat": cat,
        "taille_mo": round(path.stat().st_size / 1e6, 2),
        "timestamp_osm_base": d.get("osm3s", {}).get("timestamp_osm_base"),
    }
    return meta, rows


def profile(regions: dict[str, list[str]]) -> pd.DataFrame:
    """Profiling de tous les fichiers bronze OSM des régions demandées."""
    metas, rows, manquants = [], [], []
    for region, depts in regions.items():
        for dept in depts:
            for cat in CATS:
                path = BRONZE / region / f"osm_{region}_{dept}_{cat}.json"
                if not path.exists():
                    manquants.append(f"{region}/{dept}/{cat}")
                    continue
                meta, r = load_file(path, region, dept, cat)
                metas.append(meta)
                rows.extend(r)

    df = pd.DataFrame(rows)
    attendus = sum(len(d) for d in regions.values()) * len(CATS)
    print(f"\n=== OSM bronze — {len(metas)}/{attendus} fichiers, {len(df):,} objets, "
          f"{sum(m['taille_mo'] for m in metas):,.0f} Mo ===")
    if manquants:
        print(f"fichiers manquants ({len(manquants)}) : {', '.join(manquants)}")

    # --- profil par fichier ---
    g = df.groupby(["region", "dept", "cat"])
    fich = pd.DataFrame(metas).merge(
        pd.DataFrame({
            "nb_objets": g.size(),
            "nodes": g["type"].apply(lambda s: int((s == "node").sum())),
            "ways": g["type"].apply(lambda s: int((s == "way").sum())),
            "relations": g["type"].apply(lambda s: int((s == "relation").sum())),
            "pct_sans_nom": g["tag:name"].apply(lambda s: round((~s).mean() * 100, 2)),
            "sans_geo": g["lat"].apply(lambda s: int(s.isna().sum())),
            "doublons_id": g["id_osm"].apply(lambda s: int(s.duplicated().sum())),
        }).reset_index(),
        on=["region", "dept", "cat"], how="left",
    )
    fich["nb_objets"] = fich["nb_objets"].fillna(0).astype(int)

    print("\nobjets par région × catégorie :")
    print(df.pivot_table(index="region", columns="cat", values="id_osm", aggfunc="count",
                         margins=True, margins_name="total").to_string())
    print("\ntypes OSM :", df["type"].value_counts().to_dict())

    vides = fich.loc[fich["nb_objets"] == 0, ["region", "dept", "cat"]]
    if len(vides):
        print(f"\nfichiers vides ({len(vides)}) :\n{vides.to_string(index=False)}")

    ts = pd.to_datetime(fich["timestamp_osm_base"], errors="coerce")
    print(f"\nfraîcheur snapshots Overpass : {ts.min()} → {ts.max()} (écart {ts.max() - ts.min()})")

    # --- sous-types ---
    sous = (df.fillna({"sous_type": "(absent)"})
              .groupby(["region", "cat", "sous_type"]).size()
              .rename("nb").reset_index().sort_values(["region", "cat", "nb"], ascending=[True, True, False]))
    for cat in CATS:
        top = df.loc[df["cat"] == cat, "sous_type"].value_counts(dropna=False).head(10)
        print(f"\ntop sous-types {cat} :\n{top.to_string()}")
    tr = df[df["cat"] == "transport"]
    print(f"\nmodes transport :\n{tr['mode'].value_counts(dropna=False).to_string()}")

    # --- complétude des tags ---
    tag_cols = [f"tag:{t}" for t in TAGS_UTILES]
    compl = (df.groupby(["region", "cat"])[tag_cols].mean().mul(100).round(1)
               .rename(columns=lambda c: c.removeprefix("tag:")).reset_index())
    print("\ncomplétude des tags (% renseigné, toutes régions) :")
    print(df.groupby("cat")[tag_cols].mean().mul(100).round(1)
            .rename(columns=lambda c: c.removeprefix("tag:")).T.to_string())

    # --- anomalies ---
    lat_min, lat_max, lon_min, lon_max = BBOX_FR
    hors_bbox = df["lat"].notna() & ~(df["lat"].between(lat_min, lat_max) & df["lon"].between(lon_min, lon_max))
    dup_region = df.duplicated(["region", "cat", "id_osm"]) & ~df.duplicated(["dept", "cat", "id_osm"])
    dup_inter_region = df.drop_duplicates(["region", "cat", "id_osm"]).duplicated(["cat", "id_osm"])
    hors_perimetre = pd.Series(False, index=df.index)
    for cat, ok in PERIMETRE.items():
        hors_perimetre |= (df["cat"] == cat) & ~df["sous_type"].isin(ok)
    anomalies = {
        "objets sans géométrie (ni lat ni center)": int(df["lat"].isna().sum()),
        "coordonnées hors France métropolitaine": int(hors_bbox.sum()),
        "doublons id_osm dans un même fichier": int(fich["doublons_id"].sum()),
        "doublons id_osm entre départements (frontières)": int(dup_region.sum()),
        "doublons id_osm entre régions": int(dup_inter_region.sum()),
        "objets sans aucun tag": int((df["nb_tags"] == 0).sum()),
        "objets sans nom": int((~df["tag:name"]).sum()),
        "écoles/santé hors périmètre (driving_school...)": int(hors_perimetre.sum()),
        "sous-types multi-valeurs (contient ';')": int(df["sous_type"].str.contains(";", na=False).sum()),
        "shop=vacant (local vide)": int(((df["cat"] == "shops") & (df["sous_type"] == "vacant")).sum()),
        "shop=yes (commerce non typé)": int(((df["cat"] == "shops") & (df["sous_type"] == "yes")).sum()),
        "arrêts transport sans mode": int(tr["mode"].isna().sum()),
    }
    print("\nanomalies :")
    for k, v in anomalies.items():
        print(f"  {k:<52} {v:>10,}  ({v / len(df) * 100:5.2f}%)")

    PROFILING.mkdir(parents=True, exist_ok=True)
    fich.to_csv(PROFILING / "fichiers.csv", index=False, encoding="utf-8")
    sous.to_csv(PROFILING / "sous_types.csv", index=False, encoding="utf-8")
    compl.to_csv(PROFILING / "completude_tags.csv", index=False, encoding="utf-8")
    print(f"\n✔ profils → {PROFILING}/{{fichiers,sous_types,completude_tags}}.csv")
    return fich


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", choices=list(REGIONS), help="région unique à profiler")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows cp1252

    profile({args.region: REGIONS[args.region]} if args.region else REGIONS)


if __name__ == "__main__":
    main()
