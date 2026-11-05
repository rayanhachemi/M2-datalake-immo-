# Gold — quatre tables du schéma conceptuel

Depuis la racine du projet :

```bash
python src/charger_silver_postgres.py  # restaure DVF, OSM, INSEE si leurs Parquets existent déjà
python src/communes/silver.py          # référentiel communal Silver
python src/gold/modele_conceptuel.py
python src/gold/controle.py
```

Les quatre tables Silver PostgreSQL sont `S_dvf_ventes`, `S_osm_poi`, `S_insee_communes` et `S_communes`. Les trois premiers scripts Silver des sources créent déjà leurs tables SQL lorsqu'on les rejoue ; `charger_silver_postgres.py` permet de les restaurer directement depuis les Parquets existants. `src/communes/silver.py` construit `S_communes` à partir des contours Bronze et des codes DVF Silver.

`modele_conceptuel.py` lit **ces quatre tables Silver dans PostgreSQL** et crée les quatre tables Gold par `INSERT ... SELECT` :

| Table | Clé | Source Silver |
|---|---|---|
| `G_COMMUNE` | `code_commune` | `S_communes` |
| `G_TRANSACTION` | `id_vente`, FK `code_commune` | `S_dvf_ventes` |
| `G_POINT_INTERET` | `id_osm`, FK `code_commune` | `S_osm_poi` |
| `G_PROFIL_COMMUNE` | `code_commune`, PK et FK | `S_insee_communes` |

Le chargement SQL supprime les anciennes tables Gold agrégées si elles existent. Les requêtes B1 à B5 calculent les indicateurs directement depuis ces quatre tables ; voir [les requêtes](../../sql/gold/README.md). Les règles sont dans [la spécification](../../docs/gold/specification.md).

`controle.py` vérifie les clés, les relations, les volumes Silver et Gold et la correspondance avec les Parquets Silver. Il écrit `gold/controle_stats.json` et [le rapport](../../docs/gold/controle.md).
