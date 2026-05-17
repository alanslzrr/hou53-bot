import type { HouseFeatureName, HouseFieldValue } from "@/lib/housing/schema";

export type ParseErrorCode =
  | "invalid_request"
  | "input_too_large"
  | "rate_limited"
  | "parse_failed"
  | "parse_timeout";

export type ParseErrorPayload = {
  code: ParseErrorCode;
  message: string;
};

export type ParseSuccessResponse = {
  ok: true;
  request_id: string;
  model: string;
  parsed_fields: Partial<Record<HouseFeatureName, HouseFieldValue>>;
  guessed_fields: HouseFeatureName[];
  missing_fields: HouseFeatureName[];
  field_confidence: Partial<Record<HouseFeatureName, number>>;
  clarification_questions: string[];
  needs_confirmation: true;
  latency_ms: number;
};

export type ParseErrorResponse = {
  ok: false;
  request_id: string;
  model?: string;
  error: ParseErrorPayload;
  partial_fields: Partial<Record<HouseFeatureName, HouseFieldValue>>;
  needs_manual_entry: true;
  latency_ms: number;
};

export type ParseResponse = ParseSuccessResponse | ParseErrorResponse;
