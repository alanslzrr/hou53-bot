# `apps/api/` — FastAPI inference service

Placeholder; implemented in **Phase 4**.

Planned layout (see [ADR-0008](../../docs/adr/0008-api-framework-fastapi.md)):

```
apps/api/
├── src/app/
│   ├── api/          # HTTP adapters (routers, DTOs)
│   ├── domain/       # pure business logic, no FastAPI imports
│   ├── services/     # orchestration
│   ├── infra/        # model loader, DB, logging, metrics
│   └── main.py       # app factory + lifespan
├── tests/
├── Dockerfile
└── pyproject.toml
```
