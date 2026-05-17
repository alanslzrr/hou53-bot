"""Build a deterministic NLP-parser eval set from real Ames rows."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
from hou53_ml.constants import NA_AS_CATEGORY
from hou53_ml.io.schema import Schema

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_CSV = REPO_ROOT / "data/raw/house_prices.csv"
OUTPUT_PATH = REPO_ROOT / "ml/evals/nlp_parser/examples.jsonl"
N_EXAMPLES = 120
RANDOM_STATE = 53
SCHEMA = Schema.default()
NUMERIC_OUTPUT_FIELDS = frozenset((*SCHEMA.numeric, *SCHEMA.temporal))

NEIGHBORHOOD_NAMES: dict[str, str] = {
    "Blmngtn": "Bloomington Heights",
    "Blueste": "Bluestem",
    "BrDale": "Briardale",
    "BrkSide": "Brookside",
    "ClearCr": "Clear Creek",
    "CollgCr": "College Creek",
    "Crawfor": "Crawford",
    "Edwards": "Edwards",
    "Gilbert": "Gilbert",
    "IDOTRR": "Iowa DOT and Rail Road",
    "MeadowV": "Meadow Village",
    "Mitchel": "Mitchell",
    "NAmes": "North Ames",
    "NoRidge": "Northridge",
    "NPkVill": "Northpark Villa",
    "NridgHt": "Northridge Heights",
    "NWAmes": "Northwest Ames",
    "OldTown": "Old Town",
    "SWISU": "South and West of Iowa State University",
    "Sawyer": "Sawyer",
    "SawyerW": "Sawyer West",
    "Somerst": "Somerset",
    "StoneBr": "Stone Brook",
    "Timber": "Timberland",
    "Veenker": "Veenker",
}

QUALITY_WORDS: dict[int, str] = {
    10: "very excellent",
    9: "excellent",
    8: "very good",
    7: "good",
    6: "above average",
    5: "average",
    4: "below average",
    3: "fair",
    2: "poor",
    1: "very poor",
}


def _clean_value(field: str, value: Any) -> Any:
    if value is None:
        return "NA" if field in NA_AS_CATEGORY else None
    if isinstance(value, float) and math.isnan(value):
        return "NA" if field in NA_AS_CATEGORY else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in {"", "?", "None", "nan"}:
            return "NA" if field in NA_AS_CATEGORY else None
        if field in NUMERIC_OUTPUT_FIELDS:
            parsed = float(stripped)
            return int(parsed) if parsed.is_integer() else parsed
        return stripped
    if hasattr(value, "item"):
        return value.item()
    return value


def _number(value: Any, default: int = 0) -> int:
    cleaned = _clean_value("", value)
    if cleaned is None:
        return default
    return int(float(cleaned))


def _quality(value: Any) -> str:
    return QUALITY_WORDS.get(_number(value, 5), "average")


def _neighborhood(value: Any) -> str:
    code = str(_clean_value("Neighborhood", value) or "")
    name = NEIGHBORHOOD_NAMES.get(code, code)
    return f"{name} ({code})" if code else "Ames"


def _garage_sentence(row: pd.Series[Any]) -> str:
    cars = _number(row.get("GarageCars"))
    area = _number(row.get("GarageArea"))
    garage_type = _clean_value("GarageType", row.get("GarageType"))
    if cars <= 0 or garage_type == "NA":
        return "It does not have a garage."
    return f"The garage is {garage_type} and fits {cars} cars with about {area} square feet."


def _basement_sentence(row: pd.Series[Any]) -> str:
    total = _number(row.get("TotalBsmtSF"))
    exposure = _clean_value("BsmtExposure", row.get("BsmtExposure"))
    finish = _clean_value("BsmtFinType1", row.get("BsmtFinType1"))
    if total <= 0:
        return "There is no basement."
    return (
        f"The basement has {total} square feet, exposure {exposure}, and primary finish {finish}."
    )


def _porch_sentence(row: pd.Series[Any]) -> str:
    open_porch = _number(row.get("OpenPorchSF"))
    deck = _number(row.get("WoodDeckSF"))
    screen = _number(row.get("ScreenPorch"))
    return (
        f"Outdoor areas include {deck} sqft of wood deck, "
        f"{open_porch} sqft of open porch, and {screen} sqft of screen porch."
    )


def describe_row(row: pd.Series[Any]) -> str:
    """Render one source row into a realistic free-form description."""
    half_baths = _number(row.get("HalfBath"))
    full_baths = _number(row.get("FullBath"))
    central_air = (
        "with central air"
        if _clean_value("CentralAir", row.get("CentralAir")) == "Y"
        else "without central air"
    )
    fireplace_count = _number(row.get("Fireplaces"))
    fireplace = "no fireplaces" if fireplace_count == 0 else f"{fireplace_count} fireplace(s)"

    return " ".join(
        [
            (
                f"A {row.get('HouseStyle')} house in {_neighborhood(row.get('Neighborhood'))}, "
                f"built in {_number(row.get('YearBuilt'))} "
                f"and remodeled in {_number(row.get('YearRemodAdd'))}."
            ),
            (
                f"It has {_number(row.get('BedroomAbvGr'))} bedrooms, {full_baths} full baths, "
                f"{half_baths} half baths, and {_number(row.get('TotRmsAbvGrd'))} "
                "total rooms above grade."
            ),
            (
                f"Living area is about {_number(row.get('GrLivArea'))} square feet on a "
                f"{_number(row.get('LotArea'))} sqft lot, {central_air}, with {fireplace}."
            ),
            (
                f"Overall material quality is {_quality(row.get('OverallQual'))} "
                f"and condition is {_quality(row.get('OverallCond'))}."
            ),
            _garage_sentence(row),
            _basement_sentence(row),
            _porch_sentence(row),
        ]
    )


def build_examples() -> list[dict[str, Any]]:
    """Sample real rows and pair each with a synthetic description."""
    schema = Schema.default()
    df = pd.read_csv(SOURCE_CSV, comment="#")
    sampled = df.sample(n=N_EXAMPLES, random_state=RANDOM_STATE).sort_values("Id")

    examples: list[dict[str, Any]] = []
    for _, row in sampled.iterrows():
        ground_truth = {field: _clean_value(field, row.get(field)) for field in schema.all_features}
        source_id = _number(row.get("Id"))
        examples.append(
            {
                "id": f"ames-{source_id:04d}",
                "source_id": source_id,
                "description": describe_row(row),
                "ground_truth": ground_truth,
            }
        )
    return examples


def main() -> None:
    """Write the eval set as JSONL."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        for example in build_examples():
            handle.write(json.dumps(example, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
