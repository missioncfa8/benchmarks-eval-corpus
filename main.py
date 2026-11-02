"""
main.py — FastAPI + DuckDB Data Intelligence Portal (100% Free Tier Edition)
Personal-use OSINT search across ~3.77B records / 431 Parquet chunks hosted on Hugging Face.
Zero local disk required. Uses DuckDB httpfs cached remote view with predicate pushdown.
"""

import os
import time
import re
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from dashboard import render_dashboard_html
from db import DuckDBManager

# ---------------------------------------------------------------------------
# Logging
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
    logger.info("Starting up — initializing in-memory DuckDB engine")
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
        "Enterprise-grade identity verification and workforce records lookup platform. "
        "Powered by FastAPI and DuckDB Columnar Streaming over remote Parquet datasets."
    ),
    version="2.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Query parsing & type detection
# ---------------------------------------------------------------------------
def parse_queries(raw: str) -> List[str]:
    """Split comma/newline-separated input into individual query strings."""
    parts = re.split(r"[,\n]+", raw)
    return [p.strip() for p in parts if p.strip()]


def detect_query_type(q: str) -> str:
    """Detect search type: phone, id, name, address, circle, email, oid, etc."""
    if ":" in q:
        prefix = q.split(":", 1)[0].strip().lower()
        prefix_map = {
            "mobile": "mobile", "phone": "mobile", "mob": "mobile",
            "id": "id", "uid": "id", "aadhaar": "id",
            "name": "name",
            "fname": "fname",
            "address": "address", "addr": "address",
            "circle": "circle", "operator": "circle",
            "email": "email", "mail": "email",
            "alt": "alt",
            "oid": "oid", "linkedin": "oid", "otherid": "oid",
        }
        return prefix_map.get(prefix, "name")

    digits = re.sub(r"[\s\-+]", "", q)
    if digits.isdigit():
        if len(digits) >= 10:
            return "mobile"
        if len(digits) >= 8:
            return "id"
    return "name"


def extract_value(q: str) -> str:
    """Extract query value after prefix or return the whole query."""
    if ":" in q:
        return q.split(":", 1)[1].strip()
    return q.strip()


def _do_search(sub_q: str, limit: int) -> dict:
    """Execute search against remote HuggingFace Parquet view via DuckDB."""
    qtype = detect_query_type(sub_q)
    value = extract_value(sub_q)

    if not db_manager or not db_manager.is_ready:
        # Attempt reconnect if not ready
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
# Routes — Health & Status
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for Render.com."""
    status = db_manager.get_status() if db_manager else {"ready": False}
    return {
        "status": "healthy" if status.get("ready") else "initializing",
        **status,
    }


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
    q: str = Query(..., description="Search query (e.g. 9810014045, name:rahul, address:delhi)"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
):
    """REST API endpoint returning JSON search results."""
    queries = parse_queries(q)
    t0 = time.perf_counter()
    all_results = [_do_search(sub_q, limit) for sub_q in queries]
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "total_results": sum(r["count"] for r in all_results),
        "search_time_ms": round(elapsed_ms, 2),
        "data": all_results,
    }


@app.post("/api/hf/reconnect", tags=["Admin"])
async def reconnect_hf(
    repo: str = Query("", description="Override HuggingFace repo name"),
    split: str = Query("", description="Optional dataset split or subfolder"),
):
    """Manually re-mount or update HuggingFace remote view."""
    try:
        db_manager.mount_hf_view(repo=repo, split=split)
        return {"status": "ok", "message": "HF view re-mounted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", tags=["Admin"])
async def raw_query(
    sql: str = Query(..., description="Raw SELECT SQL query"),
):
    """Execute raw read-only SQL query against the records view."""
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("DESCRIBE") and not sql_upper.startswith("EXPLAIN"):
        raise HTTPException(status_code=400, detail="Only SELECT / DESCRIBE / EXPLAIN allowed")
    try:
        return {"results": db_manager.execute_query(sql)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
