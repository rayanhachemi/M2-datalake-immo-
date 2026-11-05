# Contrôle Silver → Gold

Exécuté le 2026-11-05T16:16:30.676954+00:00 — **OK**.

## Silver PostgreSQL

| Table | Lignes |
|---|---:|
| `S_dvf_ventes` | 2,070,699 |
| `S_osm_poi` | 305,925 |
| `S_insee_communes` | 10,939 |
| `S_communes` | 10,966 |

## Gold PostgreSQL

| Table | Lignes |
|---|---:|
| `G_COMMUNE` | 10,966 |
| `G_TRANSACTION` | 1,991,665 |
| `G_POINT_INTERET` | 305,839 |
| `G_PROFIL_COMMUNE` | 10,939 |

## Contrôles

| Contrôle | Résultat | Anomalies | Détail |
|---|---:|---:|---|
| Quatre tables Silver présentes | OK | 0 |  |
| Uniquement quatre tables Gold | OK | 0 |  |
| S_dvf_ventes = Parquet Silver | OK | 0 | 2,070,699 lignes |
| S_osm_poi = Parquet Silver | OK | 0 | 305,925 lignes |
| S_insee_communes = Parquet Silver | OK | 0 | 10,939 lignes |
| S_communes = Parquet Silver | OK | 0 | 10,966 lignes |
| Schéma G_COMMUNE | OK | 0 |  |
| Schéma G_TRANSACTION | OK | 0 |  |
| Schéma G_POINT_INTERET | OK | 0 |  |
| Schéma G_PROFIL_COMMUNE | OK | 0 |  |
| Lignage G_COMMUNE ← Silver | OK | 0 | 10,966 lignes |
| Lignage G_TRANSACTION ← Silver | OK | 0 | 1,991,665 lignes |
| Lignage G_POINT_INTERET ← Silver | OK | 0 | 305,839 lignes |
| Lignage G_PROFIL_COMMUNE ← Silver | OK | 0 | 10,939 lignes |
| Quatre clés primaires et trois clés étrangères | OK | 0 |  |
| Domaines des valeurs Gold | OK | 0 |  |
