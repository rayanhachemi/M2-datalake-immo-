# Dictionnaire silver INSEE

Fichier produit par `src/insee/silver.py` — une ligne par commune.

- **Chemin** : `silver/insee_communes.parquet`
- **Volume** : 10 939 communes × 36 colonnes

## Clé de jointure

| Colonne | Description |
|---|---|
| `code_commune` | Code INSEE commune (5 caractères) — **clé de jointure avec DVF et OSM** |
| `departement` | Code département (déduit du code commune) |

## Revenus

| Colonne | Description | Couverture |
|---|---|---|
| `revenu_median` | Revenu médian annuel en euros (Filosofi) | 88 % des communes |
| `taux_pauvrete` | Part de la population sous le seuil de pauvreté (%) | 20 % (grandes villes) |

## Population

| Colonne | Description |
|---|---|
| `population` | Nombre d'habitants (recensement) |
| `population_municipale` | Population légale |
| `pop_moins_15` | Moins de 15 ans |
| `pop_15_24` | 15 à 24 ans |
| `pop_25_39` | 25 à 39 ans |
| `pop_40_54` | 40 à 54 ans |
| `pop_55_64` | 55 à 64 ans |
| `pop_65_plus` | 65 ans et plus |

## Logements

| Colonne | Description |
|---|---|
| `logements` | Total des logements |
| `residences_principales` | Résidences principales |
| `residences_secondaires` | Résidences secondaires |
| `logements_vacants` | Logements vacants |
| `rp_avant_1919` / `rp_1919_1945` / ... / `rp_apres_2006` | Résidences principales par époque de construction |
| `rp_1_piece` / `rp_5_pieces_ou_plus` | Résidences principales par taille |

## Emploi et diplômes

| Colonne | Description |
|---|---|
| `pop_15_plus_diplome` | Population de 15 ans et plus non scolarisée |
| `diplome_superieur` | Dont diplôme du supérieur |
| `actifs_15_64` | Actifs de 15 à 64 ans |
| `chomeurs_15_64` | Dont chômeurs |

## Indicateurs calculés

| Colonne | Calcul |
|---|---|
| `taux_vacance` | `logements_vacants / logements × 100` |
| `part_residences_secondaires` | `residences_secondaires / logements × 100` |
| `part_moins_15` | `pop_moins_15 / population × 100` |
| `part_25_39` | `pop_25_39 / population × 100` |
| `part_65_plus` | `pop_65_plus / population × 100` |
| `part_diplome_superieur` | `diplome_superieur / pop_15_plus_diplome × 100` |
| `taux_chomage` | `chomeurs_15_64 / actifs_15_64 × 100` |
| `rp_avant_1946` | `rp_avant_1919 + rp_1919_1945` |

**Note :** Paris, Lyon et Marseille n'existent qu'en commune entière (`75056`, `69123`, `13055`). Le rattachement des arrondissements DVF se fait côté DVF.
