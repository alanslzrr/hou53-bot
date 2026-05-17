"""Generate the TypeScript-facing house input contract from Pydantic.

The FastAPI input DTO is generated from ``hou53_ml.io.Schema``. This
script materializes the same contract as JSON for the Next.js parser so
the web app does not maintain a hand-written 79-field schema.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.api.dtos import HousePredictionRequest
from hou53_ml.constants import (
    NUMERIC_BUT_CATEGORICAL,
    NUMERIC_ORDINAL_FEATURES,
    ORDINAL_OTHER_ORDERS,
    QUALITY_ORDER,
)
from hou53_ml.io.schema import Schema

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = REPO_ROOT / "apps/web/src/lib/housing/house-schema.generated.json"


def _nonnull_variants(prop: dict[str, Any]) -> list[dict[str, Any]]:
    variants = prop.get("anyOf", [prop])
    return [variant for variant in variants if variant.get("type") != "null"]


def _json_schema_bounds(prop: dict[str, Any]) -> tuple[float | None, float | None]:
    bounds_source = _nonnull_variants(prop)[0]
    minimum = bounds_source.get("minimum")
    maximum = bounds_source.get("maximum")
    return (
        float(minimum) if minimum is not None else None,
        float(maximum) if maximum is not None else None,
    )


def _field_kind(column: str, schema: Schema) -> str:
    if column in schema.temporal:
        return "temporal"
    if column in schema.ordinal_quality:
        return "quality_ordinal"
    if column in NUMERIC_ORDINAL_FEATURES:
        return "numeric_ordinal"
    if column in NUMERIC_BUT_CATEGORICAL:
        return "numeric_categorical"
    if column in ORDINAL_OTHER_ORDERS:
        return "ordered_ordinal"
    if column in schema.numeric:
        return "numeric"
    return "nominal"


def _field_type(column: str, kind: str) -> str:
    if kind in {"numeric", "temporal", "numeric_ordinal"}:
        return "integer" if kind in {"temporal", "numeric_ordinal"} else "number"
    if kind == "numeric_categorical":
        return "integer_or_string"
    if kind in {"quality_ordinal", "ordered_ordinal"}:
        return "string_enum"
    return "string"


def _field_enum(column: str, kind: str) -> list[str] | None:
    if kind == "quality_ordinal":
        return list(QUALITY_ORDER.keys())
    if kind == "ordered_ordinal":
        return list(ORDINAL_OTHER_ORDERS[column])
    return None


def build_contract() -> dict[str, Any]:
    """Build a JSON-serializable contract from the Pydantic model."""
    schema = Schema.default()
    pydantic_schema = HousePredictionRequest.model_json_schema(by_alias=True)
    properties = pydantic_schema["properties"]

    missing = [column for column in schema.all_features if column not in properties]
    if missing:
        msg = f"Pydantic input model is missing fields: {missing}"
        raise RuntimeError(msg)

    features: list[dict[str, Any]] = []
    for column in schema.all_features:
        kind = _field_kind(column, schema)
        minimum, maximum = _json_schema_bounds(properties[column])
        features.append(
            {
                "name": column,
                "kind": kind,
                "type": _field_type(column, kind),
                "minimum": minimum,
                "maximum": maximum,
                "enum": _field_enum(column, kind),
            }
        )

    return {
        "version": 1,
        "source": "app.api.dtos.HousePredictionRequest",
        "feature_count": len(features),
        "quality_levels": list(QUALITY_ORDER.keys()),
        "features": features,
    }


def main() -> None:
    """Write the generated contract to ``apps/web/src/lib/housing``."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    contract = build_contract()
    OUTPUT_PATH.write_text(json.dumps(contract, indent=2, sort_keys=False) + "\n")


if __name__ == "__main__":
    main()
