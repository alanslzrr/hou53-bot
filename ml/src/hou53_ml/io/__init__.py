"""Dataset and artifact I/O.

Narrow public surface: outside callers depend on the loader and the
schema, not on internal helpers. Re-exporting from this module
permits internal refactors without breaking downstream imports.
"""

from hou53_ml.io.loaders import (
    EXPECTED_RAW_SHAPE,
    AmesHousingLoader,
    LoadResult,
)
from hou53_ml.io.schema import Schema

__all__ = [
    "EXPECTED_RAW_SHAPE",
    "AmesHousingLoader",
    "LoadResult",
    "Schema",
]
