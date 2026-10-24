"""Indicateurs Gold du marché immobilier et de l'attractivité communale.

Usage : python src/gold/indicateurs.py
Prérequis : python src/gold/jointure.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import write_table

SILVER = ROOT / "silver"
GOLD = ROOT / "gold"
SEUIL_VENTES = 10
ANNEES_RECENTES = (2024, 2025)
COLONNES_DVF = [
    "id_vente", "code_commune", "annee", "type_bien", "nature_mutation",
    "revente_moins_30j", "prix_m2", "valeur_fonciere",
]
MESURES_PRIX = ["prix_m2_median", "prix_m2_moyen", "prix_m2_q1", "prix_m2_q3", "prix_vente_median"]
EQUIPEMENTS = {
    "ecoles": "nb_ecoles",
    "sante": "nb_sante",
    "commerces_actifs": "nb_commerces_actifs",
    "arrets_transport": "nb_arrets_transport",
}


def ventes_comparables(dvf: pd.DataFrame) -> pd.DataFrame:
    if dvf["id_vente"].isna().any() or dvf["id_vente"].duplicated().any():
        raise ValueError("DVF : id_vente nul ou dupliqué")
    filtre = dvf["nature_mutation"].eq("Vente") & ~dvf["revente_moins_30j"]
    return dvf.loc[filtre, ["id_vente", "code_commune", "annee", "type_bien", "prix_m2", "valeur_fonciere"]].copy()


def marche_annuel(ventes: pd.DataFrame) -> pd.DataFrame:
    cles = ["code_commune", "annee", "type_bien"]
    groupes = ventes.groupby(cles, observed=True, sort=True)
    marche = groupes.agg(
        nb_ventes=("id_vente", "size"),
        prix_m2_median=("prix_m2", "median"),
        prix_m2_moyen=("prix_m2", "mean"),
        prix_vente_median=("valeur_fonciere", "median"),
    )
    quartiles = groupes["prix_m2"].quantile([0.25, 0.75]).unstack()
    quartiles.columns = ["prix_m2_q1", "prix_m2_q3"]
    marche = marche.join(quartiles).reset_index().sort_values(cles).reset_index(drop=True)

    marche.loc[marche["nb_ventes"] < SEUIL_VENTES, MESURES_PRIX] = np.nan
    par_type = marche.groupby(["code_commune", "type_bien"], observed=True, sort=False)
    avant = par_type["prix_m2_median"].shift()
    annee_avant = par_type["annee"].shift()
    variation = 100 * (marche["prix_m2_median"] / avant - 1)
    marche["variation_annuelle_pct"] = variation.where(marche["annee"] - annee_avant == 1).round(2)
    v = marche["variation_annuelle_pct"]
    marche["tendance_annuelle"] = np.select(
        [v >= 3, v <= -3, v.notna()],
        ["hausse", "baisse", "stable"],
        default="non_concluante",
    )
    marche[MESURES_PRIX] = marche[MESURES_PRIX].round(2)
    if marche.duplicated(cles).any() or int(marche["nb_ventes"].sum()) != len(ventes):
        raise AssertionError("Marché annuel : clé ou volume DVF incohérent")
    return marche


def prix_recents(ventes: pd.DataFrame) -> pd.DataFrame:
    recent = ventes[ventes["annee"].isin(ANNEES_RECENTES)]
    groupes = (recent.groupby(["code_commune", "type_bien"], observed=True)
              .agg(nb_ventes=("id_vente", "size"),
                   median=("prix_m2", "median"),
                   moyenne=("prix_m2", "mean"))
              .reset_index())
    groupes.loc[groupes["nb_ventes"] < SEUIL_VENTES, ["median", "moyenne"]] = np.nan
    pieces = []
    for type_bien, suffixe in (("Maison", "maison"), ("Appartement", "appartement")):
        part = groupes[groupes["type_bien"] == type_bien][["code_commune", "nb_ventes", "median", "moyenne"]]
        part = part.rename(columns={
            "nb_ventes": f"nb_ventes_{suffixe}_2024_2025_controle",
            "median": f"prix_m2_median_{suffixe}_2024_2025",
            "moyenne": f"prix_m2_moyen_{suffixe}_2024_2025",
        }).set_index("code_commune")
        pieces.append(part)
    return pd.concat(pieces, axis=1).reset_index()


def dynamique_prix(ventes: pd.DataFrame) -> pd.DataFrame:
    periode = ventes[ventes["annee"].isin([2022, 2023, 2024, 2025])].copy()
    periode["fenetre"] = np.where(periode["annee"] <= 2023, "2022_2023", "2024_2025")
    groupes = (periode.groupby(["code_commune", "type_bien", "fenetre"], observed=True)
              .agg(nb=("id_vente", "size"), median=("prix_m2", "median")))
    nb = groupes["nb"].unstack("fenetre")
    medianes = groupes["median"].unstack("fenetre")
    valide = (nb["2022_2023"] >= SEUIL_VENTES) & (nb["2024_2025"] >= SEUIL_VENTES)
    variation = (100 * (medianes["2024_2025"] / medianes["2022_2023"] - 1)).where(valide)
    par_commune = variation.groupby(level="code_commune").agg(["median", "count"])
    return par_commune.rename(columns={"median": "dynamique_prix_pct", "count": "nb_types_dynamique_fiables"}).reset_index()


def rang_regional(valeurs: pd.Series, region: pd.Series, eligible: pd.Series) -> pd.Series:
    return (valeurs.where(eligible).groupby(region).rank(pct=True) * 100)


def communes_metier(jointure: pd.DataFrame, ventes: pd.DataFrame) -> pd.DataFrame:
    if jointure["code_commune"].isna().any() or jointure["code_commune"].duplicated().any():
        raise ValueError("Jointure : code_commune nul ou dupliqué")
    communes = jointure.merge(prix_recents(ventes), on="code_commune", how="left", validate="one_to_one")
    communes = communes.merge(dynamique_prix(ventes), on="code_commune", how="left", validate="one_to_one")

    for suffixe in ("maison", "appartement"):
        controle = f"nb_ventes_{suffixe}_2024_2025_controle"
        attendu = f"nb_ventes_{suffixe}_2024_2025"
        if not communes[controle].fillna(0).astype("int64").eq(communes[attendu]).all():
            raise AssertionError(f"Prix récents : volume {suffixe} différent de la jointure")
        communes = communes.drop(columns=controle)
        for mesure in ("median", "moyen"):
            col = f"prix_m2_{mesure}_{suffixe}_2024_2025"
            communes[col] = communes[col].round(2)

    communes["nb_types_dynamique_fiables"] = communes["nb_types_dynamique_fiables"].fillna(0).astype("int64")
    population = communes["population"].where(communes["population"] > 0)
    pop_score = population.clip(lower=1000)
    densites_score = []
    for suffixe, compteur in EQUIPEMENTS.items():
        communes[f"densite_{suffixe}_pour_1000_habitants"] = (1000 * communes[compteur] / population).round(2)
        densites_score.append(1000 * communes[compteur] / pop_score)

    eligible = (population.notna() & (communes["nb_ventes_2024_2025"] >= SEUIL_VENTES)
                & communes["dynamique_prix_pct"].notna())
    communes["score_eligible"] = eligible
    region = communes["region"]
    communes["score_dynamique"] = rang_regional(communes["dynamique_prix_pct"].clip(-50, 100), region, eligible)
    communes["score_activite"] = rang_regional(communes["nb_ventes_2024_2025"], region, eligible)
    scores_equipements = [rang_regional(densite, region, eligible) for densite in densites_score]
    communes["score_equipements"] = pd.concat(scores_equipements, axis=1).mean(axis=1)
    communes["score_attractivite"] = (0.40 * communes["score_dynamique"]
                                     + 0.30 * communes["score_activite"]
                                     + 0.30 * communes["score_equipements"]).round(1)
    communes[["dynamique_prix_pct", "score_dynamique", "score_activite", "score_equipements"]] = (
        communes[["dynamique_prix_pct", "score_dynamique", "score_activite", "score_equipements"]].round(2))

    if len(communes) != len(jointure) or communes["code_commune"].duplicated().any():
        raise AssertionError("Gold communes : clé ou nombre de lignes incohérent")
    if communes.loc[eligible, "score_attractivite"].isna().any():
        raise AssertionError("Gold communes : score absent pour une commune éligible")
    if communes.loc[~eligible, "score_attractivite"].notna().any():
        raise AssertionError("Gold communes : score présent pour une commune non éligible")
    if not communes["score_attractivite"].dropna().between(0, 100).all():
        raise AssertionError("Gold communes : score hors de l'intervalle 0–100")
    return communes.sort_values("code_commune").reset_index(drop=True)


def main() -> None:
    jointure = pd.read_parquet(GOLD / "jointure_communes.parquet")
    dvf = pd.read_parquet(SILVER / "dvf_ventes.parquet", columns=COLONNES_DVF)
    ventes = ventes_comparables(dvf)
    marche = marche_annuel(ventes)
    communes = communes_metier(jointure, ventes)

    stats_jointure = json.loads((GOLD / "jointure_stats.json").read_text(encoding="utf-8"))
    if len(ventes) != stats_jointure["dvf"]["ventes_comparables"]:
        raise AssertionError("La Silver DVF a changé depuis la construction de la jointure")
    rattachees = int(communes["nb_ventes_comparables_2021_2025"].sum())
    if rattachees + stats_jointure["jointure"]["ventes_comparables_hors_insee"] != len(ventes):
        raise AssertionError("La jointure communale ne couvre plus la Silver DVF attendue")

    stats = {
        "marche": {
            "lignes": len(marche),
            "ventes_comparables": len(ventes),
            "groupes_prix_non_publies_moins_10_ventes": int((marche["nb_ventes"] < SEUIL_VENTES).sum()),
            "groupes_prix_publies": int((marche["nb_ventes"] >= SEUIL_VENTES).sum()),
            "variations_annuelles_fiables": int(marche["variation_annuelle_pct"].notna().sum()),
        },
        "communes": {
            "lignes": len(communes),
            "communes_avec_prix_maison_recent": int(communes["prix_m2_median_maison_2024_2025"].notna().sum()),
            "communes_avec_prix_appartement_recent": int(communes["prix_m2_median_appartement_2024_2025"].notna().sum()),
            "score_eligibles": int(communes["score_eligible"].sum()),
            "score_eligibles_par_region": communes.loc[communes["score_eligible"], "region"].value_counts().to_dict(),
        },
    }

    GOLD.mkdir(exist_ok=True)
    marche.to_parquet(GOLD / "marche_commune_annee_type.parquet", index=False)
    communes.to_parquet(GOLD / "communes.parquet", index=False)
    write_table(marche, "G_marche_commune_annee_type")
    write_table(communes, "G_communes")
    (GOLD / "indicateurs_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\n✔ {len(marche):,} groupes marché et {len(communes):,} communes → {GOLD}")


if __name__ == "__main__":
    main()
