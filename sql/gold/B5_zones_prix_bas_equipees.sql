-- B5 : prix DVF, équipements OSM et revenu INSEE, sans table agrégée.
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT 'occitanie'::text AS region, 'Maison'::text AS type_bien,
           0.90::double precision AS ratio_prix_max,
           60::double precision AS score_equipements_min,
           10::integer AS limite
    -- PARAMETRES_FIN
), poi AS (
    SELECT code_commune,
           COUNT(*) FILTER (WHERE categorie = 'education') AS nb_ecoles,
           COUNT(*) FILTER (WHERE categorie = 'sante') AS nb_sante,
           COUNT(*) FILTER (WHERE categorie = 'commerce') AS nb_commerces,
           COUNT(*) FILTER (WHERE categorie = 'transport') AS nb_transport
    FROM "G_POINT_INTERET"
    GROUP BY code_commune
), equipements AS (
    SELECT c.code_commune, c.region,
           1000.0 * COALESCE(p.nb_ecoles, 0) / GREATEST(pr.population, 1000) AS d_ecoles,
           1000.0 * COALESCE(p.nb_sante, 0) / GREATEST(pr.population, 1000) AS d_sante,
           1000.0 * COALESCE(p.nb_commerces, 0) / GREATEST(pr.population, 1000) AS d_commerces,
           1000.0 * COALESCE(p.nb_transport, 0) / GREATEST(pr.population, 1000) AS d_transport
    FROM "G_COMMUNE" AS c
    JOIN "G_PROFIL_COMMUNE" AS pr ON pr.code_commune = c.code_commune
    LEFT JOIN poi AS p ON p.code_commune = c.code_commune
    WHERE pr.population > 0
), score_equipements AS (
    SELECT code_commune,
           25.0 * (CUME_DIST() OVER (PARTITION BY region ORDER BY d_ecoles)
                 + CUME_DIST() OVER (PARTITION BY region ORDER BY d_sante)
                 + CUME_DIST() OVER (PARTITION BY region ORDER BY d_commerces)
                 + CUME_DIST() OVER (PARTITION BY region ORDER BY d_transport)) AS score_equipements
    FROM equipements
), prix_recents AS (
    SELECT t.code_commune, COUNT(*) AS nb_ventes_2024_2025,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.prix_m2) AS prix_m2_median
    FROM "G_TRANSACTION" AS t
    CROSS JOIN parametres AS p
    WHERE t.type_bien = p.type_bien
      AND t.date_mutation >= DATE '2024-01-01'
      AND t.date_mutation < DATE '2026-01-01'
    GROUP BY t.code_commune
    HAVING COUNT(*) >= 10
), base AS (
    SELECT c.code_commune, c.nom_commune, c.departement, c.region,
           pr.revenu_median, prix.nb_ventes_2024_2025, prix.prix_m2_median,
           e.score_equipements
    FROM "G_COMMUNE" AS c
    JOIN "G_PROFIL_COMMUNE" AS pr ON pr.code_commune = c.code_commune
    JOIN prix_recents AS prix ON prix.code_commune = c.code_commune
    JOIN score_equipements AS e ON e.code_commune = c.code_commune
    WHERE pr.revenu_median IS NOT NULL
), reference_regionale AS (
    SELECT region,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY prix_m2_median) AS prix_m2_regional,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY revenu_median) AS revenu_regional,
           COUNT(*) AS communes_reference
    FROM base
    GROUP BY region
)
SELECT b.code_commune, b.nom_commune, b.departement, b.region, p.type_bien,
       b.nb_ventes_2024_2025,
       ROUND(b.prix_m2_median::numeric, 2) AS prix_m2_median,
       ROUND(r.prix_m2_regional::numeric, 2) AS prix_m2_median_regional,
       ROUND((100 * (b.prix_m2_median / r.prix_m2_regional - 1))::numeric, 1) AS ecart_prix_region_pct,
       ROUND(b.score_equipements::numeric, 2) AS score_equipements,
       b.revenu_median,
       ROUND(r.revenu_regional::numeric, 0) AS revenu_median_regional,
       r.communes_reference
FROM base AS b
JOIN reference_regionale AS r ON r.region = b.region
CROSS JOIN parametres AS p
WHERE (p.region IS NULL OR b.region = p.region)
  AND b.prix_m2_median <= p.ratio_prix_max * r.prix_m2_regional
  AND b.score_equipements >= p.score_equipements_min
  AND b.revenu_median >= r.revenu_regional
ORDER BY ecart_prix_region_pct ASC, b.score_equipements DESC, b.code_commune
LIMIT (SELECT limite FROM parametres);
