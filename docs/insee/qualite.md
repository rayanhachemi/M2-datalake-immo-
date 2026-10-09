# Qualité INSEE

4 régions, 37 depts, 7 jeux Melodi → 406 fichiers, 4,4M observations, 1,7 Go, 10 939 communes.

## Problèmes identifiés

| # | Problème | Volume | Traitement |
|---|---|---|---|
| 1 | Filosofi : 25 indicateurs sur 27 vides à l'échelle communale | 96 % des obs Filosofi | Seulement `MED_SL` et `PR_MD60` conservés en silver |
| 2 | Taux de pauvreté secret statistique (commune trop petite) | 8 699 communes (80 %) | Gardé pour les communes urbaines (54 % des ventes DVF) |
| 3 | Revenu médian secret statistique | 1 274 communes (12 %) | Valeur absente qualifiée en silver |
| 4 | Valeur absente écrite `{}` et non `null` | Partout | Test sur la clé `value`, pas sur la clé `OBS_VALUE_NIVEAU` |
| 5 | Millésime géographique différent : 2025 vs 2026 selon le jeu | `DS_POPULATIONS_HISTORIQUES` | Millésime retiré en silver (code commune seul) |
| 6 | Modalités totales (`_T`) qui recouvrent les autres | 9 dimensions sur le jeu logements | Modalités fixées explicitement en silver |
| 7 | Arrondissements Paris/Lyon/Marseille absents côté INSEE | ~5 % des ventes DVF | Rattachement à faire côté DVF |
| 8 | Un seul millésime (2023) | Tous les jeux | Pas d'analyse d'évolution possible pour l'instant |

## Bilan

4 419 302 observations → **10 939 communes × 36 colonnes** (`silver/insee_communes.parquet`)  
0 doublon d'observations (contrôlé par profiling).
