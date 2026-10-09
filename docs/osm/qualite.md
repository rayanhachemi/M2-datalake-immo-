# Qualité OSM

4 régions, 37 depts, 4 catégories → 148 fichiers, 309 773 objets, 119 Mo.

## Problèmes identifiés

| # | Problème | Volume | Traitement |
|---|---|---|---|
| 1 | Requête sans `admin_level=6` ramenait aussi la région (même code INSEE) | 311k objets parasites (+50%) | Corrigé en ingestion |
| 2 | `shop=vacant` compté comme commerce actif | 5 488 | Flag `is_vacant` en silver |
| 3 | Sous-types multi-valeurs (`convenience;gas`) | 1 363 | Première valeur conservée |
| 4 | `shop=yes` : commerce sans type | 1 052 | Flag `is_untyped` |
| 5 | Emprises (way/relation) réduites à leur centre | 16,2 % | Accepté, `type_osm` conservé |
| 6 | Réponses Overpass vides sans erreur (Ain) | 2 fichiers | Rejet + nouvel essai en ingestion |
| 7 | ~80 % des objets sans adresse | — | Jointure spatiale sur contours communaux |
| 8 | Objets sans nom | 24 978 (8 %) | Gardés + flag `name_missing` |
| 9 | Arrêts sans mode de transport | 241 | `mode = inconnu` |
| 10 | Écoles hors périmètre (`driving_school`, `music_school`…) | 3 777 | Supprimés en silver |
| 11 | Snapshots sur 146 jours (pas une seule date) | 148 fichiers | `date_extract` conservé |
| 12 | Doublons `id_osm` aux frontières départementales | 70 | Dédoublonnage silver |
| 13 | Stop_positions surcomptés (un par sens/ligne) | ~35% redondance | Regroupement nom + 100 m → 43 996 arrêts |

## Bilan bronze → silver

309 773 → **305 925 objets** (`silver/osm_poi.parquet`)
