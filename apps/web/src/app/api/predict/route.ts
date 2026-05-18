import { NextResponse } from "next/server";
import { z } from "zod";

import { auth } from "@/auth";
import { houseFieldsSchema, type HouseFields } from "@/lib/housing/schema";
import { createPrediction, findPredictionByUserAndIdempotency } from "@/server/predictions/repository";
import { PredictClientError, predictWithFastApi } from "@/server/predict/client";
import type { PredictErrorResponse, PredictSuccessResponse } from "@/server/predict/types";
import type { PredictionRow } from "@/server/db/schema";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const parseMetadataSchema = z
  .object({
    parse_request_id: z.string().optional(),
    model: z.string().optional(),
    guessed_fields: z.array(z.string()).optional(),
    missing_fields: z.array(z.string()).optional(),
    field_confidence: z.record(z.string(), z.number()).optional(),
    clarification_questions: z.array(z.string()).optional(),
  })
  .strip();

const requestSchema = z.object({
  fields: houseFieldsSchema,
  input_source: z.enum(["manual", "nlp", "mixed"]),
  parse_metadata: parseMetadataSchema.optional(),
  idempotency_key: z.string().min(8).max(128),
});

function requestIdFrom(request: Request): string {
  return request.headers.get("x-request-id") || crypto.randomUUID();
}

function hasMeaningfulFields(fields: HouseFields): boolean {
  return Object.values(fields).some((value) => value !== null && value !== undefined && value !== "");
}

function errorPayload(
  code: PredictErrorResponse["error"]["code"],
  message: string,
  requestId: string,
): PredictErrorResponse {
  return {
    ok: false,
    request_id: requestId,
    error: { code, message },
  };
}

function jsonResponse(payload: PredictSuccessResponse | PredictErrorResponse, status: number): NextResponse {
  return NextResponse.json(payload, {
    status,
    headers: {
      "x-request-id": "request_id" in payload ? payload.request_id : payload.api_request_id,
    },
  });
}

function rowToResponse(row: PredictionRow, options?: { replayed?: boolean }): PredictSuccessResponse {
  return {
    ok: true,
    prediction_id: row.id,
    ...row.resultJsonb,
    api_request_id: row.apiRequestId,
    saved: true,
    created_at: row.createdAt.toISOString(),
    replayed: options?.replayed || undefined,
  };
}

export async function POST(request: Request): Promise<NextResponse> {
  const requestId = requestIdFrom(request);
  const session = await auth();
  const userId = session?.user?.id;

  if (!userId) {
    return jsonResponse(errorPayload("unauthorized", "Authentication is required.", requestId), 401);
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(errorPayload("invalid_request", "Request body must be valid JSON.", requestId), 400);
  }

  const parsed = requestSchema.safeParse(body);
  if (!parsed.success) {
    return jsonResponse(errorPayload("invalid_request", "Prediction request does not match the expected schema.", requestId), 400);
  }

  const {
    input_source: inputSource,
    parse_metadata: parseMetadata,
    idempotency_key: idempotencyKey,
  } = parsed.data;
  const fields = parsed.data.fields as HouseFields;
  if (!hasMeaningfulFields(fields)) {
    return jsonResponse(errorPayload("invalid_request", "At least one house feature is required.", requestId), 400);
  }

  let persistenceWarning: string | undefined;
  try {
    const existing = await findPredictionByUserAndIdempotency(userId, idempotencyKey);
    if (existing) {
      return jsonResponse(rowToResponse(existing, { replayed: true }), 200);
    }
  } catch (error) {
    persistenceWarning = error instanceof Error ? error.message : "Prediction persistence is unavailable.";
  }

  try {
    const { payload, apiRequestId } = await predictWithFastApi(fields, requestId);
    const cents = Math.round(payload.prediction.value_usd * 100);

    try {
      const saved = await createPrediction({
        userId,
        inputJsonb: fields,
        inputSource,
        parseMetadataJsonb: parseMetadata ?? null,
        predictedPriceUsdCents: cents,
        modelVersion: payload.model.version,
        apiRequestId,
        resultJsonb: payload,
        shapJsonb: payload.explanation.top_features,
        idempotencyKey,
      });

      return jsonResponse(rowToResponse(saved.row, { replayed: saved.replayed }), 200);
    } catch (error) {
      const warning =
        persistenceWarning ||
        (error instanceof Error ? error.message : "Prediction was computed but could not be saved.");

      return jsonResponse(
        {
          ok: true,
          prediction_id: `unsaved-${requestId}`,
          ...payload,
          api_request_id: apiRequestId,
          saved: false,
          created_at: new Date().toISOString(),
          warning,
        },
        200,
      );
    }
  } catch (error) {
    if (error instanceof PredictClientError) {
      const status = error.code === "predict_failed" ? error.status || 502 : 504;
      return jsonResponse(errorPayload(error.code, error.message, requestId), status);
    }
    return jsonResponse(errorPayload("api_unavailable", "Prediction service is unavailable.", requestId), 502);
  }
}
