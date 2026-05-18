import { index, integer, jsonb, pgTable, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";

import type { HouseFields } from "@/lib/housing/schema";
import type { PredictionApiPayload } from "@/server/predict/types";

export type PredictionInputSource = "manual" | "nlp" | "mixed";

export type PredictionParseMetadata = {
  parse_request_id?: string;
  model?: string;
  guessed_fields?: string[];
  missing_fields?: string[];
  field_confidence?: Record<string, number>;
  clarification_questions?: string[];
};

export const predictions = pgTable(
  "predictions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: text("user_id").notNull(),
    inputJsonb: jsonb("input_jsonb").$type<HouseFields>().notNull(),
    inputSource: text("input_source").$type<PredictionInputSource>().notNull(),
    parseMetadataJsonb: jsonb("parse_metadata_jsonb").$type<PredictionParseMetadata | null>(),
    predictedPriceUsdCents: integer("predicted_price_usd_cents").notNull(),
    modelVersion: text("model_version").notNull(),
    apiRequestId: text("api_request_id").notNull(),
    resultJsonb: jsonb("result_jsonb").$type<PredictionApiPayload>().notNull(),
    shapJsonb: jsonb("shap_jsonb").$type<PredictionApiPayload["explanation"]["top_features"]>().notNull(),
    idempotencyKey: text("idempotency_key").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    index("predictions_user_created_idx").on(table.userId, table.createdAt.desc()),
    uniqueIndex("predictions_user_idempotency_idx").on(table.userId, table.idempotencyKey),
  ],
);

export type PredictionRow = typeof predictions.$inferSelect;
export type NewPredictionRow = typeof predictions.$inferInsert;
