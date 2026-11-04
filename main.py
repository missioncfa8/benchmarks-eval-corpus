"""
main.py — FastAPI + DuckDB High-Performance Intelligence Portal
Personal OSINT verification and workforce records lookup platform across ~3.77B records.

Zero local disk required. Uses DuckDB httpfs remote streaming with 2-step inverted index
resolution and sub-second zone-map pushdown. Runs universally on Windows, Ubuntu, VMs, and Cloud.
"""

import os
import io
import csv
import time
import re
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dashboard import render_dashboard_html
from db import DuckDBManager

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("portal")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_LIMIT = int(os.environ.get("DEFAULT_LIMIT", "25"))
MAX_LIMIT = int(os.environ.get("MAX_LIMIT", "100"))

# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
db_manager: Optional[DuckDBManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager
    logger.info("Starting up — initializing high-speed in-memory DuckDB engine")
    db_manager = DuckDBManager()
    try:
        db_manager.initialize()
    except Exception as e:
        logger.error("Initialization warning (dataset will retry on first query): %s", e)

    yield
    logger.info("Shutting down — closing DuckDB engine")
    if db_manager:
        db_manager.close()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Nexus Personnel Intelligence & Verification Platform",
    description=(
        "Universal identity verification and workforce records lookup engine. "
        "Powered by FastAPI and DuckDB Columnar Streaming over remote Parquet datasets."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Query Parsing & Type Detection
# ---------------------------------------------------------------------------
def parse_queries(raw: str) -> List[str]:
    """Split comma/newline-separated input into individual query strings."""
    parts = re.split(r"[,\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def detect_query_type(q: str) -> str:
    """Detect search type: mobile, id, name, address, circle, email, alt, oid, etc."""
    if ":" in q:
        prefix = q.split(":", 1)[0].strip().lower()
        prefix_map = {
            "mobile": "mobile", "phone": "mobile", "mob": "mobile",
            "id": "id", "uid": "id", "aadhaar": "id",
            "name": "name",
            "fname": "fname", "father": "fname",
            "address": "address", "addr": "address",
            "circle": "circle", "operator": "circle",
            "email": "email", "mail": "email",
            "alt": "alt", "altphone": "alt",
            "oid": "oid", "linkedin": "oid", "otherid": "oid", "passport": "oid", "voter": "oid"
        }
        return prefix_map.get(prefix, "name")

    # Email pattern
    if "@" in q and "." in q:
        return "email"

    # Numeric inspection
    digits = re.sub(r"[\s\-+]", "", q)
    if digits.isdigit():
        if len(digits) == 10 or (len(digits) == 12 and digits.startswith("91")):
            return "mobile"
        if len(digits) == 12:
            return "id"  # 12-digit Aadhaar / ID pattern
        if len(digits) >= 8:
            return "mobile"

    return "name"


def extract_value(q: str) -> str:
    """Extract query value after prefix or return the whole query."""
    if ":" in q:
        return q.split(":", 1)[1].strip()
    return q.strip()


def _do_search(sub_q: str, limit: int) -> dict:
    """Execute search against remote Hugging Face Parquet view via DuckDB."""
    qtype = detect_query_type(sub_q)
    value = extract_value(sub_q)

    if not db_manager or not db_manager.is_ready:
        try:
            db_manager.mount_hf_view()
        except Exception:
            pass

    results = db_manager.search(qtype, value, limit) if db_manager else []

    return {
        "query": sub_q,
        "type": qtype,
        "count": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class BatchSearchRequest(BaseModel):
    queries: List[str]
    limit_per_query: Optional[int] = 10


# ---------------------------------------------------------------------------
# Routes — Health & Status
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for Render, Docker, AWS, GCP, and uptime monitors."""
    status = db_manager.get_status() if db_manager else {"ready": False}
    return {
        "status": "healthy" if status.get("ready") else "initializing",
        **status,
    }


@app.get("/api/stats", tags=["System"])
async def get_stats():
    """System and dataset metrics."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database engine initializing")
    return db_manager.get_status()


# ---------------------------------------------------------------------------
# Routes — Web UI (Dashboard)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard(
    q: str = Query("", description="Search query"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """Main Web Dashboard."""
    if not q.strip():
        return HTMLResponse(render_dashboard_html("", [], limit=limit))

    queries = parse_queries(q)
    t0 = time.perf_counter()
    search_results = [_do_search(sub_q, limit) for sub_q in queries]
    elapsed_ms = (time.perf_counter() - t0) * 1000

    total = sum(r["count"] for r in search_results)
    logger.info("Search '%s' -> %d results in %.1f ms", q, total, elapsed_ms)
    return HTMLResponse(render_dashboard_html(q, search_results, limit=limit, search_time_ms=elapsed_ms))


# ---------------------------------------------------------------------------
# Routes — REST API
# ---------------------------------------------------------------------------
@app.get("/api/search", tags=["API"])
async def api_search(
    q: str = Query(..., description="Search query (e.g. 9810014045, id:123456789012, name:rahul, email:test@domain.com)"),
    type: Optional[str] = Query(None, description="Explicit search type (mobile, id, alt, email, oid, name)"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """REST API endpoint returning JSON search results."""
    t0 = time.perf_counter()

    if type:
        results = db_manager.search(type, q.strip(), limit=limit) if db_manager else []
        all_results = [{
            "query": q,
            "type": type,
            "count": len(results),
            "results": results
        }]
    else:
        queries = parse_queries(q)
        all_results = [_do_search(sub_q, limit) for sub_q in queries]

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "status": "success",
        "total_results": sum(r["count"] for r in all_results),
        "search_time_ms": round(elapsed_ms, 2),
        "data": all_results,
    }


@app.post("/api/batch", tags=["API"])
async def api_batch_search(req: BatchSearchRequest):
    """Batch search across multiple phones, IDs, or search queries."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database engine initializing")

    t0 = time.perf_counter()
    batch_results = []
    limit = req.limit_per_query or 10

    for query in req.queries[:50]:  # Cap at 50 queries per batch
        sub_res = _do_search(query, limit=limit)
        batch_results.append(sub_res)

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "status": "success",
        "batch_count": len(batch_results),
        "total_hits": sum(r["count"] for r in batch_results),
        "execution_time_ms": round(elapsed_ms, 2),
        "results": batch_results,
    }


@app.get("/api/export", tags=["Export"])
async def api_export(
    q: str = Query(..., description="Search query to export"),
    format: str = Query("csv", regex="^(csv|json)$"),
    limit: int = Query(100, ge=1, le=500),
):
    """Export search results directly to downloadable CSV or JSON."""
    queries = parse_queries(q)
    all_rows = []
    for sub_q in queries:
        sub_res = _do_search(sub_q, limit=limit)
        all_rows.extend(sub_res.get("results", []))

    if not all_rows:
        raise HTTPException(status_code=404, detail="No records found to export")

    if format == "json":
        return JSONResponse(
            content=all_rows,
            headers={"Content-Disposition": f"attachment; filename=export_{int(time.time())}.json"}
        )

    # CSV Export
    output = io.StringIO()
    headers = ["mobile", "name", "fname", "id", "alt", "email", "circle", "address", "oid"]
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in all_rows:
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{int(time.time())}.csv"}
    )


# ---------------------------------------------------------------------------
# CLI / Direct Script Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    print(f"\n🚀 Launching Nexus Portal on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, log_level="info", reload=False)
