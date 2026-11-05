"""Contrôle les quatre tables Silver et les quatre tables Gold PostgreSQL.

Usage : python src/gold/controle.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import get_engine  # noqa: E402

SILVER = {
    "S_dvf_ventes": "dvf_ventes.parquet",
    "S_osm_poi": "osm_poi.parquet",
    "S_insee_communes": "insee_communes.parquet",
    "S_communes": "communes.parquet",
}
GOLD = ("G_COMMUNE", "G_TRANSACTION", "G_POINT_INTERET", "G_PROFIL_COMMUNE")
COLONNES = {
    "G_COMMUNE": {"code_commune", "nom_commune", "departement", "region"},
    "G_TRANSACTION": {"id_vente", "date_mutation", "type_bien", "valeur_fonciere",
                      "surface_bati", "prix_m2", "code_commune"},
    "G_POINT_INTERET": {"id_osm", "nom", "categorie", "sous_type", "latitude",
                       "longitude", "code_commune"},
    "G_PROFIL_COMMUNE": {"code_commune", "revenu_median", "population",
                         "taux_chomage", "taux_pauvrete"},
}


def verifier() -> dict:
    checks = []

    def check(nom: str, anomalies: int, detail: str = "") -> None:
        checks.append({"nom": nom, "statut": "OK" if anomalies == 0 else "ERREUR",
                       "anomalies": int(anomalies), "detail": detail})

    engine = get_engine()
    try:
        with engine.connect() as conn:
            presentes = set(conn.execute(text("""SELECT tablename FROM pg_tables
                WHERE schemaname = current_schema()""")).scalars())
            check("Quatre tables Silver présentes", len(set(SILVER) - presentes))
            check("Uniquement quatre tables Gold", len({n for n in presentes if n.startswith("G_")} ^ set(GOLD)))
            if not set(SILVER).issubset(presentes) or not set(GOLD).issubset(presentes):
                raise RuntimeError("Tables SQL manquantes : reconstruire Silver puis Gold")

            volumes_silver = {}
            for nom, fichier in SILVER.items():
                nombre = conn.execute(text(f'SELECT COUNT(*) FROM "{nom}"')).scalar_one()
                attendu = pq.ParquetFile(ROOT / "silver" / fichier).metadata.num_rows
                volumes_silver[nom] = nombre
                check(f"{nom} = Parquet Silver", abs(nombre - attendu), f"{nombre:,} lignes")

            volumes_gold = {}
            for nom in GOLD:
                nombre = conn.execute(text(f'SELECT COUNT(*) FROM "{nom}"')).scalar_one()
                volumes_gold[nom] = nombre
                colonnes = set(conn.execute(text("""SELECT column_name FROM information_schema.columns
                    WHERE table_schema = current_schema() AND table_name = :nom"""), {"nom": nom}).scalars())
                check(f"Schéma {nom}", len(COLONNES[nom] ^ colonnes))

            attendu_transactions = conn.execute(text('''SELECT COUNT(*) FROM "S_dvf_ventes"
                WHERE nature_mutation = 'Vente' AND NOT revente_moins_30j''')).scalar_one()
            attendu_poi = conn.execute(text('SELECT COUNT(DISTINCT id_osm) FROM "S_osm_poi"')).scalar_one()
            for gold, attendu in (("G_COMMUNE", volumes_silver["S_communes"]),
                                  ("G_TRANSACTION", attendu_transactions),
                                  ("G_POINT_INTERET", attendu_poi),
                                  ("G_PROFIL_COMMUNE", volumes_silver["S_insee_communes"])):
                check(f"Lignage {gold} ← Silver", abs(volumes_gold[gold] - attendu),
                      f"{volumes_gold[gold]:,} lignes")

            contraintes = conn.execute(text("""SELECT COUNT(*) FROM pg_constraint
                WHERE conrelid IN ('"G_COMMUNE"'::regclass, '"G_TRANSACTION"'::regclass,
                                   '"G_POINT_INTERET"'::regclass, '"G_PROFIL_COMMUNE"'::regclass)
                  AND contype IN ('p', 'f')""")).scalar_one()
            check("Quatre clés primaires et trois clés étrangères", abs(contraintes - 7))
            invalides = conn.execute(text('''SELECT
                (SELECT COUNT(*) FROM "G_COMMUNE" WHERE code_commune !~ '^[0-9]{5}$'
                    OR nom_commune IS NULL OR departement IS NULL OR region IS NULL) +
                (SELECT COUNT(*) FROM "G_TRANSACTION" WHERE surface_bati <= 0 OR prix_m2 <= 0
                    OR type_bien NOT IN ('Maison', 'Appartement')) +
                (SELECT COUNT(*) FROM "G_POINT_INTERET" WHERE latitude NOT BETWEEN 41 AND 52
                    OR longitude NOT BETWEEN -6 AND 10)''')).scalar_one()
            check("Domaines des valeurs Gold", invalides)
    finally:
        engine.dispose()

    return {"date_controle_utc": datetime.now(timezone.utc).isoformat(),
            "statut": "OK" if all(c["statut"] == "OK" for c in checks) else "ERREUR",
            "volumes_silver": volumes_silver, "volumes_gold": volumes_gold,
            "controles": checks}


def ecrire_rapport(rapport: dict) -> None:
    sortie = ROOT / "gold" / "controle_stats.json"
    sortie.parent.mkdir(exist_ok=True)
    sortie.write_text(json.dumps(rapport, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lignes = ["# Contrôle Silver → Gold", "",
              f"Exécuté le {rapport['date_controle_utc']} — **{rapport['statut']}**.", ""]
    for titre, cle in (("Silver PostgreSQL", "volumes_silver"), ("Gold PostgreSQL", "volumes_gold")):
        lignes += [f"## {titre}", "", "| Table | Lignes |", "|---|---:|"]
        for nom, nombre in rapport[cle].items():
            lignes.append(f"| `{nom}` | {nombre:,} |")
        lignes.append("")
    lignes += ["## Contrôles", "", "| Contrôle | Résultat | Anomalies | Détail |",
               "|---|---:|---:|---|"]
    for item in rapport["controles"]:
        lignes.append(f"| {item['nom']} | {item['statut']} | {item['anomalies']} | {item['detail']} |")
    lignes.append("")
    destination = ROOT / "docs" / "gold" / "controle.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lignes), encoding="utf-8")


def main() -> None:
    rapport = verifier()
    ecrire_rapport(rapport)
    erreurs = [c for c in rapport["controles"] if c["statut"] != "OK"]
    print(f"Silver → Gold : {len(rapport['controles']) - len(erreurs)}/{len(rapport['controles'])} contrôles OK")
    for item in erreurs:
        print(f"ERREUR : {item['nom']} — {item['anomalies']} anomalie(s)")
    if erreurs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
