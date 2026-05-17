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

To refresh the checked-in fixture:

```bash
uv run python ml/scripts/build_nlp_parser_eval_set.py
```
