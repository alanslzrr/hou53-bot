import bcrypt from "bcryptjs";
import { afterEach, describe, expect, it } from "vitest";

import { authorizeDemoUser } from "./server/auth/credentials";

const ENV_KEYS = ["HOU53_AUTH_EMAIL", "HOU53_AUTH_PASSWORD_HASH", "HOU53_AUTH_DISPLAY_NAME"] as const;

describe("authorizeDemoUser", () => {
  afterEach(() => {
    for (const key of ENV_KEYS) {
      delete process.env[key];
    }
  });

  it("accepts the configured demo user", async () => {
    process.env.HOU53_AUTH_EMAIL = "demo@hou53.local";
    process.env.HOU53_AUTH_DISPLAY_NAME = "Demo User";
    process.env.HOU53_AUTH_PASSWORD_HASH = await bcrypt.hash("correct-password", 4);

    await expect(
      authorizeDemoUser({
        email: "DEMO@hou53.local",
        password: "correct-password",
      }),
    ).resolves.toMatchObject({
      id: "demo@hou53.local",
      email: "demo@hou53.local",
      name: "Demo User",
    });
  });

  it("rejects invalid credentials", async () => {
    process.env.HOU53_AUTH_EMAIL = "demo@hou53.local";
    process.env.HOU53_AUTH_PASSWORD_HASH = await bcrypt.hash("correct-password", 4);

    await expect(
      authorizeDemoUser({
        email: "demo@hou53.local",
        password: "wrong-password",
      }),
    ).resolves.toBeNull();
  });
});
