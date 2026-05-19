import { beforeEach, describe, expect, it, vi } from "vitest";

import { auth } from "@/auth";
import { buildReadinessQuestions } from "@/server/readiness/questions";

import { POST } from "./route";

vi.mock("@/auth", () => ({
  auth: vi.fn(),
}));

vi.mock("@/server/readiness/questions", () => ({
  buildReadinessQuestions: vi.fn(),
}));

type TestSession = { user: { id: string; email: string }; expires: string };
const mockedAuth = vi.mocked(auth as unknown as () => Promise<TestSession | null>);
const mockedBuildReadinessQuestions = vi.mocked(buildReadinessQuestions);

function jsonRequest(body: unknown): Request {
  return new Request("http://localhost:3000/api/estimate/readiness", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-request-id": "req-readiness",
    },
    body: JSON.stringify(body),
  });
}

describe("POST /api/estimate/readiness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedAuth.mockResolvedValue({
      user: { id: "user-1", email: "user@example.com" },
      expires: "2099-01-01T00:00:00.000Z",
    });
    mockedBuildReadinessQuestions.mockResolvedValue([
      {
        id: "q_gr_liv_area",
        label: "What is the approximate above-grade living area?",
        target_fields: ["GrLivArea"],
        priority: 1,
        quick_answers: ["1200", "1800", "2400"],
      },
    ]);
  });

  it("rejects unauthenticated requests", async () => {
    mockedAuth.mockResolvedValueOnce(null);

    const response = await POST(jsonRequest({ fields: { FullBath: 2 }, input_source: "manual" }));
    const payload = await response.json();

    expect(response.status).toBe(401);
    expect(payload).toMatchObject({ ok: false, error: { code: "unauthorized" } });
  });

  it("rejects invalid payloads", async () => {
    const response = await POST(jsonRequest({ fields: { OverallQual: 99 }, input_source: "manual" }));
    const payload = await response.json();

    expect(response.status).toBe(400);
    expect(payload).toMatchObject({ ok: false, error: { code: "invalid_request" } });
    expect(mockedBuildReadinessQuestions).not.toHaveBeenCalled();
  });

  it("returns questions for sparse input and preserves partial prediction", async () => {
    const response = await POST(jsonRequest({ fields: { BedroomAbvGr: 3, FullBath: 2 }, input_source: "nlp" }));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toMatchObject({
      ok: true,
      level: "sparse",
      can_predict_now: true,
      questions: [{ id: "q_gr_liv_area" }],
    });
  });

  it("returns no questions for strong input", async () => {
    mockedBuildReadinessQuestions.mockResolvedValueOnce([]);

    const response = await POST(
      jsonRequest({
        fields: {
          GrLivArea: 2400,
          OverallQual: 8,
          YearBuilt: 2005,
          Neighborhood: "StoneBr",
          GarageCars: 2,
          FullBath: 3,
        },
        input_source: "manual",
      }),
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toMatchObject({ ok: true, level: "strong", questions: [] });
  });
});
