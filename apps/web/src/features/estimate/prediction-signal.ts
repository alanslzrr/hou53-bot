import type { HouseFields } from "@/lib/housing/schema";
import { assessPredictionReadiness } from "@/lib/readiness/scoring";
import type { ReadinessAssessment } from "@/lib/readiness/types";

export type PredictionSignal = ReadinessAssessment & {
  ready: boolean;
  missingSignals: string[];
};

const SIGNAL_LABELS: Record<string, string> = {
  living_area: "living area",
  quality_condition: "quality/condition",
  age: "year built/remodeled",
  location: "neighborhood",
  basement_garage: "basement or garage details",
  rooms_baths: "rooms and bathrooms",
};

function signalLabel(group: string): string {
  return SIGNAL_LABELS[group] ?? group;
}

export function assessPredictionSignal(fields: HouseFields): PredictionSignal {
  const readiness = assessPredictionReadiness(fields);

  return {
    ...readiness,
    ready: readiness.level === "strong",
    missingSignals: readiness.missing_signal_groups.map(signalLabel),
  };
}
