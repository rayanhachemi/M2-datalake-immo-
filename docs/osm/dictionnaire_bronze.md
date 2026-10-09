# Dictionnaire bronze OSM

Fichiers produits par `src/osm/main.py`.

- **Chemin** : `bronze/osm/{region}/osm_{region}_{dept}_{cat}.json`
- **Format** : JSON brut Overpass (`out center`)
- **Volume** : 148 fichiers, 309 773 objets, ~119 Mo
- **Licence** : ODbL — mention « © contributeurs OpenStreetMap » obligatoire

| Catégorie | Filtre Overpass |
|---|---|
| `ecoles` | `amenity ~ school\|college\|university\|kindergarten` |
| `sante` | `amenity ~ pharmacy\|hospital\|clinic\|doctors` |
| `shops` | tag `shop` présent |
| `transport` | `public_transport = stop_position` |

## Structure d'un objet

Chaque fichier contient une liste `elements`. Chaque élément a :

| Champ | Description |
|---|---|
| `type` | `node`, `way` ou `relation` |
| `id` | Identifiant OSM (unique par type) |
| `lat` / `lon` | Coordonnées (uniquement pour les `node`) |
| `center.lat` / `center.lon` | Centre calculé pour les `way` et `relation` |
| `tags` | Attributs libres : `name`, `amenity`, `shop`, `public_transport`, modes de transport... |
| `osm3s.timestamp_osm_base` | Date de la base OSM interrogée (fraîcheur de la donnée) |

La complétude détaillée des tags est dans `docs/osm/profiling/completude_tags.csv`.
