# Dictionnaire — bronze OSM

Produit par `python src/osm/main.py`. Réponses brutes de l'API Overpass, non transformées.

- **Emplacement** : `bronze/osm/{region}/osm_{region}_{dept}_{cat}.json`
- **Volume** : 4 régions × 37 départements × 4 catégories = 148 fichiers, 309 773 objets, 119 Mo
- **Format** : JSON Overpass (`out center`)
- **Licence** : ODbL, mention « © contributeurs OpenStreetMap » obligatoire

| Catégorie (`cat`) | Filtre Overpass |
|---|---|
| `ecoles` | `amenity ~ school\|college\|university\|kindergarten` |
| `sante` | `amenity ~ pharmacy\|hospital\|clinic\|doctors` |
| `shops` | tout objet ayant un tag `shop` |
| `transport` | `public_transport = stop_position` |

## Enveloppe du fichier

| Champ | Type | Description | Exemple |
|---|---|---|---|
| `version` | float | Version du format OSM | `0.6` |
| `generator` | str | Version du serveur Overpass qui a répondu | `Overpass API 0.7.62.11` |
| `osm3s.timestamp_osm_base` | str | Date de la base OSM interrogée = fraîcheur réelle de la donnée | `2026-05-31T22:37:44Z` |
| `osm3s.timestamp_areas_base` | str | Date de la base des zones du serveur | `2026-05-31T22:37:44Z` |
| `osm3s.copyright` | str | Mention de licence ODbL | |
| `elements` | list | Les objets OSM (voir ci-dessous) | |

## Objet (`elements[]`)

| Champ | Type | Présent pour | Description | Exemple |
|---|---|---|---|---|
| `type` | str | tous | `node` (point), `way` (ligne / polygone), `relation` (objet composé) | `node` |
| `id` | int | tous | Identifiant OSM, unique **par type** seulement | `251652819` |
| `lat`, `lon` | float | `node` | Coordonnées WGS84 | `48.8527`, `2.3333` |
| `center.lat`, `center.lon` | float | `way`, `relation` | Centre calculé par Overpass | `48.8663`, `2.4020` |
| `nodes` | list[int] | `way` | Ids des points du contour (coordonnées absentes du fichier) | |
| `members` | list | `relation` | Composants `{type, ref, role}` ; `role` = `outer` / `inner` | |
| `tags` | dict | tous | Attributs libres `clé = valeur` (voir ci-dessous) | |

Répartition : 83,8 % de `node`, 16,2 % de `way` / `relation`.

## Tags

Les tags sont libres : aucun n'est obligatoire et chaque objet a son propre ensemble.
Les complétudes viennent de `profiling/completude_tags.csv`.

### Classification

| Tag | Description | Exemple |
|---|---|---|
| `amenity` | Type d'équipement (écoles, santé) | `pharmacy`, `school` |
| `shop` | Type de commerce | `bakery`, `vacant`, `yes` |
| `public_transport` | Rôle dans le réseau de transport | `stop_position` |
| `bus`, `tram`, `train`, `subway`, `light_rail`, `trolleybus`, `ferry`, `monorail` | Mode de transport desservi (`yes`) | `subway=yes` |
| `healthcare`, `education`, `school:FR` | Précisions sur le type | `maternelle` |

Un objet peut porter plusieurs tags de classification (ex. `shop=pastry` et `amenity=restaurant`).
Une valeur peut être multiple, séparée par `;` (ex. `convenience;gas`).

### Identité, adresse, attributs pratiques

Complétude (% d'objets renseignés, toutes régions) :

| Tag | Description | Écoles | Santé | Commerces | Transport |
|---|---|---|---|---|---|
| `name` | Nom | 94,0 | 89,4 | 90,3 | 95,7 |
| `brand` | Enseigne | 0,8 | 1,2 | 23,5 | 0,0 |
| `operator` | Gestionnaire | 6,7 | 6,8 | 7,4 | 7,6 |
| `addr:housenumber` | Numéro | 19,2 | 31,8 | 24,0 | 0,0 |
| `addr:street` | Voie | 22,3 | 33,9 | 26,7 | 0,0 |
| `addr:postcode` | Code postal | 17,5 | 25,8 | 21,4 | 0,0 |
| `addr:city` | Ville | 16,3 | 23,9 | 19,2 | 0,0 |
| `opening_hours` | Horaires (format OSM, ex. `Mo-Fr 08:30-21:00`) | 4,8 | 34,1 | 42,8 | 0,0 |
| `wheelchair` | Accessibilité `yes` / `no` / `limited` | 3,5 | 17,8 | 16,3 | 4,5 |
| `phone` | Téléphone | 16,3 | 31,1 | 24,4 | 0,0 |
| `website` | Site web | 15,4 | 14,8 | 24,1 | 0,0 |

### Identifiants externes

| Tag | Référentiel | Catégorie |
|---|---|---|
| `ref:UAI` | Établissements Éducation nationale | écoles |
| `ref:FR:FINESS` | Établissements de santé | santé |
| `ref:FR:SIRET`, `ref:FR:SIREN` | Répertoire Sirene | commerces, santé |
| `ref:FR:STIF`, `ref:FR:RATP` | Île-de-France Mobilités | transport IdF |
| `wikidata`, `wikipedia` | Liens encyclopédiques | gros objets |

### Métadonnées contributives

| Tag | Description |
|---|---|
| `source` | Origine de l'information selon le contributeur (texte libre) |
| `check_date` | Date de dernière vérification sur le terrain |

## Champs repris en silver

`type`, `id`, `lat`/`lon` (ou `center`), `tags.name`, tag de classification, tags de mode,
`osm3s.timestamp_osm_base`. Voir `dictionnaire_silver.md`.
