import { beforeEach, describe, expect, it, vi } from "vitest";

import { auth } from "@/auth";
import { createPrediction, findPredictionByUserAndIdempotency } from "@/server/predictions/repository";
import { PredictClientError, predictWithFastApi } from "@/server/predict/client";

import { POST } from "./route";

vi.mock("@/auth", () => ({
  auth: vi.fn(),
}));

vi.mock("@/server/predictions/repository", () => ({
  createPrediction: vi.fn(),
  findPredictionByUserAndIdempotency: vi.fn(),
}));

vi.mock("@/server/predict/client", () => ({
  PredictClientError: class PredictClientError extends Error {
    constructor(
      message: string,
      readonly code: "predict_failed" | "predict_timeout" | "api_unavailable",
      readonly status?: number,
    ) {
      super(message);
    }
  },
  predictWithFastApi: vi.fn(),
}));

type TestSession = { user: { id: string; email: string }; expires: string };
const mockedAuth = vi.mocked(auth as unknown as () => Promise<TestSession | null>);
const mockedFindPredictionByUserAndIdempotency = vi.mocked(findPredictionByUserAndIdempotency);
const mockedCreatePrediction = vi.mocked(createPrediction);
const mockedPredictWithFastApi = vi.mocked(predictWithFastApi);

const apiPayload = {
  prediction: {
    value_usd: 250_000,
    currency: "USD" as const,
  },
  explanation: {
    baseline_usd: 180_000,
    natural_language: "Estimated price: $250,000.",
    top_features: [
      {
        feature: "OverallQual",
        shap_value: 0.3,
        contribution_usd: 45_000,
        direction: "up" as const,
      },
    ],
  },
  model: {
    name: "xgboost",
    version: "2026-05-17",
    trained_at_utc: "2026-05-17T00:00:00Z",
  },
};

function jsonRequest(body: unknown): Request {
  return new Request("http://localhost:3000/api/predict", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-request-id": "req-predict",
    },
    body: JSON.stringify(body),
  });
}

function predictionRow(overrides = {}) {
  return {
    id: "prediction-1",
    userId: "user-1",
    inputJsonb: { OverallQual: 8 },
    inputSource: "manual" as const,
    parseMetadataJsonb: null,
    predictedPriceUsdCents: 25_000_000,
    modelVersion: "2026-05-17",
    apiRequestId: "api-req",
    resultJsonb: apiPayload,
    shapJsonb: apiPayload.explanation.top_features,
    idempotencyKey: "idem-123",
    createdAt: new Date("2026-05-17T12:00:00Z"),
    ...overrides,
  };
}

describe("POST /api/predict", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedAuth.mockResolvedValue({
      user: { id: "user-1", email: "user@example.com" },
      expires: "2099-01-01T00:00:00.000Z",
    });
    mockedFindPredictionByUserAndIdempotency.mockResolvedValue(null);
    mockedPredictWithFastApi.mockResolvedValue({
      payload: apiPayload,
      apiRequestId: "api-req",
    });
    mockedCreatePrediction.mockResolvedValue({
      row: predictionRow(),
      replayed: false,
    });
  });

  it("rejects unauthenticated requests", async () => {
    mockedAuth.mockResolvedValueOnce(null);

    const response = await POST(jsonRequest({}));
    const payload = await response.json();

    expect(response.status).toBe(401);
    expect(payload).toMatchObject({ ok: false, error: { code: "unauthorized" } });
  });

  it("rejects invalid payloads", async () => {
    const response = await POST(jsonRequest({ fields: {}, input_source: "manual", idempotency_key: "short" }));
    const payload = await response.json();

    expect(response.status).toBe(400);
    expect(payload).toMatchObject({ ok: false, error: { code: "invalid_request" } });
    expect(mockedPredictWithFastApi).not.toHaveBeenCalled();
  });

  it("calls FastAPI and persists successful predictions", async () => {
    const response = await POST(
      jsonRequest({
        fields: { OverallQual: 8 },
        input_source: "manual",
        idempotency_key: "idem-123",
      }),
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(mockedPredictWithFastApi).toHaveBeenCalledWith({ OverallQual: 8 }, "req-predict");
    expect(mockedCreatePrediction).toHaveBeenCalledWith(expect.objectContaining({ userId: "user-1" }));
    expect(payload).toMatchObject({ ok: true, prediction_id: "prediction-1", saved: true });
  });

  it("returns existing rows on idempotency replay", async () => {
    mockedFindPredictionByUserAndIdempotency.mockResolvedValueOnce(predictionRow());

    const response = await POST(
      jsonRequest({
        fields: { OverallQual: 8 },
        input_source: "manual",
        idempotency_key: "idem-123",
      }),
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(mockedPredictWithFastApi).not.toHaveBeenCalled();
    expect(payload).toMatchObject({ ok: true, replayed: true, saved: true });
  });

  it("normalizes FastAPI validation failures", async () => {
    mockedPredictWithFastApi.mockRejectedValueOnce(new PredictClientError("Invalid feature.", "predict_failed", 422));

    const response = await POST(
      jsonRequest({
        fields: { OverallQual: 8 },
        input_source: "manual",
        idempotency_key: "idem-123",
      }),
    );
    const payload = await response.json();

    expect(response.status).toBe(422);
    expect(payload).toMatchObject({ ok: false, error: { code: "predict_failed" } });
  });

  it("returns a warning when persistence fails after prediction", async () => {
    mockedCreatePrediction.mockRejectedValueOnce(new Error("database offline"));

    const response = await POST(
      jsonRequest({
        fields: { OverallQual: 8 },
        input_source: "manual",
        idempotency_key: "idem-123",
      }),
    );
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toMatchObject({ ok: true, saved: false, warning: "database offline" });
  });
});
