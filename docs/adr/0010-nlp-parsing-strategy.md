# ADR-0010: LLM with structured output for natural-language input

- **Status:** proposed
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
   the Pydantic schema).
4. **Hybrid** — regex for "easy" fields (numbers, dates), LLM for the rest.

## Decision Outcome

Chosen option: **LLM with structured output** using the Vercel AI SDK's
`generateObject` (or equivalent), because it is the only option that
naturally handles the full field space in unconstrained English, produces
validated JSON by construction, and scales to new fields without new code.

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
  Mitigated by `temperature=0` and by showing the parsed values to the
  user for confirmation before sending to `/predict`.
- Cost per request, however small, is nonzero. Mitigated by (a) choosing a
  small/cheap model (Haiku or 4o-mini class), (b) caching prompts on the
  provider side, (c) debouncing the "parse" button so we do not fire on
  every keystroke.
- External dependency on an LLM provider. Mitigated by the AI SDK's
  provider abstraction — the model is a config value, not a hard
  dependency.

### Operational guardrails

- The LLM is called from a Next.js Route Handler, not from the browser.
  Keys never leave the server.
- Input length is capped (e.g., 2,000 chars) server-side to bound cost.
- Rate limiting per authenticated user (basic, via middleware).
- The response goes back to the **user's form** for confirmation, not
  directly to the prediction API. The user is always in the loop.

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

## Links

- [Vercel AI SDK — `generateObject`](https://sdk.vercel.ai/docs/reference/ai-sdk-core/generate-object)
- [ADR-0008 — FastAPI](./0008-api-framework-fastapi.md)
- [ADR-0009 — Frontend stack](./0009-frontend-stack.md)
