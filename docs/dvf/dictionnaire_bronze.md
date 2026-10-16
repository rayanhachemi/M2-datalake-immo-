# Dictionnaire bronze DVF

Fichiers produits par `src/dvf/main.py`.

- **Chemin** : `bronze/dvf/dvf_{annee}_cibles.txt`
- **Format** : fichier texte tabulaire, séparateur `|`, encodage UTF-8
- **Volume** : 5 fichiers (2021-2025), ~8,9 millions de lignes, ~1,2 Go
- **Licence** : Licence Ouverte — CGU DGFiP : ne pas ré-identifier les personnes ni indexer les adresses

**Attention :** une vente est éclatée en plusieurs lignes (une par local × nature de culture du terrain). La valeur foncière est répétée sur chaque ligne — il ne faut pas les additionner.

## Colonnes principales

| Colonne | Description |
|---|---|
| `Date mutation` | Date de la transaction (format jj/mm/aaaa) |
| `Nature mutation` | Type d'acte : `Vente`, `Vente en l'état futur d'achèvement`, adjudication... |
| `Valeur fonciere` | Prix de vente en euros (virgule décimale, séparateur point dans les milliers) |
| `Code departement` | Code département sur 2 caractères |
| `Code commune` | Code commune sur 3 caractères (à combiner avec le département pour obtenir le code INSEE) |
| `Commune` | Nom de la commune |
| `Section` | Section cadastrale |
| `No plan` | Numéro de plan cadastral |
| `Type local` | `Maison`, `Appartement`, `Dépendance`, `Local industriel. commercial ou assimilé` |
| `Surface reelle bati` | Surface bâtie en m² (virgule décimale) |
| `Nombre pieces principales` | Nombre de pièces principales |
| `Nature culture` | Type de terrain (`Jardins`, `Terres`, `Bois`...) — présent uniquement sur les lignes terrain |
| `Surface terrain` | Surface du terrain en m² |

La complétude détaillée par colonne et par millésime est dans `docs/dvf/profiling/colonnes_{annee}.csv`.
