"""VIGIE — shared library of the Integrated Project (Group BI 5).

One place for the project identity, data loading, the analysis grains (account,
customer) and the weekly series. The notebooks, the Python ETL and the model
training all use it, so every figure in the report comes from the same code.
"""

from . import config  # noqa: F401

__version__ = "1.0.0"
