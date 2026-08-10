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

## Ligne de commande

```bash
python3 src/pipeline.py
python3 -m unittest discover -s tests
```
