WITH parametres AS (
    SELECT 'idf'::text AS region
)
SELECT
    c.code_commune,
    c.departement,
    c.region,
    c.population,
    c.revenu_median,
    c.taux_pauvrete,
    ROUND(c.taux_chomage::numeric, 2) AS taux_chomage,
    ROUND(c.taux_vacance::numeric, 2) AS taux_vacance,
    ROUND(c.part_diplome_superieur::numeric, 2) AS part_diplome_superieur,
    ROUND(c.part_moins_15::numeric, 2) AS part_moins_15,
    ROUND(c.part_25_39::numeric, 2) AS part_25_39,
    ROUND(c.part_65_plus::numeric, 2) AS part_65_plus,
    ROUND(c.part_residences_secondaires::numeric, 2) AS part_residences_secondaires,
    ROUND(c.taille_moyenne_menage::numeric, 2) AS taille_moyenne_menage,
    ROUND(c.part_menages_une_personne::numeric, 2) AS part_menages_une_personne,
    ROUND(c.part_familles_avec_enfants_moins_25::numeric, 2) AS part_familles_avec_enfants,
    COALESCE(c.prix_m2_median_maison_2024_2025, c.prix_m2_median_appartement_2024_2025) AS prix_m2_recent
FROM "G_communes" AS c
CROSS JOIN parametres AS p
WHERE c.population > 0
  AND c.revenu_median IS NOT NULL
  AND (p.region IS NULL OR c.region = p.region)
ORDER BY c.revenu_median DESC;
