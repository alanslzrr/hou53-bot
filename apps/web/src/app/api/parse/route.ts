import { NextResponse } from "next/server";
import { z } from "zod";

import { getParserConfig } from "@/lib/nlp/config";
import { consumeRateLimit } from "@/lib/nlp/rate-limit";
import { parseHouseDescription } from "@/lib/nlp/parser";
import type { ParseErrorCode, ParseErrorResponse, ParseResponse } from "@/lib/nlp/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const requestSchema = z.object({
  description: z.string(),
});

function requestIdFrom(request: Request): string {
  return request.headers.get("x-request-id") || crypto.randomUUID();
}

function identityFrom(request: Request): string {
  const userId = request.headers.get("x-user-id");
  if (userId) {
    return `user:${userId}`;
  }

  const forwardedFor = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const realIp = request.headers.get("x-real-ip");
  return `ip:${forwardedFor || realIp || "anonymous"}`;
}

function latencySince(startedAt: number): number {
  return Math.round(performance.now() - startedAt);
}

function errorPayload(
  code: ParseErrorCode,
  message: string,
  requestId: string,
  latencyMs: number,
): ParseErrorResponse {
  return {
    ok: false,
    request_id: requestId,
    error: { code, message },
    partial_fields: {},
    needs_manual_entry: true,
    latency_ms: latencyMs,
  };
}

function jsonResponse(payload: ParseResponse, status: number, headers?: HeadersInit): NextResponse {
  return NextResponse.json(payload, {
    status,
    headers: {
      "x-request-id": payload.request_id,
      ...headers,
    },
  });
}

export async function POST(request: Request): Promise<NextResponse> {
  const startedAt = performance.now();
  const requestId = requestIdFrom(request);
  const config = getParserConfig();
  const contentLength = Number.parseInt(request.headers.get("content-length") ?? "0", 10);

  if (Number.isFinite(contentLength) && contentLength > config.maxInputChars + 512) {
    return jsonResponse(
      errorPayload(
        "input_too_large",
        `Description must be ${config.maxInputChars} characters or fewer.`,
        requestId,
        latencySince(startedAt),
      ),
      400,
    );
  }

  const rateLimit = consumeRateLimit(identityFrom(request), config);
  if (!rateLimit.allowed) {
    return jsonResponse(
      errorPayload(
        "rate_limited",
        "Too many parse requests. Try again after the rate-limit window resets.",
        requestId,
        latencySince(startedAt),
      ),
      429,
      {
        "retry-after": String(rateLimit.retryAfterSeconds),
        "x-ratelimit-limit": String(config.rateLimitRequests),
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": String(rateLimit.resetAt),
      },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse(
      errorPayload("invalid_request", "Request body must be valid JSON.", requestId, latencySince(startedAt)),
      400,
    );
  }

  const parsed = requestSchema.safeParse(body);
  if (!parsed.success) {
    return jsonResponse(
      errorPayload(
        "invalid_request",
        "Request body must include a string description field.",
        requestId,
        latencySince(startedAt),
      ),
      400,
    );
  }

  const description = parsed.data.description.trim();
  if (description.length === 0) {
    return jsonResponse(
      errorPayload("invalid_request", "Description must not be empty.", requestId, latencySince(startedAt)),
      400,
    );
  }

  if (description.length > config.maxInputChars) {
    return jsonResponse(
      errorPayload(
        "input_too_large",
        `Description must be ${config.maxInputChars} characters or fewer.`,
        requestId,
        latencySince(startedAt),
      ),
      400,
    );
  }

  const result = await parseHouseDescription({
    description,
    requestId,
    config,
  });

  return jsonResponse(result, result.ok || result.error.code === "parse_failed" ? 200 : 504, {
    "x-ratelimit-limit": String(config.rateLimitRequests),
    "x-ratelimit-remaining": String(rateLimit.remaining),
    "x-ratelimit-reset": String(rateLimit.resetAt),
  });
}
