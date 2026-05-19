import { describe, expect, it } from "vitest";

import { shouldAuthenticateApiRequest } from "./authenticated-cloud-run-fetch";

describe("shouldAuthenticateApiRequest", () => {
  it("does not authenticate local or docker-style API URLs in auto mode", () => {
    expect(shouldAuthenticateApiRequest(new URL("http://localhost:8000"), "auto")).toBe(false);
    expect(shouldAuthenticateApiRequest(new URL("http://127.0.0.1:8000"), "auto")).toBe(false);
    expect(shouldAuthenticateApiRequest(new URL("http://api:8000"), "auto")).toBe(false);
  });

  it("authenticates Cloud Run URLs in auto mode", () => {
    expect(shouldAuthenticateApiRequest(new URL("https://hou53-api-abc-uc.a.run.app"), "auto")).toBe(true);
  });

  it("supports explicit auth mode overrides", () => {
    expect(shouldAuthenticateApiRequest(new URL("https://api.example.com"), "google")).toBe(true);
    expect(shouldAuthenticateApiRequest(new URL("https://hou53-api-abc-uc.a.run.app"), "none")).toBe(false);
  });
});
