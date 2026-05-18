import { describe, expect, it } from "vitest";

import { staleParsedFieldNamesToClear } from "./parse-field-application";

describe("staleParsedFieldNamesToClear", () => {
  it("clears previous AI fields omitted by the next parse", () => {
    const stale = staleParsedFieldNamesToClear({
      previousAiFields: new Set(["OverallQual", "GrLivArea"]),
      previousGuessedFields: new Set(["GarageCars"]),
      nextFields: { GrLivArea: 1800 },
      dirtyFields: {},
    });

    expect(stale.sort()).toEqual(["GarageCars", "OverallQual"].sort());
  });

  it("preserves manually edited previous AI fields", () => {
    const stale = staleParsedFieldNamesToClear({
      previousAiFields: new Set(["OverallQual", "GrLivArea"]),
      previousGuessedFields: new Set(),
      nextFields: {},
      dirtyFields: { OverallQual: true },
    });

    expect(stale).toEqual(["GrLivArea"]);
  });
});
