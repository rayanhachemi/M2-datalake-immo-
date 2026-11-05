# Requêtes métier disponibles

Les trois fichiers `.sql` s'exécutent **directement dans pgAdmin/PostgreSQL** : leurs paramètres d'exemple sont dans le premier bloc `WITH parametres AS (...)`. Pour changer la région, la commune, le type de bien ou les seuils, modifier uniquement les valeurs du `SELECT` dans ce bloc. Par exemple, remplacer `'idf'::text` par `'bretagne'::text` dans B2 ; `NULL::text` affiche toutes les régions.

Les mêmes requêtes s'exécutent aussi en ligne de commande depuis la racine du projet :

```bash
python src/gold/requetes.py B2 --region idf --limite 10
python src/gold/requetes.py B4 --code-commune 75056 --type-bien Appartement
python src/gold/requetes.py B5 --region occitanie --type-bien Maison --limite 10
```

La connexion est lue dans `.env` (`DATABASE_URL`). Installer les dépendances avec `python -m pip install -r requirements.txt`.

| Besoin | Table PostgreSQL lue | Résultat | Paramètres |
|---|---|---|---|
| B2 | `G_COMMUNE`, `G_TRANSACTION`, `G_POINT_INTERET`, `G_PROFIL_COMMUNE` | Classement régional calculé depuis les ventes et les POI ; score 40 % dynamique, 30 % activité, 30 % équipements | `--region` facultatif ; `--limite` (10 par défaut) |
| B4 | `G_TRANSACTION`, `G_COMMUNE` | Prix et tendance annuels 2021–2025 calculés sur les ventes comparables | `--code-commune` obligatoire ; `--type-bien` (`Maison` par défaut) |
| B5 | `G_COMMUNE`, `G_TRANSACTION`, `G_POINT_INTERET`, `G_PROFIL_COMMUNE` | Communes au prix récent faible, bien équipées et dont le revenu médian atteint la médiane régionale | `--region` facultatif ; `--type-bien`, `--ratio-prix-max` (0,90), `--score-equipements-min` (60), `--limite` |

Ces requêtes lisent uniquement les quatre tables Gold du schéma conceptuel. Les scores et agrégats sont calculés dans les requêtes, sans table Gold supplémentaire.

B5 compare les communes **de la même région et du même type de logement**. Le prix de référence est la médiane des médianes communales 2024–2025 parmi les communes ayant au moins 10 ventes de ce type et un revenu renseigné. Le seuil de 90 % signifie « au moins 10 % sous cette référence ». Le revenu médian régional sert de filtre descriptif ; ce résultat ne prouve pas une sous-évaluation ni une hausse future.

Le score d'équipements B2/B5 utilise les quatre catégories de POI uniques par commune et leurs densités pour 1 000 habitants. Les percentiles sont calculés avec `CUME_DIST` parmi les communes de la même région ayant une population positive. Le schéma fourni ne contient pas `id_arret` ni `is_vacant` : le transport compte des POI OSM et tous les POI de catégorie commerce sont comptés.

B4 laisse les années sans vente à zéro vente et sans prix. Les prix restent masqués sous 10 ventes. La tendance sur cinq ans est `non_concluante` si le prix 2021 ou 2025 n'est pas publiable. Les prix sont en euros courants.
