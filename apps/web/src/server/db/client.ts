import { neon } from "@neondatabase/serverless";
import { drizzle, type NeonHttpDatabase } from "drizzle-orm/neon-http";

import * as schema from "./schema";

let db: NeonHttpDatabase<typeof schema> | null = null;

export function getDb(): NeonHttpDatabase<typeof schema> {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required for prediction persistence.");
  }

  if (!db) {
    db = drizzle(neon(databaseUrl), { schema });
  }

  return db;
}

export function resetDbForTests(): void {
  db = null;
}
