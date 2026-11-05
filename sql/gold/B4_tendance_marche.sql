-- Tendance calculée sur les transactions Gold reliées à leur commune.
WITH parametres AS (
    -- PARAMETRES_DEBUT
    SELECT '75056'::text AS code_commune, 'Appartement'::text AS type_bien
    -- PARAMETRES_FIN
), ventes_annuelles AS (
    SELECT
        EXTRACT(YEAR FROM t.date_mutation)::integer AS annee,
        COUNT(*)::bigint AS nb_ventes,
        CASE WHEN COUNT(*) >= 10
             THEN ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.prix_m2))::numeric, 2)
        END AS prix_m2_median,
        CASE WHEN COUNT(*) >= 10 THEN ROUND(AVG(t.prix_m2)::numeric, 2)
        END AS prix_m2_moyen
    FROM "G_TRANSACTION" AS t
    JOIN "G_COMMUNE" AS commune ON commune.code_commune = t.code_commune
    CROSS JOIN parametres AS p
    WHERE commune.code_commune = p.code_commune
      AND t.type_bien = p.type_bien
      AND t.date_mutation >= DATE '2021-01-01'
      AND t.date_mutation < DATE '2026-01-01'
    GROUP BY EXTRACT(YEAR FROM t.date_mutation)::integer
), serie AS (
    SELECT a.annee, COALESCE(v.nb_ventes, 0) AS nb_ventes,
           v.prix_m2_median, v.prix_m2_moyen
    FROM generate_series(2021, 2025) AS a(annee)
    LEFT JOIN ventes_annuelles AS v ON v.annee = a.annee
), evolution AS (
    SELECT s.*,
           LAG(s.prix_m2_median) OVER (ORDER BY s.annee) AS prix_precedent
    FROM serie AS s
), bornes AS (
    SELECT MAX(prix_m2_median) FILTER (WHERE annee = 2021) AS prix_2021,
           MAX(prix_m2_median) FILTER (WHERE annee = 2025) AS prix_2025
    FROM serie
), variation AS (
    SELECT CASE WHEN prix_2021 > 0 AND prix_2025 IS NOT NULL
                THEN ROUND(100 * (prix_2025 / prix_2021 - 1), 2)
           END AS variation_2021_2025_pct
    FROM bornes
)
SELECT
    p.code_commune, commune.nom_commune, p.type_bien,
    e.annee, e.nb_ventes, e.prix_m2_median, e.prix_m2_moyen,
    CASE WHEN e.prix_precedent > 0 AND e.prix_m2_median IS NOT NULL
         THEN ROUND(100 * (e.prix_m2_median / e.prix_precedent - 1), 2)
    END AS variation_annuelle_pct,
    CASE WHEN e.prix_precedent > 0 AND e.prix_m2_median IS NOT NULL
         THEN CASE WHEN 100 * (e.prix_m2_median / e.prix_precedent - 1) >= 3 THEN 'hausse'
                   WHEN 100 * (e.prix_m2_median / e.prix_precedent - 1) <= -3 THEN 'baisse'
                   ELSE 'stable' END
         ELSE 'non_concluante'
    END AS tendance_annuelle,
    v.variation_2021_2025_pct,
    CASE WHEN v.variation_2021_2025_pct >= 3 THEN 'hausse'
         WHEN v.variation_2021_2025_pct <= -3 THEN 'baisse'
         WHEN v.variation_2021_2025_pct IS NOT NULL THEN 'stable'
         ELSE 'non_concluante'
    END AS tendance_2021_2025
FROM evolution AS e
CROSS JOIN parametres AS p
LEFT JOIN "G_COMMUNE" AS commune ON commune.code_commune = p.code_commune
CROSS JOIN variation AS v
ORDER BY e.annee;
