# Contrôle Gold

Exécuté le 2026-10-18T15:31:30.694188+00:00 — **OK**.

Rejouer depuis la racine : `python src/gold/controle.py`.

## Résultat des contrôles

| Contrôle | Résultat | Anomalies | Détail |
|---|---:|---:|---|
| Clé communale unique et conforme : INSEE Silver | OK | 0 |  |
| Clé communale unique et conforme : jointure Gold | OK | 0 |  |
| Clé communale unique et conforme : communes Gold | OK | 0 |  |
| Clé unique du marché et domaines année/type | OK | 0 |  |
| Communes Gold = référentiel INSEE | OK | 0 |  |
| Valeurs INSEE préservées dans la jointure | OK | 0 |  |
| Colonnes de la jointure préservées dans G_communes | OK | 0 |  |
| B3 : taille moyenne des ménages | OK | 0 |  |
| B3 : part des ménages d'une personne | OK | 0 |  |
| B3 : ménages d'une personne au plus égaux aux ménages | OK | 0 |  |
| B3 : part familles avec enfants de moins de 25 ans | OK | 0 |  |
| B3 : part familles avec enfants de moins de 25 ans bornée | OK | 0 |  |
| B3 : part familles monoparentales dans les ménages | OK | 0 |  |
| B3 : part familles monoparentales dans les ménages bornée | OK | 0 |  |
| Identifiants DVF uniques | OK | 0 |  |
| Ventes filtrées = volume du marché | OK | 0 |  |
| Ventes par commune, année et type | OK | 0 | 69,498 groupes |
| Volumes DVF communaux joints | OK | 0 |  |
| Ventes récentes par commune | OK | 0 |  |
| Ventes récentes maison par commune | OK | 0 |  |
| Ventes récentes appartement par commune | OK | 0 |  |
| OSM : nb_poi_osm par commune | OK | 0 |  |
| OSM : nb_ecoles par commune | OK | 0 |  |
| OSM : nb_sante par commune | OK | 0 |  |
| OSM : nb_commerces_actifs par commune | OK | 0 |  |
| OSM : nb_arrets_transport par commune | OK | 0 |  |
| Prix annuels masqués sous 10 ventes | OK | 0 |  |
| Prix annuels présents dès 10 ventes | OK | 0 |  |
| Médianes annuelles recalculées depuis DVF | OK | 0 |  |
| Variations annuelles et années consécutives | OK | 0 |  |
| Tendances annuelles cohérentes | OK | 0 |  |
| Seuil prix récents maison median | OK | 0 |  |
| Seuil prix récents maison moyen | OK | 0 |  |
| Prix récents maison median recalculés | OK | 0 |  |
| Prix récents maison moyen recalculés | OK | 0 |  |
| Seuil prix récents appartement median | OK | 0 |  |
| Seuil prix récents appartement moyen | OK | 0 |  |
| Prix récents appartement median recalculés | OK | 0 |  |
| Prix récents appartement moyen recalculés | OK | 0 |  |
| Densité ecoles recalculée | OK | 0 |  |
| Densité sante recalculée | OK | 0 |  |
| Densité commerces_actifs recalculée | OK | 0 |  |
| Densité arrets_transport recalculée | OK | 0 |  |
| Éligibilité du score | OK | 0 |  |
| Scores absents hors éligibilité et présents sinon | OK | 0 |  |
| Scores bornés entre 0 et 100 | OK | 0 |  |
| Pondération 40/30/30 du score | OK | 0 |  |
| Aucune valeur numérique infinie | OK | 0 |  |
| Statistiques JSON cohérentes | OK | 0 |  |
| Codes DVF sans correspondance documentés | OK | 0 |  |
| Date d'extraction OSM renseignée | OK | 0 |  |
| B1 : ventes géolocalisées uniques | OK | 0 |  |
| B1 : ventes géolocalisées conformes à la Silver DVF | OK | 0 |  |
| B1 : coordonnées géographiques valides | OK | 0 |  |
| B1 : statistiques de géolocalisation | OK | 0 |  |
| Gold à jour après insee_communes.parquet | OK | 0 |  |
| Gold à jour après dvf_ventes.parquet | OK | 0 |  |
| Gold à jour après osm_poi.parquet | OK | 0 |  |
| PostgreSQL G_jointure_communes : nombre de lignes | OK | 0 | 10,939 lignes |
| PostgreSQL G_marche_commune_annee_type : nombre de lignes | OK | 0 | 69,498 lignes |
| PostgreSQL G_communes : nombre de lignes | OK | 0 | 10,939 lignes |
| PostgreSQL G_ventes_geolocalisees : nombre de lignes | OK | 0 | 687,477 lignes |
| PostgreSQL G_jointure_communes : total nb_poi_osm | OK | 0 |  |
| PostgreSQL G_marche_commune_annee_type : total nb_ventes | OK | 0 |  |
| PostgreSQL G_communes : total score_eligible | OK | 0 |  |

## Couverture et limites

- Référentiel INSEE : 10,939 communes ; marché : 1,991,665 ventes comparables et 69,498 groupes annuels.
- DVF hors INSEE : 1,734 ventes (0.087 %) sur 27 codes. Ces ventes restent dans le marché annuel, mais ne sont pas rattachées aux scores communaux.
- Prix annuels masqués sous 10 ventes : 39,275 groupes ; communes éligibles au score : 6,136.
- Sans POI OSM : 2,451 communes ; sans vente récente : 316.
- Revenu médian présent : 9,658 communes ; taux de pauvreté présent : 2,233. Les valeurs INSEE manquantes restent nulles.
- Taille moyenne des ménages présente : 10,939 communes ; part des familles avec enfants de moins de 25 ans : 10,924 communes.
- B1 à 500 m : 687,477 ventes récentes géolocalisées (99.3 %). Les autres ventes ne figurent pas dans la comparaison spatiale.
- Dates d'extraction OSM : 2026-05-06, 2026-05-31, 2026-06-01, 2026-07-15, 2026-07-24, 2026-07-28, 2026-09-25, 2026-09-28, 2026-09-29. INSEE concerne 2023 (COG 2026) et DVF 2021–2025 : ces millésimes ne décrivent pas une même année.
- B1 : comparaison communale et comparaison à 500 m disponibles ; la localisation DVF est au centre de la parcelle et peut manquer. B3 : la part des familles avec enfants de moins de 25 ans ne doit pas être appelée part des ménages avec enfants.
