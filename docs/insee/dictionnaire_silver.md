# Silver INSEE — `silver/insee_communes.parquet`

Script : `python src/insee/silver.py`  
Résultat : **10 939 communes × 36 colonnes**

## Clés

| Colonne | Description |
|---|---|
| `code_commune` | Code INSEE 5 caractères — **clé de jointure DVF/OSM** |
| `departement` | Code département, déduit du code commune |

## Revenus (Filosofi)

| Colonne | Description | Remplissage |
|---|---|---|
| `revenu_median` | Revenu médian annuel (€) | 88 % |
| `taux_pauvrete` | Part sous le seuil de pauvreté (%) | 20 % (communes urbaines surtout) |

## Population

| Colonne | Description |
|---|---|
| `population` | Habitants (recensement) |
| `population_municipale` | Population légale (contrôle croisé) |
| `pop_moins_15` / `pop_15_24` / `pop_25_39` / `pop_40_54` / `pop_55_64` / `pop_65_plus` | Par tranche d'âge |

## Logements

| Colonne | Description |
|---|---|
| `logements` | Total |
| `residences_principales` / `residences_secondaires` / `logements_vacants` | Par occupation |
| `rp_avant_1919`, `rp_1919_1945`, `rp_1946_1970`, `rp_1971_1990`, `rp_1991_2005`, `rp_apres_2006` | Par époque de construction |
| `rp_1_piece` / `rp_5_pieces_ou_plus` | Petits et grands logements |

## Diplômes et emploi

| Colonne | Description |
|---|---|
| `pop_15_plus_diplome` | Population de 15 ans et plus non scolarisée |
| `diplome_superieur` | Dont diplôme du supérieur |
| `actifs_15_64` / `chomeurs_15_64` | Actifs et chômeurs (15-64 ans) |

## Indicateurs calculés

| Colonne | Calcul |
|---|---|
| `taux_vacance` | `logements_vacants / logements × 100` |
| `part_residences_secondaires` | `residences_secondaires / logements × 100` |
| `part_moins_15` / `part_25_39` / `part_65_plus` | Tranches d'âge / population × 100 |
| `part_diplome_superieur` | `diplome_superieur / pop_15_plus_diplome × 100` |
| `taux_chomage` | `chomeurs_15_64 / actifs_15_64 × 100` |
| `rp_avant_1946` | `rp_avant_1919 + rp_1919_1945` |

> Paris, Lyon, Marseille : INSEE n'a que la commune entière (`75056`, `69123`, `13055`). DVF utilise les arrondissements — le rattachement se fait côté DVF.
