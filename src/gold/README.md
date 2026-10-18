# Tables Gold

Depuis la racine du projet :

```bash
python src/gold/jointure.py
python src/gold/indicateurs.py
python src/gold/controle.py
```

Le script lit les trois Parquets Silver, agrège DVF et OSM par `code_commune`, puis les joint à INSEE. Il produit :

- `gold/jointure_communes.parquet` : une ligne par commune INSEE, avec ses indicateurs Silver et des comptages de ventes et de POI ;
- `gold/jointure_stats.json` : couverture des jointures et ventes dont le code DVF n'existe pas dans INSEE ;
- `G_jointure_communes` dans PostgreSQL.

Cette table est **intermédiaire**. Le second script produit :

- `gold/marche_commune_annee_type.parquet` et `G_marche_commune_annee_type` : prix et tendance par commune, année et type de bien ;
- `gold/communes.parquet` et `G_communes` : prix récents, densités d'équipements et score d'attractivité par commune ;
- `gold/indicateurs_stats.json` : volumes, seuils de publication et couverture du score.

Les calculs et seuils sont définis dans [la spécification](../../docs/gold/specification.md). La connexion PostgreSQL est lue depuis `.env` (`DATABASE_URL`).

Le contrôle compare les tables Gold aux trois Silver, vérifie les seuils et les scores, puis rapproche les volumes PostgreSQL. Il écrit `gold/controle_stats.json` et [le rapport de qualité](../../docs/gold/controle.md). Pour contrôler seulement les fichiers, lancer `python src/gold/controle.py --sans-db`.

Les requêtes métier **B2, B4 et B5** sont dans [`sql/gold`](../../sql/gold/README.md). Elles s'exécutent avec `python src/gold/requetes.py B2|B4|B5` et les paramètres décrits dans ce dossier.
