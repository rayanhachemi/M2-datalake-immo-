-- B2 : score calculé uniquement depuis les quatre tables du modèle Gold.
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT 'idf'::text AS region, 10::integer AS limite
    -- PARAMETRES_FIN
), poi AS (
    SELECT code_commune, COUNT(*) AS nb_poi_osm,
           COUNT(*) FILTER (WHERE categorie = 'education') AS nb_ecoles,
           COUNT(*) FILTER (WHERE categorie = 'sante') AS nb_sante,
           COUNT(*) FILTER (WHERE categorie = 'commerce') AS nb_commerces,
           COUNT(*) FILTER (WHERE categorie = 'transport') AS nb_transport
    FROM "G_POINT_INTERET"
    GROUP BY code_commune
), equipements AS (
    SELECT c.code_commune, c.region,
           COALESCE(p.nb_poi_osm, 0) AS nb_poi_osm,
           COALESCE(p.nb_transport, 0) AS nb_poi_transport,
           1000.0 * COALESCE(p.nb_ecoles, 0) / GREATEST(pr.population, 1000) AS d_ecoles,
           1000.0 * COALESCE(p.nb_sante, 0) / GREATEST(pr.population, 1000) AS d_sante,
           1000.0 * COALESCE(p.nb_commerces, 0) / GREATEST(pr.population, 1000) AS d_commerces,
           1000.0 * COALESCE(p.nb_transport, 0) / GREATEST(pr.population, 1000) AS d_transport
    FROM "G_COMMUNE" AS c
    JOIN "G_PROFIL_COMMUNE" AS pr ON pr.code_commune = c.code_commune
    LEFT JOIN poi AS p ON p.code_commune = c.code_commune
    WHERE pr.population > 0
), score_equipements AS (
    SELECT code_commune, nb_poi_osm, nb_poi_transport,
           25.0 * (CUME_DIST() OVER (PARTITION BY region ORDER BY d_ecoles)
                 + CUME_DIST() OVER (PARTITION BY region ORDER BY d_sante)
                 + CUME_DIST() OVER (PARTITION BY region ORDER BY d_commerces)
                 + CUME_DIST() OVER (PARTITION BY region ORDER BY d_transport)) AS score_equipements
    FROM equipements
), marche_type AS (
    SELECT code_commune, type_bien,
           COUNT(*) FILTER (WHERE date_mutation < DATE '2024-01-01') AS nb_avant,
           COUNT(*) FILTER (WHERE date_mutation >= DATE '2024-01-01') AS nb_recent,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY prix_m2)
               FILTER (WHERE date_mutation < DATE '2024-01-01') AS prix_avant,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY prix_m2)
               FILTER (WHERE date_mutation >= DATE '2024-01-01') AS prix_recent
    FROM "G_TRANSACTION"
    WHERE date_mutation >= DATE '2022-01-01' AND date_mutation < DATE '2026-01-01'
    GROUP BY code_commune, type_bien
), dynamique_type AS (
    SELECT code_commune, nb_recent,
           CASE WHEN nb_avant >= 10 AND nb_recent >= 10 AND prix_avant > 0
                THEN 100.0 * (prix_recent / prix_avant - 1)
           END AS variation_pct
    FROM marche_type
), marche_commune AS (
    SELECT code_commune, SUM(nb_recent) AS nb_ventes_2024_2025,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY variation_pct)
               FILTER (WHERE variation_pct IS NOT NULL) AS dynamique_prix_pct
    FROM dynamique_type
    GROUP BY code_commune
), eligibles AS (
    SELECT c.code_commune, c.nom_commune, c.departement, c.region, pr.population,
           m.nb_ventes_2024_2025, m.dynamique_prix_pct,
           e.nb_poi_osm, e.nb_poi_transport, e.score_equipements
    FROM "G_COMMUNE" AS c
    JOIN "G_PROFIL_COMMUNE" AS pr ON pr.code_commune = c.code_commune
    JOIN marche_commune AS m ON m.code_commune = c.code_commune
    JOIN score_equipements AS e ON e.code_commune = c.code_commune
    WHERE pr.population > 0 AND m.nb_ventes_2024_2025 >= 10
      AND m.dynamique_prix_pct IS NOT NULL
), rangs AS (
    SELECT e.*,
           100.0 * CUME_DIST() OVER (
               PARTITION BY region ORDER BY LEAST(GREATEST(dynamique_prix_pct, -50), 100)
           ) AS score_dynamique,
           100.0 * CUME_DIST() OVER (
               PARTITION BY region ORDER BY nb_ventes_2024_2025
           ) AS score_activite
    FROM eligibles AS e
), scores AS (
    SELECT r.*,
           ROUND((0.4 * score_dynamique + 0.3 * score_activite
                  + 0.3 * score_equipements)::numeric, 1) AS score_attractivite
    FROM rangs AS r
)
SELECT code_commune, nom_commune, departement, region, population,
       score_attractivite,
       ROUND(score_dynamique::numeric, 2) AS score_dynamique,
       ROUND(score_activite::numeric, 2) AS score_activite,
       ROUND(score_equipements::numeric, 2) AS score_equipements,
       ROUND(dynamique_prix_pct::numeric, 2) AS dynamique_prix_pct,
       nb_ventes_2024_2025, nb_poi_osm, nb_poi_transport,
       RANK() OVER (PARTITION BY region ORDER BY score_attractivite DESC) AS rang_dans_la_region
FROM scores
WHERE (SELECT region FROM parametres) IS NULL
   OR region = (SELECT region FROM parametres)
ORDER BY score_attractivite DESC, nb_ventes_2024_2025 DESC, code_commune
LIMIT (SELECT limite FROM parametres);
