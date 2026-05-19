import type { HouseFeatureName, HouseFields, HouseFieldValue } from "@/lib/housing/schema";

import type { ReadinessAssessment, ReadinessLevel } from "./types";

type ReadinessSignalGroup = {
  id: string;
  weight: number;
  fields: readonly HouseFeatureName[];
};

export const READINESS_SIGNAL_GROUPS: readonly ReadinessSignalGroup[] = [
  {
    id: "living_area",
    weight: 30,
    fields: ["GrLivArea", "1stFlrSF", "2ndFlrSF", "TotalBsmtSF"],
  },
  {
    id: "quality_condition",
    weight: 20,
    fields: ["OverallQual", "OverallCond", "KitchenQual", "ExterQual", "ExterCond"],
  },
  {
    id: "age",
    weight: 15,
    fields: ["YearBuilt", "YearRemodAdd"],
  },
  {
    id: "location",
    weight: 15,
    fields: ["Neighborhood", "MSZoning"],
  },
  {
    id: "basement_garage",
    weight: 10,
    fields: ["TotalBsmtSF", "BsmtQual", "BsmtExposure", "GarageCars", "GarageArea", "GarageType", "GarageYrBlt"],
  },
  {
    id: "rooms_baths",
    weight: 10,
    fields: ["BedroomAbvGr", "TotRmsAbvGrd", "FullBath", "HalfBath", "BsmtFullBath", "BsmtHalfBath"],
  },
];

function hasConcreteValue(value: HouseFieldValue | null | undefined): boolean {
  return value !== null && value !== undefined && value !== "";
}

function hasAnyField(fields: HouseFields, fieldNames: readonly HouseFeatureName[]): boolean {
  return fieldNames.some((fieldName) => hasConcreteValue(fields[fieldName]));
}

function levelFor(score: number): ReadinessLevel {
  if (score >= 70) {
    return "strong";
  }
  if (score >= 45) {
    return "usable";
  }
  return "sparse";
}

export function hasMeaningfulHouseFields(fields: HouseFields): boolean {
  return Object.values(fields).some(hasConcreteValue);
}

export function assessPredictionReadiness(fields: HouseFields): ReadinessAssessment {
  let score = 0;
  const missingSignalGroups: string[] = [];

  for (const group of READINESS_SIGNAL_GROUPS) {
    if (hasAnyField(fields, group.fields)) {
      score += group.weight;
    } else {
      missingSignalGroups.push(group.id);
    }
  }

  const readinessScore = Math.min(100, Math.max(0, score));

  return {
    readiness_score: readinessScore,
    level: levelFor(readinessScore),
    can_predict_now: hasMeaningfulHouseFields(fields),
    missing_signal_groups: missingSignalGroups,
  };
}
