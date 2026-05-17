import { openai, type OpenAILanguageModelChatOptions } from "@ai-sdk/openai";
import { generateText, Output } from "ai";
import { ZodError } from "zod";

import {
  type HouseFeatureName,
  type HouseFieldValue,
  type LooseHouseFields,
  normalizeHouseFields,
  parserModelOutputSchema,
  uniqueFeatureNames,
} from "@/lib/housing/schema";

import type { ParserConfig } from "./config";
import { logParseEvent } from "./logging";
import { buildParserSystemPrompt, buildParserUserPrompt } from "./prompt";
import type { ParseErrorCode, ParseResponse } from "./types";

type ParseDescriptionInput = {
  description: string;
  requestId: string;
  config: ParserConfig;
};

function latencySince(startedAt: number): number {
  return Math.round(performance.now() - startedAt);
}

function isTimeoutError(error: unknown): boolean {
  if (error instanceof DOMException && error.name === "AbortError") {
    return true;
  }
  if (error instanceof Error) {
    return /abort|timeout|timed out/i.test(`${error.name} ${error.message}`);
  }
  return false;
}

function errorMessage(error: unknown): string {
  if (error instanceof ZodError) {
    return "The model returned fields that did not match the house input schema.";
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "The parser could not extract structured fields from the description.";
}

function filterConfidence(
  confidence: Partial<Record<HouseFeatureName, number>> | undefined,
  parsedFields: Partial<Record<HouseFeatureName, HouseFieldValue>>,
): Partial<Record<HouseFeatureName, number>> {
  const parsedNames = new Set(Object.keys(parsedFields));
  const filtered: Partial<Record<HouseFeatureName, number>> = {};

  for (const [name, value] of Object.entries(confidence ?? {})) {
    if (parsedNames.has(name)) {
      filtered[name] = value;
    }
  }

  return filtered;
}

function normalizeOutput(
  output: unknown,
): Pick<
  Extract<ParseResponse, { ok: true }>,
  "parsed_fields" | "guessed_fields" | "missing_fields" | "field_confidence" | "clarification_questions"
> {
  const parsedOutput = parserModelOutputSchema.parse(output);
  const parsedFields = normalizeHouseFields(parsedOutput.partial_fields as LooseHouseFields);
  const parsedFieldNames = new Set(Object.keys(parsedFields));
  const guessedFields = uniqueFeatureNames(parsedOutput.guessed_fields).filter((name) =>
    parsedFieldNames.has(name),
  );
  const missingFields = uniqueFeatureNames(parsedOutput.missing_fields).filter(
    (name) => !parsedFieldNames.has(name),
  );

  return {
    parsed_fields: parsedFields,
    guessed_fields: guessedFields,
    missing_fields: missingFields,
    field_confidence: filterConfidence(parsedOutput.field_confidence, parsedFields),
    clarification_questions: parsedOutput.clarification_questions ?? [],
  };
}

function errorCode(error: unknown): ParseErrorCode {
  return isTimeoutError(error) ? "parse_timeout" : "parse_failed";
}

export async function parseHouseDescription({
  description,
  requestId,
  config,
}: ParseDescriptionInput): Promise<ParseResponse> {
  const startedAt = performance.now();

  try {
    const { output } = await generateText({
      model: openai.chat(config.model),
      system: buildParserSystemPrompt(),
      prompt: buildParserUserPrompt(description),
      output: Output.object({
        schema: parserModelOutputSchema,
        name: "house_parse",
        description: "Structured Ames Housing fields extracted from natural language.",
      }),
      seed: config.seed,
      maxRetries: 0,
      maxOutputTokens: config.maxOutputTokens,
      providerOptions: {
        openai: {
          store: false,
          strictJsonSchema: false,
        } satisfies OpenAILanguageModelChatOptions,
      },
      timeout: { totalMs: config.timeoutMs },
    });

    const normalized = normalizeOutput(output);
    const latencyMs = latencySince(startedAt);

    logParseEvent({
      request_id: requestId,
      model: config.model,
      latency_ms: latencyMs,
      n_chars_in: description.length,
      n_fields_extracted: Object.keys(normalized.parsed_fields).length,
    });

    return {
      ok: true,
      request_id: requestId,
      model: config.model,
      ...normalized,
      needs_confirmation: true,
      latency_ms: latencyMs,
    };
  } catch (error) {
    const latencyMs = latencySince(startedAt);
    const code = errorCode(error);

    logParseEvent({
      request_id: requestId,
      model: config.model,
      latency_ms: latencyMs,
      n_chars_in: description.length,
      n_fields_extracted: 0,
      error: code,
    });

    return {
      ok: false,
      request_id: requestId,
      model: config.model,
      error: {
        code,
        message: errorMessage(error),
      },
      partial_fields: {},
      needs_manual_entry: true,
      latency_ms: latencyMs,
    };
  }
}
