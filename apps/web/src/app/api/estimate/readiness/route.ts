import { NextResponse } from "next/server";
import { z } from "zod";

import { auth } from "@/auth";
import { houseFieldsSchema, type HouseFields } from "@/lib/housing/schema";
import { assessPredictionReadiness } from "@/lib/readiness/scoring";
import type { ReadinessErrorResponse, ReadinessSuccessResponse } from "@/lib/readiness/types";
import { predictionParseMetadataSchema } from "@/server/predict/metadata";
import { buildReadinessQuestions } from "@/server/readiness/questions";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const requestSchema = z.object({
  fields: houseFieldsSchema,
  input_source: z.enum(["manual", "nlp", "mixed"]),
  parse_metadata: predictionParseMetadataSchema.optional(),
});

function requestIdFrom(request: Request): string {
  return request.headers.get("x-request-id") || crypto.randomUUID();
}

function errorPayload(
  code: ReadinessErrorResponse["error"]["code"],
  message: string,
  requestId: string,
): ReadinessErrorResponse {
  return {
    ok: false,
    request_id: requestId,
    error: { code, message },
  };
}

function jsonResponse(
  payload: ReadinessSuccessResponse | ReadinessErrorResponse,
  status: number,
  requestId: string,
): NextResponse {
  return NextResponse.json(payload, {
    status,
    headers: {
      "x-request-id": requestId,
    },
  });
}

export async function POST(request: Request): Promise<NextResponse> {
  const requestId = requestIdFrom(request);
  const session = await auth();
  const userId = session?.user?.id;

  if (!userId) {
    return jsonResponse(errorPayload("unauthorized", "Authentication is required.", requestId), 401, requestId);
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(errorPayload("invalid_request", "Request body must be valid JSON.", requestId), 400, requestId);
  }

  const parsed = requestSchema.safeParse(body);
  if (!parsed.success) {
    return jsonResponse(
      errorPayload("invalid_request", "Readiness request does not match the expected schema.", requestId),
      400,
      requestId,
    );
  }

  try {
    const fields = parsed.data.fields as HouseFields;
    const assessment = assessPredictionReadiness(fields);
    const questions = await buildReadinessQuestions({
      fields,
      assessment,
      parseMetadata: parsed.data.parse_metadata,
    });

    return jsonResponse(
      {
        ok: true,
        ...assessment,
        questions,
      },
      200,
      requestId,
    );
  } catch {
    return jsonResponse(
      errorPayload("readiness_failed", "Readiness assessment is unavailable.", requestId),
      500,
      requestId,
    );
  }
}
