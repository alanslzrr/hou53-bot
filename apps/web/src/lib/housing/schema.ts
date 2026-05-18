import { z } from "zod";

import contractJson from "./house-schema.generated.json";

type FieldKind =
  | "numeric"
  | "temporal"
  | "quality_ordinal"
  | "numeric_ordinal"
  | "numeric_categorical"
  | "ordered_ordinal"
  | "nominal";

type FieldType = "number" | "integer" | "integer_or_string" | "string_enum" | "string";

type ContractFeature = {
  name: string;
  kind: FieldKind;
  type: FieldType;
  minimum: number | null;
  maximum: number | null;
  enum: string[] | null;
  options?: string[] | null;
};

type HouseSchemaContract = {
  version: number;
  source: string;
  feature_count: number;
  quality_levels: string[];
  features: ContractFeature[];
};

export type HouseFeatureName = (typeof HOUSE_FEATURES)[number];
export type HouseFieldValue = number | string;
export type LooseHouseFieldValue = HouseFieldValue | boolean;
export type HouseFields = Partial<Record<HouseFeatureName, HouseFieldValue | null | undefined>>;
export type LooseHouseFields = Record<string, LooseHouseFieldValue | null | undefined>;

export const houseSchemaContract = contractJson as HouseSchemaContract;

export const HOUSE_FEATURES = houseSchemaContract.features.map((feature) => feature.name);
export const HOUSE_FEATURE_COUNT = houseSchemaContract.feature_count;

function asNonEmptyStringTuple(values: readonly string[], label: string): [string, ...string[]] {
  if (values.length === 0) {
    throw new Error(`${label} must contain at least one value`);
  }
  return [...values] as [string, ...string[]];
}

function numberSchema(feature: ContractFeature, integer: boolean): z.ZodNumber {
  let schema = integer ? z.number().int() : z.number();

  if (feature.minimum !== null) {
    schema = schema.min(feature.minimum);
  }
  if (feature.maximum !== null) {
    schema = schema.max(feature.maximum);
  }

  return schema;
}

function fieldValueSchema(feature: ContractFeature): z.ZodTypeAny {
  switch (feature.type) {
    case "number":
      return numberSchema(feature, false).nullable().optional();
    case "integer":
      return numberSchema(feature, true).nullable().optional();
    case "integer_or_string":
      return z.union([z.number().int(), z.string().min(1)]).nullable().optional();
    case "string_enum":
      if (!feature.enum) {
        throw new Error(`${feature.name} is missing enum values`);
      }
      return z.enum(asNonEmptyStringTuple(feature.enum, feature.name)).nullable().optional();
    case "string":
      return z.string().min(1).nullable().optional();
  }
}

const houseFieldShape = Object.fromEntries(
  houseSchemaContract.features.map((feature) => [feature.name, fieldValueSchema(feature)]),
) as z.ZodRawShape;

export const houseFeatureNameSchema = z.enum(asNonEmptyStringTuple(HOUSE_FEATURES, "features"));

export const houseFieldsSchema = z.object(houseFieldShape).strip();

export const completeHouseFieldsSchema = houseFieldsSchema.refine(
  (fields) =>
    Object.values(fields).some(
      (value) => value !== null && value !== undefined && value !== "",
    ),
  { message: "At least one house feature is required." },
);

export const looseHouseFieldsSchema = z
  .record(z.string().min(1), z.union([z.string().min(1), z.number(), z.boolean(), z.null()]))
  .describe("Extracted feature values keyed by canonical Ames Housing feature name.");

export const parserModelOutputSchema = z
  .object({
    partial_fields: looseHouseFieldsSchema,
    guessed_fields: z
      .array(houseFeatureNameSchema)
      .max(HOUSE_FEATURE_COUNT)
      .optional()
      .describe("Fields inferred from context rather than explicitly stated."),
    missing_fields: z
      .array(houseFeatureNameSchema)
      .max(HOUSE_FEATURE_COUNT)
      .optional()
      .describe("Important fields that are still missing and should be confirmed manually."),
    field_confidence: z
      .partialRecord(houseFeatureNameSchema, z.number().min(0).max(1))
      .optional()
      .describe("Confidence per extracted field, from 0 to 1."),
    clarification_questions: z
      .array(z.string().min(1).max(180))
      .max(5)
      .optional()
      .describe("Short questions that would improve the parse before prediction."),
  })
  .strip();

export type ParserModelOutput = z.infer<typeof parserModelOutputSchema>;

const CANONICAL_STRING_VALUES: Record<string, Record<string, string>> = {
  Neighborhood: {
    "bloomington heights": "Blmngtn",
    blmngtn: "Blmngtn",
    bluestem: "Blueste",
    blueste: "Blueste",
    briardale: "BrDale",
    brdale: "BrDale",
    brookside: "BrkSide",
    brkside: "BrkSide",
    "clear creek": "ClearCr",
    clearcr: "ClearCr",
    "college creek": "CollgCr",
    collgcr: "CollgCr",
    crawford: "Crawfor",
    crawfor: "Crawfor",
    edwards: "Edwards",
    gilbert: "Gilbert",
    "iowa dot and rail road": "IDOTRR",
    idotrr: "IDOTRR",
    "meadow village": "MeadowV",
    meadowv: "MeadowV",
    mitchell: "Mitchel",
    mitchel: "Mitchel",
    "north ames": "NAmes",
    names: "NAmes",
    "northridge heights": "NridgHt",
    nridght: "NridgHt",
    northridge: "NoRidge",
    noridge: "NoRidge",
    "northpark villa": "NPkVill",
    npkvill: "NPkVill",
    "northwest ames": "NWAmes",
    nwames: "NWAmes",
    "old town": "OldTown",
    oldtown: "OldTown",
    "south and west of iowa state university": "SWISU",
    "south west of iowa state university": "SWISU",
    swisu: "SWISU",
    sawyer: "Sawyer",
    "sawyer west": "SawyerW",
    sawyerw: "SawyerW",
    somerset: "Somerst",
    somerst: "Somerst",
    "stone brook": "StoneBr",
    stonebr: "StoneBr",
    timberland: "Timber",
    timber: "Timber",
    veenker: "Veenker",
  },
  GarageType: {
    "2 types": "2Types",
    "two types": "2Types",
    "more than one type": "2Types",
    "more than one type of garage": "2Types",
    "2types": "2Types",
    attached: "Attchd",
    attchd: "Attchd",
    basement: "Basment",
    basment: "Basment",
    "built in": "BuiltIn",
    "built-in": "BuiltIn",
    builtin: "BuiltIn",
    "car port": "CarPort",
    carport: "CarPort",
    detached: "Detchd",
    detchd: "Detchd",
    "no garage": "NA",
    none: "NA",
    na: "NA",
  },
};

function canonicalizeStringValue(featureName: HouseFeatureName, value: string): string {
  const normalized = value.trim().toLowerCase().replace(/\s+/g, " ");
  return CANONICAL_STRING_VALUES[featureName]?.[normalized] ?? value;
}

function coerceBooleanValue(value: LooseHouseFieldValue): HouseFieldValue {
  if (typeof value !== "boolean") {
    return value;
  }
  return value ? "Y" : "N";
}

function normalizeRawValue(featureName: HouseFeatureName, value: LooseHouseFieldValue): HouseFieldValue {
  const coerced = coerceBooleanValue(value);
  if (typeof coerced === "string") {
    return canonicalizeStringValue(featureName, coerced);
  }
  return coerced;
}

function validateHouseField(
  featureName: HouseFeatureName,
  value: string | number | boolean | null | undefined,
): HouseFieldValue | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const parsed = houseFieldsSchema.pick({ [featureName]: true }).safeParse({
    [featureName]: normalizeRawValue(featureName, value),
  });
  if (!parsed.success) {
    return null;
  }

  const parsedValue = parsed.data[featureName];
  if (typeof parsedValue === "string" || typeof parsedValue === "number") {
    return parsedValue;
  }
  return null;
}

export function normalizeHouseFields(
  fields: HouseFields | LooseHouseFields,
): Partial<Record<HouseFeatureName, HouseFieldValue>> {
  const normalized: Partial<Record<HouseFeatureName, HouseFieldValue>> = {};

  for (const featureName of HOUSE_FEATURES) {
    const value = validateHouseField(featureName, fields[featureName]);
    if (value !== null) {
      normalized[featureName] = value;
    }
  }

  return normalized;
}

export function uniqueFeatureNames(names: readonly HouseFeatureName[] | undefined): HouseFeatureName[] {
  return [...new Set(names ?? [])];
}
