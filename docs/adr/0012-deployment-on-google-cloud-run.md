# ADR-0012: Deployment on Google Cloud Run

- **Status:** accepted
- **Date:** 2026-05-18
- **Deciders:** Alan Salazar

## Context and Problem Statement

The challenge expects the system to be runnable end-to-end. I needed a
target where both services (FastAPI inference + Next.js BFF) could
live, talk to each other over HTTPS, scale to zero, and stay cheap or
free for a single-developer submission. The decision was less about
the perfect cloud and more about the one where I could move fastest
without learning a new platform on top of finishing the rest of the
project.

## Decision Drivers

- **Time budget.** The submission has a fixed scope. Spending two days
  learning a new cloud is two days not spent on EDA, modelling, or
  the frontend.
- **Two stateless services.** Both apps are containerised, single-
  process, request/response. Anything that runs containers behind
  HTTPS satisfies the technical requirement.
- **Service-to-service auth without inventing tokens.** The browser
  must not talk to FastAPI directly. The web service has to
  authenticate to the API; I did not want to ship a static API key.
- **Scale to zero.** This is a demo. It should not cost money while
  no one is using it.
- **Managed Postgres compatibility.** Neon (ADR-0003) needs egress
  from the web service.

## Considered Options

1. **Google Cloud Run** with Cloud Build for image build, IAM-based
   service-to-service auth, Cloud Logging by default.
2. **Fly.io.** Containers + global routing, generous free tier, simple
   CLI, popular with side projects.
3. **AWS Fargate / Lambda Container.** First-class, ubiquitous, but
   the cold-start story and the IAM ceremony are heavier than the
   alternatives for two stateless services.
4. **Render / Railway.** PaaS that abstracts the container plane.
   Lowest setup, highest vendor coupling.

## Decision Outcome

Chosen option: **Google Cloud Run**, primarily because I had recent
hands-on experience with GCP and could ship the deployment in hours
instead of days. The alternatives are technically fine for this
workload; the deciding factor was operational familiarity, not a
benchmark.

The capability profile that made this acceptable beyond familiarity:

- **IAM-based service-to-service auth out of the box.** The web
  service uses `google-auth-library` to mint short-lived ID tokens
  scoped to the API's Cloud Run audience. The API trusts Google's
  signature without any custom token-issuance code. Implementation
  lives in
  [`apps/web/src/server/gcp/authenticated-cloud-run-fetch.ts`](../../apps/web/src/server/gcp/authenticated-cloud-run-fetch.ts).
- **Cloud Build with substitutions** lets the image tag come from
  `_IMAGE` and keeps the YAML configs short
  ([`.gcp/cloudbuild-api.yaml`](../../.gcp/cloudbuild-api.yaml),
  [`.gcp/cloudbuild-web.yaml`](../../.gcp/cloudbuild-web.yaml)).
- **Cloud Logging** is automatic. structlog JSON lines land already
  parsed and filterable in the Cloud Run logs panel — no exporter to
  configure for v1.
- **Scale to zero** matches the demo budget: the services cost
  effectively nothing when idle.

### Positive consequences

- Two `gcloud builds submit` commands plus two `gcloud run deploy`
  commands ship the whole system.
- The browser never reaches FastAPI directly; the BFF mints an ID
  token per request, and the API is locked down to authenticated
  Cloud Run-to-Cloud Run traffic.
- The API image is immutable: model artifact, dataset, and data
  description are baked in
  ([`apps/api/Dockerfile.gcp`](../../apps/api/Dockerfile.gcp)). Cold
  starts land on a ready container.
- Same Postgres setup as the rest of the project — Neon is reachable
  from Cloud Run egress without VPC tricks.

### Negative consequences / trade-offs

- **Vendor lock-in on the auth mechanism.** Moving off GCP later means
  replacing the ID-token signing with whatever the next provider
  uses. The rest of the stack (FastAPI, Next.js, Postgres, Docker) is
  portable.
- **Cold starts.** Scale-to-zero means the first request after a quiet
  period pays a ~2-3 s cold-start tax. Acceptable for a demo. Cloud
  Run min-instances solves it for production.
- **Cloud Build minutes.** Not free past the daily quota for repeated
  iterations. Mitigated by caching layers in the Dockerfiles.

## Image layout

The API image bakes the artifact and dataset on purpose:

```
/repo/.venv                    # editable workspace install
/repo/ml/{src,README.md}
/repo/apps/api/{src,README.md}
/repo/models/hou53-pipeline.joblib
/repo/models/model_metadata.json
/repo/data/raw/house_prices.csv
/repo/data/external/data_description.txt
```

The trade-off is immutability vs. retrain cost: every retrain requires
a new image build. For a model that changes rarely, this is the right
side of the trade. The local `apps/api/Dockerfile` expects mounts
instead, so the docker-compose dev story does not pay this cost.

## Links

- [ADR-0003 — Database (Neon)](./0003-database-choice.md)
- [ADR-0008 — API framework (FastAPI)](./0008-api-framework-fastapi.md)
- [`.gcp/`](../../.gcp/) — Cloud Build configs
- [`apps/api/Dockerfile.gcp`](../../apps/api/Dockerfile.gcp)
- [`apps/web/Dockerfile.gcp`](../../apps/web/Dockerfile.gcp)
- [`apps/web/src/server/gcp/authenticated-cloud-run-fetch.ts`](../../apps/web/src/server/gcp/authenticated-cloud-run-fetch.ts)
