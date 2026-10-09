# Module INSEE

Récupère les données statistiques par commune depuis l'API Melodi de l'INSEE pour les 4 régions cibles.

## Scripts

| Script | Rôle |
|---|---|
| `main.py` | Téléchargement bronze (7 jeux de données, 4 régions) |
| `profiling.py` | Analyse du bronze : volumétrie, complétude, couverture géographique |
| `silver.py` | Transformation en table commune × indicateurs |

## Lancer

```bash
python src/insee/main.py       # bronze — tous les jeux, toutes les régions (~1-2h)
python src/insee/profiling.py  # profiling — résultats dans docs/insee/profiling/
python src/insee/silver.py     # silver — résultat dans silver/insee_communes.parquet
```

## Données collectées

7 jeux de données : revenus (Filosofi), population par âge, logements, emploi, diplômes, ménages, populations légales historiques.

## Sorties

- Bronze : `bronze/insee/{DATASET}/region_{code}_{nom}/part_XXXX.json` — 406 fichiers, ~1,7 Go
- Silver : `silver/insee_communes.parquet` — 10 939 communes × 36 colonnes, colonne `code_commune` pour les jointures

Licence : Licence Ouverte INSEE.
