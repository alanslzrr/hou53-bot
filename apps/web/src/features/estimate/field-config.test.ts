import { describe, expect, it } from "vitest";

import { HOUSE_FEATURE_COUNT, HOUSE_FEATURES } from "@/lib/housing/schema";

import { ESTIMATE_FIELD_CONFIGS, hasCompleteFieldCoverage } from "./field-config";

describe("estimate field config", () => {
  it("covers all housing features exactly once", () => {
    const configuredNames = ESTIMATE_FIELD_CONFIGS.map((field) => field.name);

    expect(configuredNames).toHaveLength(HOUSE_FEATURE_COUNT);
    expect(new Set(configuredNames).size).toBe(HOUSE_FEATURE_COUNT);
    expect(configuredNames.sort()).toEqual([...HOUSE_FEATURES].sort());
    expect(hasCompleteFieldCoverage()).toBe(true);
  });

  it("uses known Ames options for categorical selectors", () => {
    const neighborhood = ESTIMATE_FIELD_CONFIGS.find((field) => field.name === "Neighborhood");

    expect(neighborhood?.kind).toBe("select");
    expect(neighborhood?.options).toContain("NAmes");
  });
});
