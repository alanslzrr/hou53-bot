import type { HouseFeatureName, HouseFields } from "@/lib/housing/schema";

export const MAX_READINESS_QUESTIONS = 5;

export type ReadinessLevel = "sparse" | "usable" | "strong";

export type ReadinessQuestion = {
  id: string;
  label: string;
  helper_text?: string;
  target_fields: HouseFeatureName[];
  priority: number;
  quick_answers?: string[];
};

export type ReadinessAssessment = {
  readiness_score: number;
  level: ReadinessLevel;
  can_predict_now: boolean;
  missing_signal_groups: string[];
};

export type ReadinessRouteRequest = {
  fields: HouseFields;
  input_source: "manual" | "nlp" | "mixed";
  parse_metadata?: {
    guessed_fields?: string[];
    missing_fields?: string[];
    field_confidence?: Record<string, number>;
  };
};

export type ReadinessSuccessResponse = ReadinessAssessment & {
  ok: true;
  questions: ReadinessQuestion[];
};

export type ReadinessErrorResponse = {
  ok: false;
  request_id: string;
  error: {
    code: "unauthorized" | "invalid_request" | "readiness_failed";
    message: string;
  };
};

export type ReadinessRouteResponse = ReadinessSuccessResponse | ReadinessErrorResponse;
