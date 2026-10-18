WITH parametres AS (
    SELECT '75056'::text AS code_commune, 'Appartement'::text AS type_bien
), bornes AS (
    SELECT
        MAX(m.prix_m2_median) FILTER (WHERE m.annee = 2021) AS prix_2021,
        MAX(m.prix_m2_median) FILTER (WHERE m.annee = 2025) AS prix_2025
    FROM "G_marche_commune_annee_type" AS m
    CROSS JOIN parametres AS p
    WHERE m.code_commune = p.code_commune AND m.type_bien = p.type_bien
), evolution AS (
    SELECT CASE
        WHEN prix_2021 > 0 AND prix_2025 IS NOT NULL
        THEN ROUND((100 * (prix_2025 / prix_2021 - 1))::numeric, 2)
    END AS variation_2021_2025_pct
    FROM bornes
)
SELECT
    p.code_commune,
    p.type_bien,
    annees.annee,
    COALESCE(m.nb_ventes, 0) AS nb_ventes,
    m.prix_m2_median,
    m.prix_m2_moyen,
    m.variation_annuelle_pct,
    COALESCE(m.tendance_annuelle, 'non_concluante') AS tendance_annuelle,
    evolution.variation_2021_2025_pct,
    CASE
        WHEN evolution.variation_2021_2025_pct >= 3 THEN 'hausse'
        WHEN evolution.variation_2021_2025_pct <= -3 THEN 'baisse'
        WHEN evolution.variation_2021_2025_pct IS NOT NULL THEN 'stable'
        ELSE 'non_concluante'
    END AS tendance_2021_2025
FROM generate_series(2021, 2025) AS annees(annee)
CROSS JOIN parametres AS p
LEFT JOIN "G_marche_commune_annee_type" AS m
    ON m.annee = annees.annee
   AND m.code_commune = p.code_commune
   AND m.type_bien = p.type_bien
CROSS JOIN evolution
ORDER BY annees.annee;
