# Qualité des données INSEE

Source : API Melodi de l'INSEE — 7 jeux de données, 4 régions, 10 939 communes, 4 419 302 observations brutes.

## Problèmes détectés et corrections

| Dimension | Problème | Volume | Correction |
|---|---|---|---|
| Exactitude | Melodi n'écrit pas `null` quand une valeur est absente, mais un objet vide `{}`. Un test naïf sur la clé conclut à 100 % de remplissage alors que Filosofi est rempli à seulement 4 % à la commune. | 283 408 observations vides | Test sur la clé `value` dans `OBS_VALUE_NIVEAU` dans le profiling et le silver. |
| Complétude | Filosofi propose 27 indicateurs mais 25 ne sont pas diffusés à l'échelle communale par l'INSEE (population trop petite). | 25 indicateurs sans aucune valeur | Seuls le revenu médian (`MED_SL`) et le taux de pauvreté (`PR_MD60`) sont repris en silver. |
| Complétude | Le taux de pauvreté est protégé par le secret statistique pour les petites communes. | 8 699 communes sans valeur (79 %) | Valeur marquée comme absente dans le silver, usage limité aux grandes communes. Revenu médian mieux couvert : 9 658 communes (88 %). |
| Cohérence | Le code géographique inclut son millésime (`2026-COM-35238`), mais `DS_POPULATIONS_HISTORIQUES` utilise 2025. Une jointure sur le code brut échouerait entre les jeux. | 10 939 observations | En silver, on découpe le code et on ne garde que le numéro de commune (`35238`). |
| Cohérence | Paris, Lyon et Marseille : l'INSEE publie pour la commune entière (`75056`) mais DVF utilise les codes d'arrondissement (`75115`, `75116`...). 5 % des ventes DVF sans correspondance. | ~70 000 ventes DVF | Rattachement des arrondissements à la commune côté DVF (à faire dans silver DVF). |
| Cohérence | Certaines dimensions ont une modalité `_T` = total, qui ne doit jamais être additionnée aux autres tranches. | 9 dimensions sur le jeu logement | Silver : modalités fixées explicitement pour chaque indicateur, pas de double comptage. |
| Cohérence | Schéma variable selon le jeu : le nom de l'indicateur change (`FILOSOFI_MEASURE`, `RP_MEASURE`, `POPREF_MEASURE`), le nombre de dimensions va de 4 à 13. | 7 jeux | Silver : filtres appliqués par nom de dimension pour chaque indicateur. |
| Unicité | Aucun doublon d'observation détecté. | 0 | Contrôle effectué dans `profiling.py`. |

## Bilan

4 419 302 observations bronze → **10 939 communes × 36 colonnes** (`silver/insee_communes.parquet`)
