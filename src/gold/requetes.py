"""Exécute les requêtes métier Gold dans PostgreSQL.

Exemples :
  python src/gold/requetes.py B1 --region idf --type-bien Maison
  python src/gold/requetes.py B2 --region idf
  python src/gold/requetes.py B3 --code-commune-travail 75056 --revenu-annuel-couple 60000
  python src/gold/requetes.py B4 --code-commune 75056 --type-bien Appartement
  python src/gold/requetes.py B5 --region occitanie --type-bien Maison
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import get_engine

REQUETES = {
    "B1": ROOT / "sql" / "gold" / "B1_comparaison_prix.sql",
    "B2": ROOT / "sql" / "gold" / "B2_classement_agences.sql",
    "B3": ROOT / "sql" / "gold" / "B3_profil_sociodemographique.sql",
    "B4": ROOT / "sql" / "gold" / "B4_tendance_marche.sql",
    "B5": ROOT / "sql" / "gold" / "B5_zones_prix_bas_equipees.sql",
}
PARAMETRES_SQL = {
    "B1": "SELECT CAST(:region AS text) AS region, CAST(:type_bien AS text) AS type_bien",
    "B2": "SELECT CAST(:region AS text) AS region, CAST(:limite AS integer) AS limite",
    "B3": (
        "SELECT CAST(:code_commune_travail AS text) AS code_commune_travail, "
        "CAST(:latitude_travail AS double precision) AS latitude_travail, "
        "CAST(:longitude_travail AS double precision) AS longitude_travail, "
        "CAST(:type_bien AS text) AS type_bien, "
        "CAST(:revenu_annuel_couple AS double precision) AS revenu_annuel_couple, "
        "CAST(:surface_souhaitee_m2 AS double precision) AS surface_souhaitee_m2, "
        "CAST(:tolerance_surface_pct AS double precision) AS tolerance_surface_pct, "
        "CAST(:distance_max_km AS double precision) AS distance_max_km, "
        "CAST(:budget_max_achat AS double precision) AS budget_max_achat, "
        "CAST(:limite AS integer) AS limite"
    ),
    "B4": "SELECT CAST(:code_commune AS text) AS code_commune, CAST(:type_bien AS text) AS type_bien",
    "B5": (
        "SELECT CAST(:region AS text) AS region, CAST(:type_bien AS text) AS type_bien, "
        "CAST(:ratio_prix_max AS double precision) AS ratio_prix_max, "
        "CAST(:score_equipements_min AS double precision) AS score_equipements_min, "
        "CAST(:limite AS integer) AS limite"
    ),
}


def charger_requete(besoin: str):
    sql = REQUETES[besoin].read_text(encoding="utf-8")
    debut, suite = sql.split("-- PARAMETRES_DEBUT", 1)
    _, fin = suite.split("-- PARAMETRES_FIN", 1)
    return text(debut + "\n    " + PARAMETRES_SQL[besoin] + "\n    " + fin)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("besoin", choices=REQUETES)
    parser.add_argument("--region", choices=["idf", "ara", "bretagne", "occitanie"])
    parser.add_argument("--code-commune")
    parser.add_argument("--code-commune-travail", default="75056")
    parser.add_argument("--latitude-travail", type=float)
    parser.add_argument("--longitude-travail", type=float)
    parser.add_argument("--type-bien", choices=["Maison", "Appartement"], default="Maison")
    parser.add_argument("--revenu-annuel-couple", type=float, default=60000)
    parser.add_argument("--surface-souhaitee-m2", type=float, default=80)
    parser.add_argument("--tolerance-surface-pct", type=float, default=25)
    parser.add_argument("--distance-max-km", type=float, default=30)
    parser.add_argument("--budget-max-achat", type=float)
    parser.add_argument("--limite", type=int, default=10)
    parser.add_argument("--ratio-prix-max", type=float, default=0.90)
    parser.add_argument("--score-equipements-min", type=float, default=60)
    args = parser.parse_args()
    if args.besoin == "B4" and not re.fullmatch(r"\d{5}", args.code_commune or ""):
        parser.error(f"{args.besoin} requiert --code-commune avec cinq chiffres")
    if args.besoin == "B3":
        if not re.fullmatch(r"\d{5}", args.code_commune_travail):
            parser.error("B3 requiert --code-commune-travail avec cinq chiffres")
        if (args.latitude_travail is None) != (args.longitude_travail is None):
            parser.error("B3 requiert les deux coordonnées du travail ensemble")
        if args.latitude_travail is not None and not (
            -90 <= args.latitude_travail <= 90 and -180 <= args.longitude_travail <= 180
        ):
            parser.error("B3 requiert une latitude entre -90 et 90 et une longitude entre -180 et 180")
        if args.revenu_annuel_couple <= 0 or args.surface_souhaitee_m2 <= 0:
            parser.error("B3 requiert un revenu annuel et une surface souhaitée positifs")
        if args.distance_max_km <= 0:
            parser.error("B3 requiert --distance-max-km positif")
        if not 0 <= args.tolerance_surface_pct < 100:
            parser.error("B3 requiert --tolerance-surface-pct entre 0 et 100 exclus")
        if args.budget_max_achat is not None and args.budget_max_achat <= 0:
            parser.error("B3 requiert --budget-max-achat positif")
    if not 1 <= args.limite <= 100:
        parser.error("--limite doit être compris entre 1 et 100")
    if not 0 < args.ratio_prix_max <= 1:
        parser.error("--ratio-prix-max doit être dans ]0, 1]")
    if not 0 <= args.score_equipements_min <= 100:
        parser.error("--score-equipements-min doit être entre 0 et 100")

    params = {
        "region": args.region,
        "code_commune": args.code_commune,
        "code_commune_travail": args.code_commune_travail,
        "latitude_travail": args.latitude_travail,
        "longitude_travail": args.longitude_travail,
        "type_bien": args.type_bien,
        "revenu_annuel_couple": args.revenu_annuel_couple,
        "surface_souhaitee_m2": args.surface_souhaitee_m2,
        "tolerance_surface_pct": args.tolerance_surface_pct,
        "distance_max_km": args.distance_max_km,
        "budget_max_achat": args.budget_max_achat,
        "limite": args.limite,
        "ratio_prix_max": args.ratio_prix_max,
        "score_equipements_min": args.score_equipements_min,
    }
    requete = charger_requete(args.besoin)
    engine = get_engine()
    try:
        with engine.connect() as conn:
            resultat_sql = conn.execute(requete, params)
            colonnes = list(resultat_sql.keys())
            lignes = resultat_sql.mappings().all()
    finally:
        engine.dispose()
    resultat = pd.DataFrame(lignes, columns=colonnes)
    if resultat.empty:
        print("Aucun résultat pour ces paramètres et seuils.")
    else:
        print(resultat.to_string(index=False))
        print(f"\n{len(resultat)} ligne(s)")


if __name__ == "__main__":
    main()
