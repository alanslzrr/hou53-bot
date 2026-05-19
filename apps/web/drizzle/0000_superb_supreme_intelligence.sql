CREATE TABLE "predictions" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" text NOT NULL,
	"input_jsonb" jsonb NOT NULL,
	"input_source" text NOT NULL,
	"parse_metadata_jsonb" jsonb,
	"predicted_price_usd_cents" integer NOT NULL,
	"model_version" text NOT NULL,
	"api_request_id" text NOT NULL,
	"result_jsonb" jsonb NOT NULL,
	"shap_jsonb" jsonb NOT NULL,
	"idempotency_key" text NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "predictions_user_created_idx" ON "predictions" USING btree ("user_id","created_at" DESC NULLS LAST);--> statement-breakpoint
CREATE UNIQUE INDEX "predictions_user_idempotency_idx" ON "predictions" USING btree ("user_id","idempotency_key");