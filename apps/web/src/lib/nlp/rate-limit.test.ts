import { describe, expect, it } from "vitest";

import { consumeRateLimit, resetRateLimitForTests } from "./rate-limit";

describe("consumeRateLimit", () => {
  it("allows requests until the per-window limit is reached", () => {
    resetRateLimitForTests();
    const config = { rateLimitRequests: 2, rateLimitWindowMs: 60_000 };

    expect(consumeRateLimit("user:1", config, 1_000)).toMatchObject({
      allowed: true,
      remaining: 1,
    });
    expect(consumeRateLimit("user:1", config, 2_000)).toMatchObject({
      allowed: true,
      remaining: 0,
    });
    expect(consumeRateLimit("user:1", config, 3_000)).toMatchObject({
      allowed: false,
      retryAfterSeconds: 58,
    });
  });

  it("starts a new bucket after the window resets", () => {
    resetRateLimitForTests();
    const config = { rateLimitRequests: 1, rateLimitWindowMs: 1_000 };

    expect(consumeRateLimit("ip:local", config, 1_000).allowed).toBe(true);
    expect(consumeRateLimit("ip:local", config, 1_500).allowed).toBe(false);
    expect(consumeRateLimit("ip:local", config, 2_001).allowed).toBe(true);
  });
});
