# Data quality — source OSM (bronze)

Périmètre : 4 régions (IdF, Occitanie, Bretagne, ARA), 37 départements × 4 catégories
(`ecoles`, `sante`, `shops`, `transport`) = 148 fichiers, **309 773 objets**, 119 Mo.
Chiffres issus de `python src/osm/profiling.py` (sorties : `docs/profiling/osm_*.csv`).

## Synthèse

| # | Dimension | Problème | Volume | Gravité | Traitement |
|---|---|---|---|---|---|
| 1 | Exactitude géographique | Région de même code INSEE récupérée avec le département | 311 210 objets parasites (50 % du brut) | Critique | **Corrigé à l'ingestion** |
| 2 | Validité | Réponse Overpass vide acceptée comme valide | 2 fichiers (Ain) | Critique | **Corrigé à l'ingestion** |
| 3 | Unicité | Doublons `id_osm` aux frontières départementales | 70 | Faible | Silver : dédoublonnage |
| 4 | Unicité | Arrêts de transport surcomptés (`stop_position` par sens/ligne) | ~35 % de redondance estimée | Forte | Silver : regroupement spatial |
| 5 | Conformité au périmètre | Écoles hors cible captées par la regex `school` | 3 777 | Moyenne | Silver : liste blanche |
| 6 | Validité | Commerces vacants `shop=vacant` | 5 488 | Moyenne | Silver : flag + exclusion des comptages |
| 7 | Validité | Commerces non typés `shop=yes` | 1 052 | Faible | Silver : flag |
| 8 | Validité | Sous-types multi-valeurs (`a;b;c`) | 1 363 | Faible | Silver : 1re valeur |
| 9 | Complétude | Arrêts sans mode de transport | 241 | Faible | Silver : `mode = inconnu` |
| 10 | Complétude | Objets sans nom | 24 978 (8,1 %) | Faible | Silver : gardés + flag |
| 11 | Complétude | Adresses quasi absentes (code postal ~20 %) | ~80 % des objets | Forte | Silver : jointure spatiale commune |
| 12 | Complétude | Attributs descriptifs lacunaires (horaires, accessibilité) | 3 à 42 % renseignés | Moyenne | Non utilisés |
| 13 | Couverture | Biais contributif urbain / rural | non mesuré | Forte | Gold : contrôle vs source officielle |
| 14 | Fraîcheur | Snapshots étalés sur 146 jours | 148 fichiers | Moyenne | Documenté ; re-extraction unique conseillée |
| 15 | Géométrie | Emprises (way/relation) réduites à leur centre | 16,2 % des objets | Faible | Accepté |
| 16 | Juridique | Licence ODbL | toute la source | — | Attribution + partage à l'identique |

## Détail

### 1. Données hors zone (corrigé)
La requête `area["ref:INSEE"="XX"]` sans niveau administratif récupérait aussi la **région**
portant le même code : 01 → Guadeloupe, 11 → Île-de-France, 32 → Hauts-de-France,
75 → Nouvelle-Aquitaine, 93 → PACA, 94 → Corse.

| Indicateur | Avant correction | Après |
|---|---|---|
| Objets | 620 983 | 309 773 |
| Doublons `id_osm` entre régions | 109 185 (17,6 %) | 0 |
| Points hors France métropolitaine | 2 988 | 0 |
| Aude — commerces | 70 165 | 2 218 |

**Correction** (`src/osm/main.py`) : filtre `admin_level=6` et zone construite depuis la relation
(`map_to_area`). Les 24 fichiers concernés ont été ré-extraits.
**Détection** : l'indicateur « doublons entre régions » de `profiling.py` doit rester à 0.

### 2. Réponses vides (corrigé)
Un miroir Overpass dont la base de zones était incomplète a renvoyé `elements: []` sans erreur
pour l'Ain (écoles, commerces). Le fichier était enregistré comme un résultat valide.
**Correction** : `fetch_one` rejette les réponses à 0 objet ou contenant `remark`, et réessaie.

### 3. Doublons aux frontières
70 objets sont présents dans deux départements (limites administratives partagées).
**Silver** : dédoublonner sur `id_osm`, en gardant le département de rattachement issu
de la jointure spatiale (et non le département d'extraction).

### 4. Surcomptage des arrêts de transport
Un arrêt physique est représenté par plusieurs `stop_position` (un par sens, par ligne ou par mode).
En regroupant par nom sur une grille d'environ 500 m, les 69 289 objets correspondent à environ
**44 900 arrêts** : ~35 % de redondance. Compter les `stop_position` bruts surestime l'offre.
**Silver** : regrouper par nom et proximité (moins de 50 à 100 m), ou utiliser `stop_area`.

### 5. Écoles hors périmètre
La regex Overpass `amenity~"school|..."` capte aussi : `driving_school` (2 417),
`music_school` (849), `language_school` (136), `ski_school` (114), `dancing_school` (106),
`prep_school` (66)… Ce ne sont pas des établissements scolaires.
**Silver** : liste blanche `school, college, university, kindergarten`. La catégorie santé n'est pas touchée.

### 6 à 9. Valeurs de sous-type problématiques
- `shop=vacant` : local commercial vide. À garder (indicateur de vacance commerciale), mais à exclure des comptages de commerces actifs.
- `shop=yes` : commerce sans type précis. Inutilisable pour une analyse par type de commerce.
- Valeurs multiples (`pharmacy;hearing_aids;medical_supply`) : non normalisées. On garde la première valeur.
- Arrêts sans tag `bus`/`tram`/`train`… : mode inconnu.

### 10 à 12. Complétude des attributs (% renseigné)

| Tag | Écoles | Santé | Commerces | Transport |
|---|---|---|---|---|
| `name` | 93,8 | 88,4 | 90,3 | 93,1 |
| `addr:postcode` | 18,7 | 26,5 | 22,1 | 0,0 |
| `addr:city` | 17,6 | 24,8 | 20,0 | 0,0 |
| `opening_hours` | 4,8 | 32,0 | 42,4 | 0,0 |
| `wheelchair` | 3,6 | 16,9 | 15,2 | 3,4 |

- **Coordonnées : 100 % présentes** (aucun objet sans géométrie grâce à `out center`).
- **Adresses** : environ 80 % des objets n'en ont pas. Le rattachement à la commune (clé de jointure
  avec DVF et INSEE) doit donc se faire par **jointure spatiale** sur les contours communaux, pas par l'adresse.
- Horaires et accessibilité : trop lacunaires pour servir de variables d'analyse.

### 13. Biais de couverture
OSM est contributif : les zones denses sont mieux cartographiées que les zones rurales. Un faible nombre
d'objets peut refléter un manque de contributeurs plutôt qu'un manque d'équipements.
**Contrôle proposé** : comparer la densité d'objets par habitant (population INSEE) avec une source
officielle (Base Permanente des Équipements INSEE, FINESS pour la santé).

### 14. Fraîcheur hétérogène
Dates de snapshot Overpass (`timestamp_osm_base`) par nombre de fichiers : mai 29, juin 27, juillet 19,
septembre 73. Le bronze n'est pas une photographie à une seule date. Les miroirs Overpass peuvent en plus
servir des données en retard. Conseil : ré-extraire toute la source en un seul lot avant le rendu final,
et conserver `timestamp_osm_base` dans le silver (`date_extract`).

### 15. Géométrie simplifiée
16,2 % des objets sont des emprises (`way`, `relation`) réduites à leur centre. C'est suffisant pour compter,
mais le centre d'une grande emprise (campus, hôpital) peut tomber dans une commune voisine.

### 16. Licence
Open Database License (ODbL) : mention « © contributeurs OpenStreetMap » obligatoire. Tout jeu de données
dérivé redistribué doit rester sous ODbL.
