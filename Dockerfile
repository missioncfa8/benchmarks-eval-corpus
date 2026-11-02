FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_REPO=aman29/benchmarks-eval-corpus \
    DUCKDB_MEMORY_LIMIT=450MB \
    DUCKDB_THREADS=2

WORKDIR /app

# ─── Dependencies ────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Application code ────────────────────────────────────────────────
COPY . .

# ─── Expose & run ────────────────────────────────────────────────────
# Render injects $PORT (default 10000 on free tier)
EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info"]
