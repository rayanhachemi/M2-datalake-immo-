# Dictionnaire silver DVF

Fichier produit par `src/dvf/silver.py` — une ligne par vente d'un logement unique.

- **Chemin** : `silver/dvf_ventes.parquet`
- **Volume** : 2 070 699 ventes × 17 colonnes (2021-2025)

| Colonne | Type | Description |
|---|---|---|
| `id_vente` | str | Identifiant unique de la vente (format `{annee}-{index}`) |
| `annee` | int | Année de la transaction |
| `date_mutation` | date | Date de la transaction |
| `nature_mutation` | str | `Vente` ou `Vente en l'état futur d'achèvement` |
| `type_bien` | str | `Maison` ou `Appartement` |
| `valeur_fonciere` | float | Prix de vente en euros |
| `surface_bati` | float | Surface bâtie en m² |
| `prix_m2` | float | Prix au m² calculé (`valeur_fonciere / surface_bati`), arrondi à l'euro |
| `nb_pieces` | int | Nombre de pièces principales |
| `surface_terrain` | float | Surface du terrain en m² (maisons uniquement, null pour les appartements) |
| `nb_dependances` | int | Nombre de dépendances (caves, parkings...) associées |
| `revente_moins_30j` | bool | `True` si ce même logement a été vendu à moins de 30 jours avant ou après |
| `region` | str | `idf`, `occitanie`, `bretagne` ou `ara` |
| `code_departement` | str | Code département (2 caractères) |
| `code_commune` | str | Code INSEE commune — **clé de jointure avec OSM et INSEE** (Paris = `75056`, Lyon = `69123`) |
| `code_arrondissement` | str | Code d'arrondissement DVF d'origine (Paris, Lyon) — null sinon |
| `nom_commune` | str | Nom de la commune |

Les colonnes d'adresse (numéro, voie, parcelle) ne sont pas exportées — CGU DGFiP.
