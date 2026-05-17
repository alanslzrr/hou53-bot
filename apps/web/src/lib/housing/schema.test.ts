import { describe, expect, it } from "vitest";

import {
  HOUSE_FEATURE_COUNT,
  HOUSE_FEATURES,
  type HouseFields,
  houseFieldsSchema,
  normalizeHouseFields,
  parserModelOutputSchema,
} from "./schema";

describe("house schema contract", () => {
  it("exposes the full Pydantic feature surface", () => {
    expect(HOUSE_FEATURE_COUNT).toBe(79);
    expect(HOUSE_FEATURES).toContain("1stFlrSF");
    expect(HOUSE_FEATURES).toContain("OverallQual");
    expect(HOUSE_FEATURES).toContain("Neighborhood");
  });

  it("keeps numeric and ordinal Pydantic constraints", () => {
    expect(() => houseFieldsSchema.parse({ OverallQual: 11 })).toThrow();
    expect(() => houseFieldsSchema.parse({ YearBuilt: 1700 })).toThrow();
    expect(() => houseFieldsSchema.parse({ ExterQual: "Bad" })).toThrow();

    expect(
      houseFieldsSchema.parse({
        OverallQual: 8,
        YearBuilt: 1995,
        ExterQual: "Gd",
        "1stFlrSF": 1200,
      }),
    ).toEqual({
      OverallQual: 8,
      YearBuilt: 1995,
      ExterQual: "Gd",
      "1stFlrSF": 1200,
    });
  });

  it("strips unknown model fields and null values before returning to the UI", () => {
    const output = parserModelOutputSchema.parse({
      partial_fields: {
        BedroomAbvGr: 3,
        GarageCars: null,
        invented_feature: "ignored",
      },
      guessed_fields: ["GarageCars", "BedroomAbvGr"],
      missing_fields: ["LotArea"],
      field_confidence: { BedroomAbvGr: 0.93 },
    });

    expect(output.partial_fields).toEqual({
      BedroomAbvGr: 3,
      GarageCars: null,
      invented_feature: "ignored",
    });
    expect(normalizeHouseFields(output.partial_fields as HouseFields)).toEqual({ BedroomAbvGr: 3 });
  });

  it("canonicalizes common natural-language labels to Ames codes", () => {
    expect(
      normalizeHouseFields({
        Neighborhood: "North Ames",
        GarageType: "Attached",
        CentralAir: true,
      }),
    ).toEqual({
      Neighborhood: "NAmes",
      GarageType: "Attchd",
      CentralAir: "Y",
    });
  });
});
