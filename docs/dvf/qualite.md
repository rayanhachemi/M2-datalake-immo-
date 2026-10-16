# Qualité des données DVF

Source : Demandes de Valeurs Foncières (DGFiP) via data.gouv.fr — 5 millésimes (2021-2025), 37 départements.

## Problèmes détectés et corrections

| Dimension | Problème | Volume | Correction |
|---|---|---|---|
| Exactitude | Encodage double : les fichiers sont en UTF-8 mais ont été lus en latin-1 lors du téléchargement, produisant des caractères corrompus ("DÃ©pendance" au lieu de "Dépendance"). | Toutes les colonnes texte | Ré-encodage latin-1 → UTF-8 sur les modalités distinctes dans silver.py. |
| Exactitude | Valeurs aberrantes : prix < 1 000 € (donations déguisées), surfaces hors [9–1000 m²], prix/m² hors [100–30 000 €]. | 3 336 ventes exclues (toutes années) | Filtres de plausibilité en silver. Les seuils sont documentés dans le code. |
| Exactitude | Un même logement vendu deux fois le même jour à des prix différents = double saisie ou vente en plusieurs parts. Le prix ne peut pas être attribué. | 3 136 ventes exclues | Toutes les ventes de ce logement ce jour-là sont exclues. |
| Complétude | Une vente est éclatée en plusieurs lignes (une par local × nature de culture du terrain). La valeur foncière est répétée sur chaque ligne → impossible d'additionner directement. | Toutes les lignes | Reconstruction en silver : une ligne = une vente = un logement unique. |
| Complétude | Les transactions sans logement identifiable (terrains seuls, annexes, locaux professionnels, plusieurs logements) ne permettent pas de calculer un prix/m² fiable. | ~60 % des lignes brutes exclues | On garde uniquement les ventes avec exactement un logement (maison ou appartement) et aucun local professionnel. |
| Complétude | Surface du terrain absente pour les appartements (logique : copropriété). | 56,8 % de valeurs manquantes | Accepté — la colonne est gardée et utilisée uniquement pour les maisons. |
| Cohérence | Les arrondissements de Paris et Lyon ont des codes spécifiques dans DVF (751xx, 6938x) qui ne correspondent pas aux codes INSEE utilisés par OSM et INSEE. | ~8,9 % des ventes | Rattachement en silver : 751xx → 75056, 6938x → 69123. Le code d'arrondissement est conservé à part. |
| Unicité | Lignes strictement identiques (doublons complets) présentes dans certains millésimes. | ~120 000 lignes/millésime | Suppression par `drop_duplicates()` avant tout traitement. |
| Fraîcheur | Les reventes rapides (même logement revendu à moins de 30 jours d'intervalle) peuvent signaler des transactions atypiques (marchand de biens, correction d'erreur). | 2 874 ventes signalées | Gardées mais flagées `revente_moins_30j = True`. |

## Bilan

| Millésime | Lignes bronze | Ventes silver |
|---|---|---|
| 2021 | 2 020 967 | 503 616 |
| 2022 | 2 073 355 | 485 638 |
| 2023 | 1 668 783 | 375 784 |
| 2024 | 1 524 087 | 332 794 |
| 2025 | 1 594 815 | 372 867 |
| **Total** | **8 882 007** | **2 070 699** |

Prix/m² médian : 3 789 €/m² (appartements), 2 534 €/m² (maisons).
