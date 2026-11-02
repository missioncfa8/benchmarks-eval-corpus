# Nexus Personnel Intelligence & Verification Platform

Enterprise-grade identity verification and workforce records lookup platform built on **FastAPI** and **DuckDB Columnar Streaming**.

Designed for high-throughput personnel verification, background investigations, and contact registry analytics across **~3.77 billion records** hosted on Hugging Face (`aman29/benchmarks-eval-corpus`).

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│             Nexus Personnel Intelligence Engine                 │
│                                                                 │
│  ┌───────────────────────┐         ┌─────────────────────────┐ │
│  │   Executive Web UI    │         │  FastAPI Async Engine   │ │
│  │  (Dark Enterprise UI) │◀───────▶│  REST API & Telemetry   │ │
│  └───────────────────────┘         └───────────┬─────────────┘ │
│                                                │               │
│                                                ▼               │
│                                    ┌─────────────────────────┐ │
│                                    │   DuckDB In-Memory      │ │
│                                    │   httpfs Columnar Push  │ │
│                                    └───────────┬─────────────┘ │
│                                                │ HTTP Range    │
│                                                ▼               │
│                                    ┌─────────────────────────┐ │
│                                    │  HuggingFace Repository │ │
│                                    │  431 Parquet Partitions │ │
│                                    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Technical Capabilities

- **Zero-Storage Footprint**: Operates 100% in-memory with zero local disk overhead ($0/mo cost on free tier).
- **Columnar Predicate Pushdown**: DuckDB queries Parquet chunk metadata over HTTP range headers, fetching only matching row groups in ~2 seconds.
- **Multi-Vector Identity Search**: Real-time resolution across National IDs (Aadhaar/Govt ID), 10-digit mobile numbers, alternate phones, full names, parentage, regional circles, and professional handles (LinkedIn).
- **Executive Dossier UI**: Clean enterprise-grade dark interface featuring automated avatar initials, single-click clipboard chips, status badges, and filter shortcuts.

---

## 🚀 Quick Start (Local Development)

```bash
# Clone the repository
git clone https://github.com/missioncfa8/benchmarks-eval-corpus.git
cd benchmarks-eval-corpus

# Run containerized locally
docker compose up --build

# Access Web Portal: http://localhost:8000
# Access API Documentation: http://localhost:8000/docs
```

---

## 🌐 Cloud Deployment (Render.com)

1. Connect your repository to **Render.com**.
2. Deploy as a **Web Service** with:
   - **Runtime**: `Docker`
   - **Plan**: `Free` ($0/mo)
   - **Health Check Path**: `/health`
3. Configure Environment Variables:
   - `HF_REPO`: `aman29/benchmarks-eval-corpus`
   - `HF_TOKEN`: *(Optional: Hugging Face read token if repository is private)*

---

## 🔍 Verification Query Syntax

| Query Syntax | Verification Vector | Example |
|---|---|---|
| `9810014045` | Primary Mobile Number (Exact Partition Match) | `9810014045` |
| `name:rahul` | Personnel Name Prefix / Substring Match | `name:rahul` |
| `rahul sharma` | Full Name & Lineage Composite Search | `rahul sharma` |
| `id:1234567890` | National Identity / Aadhaar / KYC ID | `id:1234567890` |
| `address:mumbai` | Jurisdictional Address Substring | `address:mumbai` |
| `circle:airtel` | Telecom Operator / Circle Region | `circle:airtel` |
| `oid:linkedin` | Auxiliary / Professional Profile Identifier | `oid:linkedin.com/in/` |
| `q1, q2, q3` | Concurrent Multi-Query Batch Processing | `9810014045, name:rahul` |

---

## 📡 REST API Endpoints

- `GET /` — Executive Personnel Search Interface
- `GET /api/search?q={query}` — JSON Record Verification Endpoint
- `GET /health` — Real-Time Engine Telemetry & View Status
- `POST /api/hf/reconnect` — Re-mount Remote Dataset
- `POST /api/query?sql={SELECT...}` — Read-Only Direct SQL Inspection
- `GET /docs` — Interactive OpenAPI / Swagger Documentation

---

**Confidential & Internal Verification System.**
