"""Validation package for unified strategy validation CLI.

ValidationRunner is NOT eagerly imported here to avoid pulling the full
strategy registry (and its transitive research/ dependencies) on any
``import validation`` or ``from validation.config import ...``.

Use ``from validation.runner import ValidationRunner`` when needed.
"""

from validation.config import ValidationConfig

__all__ = ["ValidationConfig"]
