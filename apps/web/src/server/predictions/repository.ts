import { and, desc, eq } from "drizzle-orm";

import { getDb } from "@/server/db/client";
import { type NewPredictionRow, type PredictionRow, predictions } from "@/server/db/schema";

export async function findPredictionByUserAndIdempotency(
  userId: string,
  idempotencyKey: string,
): Promise<PredictionRow | null> {
  const [row] = await getDb()
    .select()
    .from(predictions)
    .where(and(eq(predictions.userId, userId), eq(predictions.idempotencyKey, idempotencyKey)))
    .limit(1);

  return row ?? null;
}

export async function createPrediction(
  row: NewPredictionRow,
): Promise<{ row: PredictionRow; replayed: boolean }> {
  const [inserted] = await getDb()
    .insert(predictions)
    .values(row)
    .onConflictDoNothing({
      target: [predictions.userId, predictions.idempotencyKey],
    })
    .returning();

  if (inserted) {
    return { row: inserted, replayed: false };
  }

  const existing = await findPredictionByUserAndIdempotency(row.userId, row.idempotencyKey);
  if (!existing) {
    throw new Error("Prediction idempotency conflict could not be resolved.");
  }

  return { row: existing, replayed: true };
}

export async function listPredictionsForUser(userId: string): Promise<PredictionRow[]> {
  return getDb()
    .select()
    .from(predictions)
    .where(eq(predictions.userId, userId))
    .orderBy(desc(predictions.createdAt));
}

export async function getPredictionForUser(id: string, userId: string): Promise<PredictionRow | null> {
  const [row] = await getDb()
    .select()
    .from(predictions)
    .where(and(eq(predictions.id, id), eq(predictions.userId, userId)))
    .limit(1);

  return row ?? null;
}
