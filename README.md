---
title: Nexus Personnel Intelligence & Verification Platform
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

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
│                                    │   10GB RAM / 4 Threads  │ │
│                                    └───────────┬─────────────┘ │
│                                                │ HTTP Range    │
│                                                ▼               │
│                                    ┌─────────────────────────┐ │
│                                    │  HuggingFace Repository │ │
│                                    │  431 Parquet Partitions │ │
│                                    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

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

---

## 📡 REST API Endpoints

- `GET /` — Executive Personnel Search Interface
- `GET /api/search?q={query}` — JSON Record Verification Endpoint
- `GET /health` — Real-Time Engine Telemetry & View Status
- `POST /api/hf/reconnect` — Re-mount Remote Dataset
- `GET /docs` — Interactive OpenAPI / Swagger Documentation

**Confidential & Internal Verification System.**
