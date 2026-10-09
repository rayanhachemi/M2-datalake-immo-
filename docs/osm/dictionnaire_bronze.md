# Bronze OSM

Script : `python src/osm/main.py`  
Sortie : `bronze/osm/{region}/osm_{region}_{dept}_{cat}.json` — 148 fichiers, ~310k objets, 119 Mo  
Licence : ODbL — mention « © contributeurs OpenStreetMap » obligatoire

| Catégorie | Filtre Overpass |
|---|---|
| `ecoles` | `amenity ~ school\|college\|university\|kindergarten` |
| `sante` | `amenity ~ pharmacy\|hospital\|clinic\|doctors` |
| `shops` | tout tag `shop` |
| `transport` | `public_transport = stop_position` |

## Structure d'un fichier

```
{
  "osm3s": { "timestamp_osm_base": "2026-05-31T22:37:44Z", ... },
  "elements": [ ... ]
}
```

| Champ | Description |
|---|---|
| `osm3s.timestamp_osm_base` | Date de la base OSM interrogée (fraîcheur réelle) |
| `elements[].type` | `node`, `way` ou `relation` |
| `elements[].id` | ID OSM, unique **par type** |
| `elements[].lat/lon` | Coordonnées (node seulement) |
| `elements[].center.lat/lon` | Centre calculé (way/relation) |
| `elements[].tags` | Attributs libres : `name`, `amenity`, `shop`, `bus`, `addr:*`… |

83,8 % des objets sont des `node`, 16,2 % des `way`/`relation` réduits à leur centre.

## Tags de complétude (%)

| Tag | Écoles | Santé | Commerces | Transport |
|---|---|---|---|---|
| `name` | 94,0 | 89,4 | 90,3 | 95,7 |
| `addr:postcode` | 17,5 | 25,8 | 21,4 | 0,0 |
| `opening_hours` | 4,8 | 34,1 | 42,8 | 0,0 |
| `wheelchair` | 3,5 | 17,8 | 16,3 | 4,5 |
