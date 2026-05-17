# Architecture

High-level view of the system. Details of each component live in their
respective ADRs — see [`docs/adr/`](./adr/README.md).

## System diagram

```mermaid
flowchart LR
    subgraph User
      U[Browser]
    end

    subgraph Web[Next.js app · apps/web]
      UI[React UI]
      NLP[/NLP route handler/]
      AUTH[/NextAuth/]
    end

    subgraph API[FastAPI · apps/api]
      R[HTTP routers]
      S[Services]
      D[Domain]
      I[Infra]
    end

    subgraph ML[Offline · ml/]
      DVC[(DVC remote:<br/>data + models)]
      MLflow[(MLflow runs)]
      TRAIN[Training pipeline]
    end

    subgraph DB[(Neon Postgres)]
      USERS[users]
      PRED[predictions]
      FDBK[feedback]
      MV[model_versions]
    end

    subgraph LLM[LLM provider]
      L[Cheap model · temperature=0]
    end

    U -- form input / free text --> UI
    UI -- free text --> NLP
    NLP -- prompt --> L
    L -- structured JSON --> NLP
    NLP -- validated features --> UI
    UI -- POST /v1/predict --> R
    R --> S --> D
    S --> I
    I -- load once at startup --> MODEL[hou53-pipeline.joblib]
    MODEL -.artifact.-> DVC
    TRAIN -- logs --> MLflow
    TRAIN -- produces --> MODEL
    AUTH <--> USERS
    S --> PRED
    UI <--> DB
```

## Service boundaries

| Concern | Owner | Why it lives there |
|---|---|---|
| HTML/CSS/JS served to the browser | `apps/web` | Next.js runtime |
| Calling the LLM for NLP parsing | `apps/web` route handler | The LLM key must never reach the browser; putting the call in Python would mean a second network hop and a second secret to manage |
| Validating structured features | Both sides (`zod` on web, Pydantic on API) | Defense in depth; both schemas come from a single OpenAPI source of truth |
| Running the ML pipeline | `apps/api` | Single place where the serialized pipeline is loaded |
| SHAP computation | `apps/api` | Needs the model and the background dataset; returning SHAP values with the prediction keeps one round trip |
| User data (auth, history) | `apps/web` via Drizzle → Neon | Auth is a frontend concern; the Python API stays stateless |
| Training | `ml/` | Offline, not deployed |
| Experiment metadata | MLflow (local file backend) | Lives in `mlruns/`, gitignored |
| Data and model artifacts | DVC remote | Binary blobs, content-hashed |

## Data flow for a single prediction

1. User submits the form (or free text → LLM → form → confirms).
2. Next.js route handler `POST /v1/predict` to the FastAPI API with the
   validated feature payload.
3. API service layer receives the request, loads the cached pipeline
   (loaded once at startup), runs `predict`, and asks the SHAP wrapper
   for per-feature contributions.
4. API returns `{ prediction, confidence_interval, top_features[] }`.
5. Next.js stores the prediction + a denormalized `model_version` in
   Postgres, displays the result and the SHAP waterfall, and attaches it
   to the user's history.

## Cross-cutting rules

- **Clean Architecture boundaries** inside the API: `api → services →
  domain`. `infra` is behind protocols. The domain never imports FastAPI
  or sklearn — it only sees interfaces.
- **Single source of truth for the input schema.** Pydantic models in
  `hou53_ml` define the schema; FastAPI derives OpenAPI from them;
  `openapi-zod-client` generates the web-side zod schema at build time.
  Any drift breaks the build.
- **Reproducibility from a commit.** Git pins code, dependencies, and the
  small challenge source dataset; DVC pins model artifacts via `.dvc`
  files. `dvc pull` returns the exact model binaries once the environment
  has a configured remote.
- **Observability from day one.** Structured logs, request IDs, and a
  prediction-latency histogram ship with the API. We would rather have
  noisy logs early than scramble to add them under incident pressure.

## What will change later (known unknowns)

- **Confidence intervals.** Currently open between (a) bootstrapping the
  XGBoost predictions and (b) using a quantile regression forest as a
  side-car. Pick one in an ADR before merging the API.
- **Model registry.** For the challenge we ship one artifact at a time.
  If this grew into a product, we would move to a real registry and to
  MLflow's remote tracking backend.
- **Drift monitoring.** Evidently AI is a natural fit when we have a
  continuous data feed. Out of scope for the challenge but the hook is
  intentional.
