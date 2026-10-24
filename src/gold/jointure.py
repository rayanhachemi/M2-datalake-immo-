"""Jointure communale des trois Silver, sans calculer encore les scores Gold.

Usage : python src/gold/jointure.py
Sorties : gold/jointure_communes.parquet, gold/jointure_stats.json,
          table PostgreSQL G_jointure_communes.
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import write_table
from dvf.main import REGIONS

SILVER = ROOT / "silver"
GOLD = ROOT / "gold"
REGION_PAR_DEPT = {dept: region for region, depts in REGIONS.items() for dept in depts}
COLONNES_DVF = ["id_vente", "code_commune", "annee", "type_bien", "nature_mutation", "revente_moins_30j"]
COLONNES_OSM = ["id_osm", "code_commune", "categorie", "id_arret", "is_vacant"]


def verifier_cle(df: pd.DataFrame, cle: str, source: str, unique: bool = False) -> None:
    if df[cle].isna().any() or not df[cle].str.fullmatch(r"\d{5}").all():
        raise ValueError(f"{source} : {cle} nul ou non conforme au code INSEE à 5 chiffres")
    if unique and df[cle].duplicated().any():
        raise ValueError(f"{source} : doublons de {cle}")


def agreger_dvf(dvf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    verifier_cle(dvf, "code_commune", "DVF")
    if dvf["id_vente"].isna().any() or dvf["id_vente"].duplicated().any():
        raise ValueError("DVF : id_vente nul ou dupliqué")

    vente = dvf["nature_mutation"] == "Vente"
    comparable = vente & ~dvf["revente_moins_30j"]
    base = dvf.loc[comparable, ["code_commune", "annee", "type_bien"]]
    recent = base[base["annee"].isin([2024, 2025])]

    toutes = base.groupby("code_commune", observed=True).size().rename("nb_ventes_comparables_2021_2025")
    recentes = recent.groupby("code_commune", observed=True).size().rename("nb_ventes_2024_2025")
    par_type = (recent.groupby(["code_commune", "type_bien"], observed=True)
                .size().unstack(fill_value=0))
    par_type = par_type.reindex(columns=["Maison", "Appartement"], fill_value=0).rename(columns={
        "Maison": "nb_ventes_maison_2024_2025",
        "Appartement": "nb_ventes_appartement_2024_2025",
    })
    agregat = pd.concat([toutes, recentes, par_type], axis=1).fillna(0).astype("int64")
    agregat.index.name = "code_commune"

    stats = {
        "lignes_silver": len(dvf),
        "vefa_exclues": int((~vente).sum()),
        "reventes_rapides_exclues_parmi_ventes": int((vente & dvf["revente_moins_30j"]).sum()),
        "ventes_comparables": len(base),
        "ventes_recentes_2024_2025": len(recent),
    }
    if int(agregat["nb_ventes_comparables_2021_2025"].sum()) != len(base):
        raise AssertionError("DVF : total des agrégats différent des ventes comparables")
    return agregat.reset_index(), base, stats


def agreger_osm(osm: pd.DataFrame) -> pd.DataFrame:
    verifier_cle(osm, "code_commune", "OSM")
    if osm[["categorie", "id_osm"]].duplicated().any():
        raise ValueError("OSM : doublon (categorie, id_osm)")

    cat = osm["categorie"]
    indicateurs = osm.assign(
        ecole=cat.eq("education"),
        sante=cat.eq("sante"),
        commerce_actif=cat.eq("commerce") & ~osm["is_vacant"].fillna(False),
    )
    agregat = indicateurs.groupby("code_commune", observed=True).agg(
        nb_poi_osm=("id_osm", "size"),
        nb_ecoles=("ecole", "sum"),
        nb_sante=("sante", "sum"),
        nb_commerces_actifs=("commerce_actif", "sum"),
        nb_arrets_transport=("id_arret", "nunique"),
    )
    if int(agregat["nb_poi_osm"].sum()) != len(osm):
        raise AssertionError("OSM : total des agrégats différent des POI Silver")
    return agregat.reset_index()


def joindre(insee: pd.DataFrame, ventes: pd.DataFrame, poi: pd.DataFrame) -> pd.DataFrame:
    verifier_cle(insee, "code_commune", "INSEE", unique=True)
    communes = insee.merge(ventes, on="code_commune", how="left", validate="one_to_one")
    communes = communes.merge(poi, on="code_commune", how="left", validate="one_to_one")
    if len(communes) != len(insee):
        raise AssertionError("La jointure a changé le nombre de communes INSEE")

    colonnes_comptage = [c for c in [*ventes.columns, *poi.columns] if c != "code_commune"]
    communes[colonnes_comptage] = communes[colonnes_comptage].fillna(0).astype("int64")
    communes["a_ventes_recentes"] = communes["nb_ventes_2024_2025"] > 0
    communes["a_poi"] = communes["nb_poi_osm"] > 0
    communes["revenu_disponible"] = communes["revenu_median"].notna()
    communes["region"] = communes["departement"].map(REGION_PAR_DEPT).astype("string")
    if communes["region"].isna().any():
        raise ValueError("INSEE : département hors des quatre régions cibles")
    return communes.sort_values("code_commune").reset_index(drop=True)


def main() -> None:
    insee = pd.read_parquet(SILVER / "insee_communes.parquet")
    dvf = pd.read_parquet(SILVER / "dvf_ventes.parquet", columns=COLONNES_DVF)
    osm = pd.read_parquet(SILVER / "osm_poi.parquet", columns=COLONNES_OSM)

    ventes, base_dvf, stats_dvf = agreger_dvf(dvf)
    poi = agreger_osm(osm)
    communes = joindre(insee, ventes, poi)

    codes_insee = set(insee["code_commune"])
    codes_dvf_hors_insee = sorted(set(ventes["code_commune"]) - codes_insee)
    codes_osm_hors_insee = sorted(set(poi["code_commune"]) - codes_insee)
    masque_hors_insee = base_dvf["code_commune"].isin(codes_dvf_hors_insee)
    stats = {
        "dvf": stats_dvf,
        "insee": {"communes_silver": len(insee)},
        "osm": {"poi_silver": len(osm), "communes_avec_poi": len(poi)},
        "jointure": {
            "communes": len(communes),
            "communes_avec_ventes_recentes": int(communes["a_ventes_recentes"].sum()),
            "communes_avec_poi": int(communes["a_poi"].sum()),
            "codes_dvf_hors_insee": codes_dvf_hors_insee,
            "ventes_comparables_hors_insee": int(masque_hors_insee.sum()),
            "codes_osm_hors_insee": codes_osm_hors_insee,
            "ventes_comparables_rattachees": int(communes["nb_ventes_comparables_2021_2025"].sum()),
            "poi_rattaches": int(communes["nb_poi_osm"].sum()),
        },
    }

    GOLD.mkdir(exist_ok=True)
    sortie = GOLD / "jointure_communes.parquet"
    communes.to_parquet(sortie, index=False)
    write_table(communes, "G_jointure_communes")
    (GOLD / "jointure_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats["jointure"], indent=2, ensure_ascii=False))
    print(f"\n✔ {len(communes):,} communes → {sortie}")


if __name__ == "__main__":
    main()
