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

## Catégories
- `ecoles` : schools, colleges, universities, kindergartens
- `sante` : pharmacies, hospitals, clinics, doctors
- `shops` : tous les commerces
- `transport` : arrêts de transport en commun
