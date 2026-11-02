"""
db.py — High-Performance In-Memory DuckDB Engine for Hugging Face Spaces
Queries ~3.77B records / 431 Parquet chunks directly from Hugging Face
via httpfs with predicate pushdown, object caching, and multi-threading.
"""

import os
import logging
from typing import List, Dict, Any, Optional

import duckdb

logger = logging.getLogger("portal.db")

# ---------------------------------------------------------------------------
# HuggingFace dataset configuration
# ---------------------------------------------------------------------------
HF_REPO = os.environ.get("HF_REPO", "aman29/benchmarks-eval-corpus")
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # Token injected in Spaces or environment
DUCKDB_MEMORY_LIMIT = os.environ.get("DUCKDB_MEMORY_LIMIT", "10GB")  # 16GB available on HF Space
DUCKDB_THREADS = os.environ.get("DUCKDB_THREADS", "4")


class DuckDBManager:
    """In-memory DuckDB manager querying remote Parquet files on HuggingFace."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self.is_ready = False
        self.last_error: Optional[str] = None

    def initialize(self):
        """Initialize in-memory DuckDB with high-throughput cache and threading."""
        logger.info("Initializing DuckDB engine (memory: %s, threads: %s)", DUCKDB_MEMORY_LIMIT, DUCKDB_THREADS)
        self.conn = duckdb.connect(self.db_path)

        # Performance tuning: 16GB RAM + 2 vCPU available on HF Space
        self.conn.execute(f"SET memory_limit = '{DUCKDB_MEMORY_LIMIT}'")
        self.conn.execute(f"SET threads = {DUCKDB_THREADS}")
        self.conn.execute("SET preserve_insertion_order = false")

        # Object and metadata caching for ultra-fast repeated queries
        try:
            self.conn.execute("SET enable_object_cache = true")
            self.conn.execute("SET enable_http_metadata_cache = true")
            self.conn.execute("SET http_keep_alive = true")
        except Exception as e:
            logger.warning("Cache flag warning: %s", e)

        # Install & load httpfs extension
        self.conn.execute("INSTALL httpfs")
        self.conn.execute("LOAD httpfs")

        # Configure HuggingFace authentication if token provided
        if HF_TOKEN:
            logger.info("Configuring HuggingFace authenticated secret")
            try:
                self.conn.execute(f"CREATE SECRET IF NOT EXISTS hf_secret (TYPE HUGGINGFACE, TOKEN '{HF_TOKEN}')")
            except Exception as e:
                logger.warning("Could not create HF secret: %s", e)

        # Mount remote dataset view from dataset root
        self.mount_hf_view()
        logger.info("DuckDB remote dataset ready.")

    def mount_hf_view(self, repo: str = "", split: str = ""):
        """Create a cached DuckDB view over HuggingFace Parquet chunks."""
        target_repo = repo or HF_REPO
        if split:
            hf_url = f"hf://datasets/{target_repo}/{split}/*.parquet"
        else:
            hf_url = f"hf://datasets/{target_repo}/*.parquet"

        logger.info("Mounting HF Parquet view from: %s", hf_url)

        try:
            self.conn.execute(f"""
                CREATE OR REPLACE VIEW records AS
                SELECT * FROM read_parquet('{hf_url}')
            """)
            self.is_ready = True
            self.last_error = None
            logger.info("Remote view 'records' mounted successfully from %s", hf_url)
        except Exception as e:
            err = str(e)
            logger.error("Failed to mount HF view '%s': %s", hf_url, err)
            self.is_ready = False
            self.last_error = err
            raise

    def close(self):
        """Close the DuckDB connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.is_ready = False
            logger.info("DuckDB connection closed.")

    # ------------------------------------------------------------------
    # Search logic with DuckDB Predicate Pushdown
    # ------------------------------------------------------------------
    def search(self, query_type: str, value: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search records remotely with pushdown filtering."""
        if not value or not self.conn:
            return []

        cleaned_phone = self._clean_phone(value)

        query_map = {
            "mobile":  ("SELECT * FROM records WHERE mobile = ? OR alt = ? LIMIT ?", [cleaned_phone, cleaned_phone, limit]),
            "alt":     ("SELECT * FROM records WHERE alt = ? OR mobile = ? LIMIT ?", [cleaned_phone, cleaned_phone, limit]),
            "id":      ("SELECT * FROM records WHERE id = ? LIMIT ?", [value.strip(), limit]),
            "oid":     ("SELECT * FROM records WHERE LOWER(oid) LIKE LOWER(?) LIMIT ?", [f"%{value}%", limit]),
            "email":   ("SELECT * FROM records WHERE LOWER(email) LIKE LOWER(?) LIMIT ?", [f"%{value}%", limit]),
            "name":    ("SELECT * FROM records WHERE LOWER(name) LIKE LOWER(?) OR LOWER(fname) LIKE LOWER(?) LIMIT ?", [f"%{value}%", f"%{value}%", limit]),
            "fname":   ("SELECT * FROM records WHERE LOWER(fname) LIKE LOWER(?) LIMIT ?", [f"%{value}%", limit]),
            "address": ("SELECT * FROM records WHERE LOWER(address) LIKE LOWER(?) LIMIT ?", [f"%{value}%", limit]),
            "circle":  ("SELECT * FROM records WHERE LOWER(circle) LIKE LOWER(?) LIMIT ?", [f"%{value}%", limit]),
        }

        sql, params = query_map.get(query_type, query_map["name"])
        try:
            result = self.conn.execute(sql, params)
            return self._rows_to_dicts(result)
        except Exception as e:
            logger.error("Query failed for type '%s', value '%s': %s", query_type, value, e)
            return []

    def _clean_phone(self, value: str) -> str:
        """Normalize phone numbers — strip +91, spaces, dashes."""
        cleaned = value.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if cleaned.startswith("+91"):
            cleaned = cleaned[3:]
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        return cleaned

    def _rows_to_dicts(self, result) -> List[Dict[str, Any]]:
        """Convert DuckDB cursor results to list of dicts."""
        if not result or not result.description:
            return []
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    # ------------------------------------------------------------------
    # Status / Info
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Return engine status, mounted views, and errors if any."""
        views = []
        if self.conn:
            try:
                res = self.conn.execute("SHOW TABLES").fetchall()
                views = [r[0] for r in res]
            except Exception:
                pass
        return {
            "mode": "remote_huggingface",
            "repo": HF_REPO,
            "ready": self.is_ready,
            "views": views,
            "error": self.last_error,
            "storage": "in-memory (0 GB local disk)",
            "memory_limit": DUCKDB_MEMORY_LIMIT,
        }

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a raw SELECT query against the remote records view."""
        if not self.conn:
            return []
        result = self.conn.execute(sql)
        return self._rows_to_dicts(result)
