# Metric Lab

Une mini data platform e-commerce, de l’ingestion au dashboard : fichiers sources, modèle dimensionnel SQLite et métriques de pilotage.

## Lancer

```bash
python3 src/server.py
```

Ouvrir `http://127.0.0.1:8000`. La première exécution construit la base locale à partir des CSV de démonstration.

## Ce que le projet montre

- ingestion de sources brutes ;
- modèle `fact_orders` + dimensions clients et produits ;
- table de métriques quotidiennes ;
- API légère et dashboard local ;
- tests de cohérence sur le pipeline.
- contexte de marché optionnel avec les derniers taux EUR publiés par Frankfurter à partir de la BCE.

## Ce qui rend le pipeline utilisable

Avant toute reconstruction, Metric Lab applique un quality gate aux trois sources : schéma attendu, unicité des identifiants, références clients et produits, montants positifs et format de date. Un lot en échec est rejeté avec `422` sans remplacer le mart existant. Un lot accepté conserve une empreinte de contenu, la date d’exécution et le nombre de contrôles réalisés dans SQLite.

Les ventes et commandes du mini-entrepôt sont synthétiques et servent à tester le modèle. Le contexte de marché est distinct : `GET /api/market-context` interroge une source publique sans clé, identifiée par un en-tête applicatif, puis indique clairement si elle est indisponible.

La qualité du lot est disponible via `GET /api/quality`. `POST /api/rebuild` ne rebâtit le mart qu’après validation complète.

## Ligne de commande

```bash
python3 src/pipeline.py
python3 -m unittest discover -s tests
```
