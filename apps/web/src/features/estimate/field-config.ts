import {
  HOUSE_FEATURES,
  houseSchemaContract,
  type HouseFeatureName,
} from "@/lib/housing/schema";

import { FIELD_GROUP_BY_NAME, FIELD_GROUPS, type FieldGroupId } from "./groups";

export type FieldKind = "number" | "select" | "text";

export type EstimateFieldConfig = {
  name: HouseFeatureName;
  label: string;
  group: FieldGroupId;
  kind: FieldKind;
  valueType: "number" | "integer" | "integer_or_string" | "string_enum" | "string";
  required: false;
  min?: number;
  max?: number;
  options?: readonly string[];
  description?: string;
};

function labelFor(name: string): string {
  return name
    .replace(/^1st/, "1st ")
    .replace(/^2nd/, "2nd ")
    .replace(/^3Ssn/, "3 season ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Za-z])(\d)/g, "$1 $2")
    .replace(/SF$/, "SF")
    .trim();
}

function descriptionFor(field: EstimateFieldConfig): string | undefined {
  const bounds: string[] = [];
  if (field.min !== undefined) {
    bounds.push(`min ${field.min}`);
  }
  if (field.max !== undefined) {
    bounds.push(`max ${field.max}`);
  }
  if (bounds.length > 0) {
    return bounds.join(", ");
  }
  if (field.options && field.options.length > 0) {
    return `${field.options.length} known Ames values`;
  }
  return undefined;
}

function kindFor(feature: (typeof houseSchemaContract.features)[number]): FieldKind {
  if (feature.enum || feature.options) {
    return "select";
  }
  if (feature.type === "number" || feature.type === "integer") {
    return "number";
  }
  return "text";
}

export const ESTIMATE_FIELD_CONFIGS: readonly EstimateFieldConfig[] = houseSchemaContract.features.map(
  (feature) => {
    const options = feature.enum ?? feature.options ?? undefined;
    const config: EstimateFieldConfig = {
      name: feature.name as HouseFeatureName,
      label: labelFor(feature.name),
      group: FIELD_GROUP_BY_NAME.get(feature.name as HouseFeatureName) ?? "location_lot",
      kind: kindFor(feature),
      valueType: feature.type,
      required: false,
      min: feature.minimum ?? undefined,
      max: feature.maximum ?? undefined,
      options,
    };

    return {
      ...config,
      description: descriptionFor(config),
    };
  },
);

export const FIELD_CONFIG_BY_NAME = new Map<HouseFeatureName, EstimateFieldConfig>(
  ESTIMATE_FIELD_CONFIGS.map((field) => [field.name, field]),
);

export const FIELD_CONFIGS_BY_GROUP = FIELD_GROUPS.map((group) => ({
  ...group,
  fields: group.fields.map((field) => {
    const config = FIELD_CONFIG_BY_NAME.get(field);
    if (!config) {
      throw new Error(`Field ${field} is missing from the generated house contract.`);
    }
    return config;
  }),
}));

export function hasCompleteFieldCoverage(): boolean {
  return HOUSE_FEATURES.every((field) => FIELD_GROUP_BY_NAME.has(field));
}
