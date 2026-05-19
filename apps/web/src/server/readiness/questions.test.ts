import { describe, expect, it } from "vitest";

import { assessPredictionReadiness } from "@/lib/readiness/scoring";

import { buildRuleBasedReadinessQuestions } from "./questions";

describe("buildRuleBasedReadinessQuestions", () => {
  it("returns at most five questions for sparse input", () => {
    const fields = { BedroomAbvGr: 3, FullBath: 2 };
    const questions = buildRuleBasedReadinessQuestions({
      fields,
      assessment: assessPredictionReadiness(fields),
    });

    expect(questions).toHaveLength(5);
    expect(questions[0]?.target_fields).toEqual(["GrLivArea"]);
  });

  it("does not ask about fields that are already filled with strong values", () => {
    const fields = { GrLivArea: 1800, OverallQual: 7, YearBuilt: 1998 };
    const questions = buildRuleBasedReadinessQuestions({
      fields,
      assessment: assessPredictionReadiness(fields),
    });

    expect(questions.flatMap((question) => question.target_fields)).not.toContain("GrLivArea");
    expect(questions.flatMap((question) => question.target_fields)).not.toContain("OverallQual");
    expect(questions.flatMap((question) => question.target_fields)).not.toContain("YearBuilt");
  });

  it("asks to confirm guessed or low-confidence fields", () => {
    const fields = { GrLivArea: 1800, OverallQual: 7, YearBuilt: 1998 };
    const questions = buildRuleBasedReadinessQuestions({
      fields,
      assessment: assessPredictionReadiness(fields),
      parseMetadata: {
        guessed_fields: ["OverallQual"],
        field_confidence: { YearBuilt: 0.4 },
      },
    });

    const targets = questions.flatMap((question) => question.target_fields);

    expect(targets).toContain("OverallQual");
    expect(targets).toContain("YearBuilt");
  });

  it("returns no questions for strong input", () => {
    const fields = {
      GrLivArea: 2400,
      OverallQual: 8,
      YearBuilt: 2005,
      Neighborhood: "StoneBr",
      GarageCars: 2,
      FullBath: 3,
    };
    const questions = buildRuleBasedReadinessQuestions({
      fields,
      assessment: assessPredictionReadiness(fields),
    });

    expect(questions).toEqual([]);
  });
});
