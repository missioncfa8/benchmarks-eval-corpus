# Data Intelligence Portal (100% Free Tier Edition)

FastAPI + DuckDB personal OSINT search engine querying **~3.77 billion records / 431 Parquet chunks** directly from Hugging Face (`aman29/benchmarks-eval-corpus`).

- **Cost: $0/month** (runs on Render's Free Plan).
- **Disk Used: 0 GB** (no paid persistent disks, no local storage).
- **Search Latency: ~2.3 seconds** (DuckDB `httpfs` remote predicate pushdown).

---

## How It Works

DuckDB runs completely **in-memory** and queries the 431 Parquet chunks hosted on Hugging Face using HTTP range requests:
1. When you search for a phone, ID, name, or address, DuckDB reads only the metadata of the remote Parquet files.
2. DuckDB fetches only the exact row groups matching your query filter (predicate pushdown).
3. Results are returned to the web dashboard and JSON API in ~2 seconds.

---

## Deployment to Render.com (100% Free)

1. Push this folder to a **Private GitHub or GitLab** repository.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**.
3. Select your repository.
4. Set:
   - **Runtime**: `Docker`
   - **Instance Type**: **Free** ($0/mo)
   - **Health Check Path**: `/health`
5. Under **Environment Variables**, add:
   - `HF_TOKEN`: (Your Hugging Face Read token `hf_...` if dataset is private)
   - `HF_REPO`: `aman29/benchmarks-eval-corpus`
6. Click **Deploy Web Service**.

That's it! Render will build the Docker container and start your service for free.

---

## Local Development

```bash
# Set HF_TOKEN if dataset is private (optional)
export HF_TOKEN="hf_..."

# Run locally
docker compose up --build

# Open in browser: http://localhost:8000
```

---

## Search Syntax

| Query | Matches |
|---|---|
| `9810014045` | Exact mobile lookup |
| `name:rahul` | Name prefix search |
| `rahul sharma` | Name + father name search |
| `address:mumbai` | Address search |
| `id:1234567890` | Aadhaar / Gov ID lookup |
| `oid:linkedin` | LinkedIn / other ID lookup |
| `circle:airtel` | Operator / Telecom circle search |
| `email:foo@bar.com` | Email lookup |
| `9810014045, name:rahul` | Multi-query batch search |

---

## API Endpoints

- `GET /` — HTML Search Dashboard
- `GET /api/search?q=...` — REST API JSON search
- `GET /health` — Health and DuckDB engine status
- `POST /api/hf/reconnect` — Re-mount remote dataset
- `GET /docs` — Swagger UI

**Strictly for personal use.**
