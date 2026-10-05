# Module INSEE — Ingestion bronze et silver

## Source
API Melodi de l'INSEE — données statistiques par commune, JSON imbriqué, gratuite et sans clé
(30 appels par minute). 7 jeux de données : revenus (Filosofi), recensement (habitants, ménages,
logements, emploi, diplômes) et populations légales.

## Script
`main.py` — télécharge les 7 jeux pour les 4 régions cibles (IdF, Occitanie, Bretagne, ARA),
commune par commune, par lots de 200.

## Usage
```bash
python src/insee/main.py                              # les 7 jeux, les 4 régions
python src/insee/main.py --region 53                  # une région
python src/insee/main.py --dataset DS_FILOSOFI_CC     # un jeu
```

## Sortie
`{DATASET}/region_{code}_{nom}/part_XXXX.json` — 7 jeux × 4 régions = 406 fichiers,
4 419 302 observations, 1,7 Go, 10 939 communes.
Colonnes et modalités : `docs/insee/dictionnaire_bronze.md`.

## Profilage
`profiling.py` — volumétrie, complétude par indicateur, cardinalité des découpages, couverture
géographique, anomalies (millésimes divergents, pages manquantes, modalités totales, doublons).
```bash
python src/insee/profiling.py                            # les 7 jeux
python src/insee/profiling.py --dataset DS_FILOSOFI_CC   # un jeu
python src/insee/profiling.py --region 53                # une région
```
Sorties : `docs/insee/profiling/{fichiers,indicateurs,dimensions,couverture_geo}.csv`.

## Silver
`silver.py` — une ligne par commune, clé `code_commune` (jointure DVF / OSM).
```bash
python src/insee/silver.py                               # ~2 min
```
Sorties : `silver/insee_communes.parquet` (10 939 communes × 36 colonnes) +
`silver/insee_silver_stats.json`.
Colonnes et chiffres : `docs/insee/dictionnaire_silver.md`. Règles : `docs/insee/qualite.md`.

## Besoins couverts
- **B1** (argumenter un prix) : revenu médian, taux de vacance, âge du parc de logements.
- **B3** (profil familial ou jeunes actifs) : tranches d'âge, diplômes, emploi, taille des logements.
- **B2** (communes qui montent) : **bloqué**, un seul millésime téléchargé. Les populations
  légales existent de 1968 à 2023 : relancer `main.py` sans filtre d'année.
