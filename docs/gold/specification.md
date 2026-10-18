# Spécification Gold — observatoire immobilier

Cette étape fixe les grains et les indicateurs avant la construction des tables. Le périmètre retenu est celui des Silver actuelles : 37 départements dans quatre régions, ventes DVF 2021–2025, indicateurs INSEE observés en 2023 sur le référentiel communal 2026, et snapshot OSM de la date `date_extract`.

## Sources et règles communes

| Source Silver | Grain | Usage Gold |
|---|---|---|
| `silver/dvf_ventes.parquet` | Une vente d'un logement unique | Prix et activité du marché |
| `silver/insee_communes.parquet` | Une commune | Population et profil socio-économique |
| `silver/osm_poi.parquet` | Un POI | Équipements communaux |

- Pivot : `code_commune`, conservé comme texte à cinq caractères. Aucun regroupement par nom de commune.
- Marché comparable : `nature_mutation = 'Vente'` et `revente_moins_30j = False`. Les VEFA et reventes rapides restent en Silver ; leurs volumes exclus seront publiés dans les contrôles Gold. Les prix sont nominaux, sans correction de l'inflation.
- Les prix au m² sont comparés **à type de bien identique** (`Maison` ou `Appartement`). Une médiane réunissant les deux types serait sensible au changement de leur proportion.
- Une statistique de prix n'est publiée que pour **au moins 10 ventes** dans son groupe. Le nombre de ventes reste visible sous ce seuil, mais les prix et variations correspondants valent `null`.
- Sur les Silver actuelles, 39 275 des 69 498 groupes commune × année × type (56,5 %) sont sous ce seuil ; les indicateurs récents sur deux années réduisent cette fragilité pour B2.
- Aucune valeur INSEE absente n'est remplacée par zéro. Pour les POI, l'absence d'objet rattaché à une commune du périmètre vaut zéro dans le comptage ; cela ne garantit pas l'exhaustivité d'OSM.

## Table 1 — `G_marche_commune_annee_type`

Sorties prévues : `gold/marche_commune_annee_type.parquet` et table PostgreSQL `G_marche_commune_annee_type`.

**Grain et clé unique :** `(code_commune, annee, type_bien)`. Une ligne représente le marché d'un type de logement dans une commune et une année. Les années sans vente n'ont pas de ligne. La table contient aussi les codes DVF qui ne trouvent pas encore de correspondance INSEE, afin de ne pas masquer ces ventes.

| Indicateur | Définition |
|---|---|
| `nb_ventes` | Nombre de ventes comparables distinctes (`id_vente`) |
| `prix_m2_median`, `prix_m2_moyen` | Médiane et moyenne de `prix_m2`, en €/m² ; `null` si `nb_ventes < 10` |
| `prix_m2_q1`, `prix_m2_q3` | Quartiles 25 % et 75 % ; même seuil de publication |
| `prix_vente_median` | Médiane de `valeur_fonciere`, en € ; même seuil de publication |
| `variation_annuelle_pct` | `100 × (médiane année N / médiane année N-1 − 1)` pour le même type et la même commune ; `null` si une année manque ou n'atteint pas 10 ventes |
| `tendance_annuelle` | `hausse` si variation ≥ 3 %, `baisse` si ≤ −3 %, `stable` sinon ; `non_concluante` sans variation fiable |

## Table 2 — `G_communes`

Sorties prévues : `gold/communes.parquet` et table PostgreSQL `G_communes`.

**Grain et clé unique :** une ligne par `code_commune` du référentiel INSEE Silver (10 939 communes attendues). La table utilise INSEE comme base et ajoute les agrégats DVF et OSM par jointures gauches. Les codes DVF absents du référentiel sont conservés dans la table de marché et signalés dans les contrôles ; ils ne sont pas classés dans le score.

| Domaine | Colonnes à exposer | Calcul / précaution |
|---|---|---|
| Identité | `code_commune`, `departement`, `region` | Région déterminée par le département ; libellé communal à ajouter depuis un référentiel fiable si nécessaire |
| Profil INSEE | `population`, `revenu_median`, `taux_pauvrete`, `part_moins_15`, `part_25_39`, `part_65_plus`, `taux_vacance` | Reprise des Silver ; conserver les `null` du secret statistique |
| Marché récent | `nb_ventes_2024_2025`, `nb_ventes_maison_2024_2025`, `nb_ventes_appartement_2024_2025` | Ventes comparables, deux années regroupées |
| Prix récents | `prix_m2_median_maison_2024_2025`, `prix_m2_moyen_maison_2024_2025` et équivalents `appartement` | Statistiques recalculées sur les ventes des deux années, et non moyenne des statistiques annuelles ; `null` sous 10 ventes du type |
| Équipements | `nb_ecoles`, `nb_sante`, `nb_commerces_actifs`, `nb_arrets_transport` | OSM par commune ; commerces avec `is_vacant = False` ; arrêts comptés par `nunique(id_arret)` |
| Densité d'équipements | `densite_*_pour_1000_habitants` | `1000 × nombre / population` si population > 0 ; `null` sinon. Le score utilisera un plancher de 1 000 habitants au dénominateur pour éviter les valeurs extrêmes dans les petites communes. |
| Couverture | `a_ventes_recentes`, `a_poi`, `revenu_disponible`, `score_eligible` | Distinguer absence de donnée, vrai zéro et non-éligibilité au score |

### Score d'attractivité B2

Le score est un **classement exploratoire**, pas une prévision de hausse future. Il est calculé pour les communes ayant une population positive, au moins 10 ventes comparables récentes et une dynamique de prix fiable.

1. `dynamique_prix_pct` : pour chaque type, variation de la médiane entre 2022–2023 et 2024–2025, avec au moins 10 ventes dans **chacune** des deux fenêtres. On prend la médiane des variations des types disponibles, plafonnée entre −50 % et +100 % avant classement.
2. `activite_marche` : nombre total de ventes comparables en 2024–2025. Le volume brut mesure la taille du marché pour une implantation d'agence.
3. `equipements` : moyenne des rangs des quatre densités par 1 000 habitants (écoles, santé, commerces actifs, arrêts), chacune calculée avec `max(population, 1000)` au dénominateur. Les catégories ont ainsi le même poids malgré leurs volumes différents.
4. Chaque composante est convertie en rang percentile **parmi les communes éligibles de sa région**, sur 0–100. `score_attractivite = 0,40 × score_dynamique + 0,30 × score_activite + 0,30 × score_equipements`. Les trois composantes et `score_eligible` sont exposés pour expliquer le classement. Aucun score partiel n'est calculé si une composante manque.

Pour B5, une requête distincte recherchera des communes à prix médian bas **pour le même type et la même région**, avec un score d'équipements élevé et un `revenu_median` renseigné. Le taux de pauvreté ne peut pas être un filtre obligatoire : il n'est diffusé que pour environ 20 % des communes.

## Besoins couverts et limites

| Besoin | Exploitation prévue | Limite actuelle |
|---|---|---|
| B2 — implantation | Classement par `score_attractivite`, avec ses composantes | Écarter les communes sans volumes suffisants ; score à interpréter comme aide à la décision. |
| B4 — tendance | Série annuelle de prix par commune et type, avec variation et tendance | Petits échantillons masqués ; euros courants. |
| B5 — zones sous-évaluées | Prix récent + densité d'équipements + filtre de revenu | Constat descriptif, sans promesse de valorisation future. |

## Contrôles à prévoir lors de l'implémentation

- Clés uniques aux deux grains, codes commune en texte, aucune division par zéro.
- Rapprochement entre le nombre de ventes comparables Silver et la somme de `nb_ventes` de la table de marché.
- Couverture des jointures : actuellement 27 codes commune DVF sont absents des 10 939 codes INSEE ; documenter leur nombre de ventes et résoudre les changements de code si nécessaire.
- Valeurs manquantes des prix sous le seuil de 10 ventes ; score borné entre 0 et 100, `null` si non éligible.
- Distinguer les millésimes : INSEE 2023, marché DVF 2021–2025 et date d'extraction OSM. Ne pas présenter leur jointure comme une observation d'une même année.
