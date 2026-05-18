import type { ParseErrorPayload } from "@/lib/nlp/types";
import type { PredictErrorResponse, PredictSuccessResponse } from "@/server/predict/types";

export type EstimateStatus =
  | "idle"
  | "parsing"
  | "parsed_partial"
  | "parsed_valid"
  | "editing"
  | "predicting"
  | "predicted"
  | "predict_error"
  | "parse_error";

export type EstimateState = {
  status: EstimateStatus;
  parseError?: ParseErrorPayload;
  predictError?: PredictErrorResponse["error"];
  result?: PredictSuccessResponse;
};

export type EstimateAction =
  | { type: "parse_start" }
  | { type: "parse_success"; extractedCount: number; missingCount: number }
  | { type: "parse_error"; error: ParseErrorPayload }
  | { type: "edit" }
  | { type: "predict_start" }
  | { type: "predict_success"; result: PredictSuccessResponse }
  | { type: "predict_error"; error: PredictErrorResponse["error"] };

export const initialEstimateState: EstimateState = {
  status: "idle",
};

export function estimateReducer(state: EstimateState, action: EstimateAction): EstimateState {
  switch (action.type) {
    case "parse_start":
      return { status: "parsing" };
    case "parse_success":
      return {
        status: action.extractedCount > 0 && action.missingCount === 0 ? "parsed_valid" : "parsed_partial",
      };
    case "parse_error":
      return { status: "parse_error", parseError: action.error };
    case "edit":
      if (state.status === "parsing" || state.status === "predicting") {
        return state;
      }
      return { status: "editing", result: undefined };
    case "predict_start":
      if (state.status === "parsing") {
        return state;
      }
      return { ...state, status: "predicting", predictError: undefined };
    case "predict_success":
      return { status: "predicted", result: action.result };
    case "predict_error":
      return { ...state, status: "predict_error", predictError: action.error };
  }
}
