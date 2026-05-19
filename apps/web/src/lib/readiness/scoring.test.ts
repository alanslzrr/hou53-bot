import { describe, expect, it } from "vitest";

import { assessPredictionReadiness } from "./scoring";

describe("assessPredictionReadiness", () => {
  it("marks room-only payloads as sparse while allowing prediction", () => {
    const readiness = assessPredictionReadiness({
      HouseStyle: "2Story",
      BedroomAbvGr: 3,
      FullBath: 2,
      GarageCars: 2,
    });

    expect(readiness.level).toBe("sparse");
    expect(readiness.can_predict_now).toBe(true);
    expect(readiness.missing_signal_groups).toContain("living_area");
  });

  it("marks area plus year as usable", () => {
    const readiness = assessPredictionReadiness({ GrLivArea: 1800, YearBuilt: 1998 });

    expect(readiness.readiness_score).toBeGreaterThanOrEqual(45);
    expect(readiness.level).toBe("usable");
  });

  it("marks rich appraisal payloads as strong", () => {
    const readiness = assessPredictionReadiness({
      GrLivArea: 2400,
      OverallQual: 8,
      YearBuilt: 2005,
      Neighborhood: "StoneBr",
      GarageCars: 2,
      FullBath: 3,
    });

    expect(readiness.readiness_score).toBe(100);
    expect(readiness.level).toBe("strong");
  });
});
