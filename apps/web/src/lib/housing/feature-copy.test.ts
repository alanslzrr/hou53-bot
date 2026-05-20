import { describe, expect, it } from "vitest";

import { getHouseFeatureCopy, getModelFeatureCopy, humanizeExplanationText } from "./feature-copy";

describe("feature copy", () => {
  it("explains engineered model features in user-facing language", () => {
    expect(getModelFeatureCopy("QualTotalSF")).toMatchObject({
      label: "Quality-weighted total area",
      description: "Overall quality multiplied by total floor and basement area.",
    });
  });

  it("explains form fields without exposing raw validation constraints", () => {
    expect(getHouseFeatureCopy("YearBuilt").description).toBe("Original construction year of the home.");
  });

  it("humanizes model feature names inside explanation text", () => {
    const text = "QualTotalSF lowered the estimate; NeighborhoodPriceLog raised it.";

    expect(humanizeExplanationText(text, ["QualTotalSF", "NeighborhoodPriceLog"])).toBe(
      "Quality-weighted total area lowered the estimate; Neighborhood price signal raised it.",
    );
  });
});
