# Silver OSM — `silver/osm_poi.parquet`

Script : `python src/osm/silver.py`  
Résultat : **305 925 POI × 17 colonnes** (4 régions, 8 488 communes)

| Colonne | Type | Description |
|---|---|---|
| `id_osm` | str | `type/id` OSM, unique par catégorie |
| `type_osm` | str | `node` / `way` / `relation` |
| `nom` | str/null | Nom de l'objet |
| `lat` / `lon` | float | Coordonnées WGS84 |
| `categorie` | str | `education` / `sante` / `commerce` / `transport` |
| `sous_type` | str | Valeur `amenity`/`shop`/`public_transport` (1re valeur si `a;b;c`) |
| `mode` | str/null | Transport : `bus`, `tram`, `train`, `subway`… ou `inconnu` |
| `id_arret` | str/null | Transport : représentant du groupe d'arrêts (même nom, < 100 m) |
| `code_commune` | str | Code INSEE commune — **clé de jointure DVF/INSEE** |
| `nom_commune` | str | Nom de la commune |
| `dept` | str | Code département |
| `region` | str | `idf` / `occitanie` / `bretagne` / `ara` |
| `is_vacant` | bool | `shop=vacant` — local vide, à exclure des comptages |
| `is_untyped` | bool | `shop=yes` — commerce sans type |
| `name_missing` | bool | Objet sans nom (gardé) |
| `date_extract` | str | Snapshot Overpass source |

## Chiffres clés

| Étape | Volume |
|---|---|
| Bronze | 309 773 |
| − Écoles hors périmètre (`driving_school`…) | − 3 777 |
| − Hors communes (> 1 km) | − 3 |
| − Doublons frontières | − 68 |
| **Silver** | **305 925** |

Par catégorie : commerce 187 258 · transport 69 262 · éducation 33 700 · santé 15 705  
Par région : IdF 108 209 · ARA 97 670 · Occitanie 67 130 · Bretagne 32 916

> Pour compter les arrêts de transport, utiliser `nunique(id_arret)` et non `len()` — 69 262 stop_positions → 43 996 arrêts physiques.
