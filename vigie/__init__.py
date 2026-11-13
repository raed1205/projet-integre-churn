"""VIGIE — bibliothèque commune du Projet Intégré (Groupe BI 5).

Un seul endroit pour : l'identité du projet, le chargement des données,
la construction des grains (compte, client) et des séries hebdomadaires.
Les notebooks, l'ETL Python et l'entraînement des modèles l'utilisent tous,
ce qui garantit que chaque chiffre du rapport vient du même code.
"""

from . import config  # noqa: F401

__version__ = "1.0.0"
