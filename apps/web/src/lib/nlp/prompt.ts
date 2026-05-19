import { houseSchemaContract } from "@/lib/housing/schema";

function describeFeature(feature: (typeof houseSchemaContract.features)[number]): string {
  const bounds = [
    feature.minimum === null ? null : `min ${feature.minimum}`,
    feature.maximum === null ? null : `max ${feature.maximum}`,
  ]
    .filter(Boolean)
    .join(", ");
  const enumValues = feature.enum ? ` allowed values: ${feature.enum.join(", ")}` : "";
  const constraint = bounds ? ` (${bounds})` : "";

  return `- ${feature.name}: ${feature.kind}, ${feature.type}${constraint}.${enumValues}`;
}

const FIELD_GUIDE = houseSchemaContract.features.map(describeFeature).join("\n");

export function buildParserSystemPrompt(): string {
  return [
    "You extract Ames Housing model features from a user's natural-language house description.",
    "Return only values that are explicitly stated or strongly implied by common real-estate wording.",
    "Use null omission instead of guessing when the user does not provide enough evidence.",
    "Never output Id, SalePrice, engineered features, explanations for price, or fields outside the contract.",
    "Use Ames dataset codes when they are known. Examples: central air is Y or N; quality scales use NA, Po, Fa, TA, Gd, Ex.",
    "Mark inferred fields in guessed_fields. Keep clarification questions short and actionable.",
    "For missing_fields, list only the most important follow-up fields, never every omitted field. Prioritize GrLivArea, OverallQual, YearBuilt, Neighborhood, TotalBsmtSF, GarageCars, GarageArea, FullBath.",
    "The user must confirm the parsed form before prediction, so do not call or imply a price prediction.",
    "",
    "Field contract:",
    FIELD_GUIDE,
  ].join("\n");
}

export function buildParserUserPrompt(description: string): string {
  return [
    "Parse this house description into the structured Ames Housing feature contract.",
    "If a value is unknown, omit it from partial_fields and optionally add it to missing_fields.",
    "",
    "Description:",
    description,
  ].join("\n");
}
