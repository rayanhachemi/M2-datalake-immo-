"""Nettoyage INSEE : une ligne par commune, indicateurs en colonnes, clé code_commune.

Usage:
    python src/insee/silver.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from main import OUTPUT

SILVER = Path(__file__).resolve().parents[2] / "silver"
HORS_FILTRE = {"GEO", "TIME_PERIOD", "FREQ", "UNIT_MEASURE"}

# (jeu, colonne produite, modalités imposées) ; les autres dimensions doivent valoir _T
INDICATEURS = [
    ("DS_FILOSOFI_CC", "revenu_median", {"FILOSOFI_MEASURE": "MED_SL"}),
    ("DS_FILOSOFI_CC", "taux_pauvrete", {"FILOSOFI_MEASURE": "PR_MD60"}),
    ("DS_POPULATIONS_HISTORIQUES", "population_municipale", {"POPREF_MEASURE": "PMUN"}),
    ("DS_RP_POPULATION_PRINC", "population", {"RP_MEASURE": "POP", "AGE": "_T"}),
    ("DS_RP_POPULATION_PRINC", "pop_moins_15", {"RP_MEASURE": "POP", "AGE": "Y_LT15"}),
    ("DS_RP_POPULATION_PRINC", "pop_15_24", {"RP_MEASURE": "POP", "AGE": "Y15T24"}),
    ("DS_RP_POPULATION_PRINC", "pop_25_39", {"RP_MEASURE": "POP", "AGE": "Y25T39"}),
    ("DS_RP_POPULATION_PRINC", "pop_40_54", {"RP_MEASURE": "POP", "AGE": "Y40T54"}),
    ("DS_RP_POPULATION_PRINC", "pop_55_64", {"RP_MEASURE": "POP", "AGE": "Y55T64"}),
    ("DS_RP_POPULATION_PRINC", "pop_65_plus", {"RP_MEASURE": "POP", "AGE": "Y_GE65"}),
    ("DS_RP_LOGEMENT_PRINC", "logements", {"RP_MEASURE": "DWELLINGS", "OCS": "_T"}),
    ("DS_RP_LOGEMENT_PRINC", "residences_principales", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN"}),
    ("DS_RP_LOGEMENT_PRINC", "residences_secondaires", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_SEC_DW_OCC"}),
    ("DS_RP_LOGEMENT_PRINC", "logements_vacants", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_VAC"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_avant_1919", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "BUILD_END": "Y_LT1919"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_1919_1945", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "BUILD_END": "Y1919T1945"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_1946_1970", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "BUILD_END": "Y1946T1970"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_1971_1990", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "BUILD_END": "Y1971T1990"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_1991_2005", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "BUILD_END": "Y1991T2005"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_apres_2006", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "BUILD_END": "Y2006TAAAA"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_1_piece", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "NOR": "R1"}),
    ("DS_RP_LOGEMENT_PRINC", "rp_5_pieces_ou_plus", {"RP_MEASURE": "DWELLINGS", "OCS": "DW_MAIN", "NOR": "R_GE5"}),
    ("DS_RP_DIPLOMES_PRINC", "pop_15_plus_diplome", {"RP_MEASURE": "POP", "SEX": "_T", "AGE": "Y_GE15", "EDUC": "_T"}),
    ("DS_RP_DIPLOMES_PRINC", "diplome_superieur", {"RP_MEASURE": "POP", "SEX": "_T", "AGE": "Y_GE15", "EDUC": "500T702_RP"}),
    ("DS_RP_EMPLOI_LR_PRINC", "actifs_15_64", {"RP_MEASURE": "POP", "SEX": "_T", "AGE": "Y15T64", "EMPSTA_ENQ": "1T2"}),
    ("DS_RP_EMPLOI_LR_PRINC", "chomeurs_15_64", {"RP_MEASURE": "POP", "SEX": "_T", "AGE": "Y15T64", "EMPSTA_ENQ": "2"}),
]


def correspond(dims, filtres):
    """Vrai si l'observation porte les modalités demandées, les autres dimensions valant _T."""
    for dim, modalite in dims.items():
        if dim in HORS_FILTRE:
            continue
        attendu = filtres.get(dim, "_T")
        if modalite != attendu:
            return False
    return all(dim in dims for dim in filtres)


def extraire(stats):
    """Parcourt le bronze et range chaque valeur retenue dans sa colonne."""
    valeurs = defaultdict(dict)
    manquantes = defaultdict(Counter)
    jeux = {jeu for jeu, _, _ in INDICATEURS}

    for jeu in sorted(jeux):
        attendus = [(colonne, filtres) for j, colonne, filtres in INDICATEURS if j == jeu]
        lues = 0
        for chemin in sorted((OUTPUT / jeu).rglob("part_*.json")):
            for obs in json.loads(chemin.read_text(encoding="utf-8"))["observations"]:
                dims = obs["dimensions"]
                millesime, niveau, code = (dims["GEO"].split("-") + ["", ""])[:3]
                if niveau != "COM":
                    stats["hors_niveau_commune"] += 1
                    continue
                for colonne, filtres in attendus:
                    if not correspond(dims, filtres):
                        continue
                    valeur = obs["measures"]["OBS_VALUE_NIVEAU"].get("value")
                    if valeur is None:
                        attributs = obs.get("attributes", {})
                        motif = ("secret_statistique" if attributs.get("CONF_STATUS") == "C"
                                 else "non_diffuse_a_la_commune")
                        manquantes[colonne][motif] += 1
                    else:
                        valeurs[code][colonne] = valeur
                        lues += 1
        stats["valeurs_par_jeu"][jeu] = lues
        print(f"   {jeu:<30} {lues:>9,} valeurs retenues", flush=True)

    stats["valeurs_manquantes"] = {c: dict(m) for c, m in manquantes.items()}
    return valeurs


def construire(valeurs):
    df = pd.DataFrame.from_dict(valeurs, orient="index").rename_axis("code_commune").reset_index()
    for colonne in [c for _, c, _ in INDICATEURS if c not in df.columns]:
        df[colonne] = pd.NA
    df = df[["code_commune"] + [c for _, c, _ in INDICATEURS]]
    df["departement"] = df["code_commune"].str[:3].where(df["code_commune"].str.startswith(("97", "98")),
                                                         df["code_commune"].str[:2])

    df["taux_vacance"] = df["logements_vacants"] / df["logements"] * 100
    df["part_residences_secondaires"] = df["residences_secondaires"] / df["logements"] * 100
    df["part_moins_15"] = df["pop_moins_15"] / df["population"] * 100
    df["part_25_39"] = df["pop_25_39"] / df["population"] * 100
    df["part_65_plus"] = df["pop_65_plus"] / df["population"] * 100
    df["part_diplome_superieur"] = df["diplome_superieur"] / df["pop_15_plus_diplome"] * 100
    df["taux_chomage"] = df["chomeurs_15_64"] / df["actifs_15_64"] * 100
    df["rp_avant_1946"] = df["rp_avant_1919"] + df["rp_1919_1945"]

    numeriques = [c for c in df.columns if c not in ("code_commune", "departement")]
    df[numeriques] = df[numeriques].apply(pd.to_numeric, errors="coerce").round(2)
    return df.astype({"code_commune": "string", "departement": "string"}).sort_values("code_commune")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # console Windows cp1252
    stats = {"hors_niveau_commune": 0, "valeurs_par_jeu": {}}

    print("lecture du bronze", flush=True)
    df = construire(extraire(stats))

    stats["communes"] = len(df)
    stats["colonnes"] = len(df.columns)
    stats["communes_par_departement"] = df["departement"].value_counts().sort_index().to_dict()
    stats["remplissage_pct"] = {c: round(df[c].notna().mean() * 100, 1)
                                for c in df.columns if c not in ("code_commune", "departement")}
    incoherentes = df["population"].notna() & df["population_municipale"].notna() & (
        (df["population"] - df["population_municipale"]).abs() / df["population_municipale"] > 0.1)
    stats["ecart_population_superieur_10pct"] = int(incoherentes.sum())

    SILVER.mkdir(exist_ok=True)
    df.to_parquet(SILVER / "insee_communes.parquet", index=False)
    (SILVER / "insee_silver_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False),
                                                    encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\n✔ {len(df):,} communes × {len(df.columns)} colonnes → {SILVER / 'insee_communes.parquet'}")


if __name__ == "__main__":
    main()
