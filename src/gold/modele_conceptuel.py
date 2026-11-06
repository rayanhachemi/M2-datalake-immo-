"""Construit les quatre tables Gold directement depuis les quatre tables Silver SQL.

Usage : python src/gold/modele_conceptuel.py
"""

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from db import get_engine  # noqa: E402

SILVER = ("S_dvf_ventes", "S_osm_poi", "S_insee_communes", "S_communes")
GOLD = ("G_COMMUNE", "G_TRANSACTION", "G_POINT_INTERET", "G_PROFIL_COMMUNE")

SCHEMA_SQL = [
    '''CREATE TABLE "G_COMMUNE" (
         code_commune varchar(5) PRIMARY KEY, nom_commune text NOT NULL,
         departement text NOT NULL, region text NOT NULL)''',
    '''CREATE TABLE "G_TRANSACTION" (
         id_vente text PRIMARY KEY, date_mutation date NOT NULL,
         type_bien text NOT NULL, valeur_fonciere double precision NOT NULL,
         surface_bati double precision NOT NULL, prix_m2 double precision NOT NULL,
         code_commune varchar(5) NOT NULL REFERENCES "G_COMMUNE"(code_commune))''',
    '''CREATE TABLE "G_POINT_INTERET" (
         id_osm text PRIMARY KEY, nom text, categorie text NOT NULL, sous_type text,
         latitude double precision NOT NULL, longitude double precision NOT NULL,
         code_commune varchar(5) NOT NULL REFERENCES "G_COMMUNE"(code_commune))''',
    '''CREATE TABLE "G_PROFIL_COMMUNE" (
         code_commune varchar(5) PRIMARY KEY REFERENCES "G_COMMUNE"(code_commune),
         revenu_median double precision, population bigint,
         taux_chomage double precision, taux_pauvrete double precision)''',
]

INSERT_SQL = [
    '''INSERT INTO "G_COMMUNE" (code_commune, nom_commune, departement, region)
       SELECT code_commune, nom_commune, departement, region FROM "S_communes"''',
    '''INSERT INTO "G_TRANSACTION"
           (id_vente, date_mutation, type_bien, valeur_fonciere, surface_bati, prix_m2, code_commune)
       SELECT id_vente, date_mutation::date, type_bien, valeur_fonciere,
              surface_bati, prix_m2, code_commune
       FROM "S_dvf_ventes"
       WHERE nature_mutation = 'Vente' AND NOT revente_moins_30j''',
    '''INSERT INTO "G_POINT_INTERET"
           (id_osm, nom, categorie, sous_type, latitude, longitude, code_commune)
       SELECT DISTINCT ON (id_osm)
              id_osm, nom, categorie,
              CASE categorie
                WHEN \'education\' THEN
                  CASE sous_type
                    WHEN \'school\'       THEN \'Lycée / Collège\'
                    WHEN \'college\'      THEN \'Lycée\'
                    WHEN \'university\'   THEN \'Université\'
                    WHEN \'kindergarten\' THEN \'École maternelle\'
                    ELSE COALESCE(sous_type, \'Établissement scolaire\')
                  END
                WHEN \'sante\' THEN
                  CASE sous_type
                    WHEN \'pharmacy\' THEN \'Pharmacie\'
                    WHEN \'hospital\' THEN \'Hôpital\'
                    WHEN \'clinic\'   THEN \'Clinique\'
                    WHEN \'doctors\'  THEN \'Médecin\'
                    ELSE COALESCE(sous_type, \'Établissement de santé\')
                  END
                WHEN \'transport\' THEN
                  CASE mode
                    WHEN \'bus\'        THEN \'Arrêt de bus\'
                    WHEN \'tram\'       THEN \'Arrêt de tram\'
                    WHEN \'subway\'     THEN \'Station de métro\'
                    WHEN \'train\'      THEN \'Gare\'
                    WHEN \'light_rail\' THEN \'Tramway\'
                    WHEN \'ferry\'      THEN \'Embarcadère\'
                    WHEN \'monorail\'   THEN \'Monorail\'
                    ELSE \'Arrêt\'
                  END
                WHEN \'commerce\' THEN
                  CASE sous_type
                    WHEN \'supermarket\'   THEN \'Supermarché\'
                    WHEN \'convenience\'   THEN \'Épicerie\'
                    WHEN \'bakery\'        THEN \'Boulangerie\'
                    WHEN \'butcher\'       THEN \'Boucherie\'
                    WHEN \'clothes\'       THEN \'Vêtements\'
                    WHEN \'hairdresser\'   THEN \'Coiffeur\'
                    WHEN \'restaurant\'    THEN \'Restaurant\'
                    WHEN \'cafe\'          THEN \'Café / Bar\'
                    WHEN \'florist\'       THEN \'Fleuriste\'
                    WHEN \'pharmacy\'      THEN \'Pharmacie\'
                    WHEN \'hardware\'      THEN \'Bricolage\'
                    WHEN \'electronics\'   THEN \'Électronique\'
                    WHEN \'sports\'        THEN \'Sport\'
                    WHEN \'furniture\'     THEN \'Ameublement\'
                    WHEN \'books\'         THEN \'Librairie\'
                    WHEN \'optician\'      THEN \'Opticien\'
                    WHEN \'jewelry\'       THEN \'Bijouterie\'
                    WHEN \'shoes\'         THEN \'Chaussures\'
                    WHEN \'mobile_phone\'  THEN \'Téléphonie\'
                    WHEN \'car\'           THEN \'Automobile\'
                    WHEN \'car_repair\'    THEN \'Garage\'
                    WHEN \'bicycle\'       THEN \'Vélo\'
                    WHEN \'pet\'           THEN \'Animalerie\'
                    WHEN \'toy\'           THEN \'Jouets\'
                    WHEN \'stationery\'    THEN \'Papeterie\'
                    WHEN \'gift\'          THEN \'Cadeaux\'
                    WHEN \'beauty\'        THEN \'Beauté / Cosmétiques\'
                    WHEN \'alcohol\'       THEN \'Cave / Alcool\'
                    WHEN \'beverages\'     THEN \'Boissons\'
                    WHEN \'music\'         THEN \'Musique\'
                    WHEN \'outdoor\'       THEN \'Sport / Outdoor\'
                    WHEN \'garden_centre\' THEN \'Jardinerie\'
                    WHEN \'deli\'          THEN \'Épicerie fine\'
                    WHEN \'pastry\'        THEN \'Pâtisserie\'
                    WHEN \'seafood\'       THEN \'Poissonnerie\'
                    WHEN \'greengrocer\'   THEN \'Primeur\'
                    WHEN \'dry_cleaning\'  THEN \'Pressing\'
                    WHEN \'laundry\'       THEN \'Laverie\'
                    WHEN \'travel_agency\' THEN \'Agence de voyage\'
                    WHEN \'bank\'          THEN \'Banque\'
                    WHEN \'real_estate\'   THEN \'Agence immobilière\'
                    WHEN \'yes\'           THEN \'Commerce\'
                    WHEN \'vacant\'        THEN \'Local vacant\'
                    ELSE COALESCE(sous_type, \'Commerce\')
                  END
                ELSE COALESCE(sous_type, \'Autre\')
              END AS sous_type,
              lat, lon, code_commune
       FROM "S_osm_poi"
       ORDER BY id_osm,
                CASE categorie WHEN \'sante\' THEN 0 WHEN \'education\' THEN 1
                     WHEN \'transport\' THEN 2 WHEN \'commerce\' THEN 3 ELSE 99 END,
                categorie, sous_type''',
    '''INSERT INTO "G_PROFIL_COMMUNE"
           (code_commune, revenu_median, population, taux_chomage, taux_pauvrete)
       SELECT code_commune, revenu_median, population::bigint, taux_chomage, taux_pauvrete
       FROM "S_insee_communes"''',
]


def main() -> None:
    engine = get_engine()
    try:
        with engine.begin() as conn:
            presentes = set(conn.execute(text("""SELECT tablename FROM pg_tables
                WHERE schemaname = current_schema()""")).scalars())
            manquantes = set(SILVER) - presentes
            if manquantes:
                raise RuntimeError(f"Tables Silver manquantes : {', '.join(sorted(manquantes))}")
            for ancien in ("G_jointure_communes", "G_marche_commune_annee_type", "G_communes"):
                conn.execute(text(f'DROP TABLE IF EXISTS "{ancien}"'))
            for nom in reversed(GOLD):
                conn.execute(text(f'DROP TABLE IF EXISTS "{nom}"'))
            for definition in SCHEMA_SQL:
                conn.execute(text(definition))
            for nom, insertion in zip(GOLD, INSERT_SQL):
                nombre = conn.execute(text(insertion)).rowcount
                print(f"{nom} : {nombre:,} lignes créées depuis Silver", flush=True)
            conn.execute(text('CREATE INDEX idx_g_transaction_commune_type_date '
                              'ON "G_TRANSACTION" (code_commune, type_bien, date_mutation)'))
            conn.execute(text('CREATE INDEX idx_g_poi_commune_categorie '
                              'ON "G_POINT_INTERET" (code_commune, categorie)'))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
