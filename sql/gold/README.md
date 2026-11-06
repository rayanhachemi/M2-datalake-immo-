# Requêtes métier disponibles

Les cinq fichiers `.sql` s'exécutent **directement dans pgAdmin/PostgreSQL** : leurs paramètres d'exemple sont dans le premier bloc `WITH parametres AS (...)`. Pour changer la région, la commune, le type de bien ou les seuils, modifier uniquement les valeurs du `SELECT` dans ce bloc. Par exemple, remplacer `'idf'::text` par `'bretagne'::text` dans B2 ; `NULL::text` affiche toutes les régions.

Les mêmes requêtes s'exécutent aussi en ligne de commande depuis la racine du projet :

```bash
python src/gold/requetes.py B1 --region idf --type-bien Maison
python src/gold/requetes.py B2 --region idf --limite 10
python src/gold/requetes.py B3 --code-commune-travail 75056 --type-bien Maison --revenu-annuel-couple 60000 --surface-souhaitee-m2 80 --distance-max-km 30 --limite 10
python src/gold/requetes.py B4 --code-commune 75056 --type-bien Appartement
python src/gold/requetes.py B5 --region occitanie --type-bien Maison --limite 10
```

La connexion est lue dans `.env` (`DATABASE_URL`). Installer les dépendances avec `python -m pip install -r requirements.txt`.

| Besoin | Table PostgreSQL lue | Résultat | Paramètres |
|---|---|---|---|
| B1 | `G_TRANSACTION`, `G_COMMUNE` | Prix communaux 2021–2025 du type choisi, calculés à partir des prix annuels publiables | `--region` facultatif ; `--type-bien` (`Maison` par défaut) |
| B2 | `G_COMMUNE`, `G_TRANSACTION`, `G_POINT_INTERET`, `G_PROFIL_COMMUNE` | Classement régional calculé depuis les ventes et les POI ; score 40 % dynamique, 30 % activité, 30 % équipements | `--region` facultatif ; `--limite` (10 par défaut) |
| B3 | `G_COMMUNE`, `G_PROFIL_COMMUNE`, `G_TRANSACTION`, `G_POINT_INTERET` | Communes candidates selon distance au travail, équipements, transport et prix de biens comparables | `--code-commune-travail`, coordonnées de travail facultatives, `--type-bien`, `--revenu-annuel-couple`, `--surface-souhaitee-m2`, `--tolerance-surface-pct`, `--distance-max-km`, `--budget-max-achat` facultatif, `--limite` |
| B4 | `G_TRANSACTION`, `G_COMMUNE` | Prix et tendance annuels 2021–2025 calculés sur les ventes comparables | `--code-commune` obligatoire ; `--type-bien` (`Maison` par défaut) |
| B5 | `G_COMMUNE`, `G_TRANSACTION`, `G_POINT_INTERET`, `G_PROFIL_COMMUNE` | Communes au prix récent faible, bien équipées et dont le revenu médian atteint la médiane régionale | `--region` facultatif ; `--type-bien`, `--ratio-prix-max` (0,90), `--score-equipements-min` (60), `--limite` |

Ces requêtes lisent uniquement les quatre tables Gold du schéma conceptuel. Les scores et agrégats sont calculés dans les requêtes, sans table Gold supplémentaire.

B1 conserve la logique de la requête fournie : la médiane finale est la médiane des **médianes annuelles** des années ayant au moins dix ventes ; le volume total additionne toutes les années. Ce n'est ni une médiane de toutes les transactions réunies ni une comparaison à 500 m.

B3 utilise par défaut Paris (`75056`) comme commune de travail, un couple avec 60 000 € de revenu annuel et une surface souhaitée de 80 m². Dans le notebook, l'adresse de travail est géocodée par la BAN ; ses coordonnées sont transmises à B3. La requête retient les communes situées à 30 km au plus de cette adresse, ayant au moins un point OSM de transport, un équipement ou commerce, et au moins dix ventes du type choisi sur 2024–2025 avec une surface comprise entre 60 et 100 m² (tolérance de 25 %). Sans coordonnées de travail, elle utilise le centre moyen des POI de la commune indiquée. `prix_median_biens_comparables` est la médiane du prix total de ces ventes ; `ratio_prix_revenu_annuel` divise ce prix par le revenu annuel du couple. `--budget-max-achat` permet un plafond explicite ; la requête ne déduit pas une capacité d'emprunt du revenu. Les distances sont à vol d'oiseau depuis le centre moyen des POI de chaque commune candidate ; les biens vendus n'ont pas de coordonnées dans Gold, et Gold ne contient ni annonces disponibles ni indice général du coût de la vie. Les comptes OSM décrivent les équipements présents dans la commune, pas la distance depuis un logement précis. La carte B3 du notebook affiche le lieu de travail, les communes candidates, des exemples de ventes passées dans leurs fenêtres et des points OSM géolocalisés.

B5 compare les communes **de la même région et du même type de logement**. Le prix de référence est la médiane des médianes communales 2024–2025 parmi les communes ayant au moins 10 ventes de ce type et un revenu renseigné. Le seuil de 90 % signifie « au moins 10 % sous cette référence ». Le revenu médian régional sert de filtre descriptif ; ce résultat ne prouve pas une sous-évaluation ni une hausse future.

Le score d'équipements B2/B5 utilise les quatre catégories de POI uniques par commune et leurs densités pour 1 000 habitants. Les percentiles sont calculés avec `CUME_DIST` parmi les communes de la même région ayant une population positive. Le schéma fourni ne contient pas `id_arret` ni `is_vacant` : le transport compte des POI OSM et tous les POI de catégorie commerce sont comptés.

B4 laisse les années sans vente à zéro vente et sans prix. Les prix restent masqués sous 10 ventes. La tendance sur cinq ans est `non_concluante` si le prix 2021 ou 2025 n'est pas publiable. Les prix sont en euros courants.
