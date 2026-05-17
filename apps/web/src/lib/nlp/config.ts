export type ParserConfig = {
  model: string;
  timeoutMs: number;
  maxInputChars: number;
  seed: number;
  maxOutputTokens: number;
  rateLimitRequests: number;
  rateLimitWindowMs: number;
};

type ParserEnv = Record<string, string | undefined>;

function readPositiveInteger(
  env: ParserEnv,
  key: string,
  fallback: number,
  minValue = 1,
): number {
  const raw = env[key];
  if (!raw) {
    return fallback;
  }

  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < minValue) {
    return fallback;
  }

  return parsed;
}

export function getParserConfig(env: ParserEnv = process.env): ParserConfig {
  return {
    model: env.HOU53_NLP_MODEL || "gpt-5.4-mini",
    timeoutMs: readPositiveInteger(env, "HOU53_NLP_TIMEOUT_MS", 15_000, 500),
    maxInputChars: readPositiveInteger(env, "HOU53_NLP_MAX_INPUT_CHARS", 2_000),
    seed: readPositiveInteger(env, "HOU53_NLP_SEED", 53, 0),
    maxOutputTokens: readPositiveInteger(env, "HOU53_NLP_MAX_OUTPUT_TOKENS", 1_600),
    rateLimitRequests: readPositiveInteger(env, "HOU53_NLP_RATE_LIMIT_REQUESTS", 20),
    rateLimitWindowMs: readPositiveInteger(env, "HOU53_NLP_RATE_LIMIT_WINDOW_MS", 60_000, 1_000),
  };
}
