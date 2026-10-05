# Dictionnaire — silver/osm_poi.parquet

Produit par `python src/osm/silver.py` à partir du bronze OSM (4 régions, 148 fichiers).
Une ligne par objet OSM retenu. Règles de nettoyage : voir `docs/osm/qualite.md`.

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `id_osm` | str | Clé OSM `type/id`, unique par catégorie | `way/123456` |
| `type_osm` | str | `node` / `way` / `relation` (way et relation réduits à leur centre) | `node` |
| `nom` | str/null | `tags.name`, null si absent | `Boulangerie Dupont` |
| `lat` | float | Latitude WGS84 (node ou `center` du way) | `48.8566` |
| `lon` | float | Longitude WGS84 | `2.3522` |
| `categorie` | enum | `education` / `sante` / `commerce` / `transport` | `commerce` |
| `sous_type` | str | Valeur `amenity` / `shop` / `public_transport`, 1re valeur si liste `a;b;c` | `bakery` |
| `mode` | str/null | Transport uniquement : `bus`, `tram`, `train`, `subway`… ou `inconnu` | `bus` |
| `id_arret` | str/null | Transport uniquement : `id_osm` du représentant de l'arrêt physique (stop_position de même nom à moins de 100 m) | `node/25337611` |
| `code_commune` | str | Code INSEE de la commune (jointure spatiale sur contours geo.api.gouv.fr). Clé de jointure DVF / INSEE. Paris, Lyon = commune entière (75056, 69123) | `75056` |
| `nom_commune` | str | Nom de la commune | `Paris` |
| `dept` | str | Département de la commune (et non département d'extraction) | `75` |
| `region` | str | `idf` / `occitanie` / `bretagne` / `ara` | `idf` |
| `is_vacant` | bool | `shop=vacant` : local vide, à exclure du comptage des commerces actifs | `false` |
| `is_untyped` | bool | `shop=yes` : commerce sans type | `false` |
| `name_missing` | bool | Nom absent, objet gardé | `false` |
| `date_extract` | str | Snapshot Overpass `timestamp_osm_base` du fichier source | `2026-09-07T12:52:23Z` |

## Usage en gold

- Nombre d'arrêts de transport : `nunique(id_arret)`, **pas** le nombre de lignes (une ligne = un `stop_position`).
- Commerces actifs : filtrer `~is_vacant`.
- Mention obligatoire : « © contributeurs OpenStreetMap » (ODbL).

## Qualité bronze → silver

Chiffres de `silver/osm_silver_stats.json` (exécution du 2026-10-05).

| Étape | Volume |
|---|---|
| Brut (bronze) | 309 773 |
| Écoles hors périmètre supprimées (`driving_school`, `music_school`…) | − 3 777 |
| Hors de toute commune à moins de 1 km, supprimés | − 3 |
| Doublons `id_osm` aux frontières départementales supprimés | − 68 |
| **Silver** | **305 925** |

| Contrôle | Volume |
|---|---|
| Commune trouvée par contour / par plus proche commune (< 1 km, bord de côte) | 305 965 / 28 |
| Communes couvertes | 8 488 |
| Sous-types multi-valeurs ramenés à la 1re valeur | 1 363 |
| `shop=vacant` flagués (gardés) | 5 489 |
| `shop=yes` flagués (gardés) | 1 052 |
| Sans nom, flagués (gardés) | 24 694 |
| Transport : stop_position → arrêts physiques | 69 262 → 43 996 (−36 %) |
| Transport : mode inconnu | 241 |

Par catégorie : commerce 187 258, transport 69 262, éducation 33 700, santé 15 705.
Par région : IdF 108 209, ARA 97 670, Occitanie 67 130, Bretagne 32 916.
