import type { ParseErrorPayload } from "@/lib/nlp/types";
import type { ReadinessErrorResponse } from "@/lib/readiness/types";
import type { PredictErrorResponse, PredictSuccessResponse } from "@/server/predict/types";

export type EstimateStatus =
  | "idle"
  | "parsing"
  | "parsed_partial"
  | "parsed_valid"
  | "editing"
  | "assessing"
  | "needs_more_signal"
  | "applying_answers"
  | "predicting"
  | "predicted"
  | "predict_error"
  | "parse_error"
  | "readiness_error";

export type EstimateState = {
  status: EstimateStatus;
  parseError?: ParseErrorPayload;
  readinessError?: ReadinessErrorResponse["error"];
  predictError?: PredictErrorResponse["error"];
  result?: PredictSuccessResponse;
};

export type EstimateAction =
  | { type: "reset" }
  | { type: "parse_start" }
  | { type: "parse_success"; extractedCount: number; missingCount: number }
  | { type: "parse_error"; error: ParseErrorPayload }
  | { type: "edit" }
  | { type: "assess_start" }
  | { type: "readiness_needs_more_signal" }
  | { type: "readiness_error"; error: ReadinessErrorResponse["error"] }
  | { type: "apply_readiness_answers" }
  | { type: "readiness_answers_applied" }
  | { type: "predict_start" }
  | { type: "predict_success"; result: PredictSuccessResponse }
  | { type: "predict_error"; error: PredictErrorResponse["error"] };

export const initialEstimateState: EstimateState = {
  status: "idle",
};

export function estimateReducer(state: EstimateState, action: EstimateAction): EstimateState {
  switch (action.type) {
    case "reset":
      return initialEstimateState;
    case "parse_start":
      return { status: "parsing" };
    case "parse_success":
      return {
        status: action.extractedCount > 0 && action.missingCount === 0 ? "parsed_valid" : "parsed_partial",
      };
    case "parse_error":
      return { status: "parse_error", parseError: action.error };
    case "edit":
      if (state.status === "parsing" || state.status === "assessing" || state.status === "predicting") {
        return state;
      }
      return { status: "editing", result: undefined };
    case "assess_start":
      if (state.status === "parsing" || state.status === "predicting") {
        return state;
      }
      return { ...state, status: "assessing", readinessError: undefined, predictError: undefined };
    case "readiness_needs_more_signal":
      return { ...state, status: "needs_more_signal", readinessError: undefined };
    case "readiness_error":
      return { ...state, status: "readiness_error", readinessError: action.error };
    case "apply_readiness_answers":
      if (state.status !== "needs_more_signal") {
        return state;
      }
      return { ...state, status: "applying_answers" };
    case "readiness_answers_applied":
      return { status: "editing", result: undefined };
    case "predict_start":
      if (state.status === "parsing" || state.status === "assessing" || state.status === "applying_answers") {
        return state;
      }
      return { ...state, status: "predicting", predictError: undefined };
    case "predict_success":
      return { status: "predicted", result: action.result };
    case "predict_error":
      return { ...state, status: "predict_error", predictError: action.error };
  }
}
