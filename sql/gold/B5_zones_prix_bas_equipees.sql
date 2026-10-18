WITH parametres AS (
    SELECT 'occitanie'::text AS region, 'Maison'::text AS type_bien,
           0.90::double precision AS ratio_prix_max,
           60::double precision AS score_equipements_min,
           10::integer AS limite
), base AS (
    SELECT
        c.code_commune,
        c.departement,
        c.region,
        c.revenu_median,
        c.score_equipements,
        c.score_attractivite,
        CASE WHEN p.type_bien = 'Maison'
             THEN c.nb_ventes_maison_2024_2025
             ELSE c.nb_ventes_appartement_2024_2025
        END AS nb_ventes_type,
        CASE WHEN p.type_bien = 'Maison'
             THEN c.prix_m2_median_maison_2024_2025
             ELSE c.prix_m2_median_appartement_2024_2025
        END AS prix_m2_median
    FROM "G_communes" AS c
    CROSS JOIN parametres AS p
    WHERE c.score_eligible = TRUE
      AND c.revenu_median IS NOT NULL
      AND (p.region IS NULL OR c.region = p.region)
), reference_regionale AS (
    SELECT
        region,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY prix_m2_median) AS prix_m2_regional,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY revenu_median) AS revenu_regional,
        COUNT(*) AS communes_reference
    FROM base
    WHERE nb_ventes_type >= 10
    GROUP BY region
)
SELECT
    b.code_commune,
    b.departement,
    b.region,
    p.type_bien,
    b.nb_ventes_type AS nb_ventes_2024_2025,
    b.prix_m2_median,
    ROUND(r.prix_m2_regional::numeric, 2) AS prix_m2_median_regional,
    ROUND((100 * (b.prix_m2_median / r.prix_m2_regional - 1))::numeric, 1) AS ecart_prix_region_pct,
    b.score_equipements,
    b.score_attractivite,
    b.revenu_median,
    ROUND(r.revenu_regional::numeric, 0) AS revenu_median_regional,
    r.communes_reference
FROM base AS b
JOIN reference_regionale AS r ON r.region = b.region
CROSS JOIN parametres AS p
WHERE b.nb_ventes_type >= 10
  AND b.prix_m2_median <= p.ratio_prix_max * r.prix_m2_regional
  AND b.score_equipements >= p.score_equipements_min
  AND b.revenu_median >= r.revenu_regional
ORDER BY ecart_prix_region_pct ASC, b.score_equipements DESC, b.code_commune
LIMIT (SELECT limite FROM parametres);
