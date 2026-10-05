# Module OSM — Ingestion bronze

## Source
OpenStreetMap via Overpass API — données spatiales (POI géolocalisés).

## Script
`main.py` — télécharge les POI pour les 4 régions cibles (IdF, Occitanie, Bretagne, ARA).

## Usage
```bash
python src/osm/main.py                    # toutes les régions (148 requêtes)
python src/osm/main.py bretagne           # une région
python src/osm/main.py idf 75 ecoles     # un dept/catégorie précis
```

## Sortie
`bronze/osm/{region}/osm_{region}_{dept}_{cat}.json` — 37 depts × 4 catégories = 148 fichiers.

## Profilage
`profiling.py` — volumétrie, complétude des tags, doublons, anomalies (hors périmètre, `vacant`, hors bbox...).
```bash
python src/osm/profiling.py               # les 4 régions
python src/osm/profiling.py --region idf  # une région
```
Sorties : `docs/osm/profiling/{fichiers,sous_types,completude_tags}.csv`.

## Catégories
- `ecoles` : schools, colleges, universities, kindergartens
- `sante` : pharmacies, hospitals, clinics, doctors
- `shops` : tous les commerces
- `transport` : arrêts de transport en commun

## Silver
`silver.py` — POI nettoyés et rattachés à leur commune (`code_commune`, clé de jointure DVF / INSEE).
```bash
python src/osm/silver.py                  # ~3 min, télécharge les contours communaux au 1er lancement
```
Sorties : `silver/osm_poi.parquet` + `silver/osm_silver_stats.json`. Contours en cache dans `bronze/contours/`.
Colonnes et chiffres : `docs/osm/dictionnaire_silver.md`. Règles : `docs/osm/qualite.md`.
