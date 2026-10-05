# Dictionnaire — silver/insee_communes.parquet

Produit par `python src/insee/silver.py` à partir du bronze INSEE (7 jeux, 406 fichiers).
Une ligne par commune, **10 939 communes × 36 colonnes**. Règles de nettoyage : `docs/insee/qualite.md`.

Exemples pris sur Rennes (`35238`). Toutes les valeurs du recensement sont des estimations
pondérées, d'où les décimales.

## Clés

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `code_commune` | str | Code commune INSEE sur 5 caractères, **clé de jointure avec DVF et OSM**. Millésime géographique retiré | `35238` |
| `departement` | str | Code département, déduit du code commune | `35` |

## Revenus (Filosofi)

| Colonne | Type | Description | Exemple | Remplissage |
|---|---|---|---|---|
| `revenu_median` | float | Niveau de vie médian, en euros par an | `25100.0` | 88,3 % |
| `taux_pauvrete` | float | Part des habitants sous le seuil de pauvreté, en % | `22.7` | 20,4 % |

Les valeurs absentes le sont pour deux raisons distinctes, comptées dans
`silver/insee_silver_stats.json` : secret statistique (commune trop petite) ou indicateur non
diffusé à l'échelle communale.

## Population

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `population` | float | Nombre d'habitants (recensement) | `230890.0` |
| `population_municipale` | float | Population légale (source indépendante, sert de contrôle) | `230890.0` |
| `pop_moins_15` | float | Moins de 15 ans | `32554.0` |
| `pop_15_24` | float | 15 à 24 ans | `55696.56` |
| `pop_25_39` | float | 25 à 39 ans | `55675.56` |
| `pop_40_54` | float | 40 à 54 ans | `34581.06` |
| `pop_55_64` | float | 55 à 64 ans | `19337.15` |
| `pop_65_plus` | float | 65 ans et plus | `33045.67` |

## Logements

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `logements` | float | Total des logements | `137847.26` |
| `residences_principales` | float | Résidences principales | `122334.12` |
| `residences_secondaires` | float | Résidences secondaires ou occasionnelles | `6587.87` |
| `logements_vacants` | float | Logements vacants | `8925.27` |
| `rp_avant_1919` | float | Résidences principales construites avant 1919 | `5072.7` |
| `rp_1919_1945` | float | Construites entre 1919 et 1945 | `7287.36` |
| `rp_1946_1970` | float | Construites entre 1946 et 1970 | `29809.01` |
| `rp_1971_1990` | float | Construites entre 1971 et 1990 | `36316.84` |
| `rp_1991_2005` | float | Construites entre 1991 et 2005 | `19759.8` |
| `rp_apres_2006` | float | Construites à partir de 2006 | `21186.2` |
| `rp_1_piece` | float | Résidences principales d'une pièce | `18045.9` |
| `rp_5_pieces_ou_plus` | float | Résidences principales de 5 pièces ou plus | `22063.88` |

## Diplômes et emploi

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `pop_15_plus_diplome` | float | Population de 15 ans et plus, non scolarisée | `146900.68` |
| `diplome_superieur` | float | Dont diplôme de l'enseignement supérieur (code `EDUC=500T702_RP`, à confirmer) | `78243.96` |
| `actifs_15_64` | float | Actifs de 15 à 64 ans (code `EMPSTA_ENQ=1T2`, à confirmer) | `114258.75` |
| `chomeurs_15_64` | float | Dont chômeurs (code `EMPSTA_ENQ=2`, à confirmer) | `15731.47` |

## Indicateurs calculés

| Colonne | Type | Calcul | Exemple |
|---|---|---|---|
| `taux_vacance` | float | `logements_vacants / logements × 100` | `6.47` |
| `part_residences_secondaires` | float | `residences_secondaires / logements × 100` | `4.78` |
| `part_moins_15` | float | `pop_moins_15 / population × 100` | `14.1` |
| `part_25_39` | float | `pop_25_39 / population × 100` | `24.11` |
| `part_65_plus` | float | `pop_65_plus / population × 100` | `14.31` |
| `part_diplome_superieur` | float | `diplome_superieur / pop_15_plus_diplome × 100` | `53.26` |
| `taux_chomage` | float | `chomeurs_15_64 / actifs_15_64 × 100` | `13.77` |
| `rp_avant_1946` | float | `rp_avant_1919 + rp_1919_1945` | `12360.06` |

## À savoir avant d'utiliser cette table

- **Arrondissements** : Paris, Lyon et Marseille n'existent qu'en commune entière
  (`75056`, `69123`, `13055`). DVF utilise les codes d'arrondissement : le rattachement se fait
  côté DVF, sinon 5 % des ventes restent sans donnée INSEE.
- **Taux de pauvreté** : renseigné pour 2 233 communes seulement, qui concentrent toutefois
  54,7 % des ventes DVF. À réserver aux analyses urbaines.
- **Une seule année** (2023) : aucune évolution n'est calculable en l'état.
- **Ménages** : `DS_RP_MENAGES_PRINC` n'est pas encore repris, ses dimensions n'ayant pas de
  modalité « ensemble ».
