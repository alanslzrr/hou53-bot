import type { ParserConfig } from "./config";

type Bucket = {
  count: number;
  resetAt: number;
};

const buckets = new Map<string, Bucket>();

export type RateLimitResult =
  | { allowed: true; remaining: number; resetAt: number }
  | { allowed: false; retryAfterSeconds: number; resetAt: number };

export function consumeRateLimit(
  identity: string,
  config: Pick<ParserConfig, "rateLimitRequests" | "rateLimitWindowMs">,
  nowMs = Date.now(),
): RateLimitResult {
  const existing = buckets.get(identity);

  if (!existing || existing.resetAt <= nowMs) {
    const resetAt = nowMs + config.rateLimitWindowMs;
    buckets.set(identity, { count: 1, resetAt });
    return {
      allowed: true,
      remaining: Math.max(config.rateLimitRequests - 1, 0),
      resetAt,
    };
  }

  if (existing.count >= config.rateLimitRequests) {
    return {
      allowed: false,
      retryAfterSeconds: Math.max(Math.ceil((existing.resetAt - nowMs) / 1_000), 1),
      resetAt: existing.resetAt,
    };
  }

  existing.count += 1;
  return {
    allowed: true,
    remaining: Math.max(config.rateLimitRequests - existing.count, 0),
    resetAt: existing.resetAt,
  };
}

export function resetRateLimitForTests(): void {
  buckets.clear();
}
