"""Exécute les requêtes métier Gold dans PostgreSQL.

Exemples :
  python src/gold/requetes.py B2 --region idf
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
    "B2": ROOT / "sql" / "gold" / "B2_classement_agences.sql",
    "B4": ROOT / "sql" / "gold" / "B4_tendance_marche.sql",
    "B5": ROOT / "sql" / "gold" / "B5_zones_prix_bas_equipees.sql",
}
PARAMETRES_SQL = {
    "B2": "SELECT CAST(:region AS text) AS region, CAST(:limite AS integer) AS limite",
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
    parser.add_argument("--type-bien", choices=["Maison", "Appartement"], default="Maison")
    parser.add_argument("--limite", type=int, default=10)
    parser.add_argument("--ratio-prix-max", type=float, default=0.90)
    parser.add_argument("--score-equipements-min", type=float, default=60)
    args = parser.parse_args()
    if args.besoin == "B4" and not re.fullmatch(r"\d{5}", args.code_commune or ""):
        parser.error(f"{args.besoin} requiert --code-commune avec cinq chiffres")
    if not 1 <= args.limite <= 100:
        parser.error("--limite doit être compris entre 1 et 100")
    if not 0 < args.ratio_prix_max <= 1:
        parser.error("--ratio-prix-max doit être dans ]0, 1]")
    if not 0 <= args.score_equipements_min <= 100:
        parser.error("--score-equipements-min doit être entre 0 et 100")

    params = {
        "region": args.region,
        "code_commune": args.code_commune,
        "type_bien": args.type_bien,
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
