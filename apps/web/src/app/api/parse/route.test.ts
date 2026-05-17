import { beforeEach, describe, expect, it, vi } from "vitest";

import { resetRateLimitForTests } from "@/lib/nlp/rate-limit";
import { parseHouseDescription } from "@/lib/nlp/parser";

import { POST } from "./route";

vi.mock("@/lib/nlp/parser", () => ({
  parseHouseDescription: vi.fn(),
}));

const mockedParseHouseDescription = vi.mocked(parseHouseDescription);

function jsonRequest(body: unknown, headers?: HeadersInit): Request {
  return new Request("http://localhost:3000/api/parse", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-request-id": "req-route",
      "x-user-id": "user-1",
      ...headers,
    },
    body: JSON.stringify(body),
  });
}

describe("POST /api/parse", () => {
  beforeEach(() => {
    resetRateLimitForTests();
    mockedParseHouseDescription.mockReset();
    delete process.env.HOU53_NLP_RATE_LIMIT_REQUESTS;
  });

  it("rejects invalid request bodies before invoking the parser", async () => {
    const response = await POST(jsonRequest({ description: "" }));
    const payload = await response.json();

    expect(response.status).toBe(400);
    expect(payload).toMatchObject({
      ok: false,
      request_id: "req-route",
      error: { code: "invalid_request" },
    });
    expect(mockedParseHouseDescription).not.toHaveBeenCalled();
  });

  it("enforces the bounded input guardrail before invoking the parser", async () => {
    const response = await POST(jsonRequest({ description: "x".repeat(2_001) }));
    const payload = await response.json();

    expect(response.status).toBe(400);
    expect(payload).toMatchObject({
      ok: false,
      error: { code: "input_too_large" },
    });
    expect(mockedParseHouseDescription).not.toHaveBeenCalled();
  });

  it("returns parser errors as structured data", async () => {
    mockedParseHouseDescription.mockResolvedValueOnce({
      ok: false,
      request_id: "req-route",
      model: "test/model",
      error: { code: "parse_failed", message: "bad model response" },
      partial_fields: {},
      needs_manual_entry: true,
      latency_ms: 3,
    });

    const response = await POST(jsonRequest({ description: "Three bedrooms." }));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toMatchObject({
      ok: false,
      error: { code: "parse_failed" },
      needs_manual_entry: true,
    });
  });

  it("rate-limits by user identity", async () => {
    process.env.HOU53_NLP_RATE_LIMIT_REQUESTS = "1";
    mockedParseHouseDescription.mockResolvedValue({
      ok: true,
      request_id: "req-route",
      model: "test/model",
      parsed_fields: {},
      guessed_fields: [],
      missing_fields: [],
      field_confidence: {},
      clarification_questions: [],
      needs_confirmation: true,
      latency_ms: 1,
    });

    const first = await POST(jsonRequest({ description: "Three bedrooms." }));
    const second = await POST(jsonRequest({ description: "Three bedrooms." }));
    const secondPayload = await second.json();

    expect(first.status).toBe(200);
    expect(second.status).toBe(429);
    expect(secondPayload).toMatchObject({
      ok: false,
      error: { code: "rate_limited" },
    });
  });
});
