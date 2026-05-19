import { z } from "zod";

import type { HouseFields } from "@/lib/housing/schema";
import { authenticatedCloudRunFetch } from "@/server/gcp/authenticated-cloud-run-fetch";
import type { PredictionApiPayload } from "@/server/predict/types";

const featureContributionSchema = z.object({
  feature: z.string(),
  shap_value: z.number(),
  contribution_usd: z.number(),
  direction: z.enum(["up", "down"]),
});

const predictionApiPayloadSchema = z.object({
  prediction: z.object({
    value_usd: z.number(),
    currency: z.literal("USD"),
  }),
  explanation: z.object({
    baseline_usd: z.number(),
    natural_language: z.string(),
    top_features: z.array(featureContributionSchema),
  }),
  model: z.object({
    name: z.string(),
    version: z.string(),
    trained_at_utc: z.string(),
  }),
});

function timeoutMs(): number {
  const raw = Number.parseInt(process.env.HOU53_API_TIMEOUT_MS ?? "10000", 10);
  return Number.isFinite(raw) && raw > 0 ? raw : 10_000;
}

export class PredictClientError extends Error {
  constructor(
    message: string,
    readonly code: "predict_failed" | "predict_timeout" | "api_unavailable",
    readonly status?: number,
  ) {
    super(message);
    this.name = "PredictClientError";
  }
}

export async function predictWithFastApi(
  fields: HouseFields,
  requestId: string,
): Promise<{ payload: PredictionApiPayload; apiRequestId: string }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs());

  try {
    const response = await authenticatedCloudRunFetch("/v1/predict", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-request-id": requestId,
      },
      body: JSON.stringify(fields),
      signal: controller.signal,
    });

    const apiRequestId = response.headers.get("x-request-id") || requestId;
    const body: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      const detail =
        body && typeof body === "object" && "detail" in body ? String(body.detail) : "Prediction failed.";
      throw new PredictClientError(detail, "predict_failed", response.status);
    }

    return {
      payload: predictionApiPayloadSchema.parse(body),
      apiRequestId,
    };
  } catch (error) {
    if (error instanceof PredictClientError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new PredictClientError("FastAPI prediction timed out.", "predict_timeout");
    }
    if (error instanceof Error && /abort|timeout/i.test(`${error.name} ${error.message}`)) {
      throw new PredictClientError("FastAPI prediction timed out.", "predict_timeout");
    }
    throw new PredictClientError("FastAPI prediction service is unavailable.", "api_unavailable");
  } finally {
    clearTimeout(timeout);
  }
}
