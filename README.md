# ⚡ Nexus Personnel Intelligence & Verification Platform

A production-grade, universal OSINT search and verification platform engineered to query **~3.77 Billion records** in **<1 second** with **zero local disk storage** and **under 100 MB RAM**.

Powered by **FastAPI** and **DuckDB Columnar Remote Streaming** with **2-Step Inverted Index Pushdown** over Hugging Face Parquet datasets.

---

## 🌟 Key Features

* **Universal Cross-Platform:** Runs identically on **Windows**, **Ubuntu / Debian**, **macOS**, **GCP / AWS / Azure VMs**, **Docker**, and **Free Cloud Tiers** (Render, Fly.io, Hugging Face Spaces).
* **Zero Local Disk Requirement:** Streams remote Parquet bytes over HTTP byte-ranges via DuckDB HTTPFS. No need to download 50+ GB locally.
* **Sub-Second Latency (<0.5s):**
  * Direct Phone search uses Parquet zone-map metadata skipping across 184 globally sorted files.
  * Search by Aadhaar / ID, Alternate Phone, Email, Other ID, or Name uses 2-column inverted indexes (`idx_<header>/*.parquet` $\to$ `data/*.parquet`).
* **Interactive Web Dashboard:** Sleek, responsive dark-mode UI with filter pills, copyable fields, batch query support, and CSV/JSON export.
* **Standalone CLI Tool:** Run instant lookups or interactive shells directly from your command prompt / terminal.
* **REST API:** Complete REST API endpoints for automated workflows, bots, and integration.

---

## 🚀 Quick Start Guide (Run on Any Device)

### Option 1: Windows (1-Click)
Double-click `run.bat` or run in PowerShell / Command Prompt:
```cmd
cd data_intelligence_portal
.\run.bat
```
*Automatically creates a virtual environment, installs dependencies, and launches on `http://localhost:8000`.*

---

### Option 2: Linux / Ubuntu / Debian / macOS / Cloud VM
Run in your bash terminal:
```bash
cd data_intelligence_portal
chmod +x run.sh
./run.sh
```
*Or manually:*
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

---

### Option 3: Docker (Containerized)
```bash
cd data_intelligence_portal
docker-compose up -d
```
Access the dashboard at `http://localhost:8000`.

---

## 🖥️ Command-Line Interface (CLI Tool)

You can query the dataset directly from your terminal without opening a browser:

```bash
# 1. Interactive Search Shell
python cli.py -i

# 2. Search by Phone Number
python cli.py 9810014045

# 3. Search by Aadhaar / Primary ID
python cli.py --type id 123456789012

# 4. Search by Name
python cli.py --type name "Rahul Sharma"

# 5. Search by Email
python cli.py --type email "user@domain.com"

# 6. Output as Raw JSON
python cli.py 9810014045 --json
```

---

## 🌐 REST API Endpoints

The FastAPI server provides automated endpoints:

### 1. Unified Search (`GET /api/search`)
```bash
# Auto-detects query type:
curl "http://localhost:8000/api/search?q=9810014045"

# Search with explicit prefix:
curl "http://localhost:8000/api/search?q=id:123456789012"
curl "http://localhost:8000/api/search?q=name:rahul"
curl "http://localhost:8000/api/search?q=email:target@domain.com"
```

### 2. Batch Search (`POST /api/batch`)
```bash
curl -X POST "http://localhost:8000/api/batch" \
     -H "Content-Type: application/json" \
     -d '{"queries": ["9810014045", "9820012345", "id:123456789012"]}'
```

### 3. Data Export (`GET /api/export`)
```bash
# Download as CSV:
curl "http://localhost:8000/api/export?q=name:rahul&format=csv" -o results.csv

# Download as JSON:
curl "http://localhost:8000/api/export?q=9810014045&format=json" -o results.json
```

### 4. Healthcheck & Metrics (`GET /health` & `GET /api/stats`)
```bash
curl "http://localhost:8000/health"
```

---

## 🏗️ Architecture & Storage Layout

The dataset on Hugging Face (`aman29/benchmarks-eval-corpus`) is organized into:

```text
aman29/benchmarks-eval-corpus/
├── data/
│   ├── part_0000.parquet   (~288 MB, sorted by mobile)
│   ├── part_0001.parquet
│   └── ... (184 chunks, 51.0 GB total, all <500 MB)
└── indexes/
    ├── idx_id/             (20 chunks, sorted by id -> mobile)
    ├── idx_alt/            (14 chunks, sorted by alt -> mobile)
    ├── idx_email/          (2 chunks, sorted by email -> mobile)
    ├── idx_oid/            (9 chunks, sorted by oid -> mobile)
    └── idx_name/           (24 chunks, sorted by name -> mobile)
```

### Why It's 100x Faster on 512 MB RAM
1. **Direct Phone Search:** When querying `mobile = '9810014045'`, DuckDB reads only ~50 KB of Parquet metadata footers over HTTP, identifies the single 288 MB chunk and row group containing the number, and skips all 183 other files. Total data transfer is under 5 MB.
2. **Secondary Header Search:** When querying by `id`, `name`, `email`, etc., DuckDB first queries the narrow 2-column secondary index to get the target phone number in <0.1s, then retrieves the full 9-column record from `data/` in <0.3s.

---

## ⚙️ Configuration (`.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `HF_REPO` | `aman29/benchmarks-eval-corpus` | Hugging Face Dataset repository |
| `HF_TOKEN` | `your_huggingface_read_token_here` | Hugging Face authentication token |
| `PORT` | `8000` | Web server port |
| `HOST` | `0.0.0.0` | Bind address |
| `DUCKDB_MEMORY_LIMIT` | Auto-detected | `400MB` on free tier, `2GB-4GB` on standard systems |
| `DUCKDB_THREADS` | CPU count | Worker threads for DuckDB engine |
