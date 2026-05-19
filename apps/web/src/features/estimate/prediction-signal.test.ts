import { describe, expect, it } from "vitest";

import { assessPredictionSignal } from "./prediction-signal";

describe("assessPredictionSignal", () => {
  it("marks generic room-only payloads as not ready without blocking prediction", () => {
    const signal = assessPredictionSignal({
      HouseStyle: "2Story",
      BedroomAbvGr: 3,
      FullBath: 2,
      GarageCars: 2,
    });

    expect(signal.ready).toBe(false);
    expect(signal.can_predict_now).toBe(true);
    expect(signal.missingSignals).toContain("living area");
  });

  it("marks area-only payloads as not ready", () => {
    const signal = assessPredictionSignal({ GrLivArea: 1800, BedroomAbvGr: 3, FullBath: 2 });

    expect(signal.ready).toBe(false);
    expect(signal.level).toBe("sparse");
    expect(signal.missingSignals).toContain("quality/condition");
  });

  it("marks rich appraisal context as ready", () => {
    expect(
      assessPredictionSignal({
        GrLivArea: 1800,
        OverallQual: 7,
        YearBuilt: 1998,
        Neighborhood: "NAmes",
        GarageCars: 2,
        FullBath: 2,
      }).ready,
    ).toBe(true);
  });
});
