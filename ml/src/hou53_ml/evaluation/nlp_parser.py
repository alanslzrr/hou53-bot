"""Evaluation utilities for the natural-language parser."""

from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from hou53_ml.constants import NA_AS_CATEGORY, NUMERIC_BUT_CATEGORICAL, NUMERIC_ORDINAL_FEATURES
from hou53_ml.io.schema import Schema

_SCHEMA = Schema.default()
_FEATURES = frozenset(_SCHEMA.all_features)
_NUMERIC_EVAL_FEATURES = (
    frozenset((*_SCHEMA.numeric, *_SCHEMA.temporal, *NUMERIC_ORDINAL_FEATURES))
    - NUMERIC_BUT_CATEGORICAL
)


@dataclass(frozen=True, slots=True)
class NlpParserEvalExample:
    """One natural-language parser eval row."""

    id: str
    description: str
    ground_truth: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NlpParserScore:
    """Aggregate parser eval metrics."""

    examples: int
    attempted_fields: int
    correct_fields: int
    source_fields_present: int
    accuracy: float
    coverage: float

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-friendly metric dictionary."""
        return asdict(self)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and value.strip() == ""


def _canonical_value(field: str, value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "?":
            return "NA" if field in NA_AS_CATEGORY else None
        return stripped
    return value


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def _numeric_tolerance(field: str, expected: float) -> float:
    if field in _SCHEMA.temporal or field in NUMERIC_ORDINAL_FEATURES or abs(expected) <= 10:
        return 1.0
    return abs(expected) * 0.10


def is_field_correct(field: str, predicted: Any, expected: Any) -> bool:
    """Return whether one extracted field matches its source-row value."""
    predicted_value = _canonical_value(field, predicted)
    expected_value = _canonical_value(field, expected)
    if predicted_value is None or expected_value is None:
        return False

    if field in _NUMERIC_EVAL_FEATURES:
        predicted_number = _as_float(predicted_value)
        expected_number = _as_float(expected_value)
        if predicted_number is None or expected_number is None:
            return False
        return abs(predicted_number - expected_number) <= _numeric_tolerance(field, expected_number)

    return str(predicted_value) == str(expected_value)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            parsed = json.loads(stripped)
            if not isinstance(parsed, dict):
                msg = f"{path}:{line_number} is not a JSON object"
                raise ValueError(msg)
            rows.append(cast(dict[str, Any], parsed))
    return rows


def load_examples(path: Path) -> list[NlpParserEvalExample]:
    """Load checked-in eval examples."""
    examples: list[NlpParserEvalExample] = []
    for row in _load_jsonl(path):
        examples.append(
            NlpParserEvalExample(
                id=str(row["id"]),
                description=str(row["description"]),
                ground_truth=cast(dict[str, Any], row["ground_truth"]),
            )
        )
    return examples


def load_predictions(path: Path) -> dict[str, dict[str, Any]]:
    """Load parser outputs keyed by eval example id."""
    predictions: dict[str, dict[str, Any]] = {}
    for row in _load_jsonl(path):
        fields = row.get("parsed_fields", row.get("partial_fields", {}))
        if not isinstance(fields, dict):
            msg = f"prediction {row.get('id')} has no parsed_fields object"
            raise ValueError(msg)
        predictions[str(row["id"])] = cast(dict[str, Any], fields)
    return predictions


def score_parser_outputs(
    examples: Sequence[NlpParserEvalExample],
    predictions_by_id: Mapping[str, Mapping[str, Any]],
) -> NlpParserScore:
    """Score parser output accuracy and coverage.

    Missing fields are neutral: they do not enter the accuracy denominator.
    Extracted fields are attempts and must match the original source row.
    """
    attempted_fields = 0
    correct_fields = 0
    source_fields_present = 0
    covered_fields = 0

    for example in examples:
        ground_truth = example.ground_truth
        for field in _FEATURES:
            if _canonical_value(field, ground_truth.get(field)) is not None:
                source_fields_present += 1

        prediction = predictions_by_id.get(example.id, {})
        for field, value in prediction.items():
            if _canonical_value(field, value) is None:
                continue

            attempted_fields += 1
            if field not in _FEATURES:
                continue

            if _canonical_value(field, ground_truth.get(field)) is not None:
                covered_fields += 1
            if is_field_correct(field, value, ground_truth.get(field)):
                correct_fields += 1

    accuracy = correct_fields / attempted_fields if attempted_fields else 0.0
    coverage = covered_fields / source_fields_present if source_fields_present else 0.0
    return NlpParserScore(
        examples=len(examples),
        attempted_fields=attempted_fields,
        correct_fields=correct_fields,
        source_fields_present=source_fields_present,
        accuracy=accuracy,
        coverage=coverage,
    )


def _validate_http_endpoint(endpoint: str) -> None:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        msg = "parser endpoint must use http or https"
        raise ValueError(msg)


def _post_parse(
    endpoint: str,
    example: NlpParserEvalExample,
    timeout_seconds: float,
) -> dict[str, Any]:
    _validate_http_endpoint(endpoint)
    payload = json.dumps({"description": example.description}).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310
        endpoint,
        data=payload,
        headers={
            "content-type": "application/json",
            "x-request-id": f"eval-{example.id}",
            "x-user-id": "nlp-parser-eval",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        parsed = json.loads(exc.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        msg = f"parser response for {example.id} is not an object"
        raise ValueError(msg)
    if parsed.get("ok") is False:
        return {}
    fields = parsed.get("parsed_fields", {})
    return cast(dict[str, Any], fields if isinstance(fields, dict) else {})


def collect_endpoint_predictions(
    examples: Sequence[NlpParserEvalExample],
    endpoint: str,
    *,
    timeout_seconds: float = 10.0,
) -> dict[str, dict[str, Any]]:
    """Call a running parser endpoint and collect parsed fields."""
    predictions: dict[str, dict[str, Any]] = {}
    for example in examples:
        try:
            predictions[example.id] = _post_parse(endpoint, example, timeout_seconds)
        except urllib.error.URLError as exc:
            msg = f"parser endpoint failed for {example.id}: {exc}"
            raise RuntimeError(msg) from exc
    return predictions


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the HOU53 NLP parser.")
    parser.add_argument("--examples", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--predictions", type=Path)
    source.add_argument("--endpoint", type=str)
    parser.add_argument("--min-accuracy", type=float, default=0.70)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = _build_parser().parse_args(argv)
    examples = load_examples(args.examples)
    if args.predictions:
        predictions = load_predictions(args.predictions)
    else:
        predictions = collect_endpoint_predictions(
            examples,
            args.endpoint,
            timeout_seconds=args.timeout_seconds,
        )

    score = score_parser_outputs(examples, predictions)
    print(json.dumps(score.to_dict(), indent=2, sort_keys=True))
    return 0 if score.accuracy >= args.min_accuracy else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "NlpParserEvalExample",
    "NlpParserScore",
    "collect_endpoint_predictions",
    "is_field_correct",
    "load_examples",
    "load_predictions",
    "score_parser_outputs",
]
