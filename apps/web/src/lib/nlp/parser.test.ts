import { generateText } from "ai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getParserConfig } from "./config";
import { parseHouseDescription } from "./parser";

vi.mock("@ai-sdk/openai", () => ({
  openai: {
    chat: vi.fn((modelId: string) => ({ provider: "openai-chat", modelId })),
  },
}));

vi.mock("ai", () => ({
  Output: {
    object: vi.fn((value: unknown) => value),
  },
  generateText: vi.fn(),
}));

const mockedGenerateText = vi.mocked(generateText);

describe("parseHouseDescription", () => {
  beforeEach(() => {
    mockedGenerateText.mockReset();
  });

  it("returns normalized parsed fields with human confirmation required", async () => {
    mockedGenerateText.mockResolvedValueOnce({
      output: {
        partial_fields: {
          BedroomAbvGr: 3,
          GarageCars: 2,
          "1stFlrSF": null,
          invented_feature: "ignored",
        },
        guessed_fields: ["GarageCars", "LotArea"],
        missing_fields: ["LotArea", "BedroomAbvGr"],
        field_confidence: { BedroomAbvGr: 0.95, GarageCars: 0.7, LotArea: 0.2 },
        clarification_questions: ["What is the lot size?"],
      },
    } as Awaited<ReturnType<typeof generateText>>);

    const response = await parseHouseDescription({
      description: "Three bedrooms with a two-car garage.",
      requestId: "req-1",
      config: getParserConfig({ HOU53_NLP_MODEL: "test-model" }),
    });

    expect(response).toMatchObject({
      ok: true,
      request_id: "req-1",
      model: "test-model",
      parsed_fields: { BedroomAbvGr: 3, GarageCars: 2 },
      guessed_fields: ["GarageCars"],
      missing_fields: ["LotArea"],
      field_confidence: { BedroomAbvGr: 0.95, GarageCars: 0.7 },
      clarification_questions: ["What is the lot size?"],
      needs_confirmation: true,
    });
    expect(mockedGenerateText).toHaveBeenCalledWith(
      expect.objectContaining({
        model: { provider: "openai-chat", modelId: "test-model" },
        seed: 53,
        maxRetries: 0,
        providerOptions: {
          openai: {
            store: false,
            strictJsonSchema: false,
          },
        },
        timeout: { totalMs: 15_000 },
      }),
    );
  });

  it("turns provider failures into data instead of throwing", async () => {
    mockedGenerateText.mockRejectedValueOnce(new Error("provider unavailable"));

    const response = await parseHouseDescription({
      description: "Two bedrooms.",
      requestId: "req-2",
      config: getParserConfig({ HOU53_NLP_MODEL: "test-model" }),
    });

    expect(response).toMatchObject({
      ok: false,
      request_id: "req-2",
      model: "test-model",
      error: { code: "parse_failed", message: "provider unavailable" },
      partial_fields: {},
      needs_manual_entry: true,
    });
  });

  it("classifies aborts and timeouts separately", async () => {
    mockedGenerateText.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));

    const response = await parseHouseDescription({
      description: "Two bedrooms.",
      requestId: "req-3",
      config: getParserConfig({ HOU53_NLP_MODEL: "test-model" }),
    });

    expect(response).toMatchObject({
      ok: false,
      error: { code: "parse_timeout" },
    });
  });
});
