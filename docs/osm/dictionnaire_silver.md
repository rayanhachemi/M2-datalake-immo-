# Dictionnaire silver OSM

Fichier produit par `src/osm/silver.py` — une ligne par POI, toutes régions confondues.

- **Chemin** : `silver/osm_poi.parquet`
- **Volume** : 305 925 lignes × 17 colonnes

| Colonne | Type | Description |
|---|---|---|
| `id_osm` | str | Identifiant OSM (`type/id`) |
| `type_osm` | str | `node`, `way` ou `relation` |
| `nom` | str | Nom du lieu (`null` si absent) |
| `lat` / `lon` | float | Coordonnées WGS84 |
| `categorie` | str | `education`, `sante`, `commerce`, `transport` |
| `sous_type` | str | Valeur du tag principal (`amenity`, `shop`...) |
| `mode` | str | Transport : mode (`bus`, `tram`, `train`...) ou `inconnu` |
| `id_arret` | str | Transport : id de l'arrêt physique (stop_positions regroupés) |
| `code_commune` | str | Code INSEE commune — **clé de jointure avec DVF et INSEE** |
| `nom_commune` | str | Nom de la commune |
| `dept` | str | Code département |
| `region` | str | `idf`, `occitanie`, `bretagne` ou `ara` |
| `is_vacant` | bool | `True` si `shop=vacant` (local vide) |
| `is_untyped` | bool | `True` si `shop=yes` (commerce sans type) |
| `name_missing` | bool | `True` si le nom est absent |
| `date_extract` | str | Date du snapshot Overpass |

Pour compter les arrêts de transport : `nunique(id_arret)`, pas le nombre de lignes. Pour les commerces actifs : exclure `is_vacant = True`.
