FROM python:3.12-slim

# Create non-root application user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

# Default Environment
ENV PORT=8000 \
    HOST=0.0.0.0 \
    HF_REPO=aman29/benchmarks-eval-corpus \
    HF_TOKEN="" \
    DUCKDB_MEMORY_LIMIT=2GB \
    DUCKDB_THREADS=4

EXPOSE 8000

CMD ["python", "main.py"]
