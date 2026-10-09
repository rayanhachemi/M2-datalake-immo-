# Module OSM

Récupère les points d'intérêt (POI) depuis OpenStreetMap via l'API Overpass pour les 4 régions cibles.

## Scripts

| Script | Rôle |
|---|---|
| `main.py` | Téléchargement bronze (148 requêtes, 4 régions × 37 depts × 4 catégories) |
| `profiling.py` | Analyse du bronze : volumétrie, complétude des tags, anomalies |
| `silver.py` | Nettoyage et rattachement à la commune (jointure spatiale) |

## Lancer

```bash
python src/osm/main.py       # bronze — toutes les régions
python src/osm/profiling.py  # profiling — résultats dans docs/osm/profiling/
python src/osm/silver.py     # silver — résultat dans silver/osm_poi.parquet
```

## Catégories collectées

- `ecoles` : écoles, collèges, lycées, universités, maternelles
- `sante` : pharmacies, hôpitaux, cliniques, médecins
- `shops` : tous les commerces
- `transport` : arrêts de transport en commun

## Sorties

- Bronze : `bronze/osm/{region}/osm_{region}_{dept}_{cat}.json`
- Silver : `silver/osm_poi.parquet` — 305 925 POI, colonne `code_commune` pour les jointures

Licence : ODbL — mention « © contributeurs OpenStreetMap » obligatoire.
