# ADR-0010: LLM with structured output for natural-language input

- **Status:** accepted
- **Date:** 2026-04-21
- **Deciders:** Alan Salazar

## Context and Problem Statement

The challenge requires a natural-language interface: the user types
something like *"A 3-bedroom house in Ames, 1,800 sqft, built in 1995 with
a two-car garage"* and the system extracts structured features to feed the
model. The input is free-form; the output schema has 79 possible fields.

## Decision Drivers

- The output must validate against the same Pydantic schema the API
  already accepts — otherwise we would maintain two schemas.
- Failure modes must be explicit: the user must see which fields were
  parsed, which were guessed, and which are missing.
- We cannot afford to hand-write rules for 79 fields with many synonyms.
- The LLM call must be fast enough to feel interactive (< ~2 s target) and
  cheap enough to be acceptable (~fractions of a cent per parse).

## Considered Options

1. **Rule-based parser** (regex + keyword lists) per field.
2. **Named-entity recognition** (spaCy + custom entity types).
3. **LLM with structured output** (tool calling / `generateObject` against
   the Pydantic schema). Single-shot: text in → validated JSON out.
4. **Hybrid** — regex for "easy" fields (numbers, dates), LLM for the rest.
5. **Multi-turn agent with tools** — instead of one structured-output
   call, an agent loop where the LLM can call tools like
   `validate_neighborhood(name)`, `suggest_neighborhood_by_landmark(...)`,
   `get_quality_scale(column)` to disambiguate the input before
   committing to a JSON shape.
6. **Retrieval-augmented few-shot prompting** — embed a corpus of past
   ``(text → JSON)`` examples; for each new request, retrieve the top-K
   most similar examples (BM25 + dense + RRF + reranker) and include
   them in the prompt as in-context demonstrations.

## Decision Outcome

Chosen option: **LLM with structured output** (Option 3), using AI SDK
structured output with the direct OpenAI provider. In AI SDK v6 this is
implemented with `generateText` + `Output.object`; older SDK docs called
the same pattern `generateObject`. Billing and credentials are OpenAI-owned
through `OPENAI_API_KEY`. It is the only option that naturally handles the
full field space in unconstrained English, produces validated JSON by
construction, and scales to new fields without new code.

Options 5 and 6 are more powerful but resolve problems v1 may not
have. Both are recorded under "Future improvements" below — when
quality evidence demands them, not before. v1 priority is a parser
that works end-to-end with a measurable accuracy floor; richer
architectures come after that floor is reached and the evaluation
loop says single-shot is the bottleneck.

### Positive Consequences

- One source of truth for the input schema (Pydantic on the API, zod on
  the frontend, both generated from the same spec).
- The LLM returns *either* a validated object *or* an error — no "half
  parsed" state.
- Adding a new field requires no parser changes — only a schema update
  and maybe a line in the system prompt.
- We can make the model surface confidence per field ("I heard '3 bed'
  clearly; I am guessing at 'LotArea'") — great UX.

### Negative Consequences / Trade-offs

- Non-determinism: the same input may produce slightly different outputs.
  Mitigated by deterministic provider settings where supported and by
  showing the parsed values to the user for confirmation before sending
  to `/predict`.
- Cost per request, however small, is nonzero. Mitigated by (a) choosing a
  small/cheap model (Haiku or 4o-mini class), (b) caching prompts on the
  provider side, (c) debouncing the "parse" button so we do not fire on
  every keystroke.
- External dependency on an LLM provider. Mitigated by the AI SDK's
  provider abstraction — the model is a config value, but the v1 provider
  is OpenAI direct.

### Operational guardrails

Patterns adopted from agent-tooling practice:

- **Server-side call only.** The LLM is invoked from a Next.js Route
  Handler. Provider keys never reach the browser.
- **Bounded input.** Hard cap on input length (target: 2,000 chars)
  rejected with a 400 before the LLM call.
- **Bounded latency.** Explicit timeout on the LLM call. On timeout
  the API returns a structured `{ error, partial_fields: {} }` payload
  so the UI can fall back to manual form entry.
- **Bounded output.** The Pydantic schema is the contract; anything
  outside it is dropped (Pydantic ``extra="ignore"``).
- **Errors as data, not as exceptions.** Parse failure returns a
  structured response with the failure reason and any partially
  extracted fields, never a 500. The frontend renders the partial
  form and asks the user to complete it.
- **Per-user rate limit.** Middleware-level cap on parses per minute
  per authenticated user.
- **Deterministic settings.** Fixed `seed` when the provider supports it.
  `temperature=0` is used only for models that support it; OpenAI reasoning
  models such as `gpt-5.4-mini` reject temperature overrides.
- **Structured request logging.** Each parse logs
  ``{ request_id, model, latency_ms, n_chars_in, n_fields_extracted,
  error? }`` so quality regressions surface in dashboards, not in
  user complaints.
- **Human in the loop.** The response goes back to the user's form
  for confirmation. The prediction endpoint is never called by the
  parser directly. The user is always the one who hits "submit".

### Evaluation strategy

A parser without a measurable accuracy floor is a parser nobody
trusts. v1 ships with an evaluation harness, not just a prompt:

1. Sample N=100–200 rows from the real Ames Housing training set.
2. For each row, generate a synthetic natural-language description
   with a separate (offline, scripted) LLM call. Each description is
   2–3 sentences phrased the way a real user would type.
3. The pair ``(synthetic_text, original_row)`` becomes one eval
   example. The original row is the ground truth.
4. Run the parser on the synthetic text. Compare extracted fields to
   the original row:
   - Numeric fields: correct if within ±10 % (or ±1 for small counts).
   - Categorical fields: exact match.
   - Missing-from-output: counted as "not extracted" (neutral, not
     incorrect — the user can fill it in).
5. Headline metric: **per-field accuracy** = correctly extracted /
   (extracted attempts). Secondary metric: **coverage** = fields
   extracted / fields present in source.
6. CI gate: parser must hit a configurable accuracy floor (proposed
   ≥ 70 %) before a new prompt or model lands on `main`.

The eval set lives under ``ml/evals/nlp_parser/`` with the synthetic
descriptions checked in (deterministic from a fixed seed + the same
source rows) so CI can reproduce.

### Future improvements (i want to track but not implement yet)

These are architectures to revisit once the eval harness shows
single-shot ``generateObject`` is the bottleneck. None of them block
v1 shipping, So whe have this option:

- **Multi-turn agent with tools** (Option 5). Useful if the eval set
  shows the model misroutes indirect references — e.g., "near Iowa
  State" failing to resolve to `Neighborhood: "NAmes"`. A small set
  of read-only tools (`suggest_neighborhood_by_landmark`,
  `get_quality_scale`) lets the model ask for context before
  committing. Trade-off: multi-turn loops add latency, cost, and
  debugging surface.
- **Retrieval-augmented few-shot** (Option 6). Becomes viable once a
  corpus of confirmed ``(user_text, user_confirmed_json)`` pairs
  accumulates in production. Embed and index that corpus; on each
  new parse, retrieve the top-K most similar past pairs (sparse +
  dense + RRF + cross-encoder reranker) and include them as
  in-context examples. Largest expected lift on idiomatic phrasings
  and real-estate shorthand the base model handles poorly.
- **Both combined** (tools + few-shot) is a known production pattern
  for structured-extraction agents on schemas this wide.

Each future improvement gets its own ADR when proposed. The decision
to defer is itself the architectural choice: v1 focuses on the
working single-shot baseline plus the evaluation loop. Without the
eval loop, "improvements" are guesses.

## Pros and Cons of the Options

### Rule-based parser

- Good, because deterministic and debuggable.
- Bad, because synonyms and paraphrases explode the rule surface. "5-year-old
  house" vs. "built in 2021" vs. "construction date: 2021" all mean the
  same thing.
- Bad, because 79 fields × many phrasings = more code than the rest of the
  project.

### spaCy NER

- Good, because fast and local.
- Bad, because requires a labeled dataset we do not have.
- Bad, because even with labels, it struggles with implicit fields (e.g.,
  inferring `OverallQual` from "well maintained").

### LLM structured output

- Good, because it is exactly the shape of this problem.
- Bad, because external call, costs something, non-deterministic.
- These are manageable; the alternatives are not.

### Hybrid

- Good, because it minimizes LLM load.
- Bad, because it doubles the code surface — two parsers to maintain,
  two failure modes to reason about.
- Revisit only if cost/latency become real issues.

### Multi-turn agent with tools

- Good, because the model can resolve indirect or ambiguous
  references by querying small read-only tools instead of guessing.
- Good, because tool returns enforce domain constraints before the
  schema layer sees them.
- Bad, because every parse becomes a multi-turn loop. Latency, cost,
  and debugging difficulty scale with turn count.
- Bad, because most of what the tools would defend against
  (invalid quality values, unknown neighborhoods) is already caught
  by Pydantic validation on the single-shot output.
- Deferred to a future ADR when the eval loop justifies it.

### Retrieval-augmented few-shot

- Good, because in-context examples drawn from real past parses are
  the most reliable lever for handling idiomatic phrasing and
  domain shorthand the base model does not know.
- Good, because the retrieval stack composes cleanly with Option 3 —
  the few-shot examples sit in the prompt; the structured-output
  contract is unchanged.
- Bad, because it requires a corpus that does not yet exist (zero
  past parses at v1).
- Bad, because it adds an embedding pipeline + a vector index to
  infra (pgvector or equivalent) — non-trivial new infra for v1.
- Deferred to a future ADR once a meaningful corpus of confirmed
  parses has accumulated in production.

## Links

- [AI SDK — structured output](https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data)
- [ADR-0008 — FastAPI](./0008-api-framework-fastapi.md)
- [ADR-0009 — Frontend stack](./0009-frontend-stack.md)
