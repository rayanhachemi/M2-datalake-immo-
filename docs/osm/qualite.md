# Qualité des données OSM

Source : OpenStreetMap via l'API Overpass — 4 régions, 37 départements, 4 catégories = 148 fichiers, 309 773 objets bruts.

## Problèmes détectés et corrections

| Dimension | Problème | Volume | Correction |
|---|---|---|---|
| Exactitude | La requête Overpass sans niveau administratif renvoyait aussi les objets de la région portant le même code INSEE (ex. dept 75 → Nouvelle-Aquitaine). ~50 % des objets étaient hors périmètre. | 311 210 objets parasites | Ajout du filtre `admin_level=6` dans `main.py`. Les fichiers concernés ont été ré-extraits. |
| Exactitude | La requête "école" captait aussi les auto-écoles, écoles de musique, de ski, de danse... | 3 777 objets | Suppression en silver via une liste blanche des sous-types valides. |
| Exactitude | Certains tags ont plusieurs valeurs séparées par `;` (ex. `convenience;gas`). | 1 363 objets | On garde la première valeur uniquement. |
| Exactitude | `shop=vacant` = local vide, ne doit pas compter comme commerce actif. | 5 488 objets | Gardés avec flag `is_vacant`, exclus des comptages de commerces. |
| Exactitude | `shop=yes` = commerce sans type précis. | 1 052 objets | Gardés avec flag `is_untyped`. |
| Exactitude | Les emprises (`way`, `relation`) n'ont pas de coordonnées directes, Overpass renvoie le centre calculé. | 16 % des objets | Accepté — suffisant pour nos analyses. Le champ `type_osm` permet d'identifier ces objets. |
| Complétude | Environ 80 % des objets n'ont pas d'adresse. Impossible de rattacher à une commune directement. | ~248 000 objets sans adresse | Jointure spatiale sur les contours communaux (geo.api.gouv.fr). Les points hors contours prennent la commune la plus proche à < 1 km. |
| Complétude | 24 978 objets sans nom (8 %). | 24 978 objets | Gardés avec flag `name_missing`. |
| Unicité | 70 objets présents dans deux fichiers départementaux (frontière partagée). | 70 doublons | Dédoublonnage en silver sur `(categorie, id_osm)`. |
| Unicité | Un arrêt physique est représenté par plusieurs `stop_position` (un par sens, par ligne). Comptage brut = surreprésentation. | 69 262 → 43 996 arrêts réels | Regroupement en silver des stop_positions de même nom distants de moins de 100 m. |

## Bilan

| Étape | Volume |
|---|---|
| Bronze brut | 309 773 |
| − Écoles hors périmètre | − 3 777 |
| − Points hors communes (> 1 km) | − 3 |
| − Doublons aux frontières | − 68 |
| **Silver** | **305 925** |
