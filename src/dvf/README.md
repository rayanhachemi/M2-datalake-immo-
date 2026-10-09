# Module DVF

Récupère les données de transactions immobilières (Demandes de Valeurs Foncières) depuis data.gouv.fr pour les 4 régions cibles.

## Scripts

| Script | Rôle |
|---|---|
| `main.py` | Téléchargement bronze (5 années, filtrées aux 37 départements cibles) |
| `profiling.py` | Analyse du bronze : volumétrie, distributions, anomalies |
| `silver.py` | Nettoyage : une ligne par vente d'un logement unique, prix au m², clé `code_commune` |

## Lancer

```bash
python src/dvf/main.py       # bronze — 5 millésimes (2021-2025), ~1,2 Go
python src/dvf/profiling.py  # profiling (par millésime + reventes inter-millésimes)
python src/dvf/silver.py     # silver
```

## Données collectées

Transactions immobilières de 2021 à 2025 : ventes de maisons et appartements avec surface, prix, localisation (adresse, département, commune).

## Sorties

- Bronze : `bronze/dvf/dvf_{annee}_cibles.txt` — fichiers tabulaires (séparateur `|`), 37 départements
- Silver : `silver/dvf_ventes.parquet` (~2,07 M ventes, 2021-2025) + `silver/dvf_silver_stats.json` (volumes après chaque règle)

**Attention CGU :** les DVF contiennent des données personnelles. Ne pas ré-identifier les acheteurs/vendeurs ni indexer ces données sur des services externes.
