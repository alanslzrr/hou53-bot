import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest
from hou53_ml.evaluation.nlp_parser import (
    NlpParserEvalExample,
    collect_endpoint_predictions,
    is_field_correct,
    load_examples,
    load_predictions,
    main,
    score_parser_outputs,
)


def test_numeric_fields_allow_relative_tolerance() -> None:
    assert is_field_correct("GrLivArea", 1_850, 1_800)
    assert not is_field_correct("GrLivArea", 2_100, 1_800)


def test_small_counts_and_years_allow_one_unit_tolerance() -> None:
    assert is_field_correct("BedroomAbvGr", 4, 3)
    assert not is_field_correct("BedroomAbvGr", 5, 3)
    assert is_field_correct("YearBuilt", 1996, 1995)
    assert not is_field_correct("YearBuilt", 2000, 1995)


def test_categorical_fields_require_exact_canonical_match() -> None:
    assert is_field_correct("Neighborhood", "NAmes", "NAmes")
    assert is_field_correct("GarageType", "NA", "?")
    assert not is_field_correct("Neighborhood", "North Ames", "NAmes")


def test_score_counts_missing_predictions_as_neutral() -> None:
    examples = [
        NlpParserEvalExample(
            id="ames-1",
            description="A 3 bedroom home in North Ames with 1800 sqft.",
            ground_truth={
                "Neighborhood": "NAmes",
                "BedroomAbvGr": 3,
                "GrLivArea": 1800,
                "YearBuilt": 1995,
            },
        )
    ]
    predictions = {
        "ames-1": {
            "Neighborhood": "NAmes",
            "BedroomAbvGr": 3,
            "GrLivArea": 2100,
        }
    }

    score = score_parser_outputs(examples, predictions)

    assert score.attempted_fields == 3
    assert score.correct_fields == 2
    assert score.accuracy == 2 / 3
    assert score.coverage == 3 / 4


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_load_examples_and_predictions(tmp_path: Path) -> None:
    examples_path = tmp_path / "examples.jsonl"
    predictions_path = tmp_path / "predictions.jsonl"
    _write_jsonl(
        examples_path,
        [
            {
                "id": "ames-1",
                "description": "Three bedrooms.",
                "ground_truth": {"BedroomAbvGr": 3},
            }
        ],
    )
    _write_jsonl(
        predictions_path,
        [{"id": "ames-1", "parsed_fields": {"BedroomAbvGr": 3}}],
    )

    examples = load_examples(examples_path)
    predictions = load_predictions(predictions_path)

    assert examples == [
        NlpParserEvalExample(
            id="ames-1",
            description="Three bedrooms.",
            ground_truth={"BedroomAbvGr": 3},
        )
    ]
    assert predictions == {"ames-1": {"BedroomAbvGr": 3}}


def test_cli_returns_nonzero_when_accuracy_floor_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    examples_path = tmp_path / "examples.jsonl"
    predictions_path = tmp_path / "predictions.jsonl"
    _write_jsonl(
        examples_path,
        [
            {
                "id": "ames-1",
                "description": "Three bedrooms.",
                "ground_truth": {"BedroomAbvGr": 3},
            }
        ],
    )
    _write_jsonl(
        predictions_path,
        [{"id": "ames-1", "parsed_fields": {"BedroomAbvGr": 5}}],
    )

    exit_code = main(
        [
            "--examples",
            str(examples_path),
            "--predictions",
            str(predictions_path),
            "--min-accuracy",
            "0.70",
        ]
    )

    assert exit_code == 1
    assert json.loads(capsys.readouterr().out)["accuracy"] == 0.0


def test_collect_endpoint_predictions_posts_descriptions(monkeypatch: pytest.MonkeyPatch) -> None:
    example = NlpParserEvalExample(
        id="ames-1",
        description="Three bedrooms.",
        ground_truth={"BedroomAbvGr": 3},
    )

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true, "parsed_fields": {"BedroomAbvGr": 3}}'

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        assert request.full_url == "http://localhost:3000/api/parse"
        assert timeout == 2.0
        assert request.headers["X-user-id"] == "nlp-parser-eval"
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    predictions = collect_endpoint_predictions(
        [example],
        "http://localhost:3000/api/parse",
        timeout_seconds=2.0,
    )

    assert predictions == {"ames-1": {"BedroomAbvGr": 3}}


def test_collect_endpoint_predictions_rejects_non_http_endpoint() -> None:
    example = NlpParserEvalExample(id="ames-1", description="x", ground_truth={})

    with pytest.raises(ValueError, match="http or https"):
        collect_endpoint_predictions([example], "file:///tmp/parser")


def test_collect_endpoint_predictions_wraps_url_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    example = NlpParserEvalExample(id="ames-1", description="x", ground_truth={})

    def fake_urlopen(_request: Any, timeout: float) -> None:
        assert timeout == 10.0
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="parser endpoint failed"):
        collect_endpoint_predictions([example], "http://localhost:3000/api/parse")
