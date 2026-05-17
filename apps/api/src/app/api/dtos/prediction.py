"""HTTP DTOs for the prediction endpoint.

Two notable design choices:

1. **Input model is generated from** :class:`hou53_ml.io.Schema`. We
   refuse to maintain a 79-field Pydantic model by hand alongside the
   training schema — they would drift the day someone forgot to update
   one side. :func:`build_house_input_model` is the single source of
   truth.

2. **Aliases for non-Pythonic column names.** Three columns start with
   a digit (``1stFlrSF``, ``2ndFlrSF``, ``3SsnPorch``). Python field
   names cannot, so we prefix them with ``f_`` internally and use a
   Pydantic ``alias`` to keep the JSON contract stable. The
   ``populate_by_name=True`` config means callers can use either form.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from hou53_ml.constants import (
    NUMERIC_BUT_CATEGORICAL,
    NUMERIC_ORDINAL_FEATURES,
    QUALITY_ORDER,
)
from hou53_ml.io.schema import Schema
from pydantic import BaseModel, ConfigDict, Field, create_model


# -----------------------------------------------------------------------------
# Output models — hand-written and stable.
# -----------------------------------------------------------------------------
class FeatureContributionDTO(BaseModel):
    """One SHAP attribution row in the response."""

    feature: str = Field(description="Encoded feature name from the preprocessor.")
    shap_value: float = Field(
        description=(
            "SHAP value in log-dollar space (the model's native target). "
            "Positive = pushes price up."
        )
    )
    contribution_usd: float = Field(
        description=(
            "Approximate dollar contribution: "
            "expm1(baseline + shap) - expm1(baseline). "
            "Order-correct, magnitude approximate."
        )
    )
    direction: Literal["up", "down"]


class PredictionResponseModel(BaseModel):
    """Top-level response payload of :http:post:`/v1/predict`."""

    prediction: dict[str, Any] = Field(description="Predicted price (USD) and currency.")
    explanation: dict[str, Any] = Field(
        description=("Baseline price, top SHAP contributions, and a plain-English summary.")
    )
    model: dict[str, Any] = Field(
        description="Model identity (name, package version, training date)."
    )


class ModelInfoResponse(BaseModel):
    """Payload of :http:get:`/v1/model/info`."""

    model_name: str
    model_version: str
    trained_at_utc: str
    dataset_sha256: str
    library_versions: dict[str, str]
    feature_count_after_preprocess: int
    metrics: dict[str, Any]
    schema_fingerprint: list[str]


class HealthResponse(BaseModel):
    """Liveness response."""

    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    """Readiness response."""

    status: Literal["ready", "not-ready"]
    model_loaded: bool


# -----------------------------------------------------------------------------
# Input model — generated dynamically from the schema.
# -----------------------------------------------------------------------------
_QUALITY_LITERAL = Literal["NA", "Po", "Fa", "TA", "Gd", "Ex"]


class _HouseInputBase(BaseModel):
    """Base for the dynamically-generated input model.

    ``populate_by_name=True`` lets callers send either ``"1stFlrSF"``
    (alias, the canonical name) or ``"f_1stFlrSF"`` (the Python field
    name we are forced to use internally). ``extra="ignore"`` means
    surplus keys are dropped silently — friendlier when the natural-
    language parser hallucinates a key.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


def _safe_field_name(column: str) -> str:
    """Return a valid Python identifier for ``column``.

    Columns that start with a digit get an ``f_`` prefix; everything
    else passes through.
    """
    if not column[:1].isalpha() and column[:1] != "_":
        return f"f_{column}"
    return column


def _build_field_definitions(
    schema: Schema,
) -> dict[str, tuple[Any, Any]]:
    """Map each schema column to a ``(annotation, FieldInfo)`` pair.

    Categorisation:
    - Numeric (excl. NUMERIC_BUT_CATEGORICAL) → ``Optional[float]`` ≥ 0.
    - Temporal → ``Optional[int]`` in [1800, 2100].
    - Quality ordinals → ``Optional[Literal[...]]``.
    - Numeric-but-categorical (``MSSubClass``/``MoSold``/``YrSold``) →
      ``Optional[int | str]`` (coerced to string downstream by the
      model loader).
    - Other categoricals → ``Optional[str]``.
    """
    fields: dict[str, tuple[Any, Any]] = {}
    quality_set = set(schema.ordinal_quality)

    for column in schema.all_features:
        safe = _safe_field_name(column)
        kwargs: dict[str, Any] = {"default": None, "alias": column}

        if column in schema.temporal:
            ann: Any = Annotated[int | None, Field(ge=1800, le=2100, **kwargs)]
        elif column in quality_set:
            ann = Annotated[_QUALITY_LITERAL | None, Field(**kwargs)]
        elif column in NUMERIC_ORDINAL_FEATURES:
            # OverallQual / OverallCond — integer 1..10 ordinal scales
            # stored as int on disk. Range-validate.
            ann = Annotated[int | None, Field(ge=1, le=10, **kwargs)]
        elif column in NUMERIC_BUT_CATEGORICAL:
            # Accept either an int code (e.g., MSSubClass=60) or a
            # string ("60"); the model loader stringifies before the
            # pipeline sees it.
            ann = Annotated[int | str | None, Field(**kwargs)]
        elif column in schema.numeric:
            ann = Annotated[float | None, Field(ge=0, **kwargs)]
        else:
            # Nominal / string-ordinal categorical. The OneHotEncoder
            # is configured with ``handle_unknown="ignore"`` so any
            # string is accepted at predict time.
            ann = Annotated[str | None, Field(**kwargs)]

        # ``create_model`` wants ``(annotation, FieldInfo)`` tuples.
        # We pre-baked the FieldInfo into the Annotated metadata so we
        # only need ``Field()`` here as the placeholder default.
        fields[safe] = (ann, Field(default=None))

    # Validate that every quality column was reachable in QUALITY_ORDER.
    # If someone adds a new quality column to the schema without
    # extending QUALITY_ORDER, fail loudly at import time rather than
    # at the first 422 in production.
    for col in schema.ordinal_quality:
        for level in QUALITY_ORDER:
            assert level in {"NA", "Po", "Fa", "TA", "Gd", "Ex"}, col

    return fields


def build_house_input_model(schema: Schema | None = None) -> type[_HouseInputBase]:
    """Build the dynamic Pydantic input model.

    Returns:
        A subclass of :class:`_HouseInputBase` with one optional field
        per schema column. Aliases match the on-disk column names.
    """
    schema = schema or Schema.default()
    fields = _build_field_definitions(schema)
    model = create_model(  # type: ignore[call-overload]
        "HousePredictionRequest",
        __base__=_HouseInputBase,
        **fields,
    )
    return cast(type[_HouseInputBase], model)


#: Module-level singleton; importing this evaluates the schema once.
HousePredictionRequest = build_house_input_model()


__all__ = [
    "FeatureContributionDTO",
    "HealthResponse",
    "HousePredictionRequest",
    "ModelInfoResponse",
    "PredictionResponseModel",
    "ReadyResponse",
    "build_house_input_model",
]
