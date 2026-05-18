import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDb } from "@/server/db/client";

import { getPredictionForUser, listPredictionsForUser } from "./repository";

vi.mock("@/server/db/client", () => ({
  getDb: vi.fn(),
}));

vi.mock("drizzle-orm", () => ({
  and: vi.fn((...conditions: unknown[]) => ({ type: "and", conditions })),
  desc: vi.fn((column: unknown) => ({ type: "desc", column })),
  eq: vi.fn((column: unknown, value: unknown) => ({ type: "eq", column, value })),
}));

const mockedGetDb = vi.mocked(getDb);

describe("prediction repository", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("filters list queries by user id", async () => {
    const where = vi.fn(() => ({ orderBy: vi.fn(() => Promise.resolve([])) }));
    mockedGetDb.mockReturnValue({
      select: () => ({
        from: () => ({ where }),
      }),
    } as never);

    await listPredictionsForUser("user-1");

    expect(where).toHaveBeenCalledWith(expect.objectContaining({ value: "user-1" }));
  });

  it("filters detail queries by prediction id and user id", async () => {
    const limit = vi.fn(() => Promise.resolve([]));
    const where = vi.fn(() => ({ limit }));
    mockedGetDb.mockReturnValue({
      select: () => ({
        from: () => ({ where }),
      }),
    } as never);

    await getPredictionForUser("prediction-1", "user-1");

    expect(where).toHaveBeenCalledWith(
      expect.objectContaining({
        conditions: expect.arrayContaining([
          expect.objectContaining({ value: "prediction-1" }),
          expect.objectContaining({ value: "user-1" }),
        ]),
      }),
    );
  });
});
