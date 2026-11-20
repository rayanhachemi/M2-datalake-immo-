# Observatoire immobilier — Clé en Main Immo

Projet M2 DS4SC — Université de Tours, antenne de Blois — Groupe 4  
Cours Warehousing & Data Lakes

---

## Présentation

Pipeline de données immobilières pour le compte de l'agence fictive **Clé en Main Immo**. Il collecte, nettoie et centralise des données DVF, OSM et INSEE dans un entrepôt PostgreSQL structuré en couches Bronze / Silver / Gold, puis répond à cinq besoins métier via des requêtes SQL et un notebook d'analyse interactif.

---

## Architecture

```
Bronze (données brutes)
  ├── dvf/          transactions DVF annuelles (data.gouv.fr)
  ├── osm/          points d'intérêt OSM (Overpass API)
  ├── insee/        indicateurs socio-démographiques (API Melodi)
  └── contours/     contours communaux GeoJSON (geo.api.gouv.fr)

Silver (données nettoyées, une ligne par entité)
  ├── dvf_ventes.parquet        ~2,07 M ventes 2021-2025
  ├── osm_poi.parquet           ~305 K points d'intérêt
  ├── insee_communes.parquet    ~10 939 communes × 36 indicateurs
  └── communes.parquet          référentiel communal unifié

Gold (4 tables PostgreSQL)
  ├── G_COMMUNE                 référentiel communes
  ├── G_TRANSACTION             ventes immobilières nettoyées
  ├── G_POINT_INTERET           POI OSM avec libellés français
  └── G_PROFIL_COMMUNE          indicateurs INSEE par commune
```

---

## Sources de données

| Source | Données | Licence |
|---|---|---|
| DVF — data.gouv.fr | Transactions immobilières 2021–2025 | CGF DGFiP — pas de ré-identification |
| OpenStreetMap (Overpass) | POI : écoles, santé, commerces, transport | ODbL — mention © contributeurs OSM obligatoire |
| INSEE Filosofi (API Melodi) | Revenus, population, emploi, logements | Licence Ouverte INSEE |
| geo.api.gouv.fr | Contours communaux GeoJSON | Licence Ouverte |
| BAN (api-adresse.data.gouv.fr) | Géocodage adresses (notebook) | Licence Ouverte |

Périmètre géographique : Île-de-France, Bretagne, Occitanie, Auvergne-Rhône-Alpes (37 départements).

---

## Prérequis

- Python 3.11+
- PostgreSQL accessible (local ou distant)
- Docker + buildx (pour le déploiement)

## Structure du projet

```
.
├── bronze/          données brutes (généré au runtime)
├── silver/          données nettoyées Parquet (généré au runtime)
├── gold/            cartes HTML exportées (généré au runtime)
├── src/
│   ├── dvf/         ingestion et nettoyage DVF
│   ├── osm/         ingestion et nettoyage OSM
│   ├── insee/       ingestion et nettoyage INSEE
│   ├── communes/    référentiel communal Silver
│   ├── gold/        modèle conceptuel, requêtes, cartes
│   ├── db.py        connexion SQLAlchemy
│   └── charger_silver_postgres.py
├── sql/gold/        requêtes métier B1–B5
├── notebooks/       notebook d'analyse interactif
├── docs/            dictionnaires de données et rapports qualité
├── Dockerfile
├── requirements.txt
└── .env             (à créer, non versionné)
```

## Installation

```bash
pip install -r requirements.txt
```

Créer un fichier `.env` à la racine :

```
DATABASE_URL=postgresql://user:password@host:port/database
```

---

## Pipeline — ordre d'exécution

```bash
# 1. Bronze
python src/dvf/main.py
python src/osm/main.py
python src/insee/main.py

# 2. Silver
python src/dvf/silver.py
python src/osm/silver.py
python src/insee/silver.py
python src/communes/silver.py

# 3. Chargement Silver → PostgreSQL (si Parquets déjà produits)
python src/charger_silver_postgres.py

# 4. Gold
python src/gold/modele_conceptuel.py
python src/gold/controle.py
```

---

## Besoins métier

| Besoin | Description | Requête |
|---|---|---|
| B1 | Argumentaire de prix en temps réel pour un bien | `sql/gold/B1_comparaison_prix.sql` |
| B2 | Score de potentiel pour l'implantation d'une 6e agence | `sql/gold/B2_classement_agences.sql` |
| B3 | Recherche de logement autour du lieu de travail | `sql/gold/B3_profil_sociodemographique.sql` |
| B4 | Indicateur de tendance du marché (5 ans) | `sql/gold/B4_tendance_marche.sql` |
| B5 | Détection de zones sous-évaluées mais bien équipées | `sql/gold/B5_zones_prix_bas_equipees.sql` |

Les requêtes s'exécutent directement dans pgAdmin ou en ligne de commande :

```bash
python src/gold/requetes.py B1 --region idf --type-bien Maison
python src/gold/requetes.py B2 --region bretagne --limite 10
python src/gold/requetes.py B3 --code-commune-travail 75056 --surface-souhaitee-m2 80 --distance-max-km 30
python src/gold/requetes.py B4 --code-commune 69123 --type-bien Appartement
python src/gold/requetes.py B5 --region occitanie --type-bien Maison
```

---

## Notebook d'analyse

`notebooks/analyse_immo.ipynb` présente les cinq besoins avec des scénarios réels, des visualisations matplotlib et des cartes Folium interactives.

```bash
# Lancer en local (depuis la racine du projet)
jupyter notebook notebooks/analyse_immo.ipynb
```

---

## Déploiement Docker

Image publique : **[hub.docker.com/r/rayanhcm0/datalake-immo](https://hub.docker.com/r/rayanhcm0/datalake-immo)**

```bash
# Lancer le notebook depuis l'image (nécessite un .env avec DATABASE_URL)
docker run --env-file .env -p 8888:8888 rayanhcm0/datalake-immo:latest
```

Accéder au notebook : `http://localhost:8888` — mot de passe : `cleenmain2025`

**Instance déployée (sandbox université de Tours) :** [docker1.pedagogie.sandbox.univ-tours.fr:8888/notebooks/analyse_immo.ipynb](http://docker1.pedagogie.sandbox.univ-tours.fr:8888/notebooks/analyse_immo.ipynb) — jeton : `cleenmain2025`

```bash
# Rebuild et push (cross-compilation amd64 depuis Apple Silicon)
docker buildx build --platform linux/amd64 -t rayanhcm0/datalake-immo:latest --push .
```
