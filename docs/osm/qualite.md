# Data quality — source OSM

Périmètre : 4 régions (IdF, Occitanie, Bretagne, ARA), 37 départements × 4 catégories
(`ecoles`, `sante`, `shops`, `transport`) = 148 fichiers, **309 773 objets**, 119 Mo.
Mesures bronze : `python src/osm/profiling.py` (sorties : `docs/osm/profiling/*.csv`).
Résultats silver : `python src/osm/silver.py` (sortie : `silver/osm_silver_stats.json`).

Grille d'analyse : les cinq dimensions de qualité les plus utilisées et leurs facteurs [Akoka+2007] —
exactitude, complétude, cohérence, fraîcheur, unicité.

## Synthèse

| # | Dimension | Facteur | Problème | Volume (bronze) | Gravité | Traitement | Résultat |
|---|---|---|---|---|---|---|---|
| 1 | Exactitude | Correction sémantique | Région de même code INSEE récupérée avec le département | 311 210 objets parasites (50 % du brut) | Critique | Ingestion : `admin_level=6` | 620 983 → 309 773 objets |
| 2 | Exactitude | Correction sémantique | Commerces vacants `shop=vacant` comptés comme commerces | 5 488 | Moyenne | Silver : flag `is_vacant` | 5 489 flagués, exclus des comptages |
| 3 | Exactitude | Correction syntaxique | Sous-types multi-valeurs (`a;b;c`) | 1 363 | Faible | Silver : 1re valeur | 1 363 normalisés |
| 4 | Exactitude | Précision | Commerces non typés `shop=yes` | 1 052 | Faible | Silver : flag `is_untyped` | 1 052 flagués |
| 5 | Exactitude | Précision | Emprises (way/relation) réduites à leur centre | 16,2 % des objets | Faible | Accepté | `type_osm` conservé |
| 6 | Complétude | Couverture | Réponse Overpass vide acceptée comme valide | 2 fichiers (Ain) | Critique | Ingestion : rejet + nouvel essai | 148/148 fichiers non vides |
| 7 | Complétude | Couverture | Biais contributif urbain / rural | non mesuré | Forte | Gold : contrôle vs source officielle | À faire |
| 8 | Complétude | Densité | Adresses quasi absentes (code postal ~20 %) | ~80 % des objets | Forte | Silver : jointure spatiale commune | 100 % des objets rattachés à une commune |
| 9 | Complétude | Densité | Objets sans nom | 24 978 (8,1 %) | Faible | Silver : gardés + flag | 24 694 flagués |
| 10 | Complétude | Densité | Arrêts sans mode de transport | 241 | Faible | Silver : `mode = inconnu` | 241 |
| 11 | Complétude | Densité | Attributs descriptifs lacunaires (horaires, accessibilité) | 3 à 42 % renseignés | Moyenne | Non utilisés | — |
| 12 | Cohérence | Intégrité de domaine | Écoles hors cible captées par la regex `school` | 3 777 | Moyenne | Silver : liste blanche | 3 777 supprimés |
| 13 | Fraîcheur | Actualité (currency) | Snapshots étalés sur 146 jours | 148 fichiers | Moyenne | `date_extract` conservé | Re-extraction unique conseillée |
| 14 | Unicité | Unicité | Doublons `id_osm` aux frontières départementales | 70 | Faible | Silver : dédoublonnage | 68 supprimés (+ 2 copies d'un objet hors zone, cf. #5) |
| 15 | Unicité | Unicité | Arrêts de transport surcomptés (`stop_position` par sens/ligne) | ~35 % de redondance estimée | Forte | Silver : regroupement nom + 100 m | 69 262 → 43 996 arrêts (−36 %) |

Bilan : 309 773 objets bronze → **305 925 objets silver** (`silver/osm_poi.parquet`).

## 1. Exactitude

Les données représentent-elles correctement le monde réel ?

### Correction sémantique — données hors zone (#1, corrigé)
La requête `area["ref:INSEE"="XX"]` sans niveau administratif récupérait aussi la **région**
portant le même code : 01 → Guadeloupe, 11 → Île-de-France, 32 → Hauts-de-France,
75 → Nouvelle-Aquitaine, 93 → PACA, 94 → Corse. Les objets étaient attribués à un département
où ils ne se trouvent pas.

| Indicateur | Avant correction | Après |
|---|---|---|
| Objets | 620 983 | 309 773 |
| Doublons `id_osm` entre régions | 109 185 (17,6 %) | 0 |
| Points hors France métropolitaine | 2 988 | 0 |
| Aude — commerces | 70 165 | 2 218 |

**Correction** (`src/osm/main.py`) : filtre `admin_level=6` et zone construite depuis la relation
(`map_to_area`). Les 24 fichiers concernés ont été ré-extraits.
**Détection** : l'indicateur « doublons entre régions » de `profiling.py` doit rester à 0.

### Correction sémantique — commerces vacants (#2)
`shop=vacant` désigne un local commercial vide (ex. `node/260016963`, Paris). Le compter comme
commerce surestime l'offre réelle.
**Silver** : flag `is_vacant`. L'objet est gardé (indicateur de vacance commerciale) mais exclu
des comptages de commerces actifs.

### Correction syntaxique — valeurs multiples (#3)
Certains sous-types contiennent plusieurs valeurs séparées par `;`
(ex. `node/66492656` « Total » : `convenience;gas`), format non conforme à une valeur unique.
**Silver** : première valeur conservée, avant application de la liste blanche (#12).

### Précision — commerces non typés (#4)
`shop=yes` indique un commerce sans en préciser le type (ex. `node/1252380779` « Check Planet ») :
niveau de détail insuffisant pour une analyse par type de commerce.
**Silver** : flag `is_untyped`. L'objet compte dans le total des commerces, pas dans les comptages par type.

### Précision — géométrie simplifiée (#5)
16,2 % des objets sont des emprises (`way`, `relation`) réduites à leur centre (`out center`).
Suffisant pour compter, mais le centre d'une grande emprise (campus, hôpital) peut tomber dans une
commune voisine, voire hors zone : `relation/16105968` « Mines Paris – PSL » regroupe des campus
éloignés et son centre calculé tombe en Bourgogne (46,23 N ; 4,70 E).
**Silver** : accepté ; `type_osm` conservé pour identifier ces objets. Les objets dont le centre est à
plus de 1 km de toute commune des régions cibles sont supprimés (3 objets).

## 2. Complétude

Toutes les entités et tous les attributs utiles sont-ils présents ?

### Couverture — réponses vides (#6, corrigé)
Un miroir Overpass dont la base de zones était incomplète a renvoyé `elements: []` sans erreur
pour l'Ain (écoles, commerces). Le fichier était enregistré comme un résultat valide : toutes les
entités du département manquaient.
**Correction** : `fetch_one` rejette les réponses à 0 objet ou contenant `remark`, et réessaie.

### Couverture — biais contributif (#7)
OSM est contributif : les zones denses sont mieux cartographiées que les zones rurales. Un faible nombre
d'objets peut refléter un manque de contributeurs plutôt qu'un manque d'équipements.
**Contrôle proposé (gold)** : comparer la densité d'objets par habitant (population INSEE) avec une source
officielle (Base Permanente des Équipements INSEE, FINESS pour la santé). Les identifiants `ref:UAI`
(écoles) et `ref:FR:FINESS` (santé) présents dans OSM permettent un rapprochement direct.

### Densité — attributs (#8 à #11)

| Tag | Écoles | Santé | Commerces | Transport |
|---|---|---|---|---|
| `name` | 93,8 | 88,4 | 90,3 | 93,1 |
| `addr:postcode` | 18,7 | 26,5 | 22,1 | 0,0 |
| `addr:city` | 17,6 | 24,8 | 20,0 | 0,0 |
| `opening_hours` | 4,8 | 32,0 | 42,4 | 0,0 |
| `wheelchair` | 3,6 | 16,9 | 15,2 | 3,4 |

- **Coordonnées : 100 % présentes** (aucun objet sans géométrie grâce à `out center`).
- **Adresses (#8)** : environ 80 % des objets n'en ont pas. **Silver** : la commune (clé de jointure avec
  DVF et INSEE) est obtenue par jointure spatiale sur les contours communaux (geo.api.gouv.fr) ;
  les 28 points hors contours (bord de côte) prennent la commune la plus proche à moins de 1 km,
  3 objets au-delà sont supprimés.
- **Noms (#9)** : objets gardés (ils comptent dans les densités), flag `name_missing`.
- **Mode de transport (#10)** : arrêts sans tag `bus`/`tram`/`train`… (ex. funiculaire de Montmartre) → `mode = inconnu`.
- **Horaires et accessibilité (#11)** : trop lacunaires pour servir de variables d'analyse, non repris en silver.

## 3. Cohérence

Les données respectent-elles les règles du domaine ?

### Intégrité de domaine — écoles hors périmètre (#12)
Règle : une école a un sous-type parmi `school, college, university, kindergarten`.
La regex Overpass `amenity~"school|..."` capte aussi : `driving_school` (2 417),
`music_school` (849), `language_school` (136), `ski_school` (114), `dancing_school` (106),
`prep_school` (66)… (ex. `node/1113739034` « C.E.R. Pasteur », auto-école).
**Silver** : liste blanche, 3 777 objets supprimés. La catégorie santé n'est pas touchée.

## 4. Fraîcheur

Les données sont-elles assez récentes ?

### Actualité — snapshots hétérogènes (#13)
Dates de snapshot Overpass (`timestamp_osm_base`) par nombre de fichiers : mai 29, juin 27, juillet 19,
septembre 73. Le bronze n'est pas une photographie à une seule date. Les miroirs Overpass peuvent en plus
servir des données en retard.
**Silver** : `timestamp_osm_base` conservé par objet (`date_extract`).
**Conseil** : ré-extraire toute la source en un seul lot avant le rendu final.

## 5. Unicité

Une entité du monde réel est-elle représentée une seule fois ?

### Doublons aux frontières (#14)
70 objets sont présents dans deux départements (limites administratives partagées),
ex. `node/10754711287` « Ernest Renan », extrait à la fois par le 93 et le 94.
**Silver** : dédoublonnage sur `(categorie, id_osm)`, département issu de la jointure spatiale
(et non du département d'extraction) : 68 supprimés. Les 2 restants sont les copies de
`relation/16105968` (extraite par le 75, le 77 et le 91), supprimée car son centre tombe hors zone (#5).

### Arrêts de transport surcomptés (#15)
Un arrêt physique est représenté par plusieurs `stop_position` (un par sens, par ligne ou par mode) :
« Châtelet » compte 31 `stop_position` pour un seul pôle. Compter les objets bruts surestime l'offre.
**Silver** : regroupement des `stop_position` de même nom (normalisé, sans accents) distants de moins de
100 m → colonne `id_arret`. 69 262 objets → **43 996 arrêts** (−36 %). Les homonymes de communes
différentes ne sont pas fusionnés (« Mairie » : 230 objets → 168 arrêts dans 159 communes).
En gold, compter `nunique(id_arret)`.

## Référence

[Akoka+2007] Akoka, J.; Berti-Equille, L.; Boucelma, O.; Bouzeghoub, M.; Comyn-Wattiau, I.; Cosquer, M.;
Goasdoué-Thion, V.; Kedad, Z.; Nugier, S.; Peralta, V.; Sisaid-Cherfi, S.: A Framework for quality
evaluation in data integration systems. ICEIS 2007.
