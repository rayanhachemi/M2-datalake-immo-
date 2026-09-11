# Dictionnaire — silver.osm_idf_poi

| Colonne | Type | Description | Exemple |
|---|---|---|---|
| `id_osm` | str | Clé OSM `type/id`, dédupliquée | `way/123456` |
| `nom` | str/null | `tags.name`, null si absent | `Boulangerie Dupont` |
| `lat` | float | Latitude (node ou `center` du way) | `48.8566` |
| `lon` | float | Longitude | `2.3522` |
| `categorie` | enum | education / sante / commerce / transport | `commerce` |
| `sous_type` | str | Valeur `amenity` / `shop` / `public_transport` | `bakery` |
| `dept` | str | Département INSEE d'extraction (doublons frontières dédupliqués) | `75` |
| `is_vacant` | bool | `shop=vacant` : local vide, exclu du comptage actif | `false` |
| `name_missing` | bool | Nom absent, objet gardé | `false` |
| `date_extract` | str | Snapshot Overpass `timestamp_osm_base` du fichier source | `2026-09-07T12:52:23Z` |

## Qualité avant → après (profilage → silver)

Brut 252 094 → silver 249 197. Écarts : ~2 775 écoles parasites
(`driving/music/language_school`) exclues, 5 305 `vacant` flagués (gardés),
20 679 sans nom gardés avec flag, 147 doublons `id_osm` frontières supprimés,
0 sans geo grâce à `out center`.
Détail complet : `docs/profilage_bronze.txt` + `silver/osm_idf_silver_stats.json`.
