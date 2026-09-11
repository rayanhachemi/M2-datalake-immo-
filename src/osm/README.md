# Module OSM (IdF)

## Scripts

| Script | Rôle | Commande |
|---|---|---|
| `main_idf.py` | Bronze : 8 depts x 4 cats via Overpass `area INSEE`, `nwr + out center`, sleep 15 s, reprise auto | `python3 src/osm/main_idf.py [dept] [cat]` ex : `... 75 shops`, `... ecoles` |
| `profile_osm.py` | Profilage : volumes, types node/way/relation, sans `name`, `vacant`, top sous-types, version OSM | `python3 src/osm/profile_osm.py` |
| `clean_osm_silver.py` | Silver : fusion 32 JSON → 1 Parquet, filtres bruit, flags, dédup `id_osm` | `python3 src/osm/clean_osm_silver.py` |

## Catégories

`ecoles` → education (garde school/kindergarten/college/university),
`sante` → sante (garde pharmacy/hospital/clinic/doctors),
`shops` → commerce (`vacant` flagué), `transport` → transport.

## Sorties

- `bronze/idf/osm_idf_{75,77,78,91,92,93,94,95}_{ecoles,sante,shops,transport}.json` (~90 Mo, ~252k objets)
- `silver/osm_idf_poi.parquet` (249 197 lignes, 9 Mo) + `silver/osm_idf_silver_stats.json`
- Prochaine étape : pivot `code_commune` (sjoin contours) → `gold/osm_idf_density.csv`
