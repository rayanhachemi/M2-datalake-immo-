"""Crée le référentiel communal Silver depuis les contours Bronze et DVF Silver.

Usage : python src/communes/silver.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import write_table  # noqa: E402
from dvf.main import REGIONS  # noqa: E402

CONTOURS = ROOT / "bronze" / "contours"
SILVER = ROOT / "silver"
REGION_PAR_DEPT = {dept: region for region, depts in REGIONS.items() for dept in depts}


def construire() -> pd.DataFrame:
    lignes = []
    fichiers = sorted(CONTOURS.glob("communes_*.geojson"))
    if not fichiers:
        raise FileNotFoundError("Contours Bronze absents : lancer le Silver OSM")
    for path in fichiers:
        donnees = json.loads(path.read_text(encoding="utf-8"))
        for objet in donnees["features"]:
            p = objet["properties"]
            lignes.append((p["code"], p["nom"], p["codeDepartement"]))
    communes = pd.DataFrame(lignes, columns=["code_commune", "nom_commune", "departement"])
    if communes["code_commune"].duplicated().any():
        raise ValueError("Contours : codes communes dupliqués")

    dvf = pd.read_parquet(SILVER / "dvf_ventes.parquet", columns=[
        "code_commune", "nom_commune", "code_departement"])
    historiques = (dvf.drop_duplicates("code_commune")
                   .loc[lambda x: ~x["code_commune"].isin(communes["code_commune"]),
                        ["code_commune", "nom_commune", "code_departement"]]
                   .rename(columns={"code_departement": "departement"}))
    communes = pd.concat([communes, historiques], ignore_index=True)
    communes["region"] = communes["departement"].map(REGION_PAR_DEPT)
    communes = communes[["code_commune", "nom_commune", "departement", "region"]]
    if communes.isna().any().any() or communes["code_commune"].duplicated().any():
        raise ValueError("Référentiel communal incomplet ou dupliqué")
    codes_insee = set(pd.read_parquet(SILVER / "insee_communes.parquet", columns=["code_commune"])["code_commune"])
    if not codes_insee.issubset(set(communes["code_commune"])):
        raise ValueError("Des codes INSEE Silver manquent dans le référentiel communal")
    return communes.sort_values("code_commune").reset_index(drop=True)


def main() -> None:
    communes = construire()
    SILVER.mkdir(exist_ok=True)
    communes.to_parquet(SILVER / "communes.parquet", index=False)
    write_table(communes, "S_communes")
    print(f"Silver : {len(communes):,} communes → {SILVER / 'communes.parquet'}")


if __name__ == "__main__":
    main()
