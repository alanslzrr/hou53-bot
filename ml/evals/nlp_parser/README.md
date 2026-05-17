# NLP parser eval set

`examples.jsonl` contains 120 deterministic natural-language descriptions
rendered from real Ames Housing rows. Each line stores:

- `id` / `source_id`
- `description`
- `ground_truth` with the original 79 model input fields

The scoring harness treats missing parser output as neutral and scores only
extracted attempts:

```bash
uv run python -m hou53_ml.evaluation.nlp_parser \
  --examples ml/evals/nlp_parser/examples.jsonl \
  --endpoint http://localhost:3000/api/parse \
  --min-accuracy 0.70
```

## Baseline

`baseline-gpt-5.4-mini.json` records the first full real-provider run against
`gpt-5.4-mini` through the local Next.js `/api/parse` handler.

Whith this command we gonna make all the real test on the api (ussing openapikey)

```bash
HOU53_NLP_RATE_LIMIT_REQUESTS=500 HOU53_NLP_RATE_LIMIT_WINDOW_MS=60000 \
  pnpm --dir apps/web dev --hostname 127.0.0.1 --port 3000

uv run python -m hou53_ml.evaluation.nlp_parser \
  --examples ml/evals/nlp_parser/examples.jsonl \
  --endpoint http://127.0.0.1:3000/api/parse \
  --min-accuracy 0.70 \
  --timeout-seconds 25
```

Result:

- accuracy: `0.9938`
- coverage: `0.2898`
- attempted fields: `2740`
- correct fields: `2723`
- examples: `120`

To refresh the checked-in fixture:

```bash
uv run python ml/scripts/build_nlp_parser_eval_set.py
```
