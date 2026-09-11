# Observatoire immobilier et attractivité résidentielle — Clé en Main Immo

Data Lake médaillon (bronze → silver → gold) sur l'Île-de-France.
Client fictif : agence régionale. Objectif : argumentaire prix (B1), score d'implantation (B2),
profil socio-démo (B3), tendance marché (B4), zones sous-évaluées (B5).

## Structure

```
bronze/          brut immuable (ignoré par git, à régénérer)
  idf/           32 dumps JSON Overpass : 8 depts x 4 cats (~90 Mo, ~252k objets)
silver/          nettoyé typé (Parquet)
  osm_idf_poi.parquet   249 197 POI : education/sante/commerce/transport
gold/            agrégé métier par commune (à construire)
src/
  osm/           partie OSM : ingestion, profilage, nettoyage  <- TOI
  dvf/           partie DVF (transactions, prix au m²)
  insee/         partie Filosofi (revenus, ménages)
  gold/          fédération polystore + score attractivité
notebooks/       démos B1-B5
docs/            profilage_bronze.txt, dico_osm.md, rapport
```

## Répartition équipe (4)

| Membre | Dossier | Livrable |
|---|---|---|
| 1 (toi) | `src/osm` | bronze IdF + silver POI + density par commune |
| 2 | `src/dvf` | bronze DVF IdF + silver dédupliqué/géocodé |
| 3 | `src/insee` | bronze/silver Filosofi + profils B3 |
| 4 | `src/gold` + `notebooks` | jointures `code_commune`, gold finale, requêtes B1-B5 |

## Quickstart OSM

```bash
pip install -r requirements.txt
python3 src/osm/main_idf.py ecoles     # 1 catégorie, 8 depts
python3 src/osm/profile_osm.py > docs/profilage_bronze.txt
python3 src/osm/clean_osm_silver.py    # -> silver/osm_idf_poi.parquet
```

Données : snapshot Overpass `timestamp_osm_base` conservé par fichier (colonne `date_extract`).
Licence OSM : ODbL, attribution obligatoire. Contrainte DVF (CGU) : pas de ré-identification,
pas d'indexation externe — à rappeler dans le rapport.
