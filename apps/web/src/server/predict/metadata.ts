import { z } from "zod";

export const readinessMetadataSchema = z
  .object({
    score: z.number().int().min(0).max(100),
    level: z.enum(["sparse", "usable", "strong"]),
    missing_signal_groups: z.array(z.string()),
    answered_question_ids: z.array(z.string()),
  })
  .strip();

export const predictionParseMetadataSchema = z
  .object({
    parse_request_id: z.string().optional(),
    model: z.string().optional(),
    guessed_fields: z.array(z.string()).optional(),
    missing_fields: z.array(z.string()).optional(),
    field_confidence: z.record(z.string(), z.number()).optional(),
    clarification_questions: z.array(z.string()).optional(),
    readiness: readinessMetadataSchema.optional(),
  })
  .strip();
