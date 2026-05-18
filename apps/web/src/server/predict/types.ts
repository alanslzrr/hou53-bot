import type { HouseFields } from "@/lib/housing/schema";
import type { PredictionInputSource, PredictionParseMetadata } from "@/server/db/schema";

export type FeatureContribution = {
  feature: string;
  shap_value: number;
  contribution_usd: number;
  direction: "up" | "down";
};

export type PredictionApiPayload = {
  prediction: {
    value_usd: number;
    currency: "USD";
  };
  explanation: {
    baseline_usd: number;
    natural_language: string;
    top_features: FeatureContribution[];
  };
  model: {
    name: string;
    version: string;
    trained_at_utc: string;
  };
};

export type PredictRouteRequest = {
  fields: HouseFields;
  input_source: PredictionInputSource;
  parse_metadata?: PredictionParseMetadata;
  idempotency_key: string;
};

export type PredictSuccessResponse = PredictionApiPayload & {
  ok: true;
  prediction_id: string;
  api_request_id: string;
  saved: boolean;
  created_at: string;
  replayed?: boolean;
  warning?: string;
};

export type PredictErrorResponse = {
  ok: false;
  request_id: string;
  error: {
    code: "unauthorized" | "invalid_request" | "predict_failed" | "predict_timeout" | "api_unavailable";
    message: string;
  };
};

export type PredictRouteResponse = PredictSuccessResponse | PredictErrorResponse;
