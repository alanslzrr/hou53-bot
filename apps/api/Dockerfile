# syntax=docker/dockerfile:1.10
#
# HOU53-bot inference API — multi-stage build.
#
# Why two stages?
#   - "builder" installs uv + the Python deps. It is fat (build tools,
#     compiler caches, sometimes a libomp).
#   - "runtime" copies just the venv and the source. Final image is
#     ~600 MB instead of ~1.5 GB.
#
# Why uv?
#   - Resolves and installs in seconds, not minutes.
#   - Reproducible from the committed uv.lock at the repo root.
#
# Why we copy ml/ AND apps/api/:
#   - The API imports ``hou53_ml`` at runtime (input schema, SHAP
#     wrapper, constants). Both packages are workspace members.
#
# The trained artifact (``models/hou53-pipeline.joblib`` + sidecar
# JSON) is mounted at runtime via ``docker compose`` rather than baked
# in — that way model retrains do not require image rebuilds.

# -----------------------------------------------------------------------------
# Stage 1 — builder
# -----------------------------------------------------------------------------
ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# OpenMP runtime for XGBoost on Linux (Debian slim).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (single static binary).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /repo

# Resolve from the lockfile FIRST (cache-friendly: the lockfile changes
# rarely, the source changes constantly). We copy only the manifests so
# the layer cache hits as long as deps did not change.
COPY pyproject.toml uv.lock ./
COPY ml/pyproject.toml ml/
COPY apps/api/pyproject.toml apps/api/

# Install runtime deps only (no dev / ml-tooling groups).
# ``--no-install-project`` skips installing our workspace members; we
# install them explicitly after their source is copied.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-group ml-tooling

# Copy package source and install both workspace members editable.
COPY ml/src ml/src
COPY ml/README.md ml/README.md
COPY apps/api/src apps/api/src
COPY apps/api/README.md apps/api/README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-group ml-tooling

# -----------------------------------------------------------------------------
# Stage 2 — runtime
# -----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/repo/.venv/bin:${PATH}" \
    HOU53_API_LOG_FORMAT=json

# OpenMP runtime needed by XGBoost.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 --shell /bin/bash app

WORKDIR /repo

# Copy the venv (immutable, prebuilt) and the source the venv points at
# (because uv sync installs workspace members editable). Owner = app.
COPY --from=builder --chown=app:app /repo/.venv /repo/.venv
COPY --from=builder --chown=app:app /repo/ml /repo/ml
COPY --from=builder --chown=app:app /repo/apps/api /repo/apps/api

USER app

EXPOSE 8000

# Lifespan checks for the artifact under ``${HOU53_API_REPO_ROOT}/models``
# (defaults to /repo/models). docker-compose mounts the host's models/
# directory there so retrains are picked up without rebuilding.

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
