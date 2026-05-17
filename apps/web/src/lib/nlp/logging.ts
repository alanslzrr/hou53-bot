import type { ParseErrorCode } from "./types";

export type ParseLogEvent = {
  request_id: string;
  model?: string;
  latency_ms: number;
  n_chars_in: number;
  n_fields_extracted: number;
  error?: ParseErrorCode;
};

export function logParseEvent(event: ParseLogEvent): void {
  console.info(
    JSON.stringify({
      event: "nlp_parse",
      ...event,
    }),
  );
}
