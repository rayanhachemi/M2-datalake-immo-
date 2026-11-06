# Spécification Gold — schéma conceptuel

Le Gold comprend **quatre tables**, construites dans PostgreSQL par des requêtes `INSERT ... SELECT` à partir de quatre tables Silver : `S_dvf_ventes`, `S_osm_poi`, `S_insee_communes` et `S_communes`. Cette dernière est préparée depuis les contours géographiques conservés en Bronze et les codes DVF Silver. Le code communal est une chaîne de cinq caractères ; les liens entre tables Gold sont des clés étrangères PostgreSQL.

| Table | Grain et clé primaire | Colonnes métier | Relation |
|---|---|---|---|
| `G_COMMUNE` | Une commune ; `code_commune` | `nom_commune`, `departement`, `region` | Parent des trois autres tables |
| `G_TRANSACTION` | Une vente comparable ; `id_vente` | `date_mutation`, `type_bien`, `valeur_fonciere`, `surface_bati`, `prix_m2` | `code_commune` → `G_COMMUNE` |
| `G_POINT_INTERET` | Un objet OSM ; `id_osm` | `nom`, `categorie`, `sous_type`, `latitude`, `longitude` | `code_commune` → `G_COMMUNE` |
| `G_PROFIL_COMMUNE` | Un profil INSEE ; `code_commune` | `revenu_median`, `population`, `taux_chomage`, `taux_pauvrete` | Sa PK est aussi une FK vers `G_COMMUNE` |

`G_TRANSACTION` conserve les ventes de maisons et appartements avec `nature_mutation = 'Vente'` et sans revente à moins de 30 jours, de 2021 à 2025. Les prix sont nominaux. Les codes DVF qui ne sont plus dans le référentiel INSEE restent dans `G_COMMUNE` afin de conserver la clé étrangère ; ces communes n'ont pas de profil.

Les noms communaux proviennent de `S_communes`. Les revenus et taux INSEE non diffusés restent `NULL`. Un même `id_osm` peut apparaître dans deux catégories Silver, notamment une pharmacie dans santé et commerce. Gold garde une seule ligne par objet avec la priorité `sante`, `education`, `transport`, `commerce`.

## Requêtes métier livrées

- **B1 — comparaison communale :** prix par commune et type sur 2021–2025, calculé comme médiane des médianes annuelles ayant au moins dix ventes. Les années moins fournies ne publient pas de prix. Le nombre de ventes total couvre les cinq ans.
- **B2 — implantation :** activité = ventes 2024–2025 ; dynamique = médiane des variations de prix par type entre 2022–2023 et 2024–2025, avec au moins dix ventes dans chaque fenêtre ; équipements = densités des quatre catégories OSM pour 1 000 habitants, avec un plancher de 1 000 habitants. Les rangs percentiles régionaux sont calculés par `CUME_DIST`. Le score est `0,40 × dynamique + 0,30 × activité + 0,30 × équipements`. Une commune est classée si sa population est positive, qu'elle a au moins dix ventes récentes et une dynamique calculable. Le schéma ne conserve ni `id_arret` ni `is_vacant` : le transport compte des objets OSM distincts et tous les commerces de la table sont comptés.
- **B3 — recherche pour un couple :** communes candidates autour du lieu de travail, classées par distance approximative de leur centre moyen de POI OSM à l'adresse de travail géocodée dans le notebook. Sans coordonnées de travail, la requête utilise le centre moyen de la commune de travail. Elle exige un point de transport, au moins un équipement ou commerce et dix ventes récentes du type choisi dans une plage de surface autour de celle souhaitée. Elle donne la médiane du prix total de ces biens comparables, rapportée au revenu annuel du couple. Un budget d'achat maximal peut être fourni explicitement. La carte montre le lieu de travail, les communes candidates, des exemples de ventes historiques et des points OSM géolocalisés. Le schéma Gold ne permet ni une distance exacte entre logement et travail, ni une distance précise aux équipements, ni un indice général du coût de la vie ou une recherche d'annonces disponibles.
- **B4 — tendance :** médiane et moyenne annuelle du prix au m² pour une commune et un type de bien, publiées à partir de dix ventes. Variation annuelle et variation 2021–2025 uniquement lorsque les deux médianes existent. Années sans vente conservées avec zéro vente et prix `NULL`.
- **B5 — zones à prix bas bien équipées :** médiane communale 2024–2025 du type choisi, au moins dix ventes, comparée à la médiane des médianes communales de sa région. Une commune est retenue si son prix est sous le seuil demandé, son score d'équipements dépasse le seuil et son revenu médian atteint la médiane régionale. Le score d'équipements suit la définition de B2 et est calculé parmi toutes les communes de la région ayant une population positive.

Les cinq requêtes lisent directement ces quatre tables. Aucun score ni prix n'est conservé dans une cinquième table.
