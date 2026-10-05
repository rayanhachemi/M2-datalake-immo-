# Dictionnaire — bronze INSEE

Produit par `python src/insee/main.py`. Réponses brutes de l'API Melodi, non transformées.

- **Emplacement** : `{DATASET}/region_{code}_{nom}/part_XXXX.json`
- **Volume** : 7 jeux × 4 régions = 406 fichiers, 4 419 302 observations, 1,7 Go, 10 939 communes
- **Format** : JSON statistique (SDMX) — une liste d'observations, pas un tableau
- **Licence** : Licence Ouverte / Open Licence (INSEE)
- **Découpage** : un fichier par page d'API, les communes étant demandées par lots (200 maximum)

| Jeu de données | Contenu | Observations |
|---|---|---|
| `DS_FILOSOFI_CC` | Revenus des habitants (Filosofi) : revenu médian, taux de pauvreté | 295 299 |
| `DS_RP_POPULATION_PRINC` | Recensement — habitants par âge et sexe | 360 987 |
| `DS_RP_MENAGES_PRINC` | Recensement — ménages, couples, personnes seules | 404 743 |
| `DS_RP_LOGEMENT_PRINC` | Recensement — logements : occupation, pièces, construction, chauffage | 1 126 717 |
| `DS_RP_EMPLOI_LR_PRINC` | Recensement — emploi et activité | 1 925 264 |
| `DS_RP_DIPLOMES_PRINC` | Recensement — niveaux de diplôme | 295 353 |
| `DS_POPULATIONS_HISTORIQUES` | Populations légales par année | 10 939 |

## Enveloppe du fichier

| Champ | Type | Description | Exemple |
|---|---|---|---|
| `identifier` | str | Nom du jeu de données | `DS_FILOSOFI_CC` |
| `title.fr` | str | Libellé du jeu | `Niveau de vie, taux de pauvreté...` |
| `publisher.id` | str | Producteur | `INSEE` |
| `paging.count` | int | Nombre d'observations annoncé pour la page | `5400` |
| `paging.isLast` | bool | Dernière page du lot | `true` |
| `paging.next` | str | URL de la page suivante, absente sur la dernière | |
| `observations` | list | Les observations elles-mêmes | |

Contrôle d'intégrité : `paging.count` doit égaler le nombre d'observations, et `isLast` doit être
vrai sur la dernière page de chaque lot. Vérifié fichier par fichier par `profiling.py`.

## Une observation

```json
{"dimensions": {"GEO": "2026-COM-35238", "TIME_PERIOD": "2023",
                "FILOSOFI_MEASURE": "MED_SL", "UNIT_MEASURE": "EUR_YR"},
 "attributes": {"OBS_STATUS": "A", "UNIT_MULT": "0", "CONF_STATUS": "F"},
 "measures":   {"OBS_VALUE_NIVEAU": {"value": 25100}}}
```

| Champ | Type | Description | Exemple |
|---|---|---|---|
| `dimensions.GEO` | str | Territoire : `{millésime}-{niveau}-{code}`. Seul `COM` est présent ici. **Le millésime vaut 2026 sauf pour `DS_POPULATIONS_HISTORIQUES`, en 2025.** | `2026-COM-35238` |
| `dimensions.TIME_PERIOD` | str | Année des données | `2023` |
| `dimensions.FREQ` | str | Périodicité, toujours annuelle | `A` |
| `dimensions.UNIT_MEASURE` | str | Unité : `EUR_YR` (euros par an), `PT` (pourcentage), `NR` (nombre) | `EUR_YR` |
| `dimensions.*_MEASURE` | str | Indicateur mesuré. **Le nom du champ change selon le jeu** : `FILOSOFI_MEASURE`, `RP_MEASURE`, `POPREF_MEASURE` | `MED_SL` |
| `dimensions.<découpage>` | str | Découpages propres au jeu : `AGE`, `SEX`, `OCS`, `NOR`, `BUILD_END`... De 0 à 9 selon le jeu | `Y25T39` |
| `attributes.OBS_STATUS` | str | `A` diffusé normalement, `O` non diffusé à ce niveau géographique | `A` |
| `attributes.CONF_STATUS` | str | `F` librement diffusable, `C` secret statistique | `F` |
| `attributes.UNIT_MULT` | str | Puissance de dix appliquée à la valeur, toujours `0` ici | `0` |
| `measures.OBS_VALUE_NIVEAU.value` | float | La valeur. **Absente = objet vide `{}`, et non `null`** | `25100` |

Le nombre de dimensions va de **4** (revenus, populations légales) à **13** (logements).
`DS_POPULATIONS_HISTORIQUES` n'a aucun attribut, donc ni `OBS_STATUS` ni `CONF_STATUS`.

## Modalités utiles

| Dimension | Modalité | Signification |
|---|---|---|
| toutes | `_T` | **Ensemble — c'est un total, à ne jamais additionner aux autres modalités** |
| `FILOSOFI_MEASURE` | `MED_SL` / `PR_MD60` | Revenu médian / taux de pauvreté. Les 25 autres indicateurs sont vides à la commune |
| `RP_MEASURE` | `POP` / `DWELLINGS` | Nombre de personnes / de logements |
| `POPREF_MEASURE` | `PMUN` | Population municipale |
| `OCS` | `DW_MAIN` / `DW_SEC_DW_OCC` / `DW_VAC` | Résidence principale / secondaire / logement vacant |
| `AGE` | `Y_LT15`, `Y15T24`, `Y25T39`, `Y40T54`, `Y55T64`, `Y_GE65` | Tranches d'âge |
| `BUILD_END` | `Y_LT1919` → `Y2006TAAAA` | Époque de construction. **`Y_LT2021` est le total des tranches** |
| `NOR` | `R1` → `R_GE5` | Nombre de pièces |
| `SEX` | `M` / `F` / `_T` | Hommes / femmes / ensemble |

Problèmes de qualité et traitements : `docs/insee/qualite.md`.
Mesures détaillées : `docs/insee/profiling/*.csv`.
