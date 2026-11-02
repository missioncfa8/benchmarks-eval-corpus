FROM python:3.12-slim

# Hugging Face Spaces runs as user 1000
RUN useradd -m -u 1000 user

WORKDIR /app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=7860 \
    HF_REPO=aman29/benchmarks-eval-corpus \
    DUCKDB_MEMORY_LIMIT=10GB \
    DUCKDB_THREADS=4

EXPOSE 7860

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860} --log-level info"]
