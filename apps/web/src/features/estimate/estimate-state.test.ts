import { describe, expect, it } from "vitest";

import { estimateReducer, initialEstimateState } from "./estimate-state";

describe("estimateReducer", () => {
  it("prevents edits while parsing", () => {
    const parsing = estimateReducer(initialEstimateState, { type: "parse_start" });

    expect(estimateReducer(parsing, { type: "edit" })).toBe(parsing);
  });

  it("moves through parse and prediction states", () => {
    const parsed = estimateReducer(initialEstimateState, {
      type: "parse_success",
      extractedCount: 3,
      missingCount: 0,
    });
    expect(parsed.status).toBe("parsed_valid");

    const predicting = estimateReducer(parsed, { type: "predict_start" });
    expect(predicting.status).toBe("predicting");
  });

  it("moves through readiness states without blocking sparse prediction", () => {
    const assessing = estimateReducer(initialEstimateState, { type: "assess_start" });
    expect(assessing.status).toBe("assessing");

    const needsMoreSignal = estimateReducer(assessing, { type: "readiness_needs_more_signal" });
    expect(needsMoreSignal.status).toBe("needs_more_signal");

    const predicting = estimateReducer(needsMoreSignal, { type: "predict_start" });
    expect(predicting.status).toBe("predicting");
  });

  it("returns to editing after applying readiness answers", () => {
    const needsMoreSignal = estimateReducer(initialEstimateState, { type: "readiness_needs_more_signal" });
    const applying = estimateReducer(needsMoreSignal, { type: "apply_readiness_answers" });

    expect(applying.status).toBe("applying_answers");
    expect(estimateReducer(applying, { type: "readiness_answers_applied" }).status).toBe("editing");
  });

  it("clears stale prediction results when parsing again", () => {
    const predicted = estimateReducer(initialEstimateState, {
      type: "predict_success",
      result: {
        ok: true,
        prediction_id: "prediction-1",
        prediction: { value_usd: 200_000, currency: "USD" },
        explanation: { baseline_usd: 180_000, natural_language: "Estimated.", top_features: [] },
        model: { name: "xgboost", version: "v1", trained_at_utc: "2026-05-17T00:00:00Z" },
        api_request_id: "req-1",
        saved: true,
        created_at: "2026-05-17T00:00:00Z",
      },
    });

    expect(estimateReducer(predicted, { type: "parse_start" }).result).toBeUndefined();
  });

  it("resets a completed estimate", () => {
    const predicted = estimateReducer(initialEstimateState, {
      type: "predict_success",
      result: {
        ok: true,
        prediction_id: "prediction-1",
        prediction: { value_usd: 200_000, currency: "USD" },
        explanation: { baseline_usd: 180_000, natural_language: "Estimated.", top_features: [] },
        model: { name: "xgboost", version: "v1", trained_at_utc: "2026-05-17T00:00:00Z" },
        api_request_id: "req-1",
        saved: true,
        created_at: "2026-05-17T00:00:00Z",
      },
    });

    expect(estimateReducer(predicted, { type: "reset" })).toEqual(initialEstimateState);
  });
});
