"""
db.py — High-Performance In-Memory DuckDB Engine with 2-Step Inverted Index Resolution
Queries ~3.77B records partitioned into 184 globally sorted Parquet chunks and 5 secondary
inverted index structures directly from Hugging Face via httpfs with zone-map pushdown.

Works universally across Windows, macOS, Ubuntu, Linux VMs, and 512MB cloud free tiers.
"""

import os
import re
import time
import logging
from typing import List, Dict, Any, Optional

import duckdb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("portal.db")

# ---------------------------------------------------------------------------
# Hugging Face Dataset & Authentication Configuration
# ---------------------------------------------------------------------------
HF_REPO = os.environ.get("HF_REPO", "aman29/benchmarks-eval-corpus")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Auto-tune memory limit based on environment
def _auto_detect_memory_limit() -> str:
    env_limit = os.environ.get("DUCKDB_MEMORY_LIMIT")
    if env_limit:
        return env_limit
    try:
        # Detect total system RAM if available
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        if total_ram_gb <= 1.0:
            return "400MB"  # Render / small VPS 512MB tier
        elif total_ram_gb <= 4.0:
            return "2GB"
        elif total_ram_gb <= 8.0:
            return "4GB"
        else:
            return "8GB"
    except Exception:
        return "2GB"

DUCKDB_MEMORY_LIMIT = _auto_detect_memory_limit()
DUCKDB_THREADS = os.environ.get("DUCKDB_THREADS", str(min(os.cpu_count() or 2, 8)))

# Data paths
PRIMARY_DATA_PATH = f"hf://datasets/{HF_REPO}/data/*.parquet"
INDEX_BASE_PATH = f"hf://datasets/{HF_REPO}/indexes"


class DuckDBManager:
    """In-memory DuckDB manager querying remote Parquet files on Hugging Face."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn: Optional[duckdb.DuckDBPyConnection] = None
        self.is_ready = False
        self.last_error: Optional[str] = None
        self._cache: Dict[str, Any] = {}
        self._cache_max_size = 500

    def initialize(self):
        """Initialize in-memory DuckDB with high-throughput cache and threading."""
        logger.info("Initializing DuckDB engine (memory: %s, threads: %s)", DUCKDB_MEMORY_LIMIT, DUCKDB_THREADS)
        self.conn = duckdb.connect(self.db_path)

        # Performance tuning
        self.conn.execute(f"SET memory_limit = '{DUCKDB_MEMORY_LIMIT}'")
        self.conn.execute(f"SET threads = {DUCKDB_THREADS}")
        self.conn.execute("SET preserve_insertion_order = false")

        # Object and metadata caching for ultra-fast repeated queries
        try:
            self.conn.execute("SET enable_object_cache = true")
            self.conn.execute("SET enable_http_metadata_cache = true")
            self.conn.execute("SET http_keep_alive = true")
            self.conn.execute("SET http_timeout = 30")
            self.conn.execute("SET http_retries = 3")
        except Exception as e:
            logger.warning("Cache flag warning: %s", e)

        # Install & load httpfs extension
        self.conn.execute("INSTALL httpfs")
        self.conn.execute("LOAD httpfs")

        # Configure Hugging Face authentication secret
        if HF_TOKEN:
            logger.info("Configuring Hugging Face authenticated secret for repository: %s", HF_REPO)
            try:
                self.conn.execute(f"""
                    CREATE SECRET IF NOT EXISTS hf_secret (
                        TYPE HUGGINGFACE,
                        TOKEN '{HF_TOKEN}'
                    )
                """)
            except Exception as e:
                logger.warning("Secret configuration notice: %s", e)

        # Mount remote dataset view
        self.mount_hf_view()
        logger.info("DuckDB remote dataset ready.")

    def mount_hf_view(self):
        """Create views over primary data and secondary indexes."""
        try:
            self.conn.execute(f"""
                CREATE OR REPLACE VIEW primary_records AS
                SELECT * FROM read_parquet('{PRIMARY_DATA_PATH}')
            """)
            self.is_ready = True
            self.last_error = None
            logger.info("Remote view 'primary_records' mounted successfully from %s", PRIMARY_DATA_PATH)
        except Exception as e:
            err = str(e)
            logger.error("Failed to mount HF view: %s", err)
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
    # High-Performance 2-Step Search Engine
    # ------------------------------------------------------------------
    def search(self, query_type: str, value: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search records remotely using optimal 1-step or 2-step index resolution."""
        if not value or not self.conn:
            return []

        cache_key = f"{query_type}:{value.strip().lower()}:{limit}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        start_time = time.time()
        results: List[Dict[str, Any]] = []

        try:
            # 1. Primary Direct Lookup (Phone / Mobile) — Parquet Zone-map Skip (< 0.4s)
            if query_type in ("mobile", "phone"):
                cleaned = self._clean_phone(value)
                sql = f"SELECT * FROM primary_records WHERE mobile = '{cleaned}' LIMIT {limit}"
                res = self.conn.execute(sql)
                results = self._rows_to_dicts(res)

                # Fallback check on alternate phone index if primary has no hit
                if not results and len(cleaned) >= 8:
                    alt_mobiles = self._resolve_secondary_index("alt", cleaned, limit=limit)
                    if alt_mobiles:
                        results = self._fetch_by_mobiles(alt_mobiles, limit=limit)

            # 2. Secondary Inverted Index: ID / Aadhaar (< 0.5s total)
            elif query_type in ("id", "aadhaar", "uid"):
                clean_id = value.strip()
                mobiles = self._resolve_secondary_index("id", clean_id, limit=limit)
                if mobiles:
                    results = self._fetch_by_mobiles(mobiles, limit=limit)

            # 3. Secondary Inverted Index: Alt Phone (< 0.5s total)
            elif query_type == "alt":
                cleaned_alt = self._clean_phone(value)
                mobiles = self._resolve_secondary_index("alt", cleaned_alt, limit=limit)
                if mobiles:
                    results = self._fetch_by_mobiles(mobiles, limit=limit)

            # 4. Secondary Inverted Index: Email (< 0.5s total)
            elif query_type == "email":
                clean_email = value.strip().lower()
                mobiles = self._resolve_secondary_index("email", clean_email, limit=limit)
                if mobiles:
                    results = self._fetch_by_mobiles(mobiles, limit=limit)

            # 5. Secondary Inverted Index: Auxiliary / Other ID (< 0.5s total)
            elif query_type in ("oid", "passport", "voter"):
                clean_oid = value.strip()
                mobiles = self._resolve_secondary_index("oid", clean_oid, limit=limit)
                if mobiles:
                    results = self._fetch_by_mobiles(mobiles, limit=limit)

            # 6. Secondary Inverted Index: Name (< 0.6s total)
            elif query_type == "name":
                clean_name = value.strip().lower()
                mobiles = self._resolve_secondary_index("name", clean_name, limit=limit)
                if mobiles:
                    results = self._fetch_by_mobiles(mobiles, limit=limit)
                else:
                    # Fallback prefix matching on name index
                    prefix_mobiles = self._resolve_secondary_index_prefix("name", clean_name, limit=limit)
                    if prefix_mobiles:
                        results = self._fetch_by_mobiles(prefix_mobiles, limit=limit)

            # 7. Fallback fields (fname, address, circle)
            elif query_type in ("fname", "address", "circle"):
                clean_val = value.strip().replace("'", "''")
                sql = f"SELECT * FROM primary_records WHERE LOWER({query_type}) LIKE LOWER('%{clean_val}%') LIMIT {limit}"
                res = self.conn.execute(sql)
                results = self._rows_to_dicts(res)

            else:
                # Default to phone or name
                digits = re.sub(r"[\s\-+]", "", value)
                if digits.isdigit() and len(digits) >= 8:
                    return self.search("mobile", value, limit=limit)
                return self.search("name", value, limit=limit)

        except Exception as e:
            logger.error("Query failed for type '%s', value '%s': %s", query_type, value, e)
            # Reconnect if connection was dropped
            if "Connection" in str(e) or "HTTP" in str(e):
                self._reconnect()
            return []

        elapsed = time.time() - start_time
        logger.info("Search [%s = '%s'] completed in %.3fs (%d results)", query_type, value, elapsed, len(results))

        # Store in cache
        if len(self._cache) >= self._cache_max_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = results

        return results

    def _resolve_secondary_index(self, index_name: str, key_val: str, limit: int = 50) -> List[str]:
        """Query secondary 2-column inverted index (search_key -> mobile)."""
        idx_url = f"{INDEX_BASE_PATH}/idx_{index_name}/*.parquet"
        quoted_val = key_val.replace("'", "''")
        try:
            query = f"""
                SELECT DISTINCT mobile 
                FROM read_parquet('{idx_url}') 
                WHERE {index_name} = '{quoted_val}' 
                LIMIT {limit}
            """
            rows = self.conn.execute(query).fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception as e:
            logger.warning("Secondary index lookup failed for %s: %s", index_name, e)
            return []

    def _resolve_secondary_index_prefix(self, index_name: str, prefix_val: str, limit: int = 50) -> List[str]:
        """Prefix search on sorted secondary index."""
        idx_url = f"{INDEX_BASE_PATH}/idx_{index_name}/*.parquet"
        quoted_prefix = prefix_val.replace("'", "''")
        try:
            query = f"""
                SELECT DISTINCT mobile 
                FROM read_parquet('{idx_url}') 
                WHERE {index_name} >= '{quoted_prefix}' 
                  AND {index_name} < '{quoted_prefix}~'
                LIMIT {limit}
            """
            rows = self.conn.execute(query).fetchall()
            return [r[0] for r in rows if r[0]]
        except Exception as e:
            logger.warning("Secondary prefix lookup failed for %s: %s", index_name, e)
            return []

    def _fetch_by_mobiles(self, mobiles: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch complete records from primary sorted dataset using list of mobile numbers."""
        if not mobiles:
            return []
        escaped_mobiles = [m.replace("'", "''") for m in mobiles[:limit]]
        quoted_list = ",".join(f"'{m}'" for m in escaped_mobiles)
        query = f"SELECT * FROM primary_records WHERE mobile IN ({quoted_list}) LIMIT {limit}"
        res = self.conn.execute(query)
        return self._rows_to_dicts(res)

    def batch_search_mobiles(self, mobiles: List[str], limit_per_mobile: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Batch query multiple mobile numbers simultaneously."""
        if not mobiles or not self.conn:
            return {}
        cleaned_mobs = [self._clean_phone(m) for m in mobiles if m.strip()]
        if not cleaned_mobs:
            return {}
        
        quoted_list = ",".join(f"'{m}'" for m in cleaned_mobs[:100])
        query = f"SELECT * FROM primary_records WHERE mobile IN ({quoted_list})"
        rows = self._rows_to_dicts(self.conn.execute(query))
        
        results: Dict[str, List[Dict[str, Any]]] = {m: [] for m in cleaned_mobs}
        for r in rows:
            mob = r.get("mobile")
            if mob in results and len(results[mob]) < limit_per_mobile:
                results[mob].append(r)
        return results

    def _clean_phone(self, value: str) -> str:
        """Normalize phone numbers — strip +91, 0 prefix, spaces, dashes."""
        cleaned = value.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if cleaned.startswith("+91"):
            cleaned = cleaned[3:]
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        elif cleaned.startswith("0") and len(cleaned) == 11:
            cleaned = cleaned[1:]
        return cleaned

    def _rows_to_dicts(self, result) -> List[Dict[str, Any]]:
        """Convert DuckDB cursor results to list of dicts."""
        if not result or not result.description:
            return []
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def _reconnect(self):
        """Attempt safe reconnection upon network or HTTP disconnect."""
        logger.info("Attempting DuckDB reconnection...")
        try:
            self.close()
            self.initialize()
        except Exception as e:
            logger.error("Reconnection failed: %s", e)

    def get_status(self) -> Dict[str, Any]:
        """Return engine status, index details, and dataset health."""
        return {
            "mode": "remote_huggingface_hybrid_indexed",
            "repo": HF_REPO,
            "ready": self.is_ready,
            "error": self.last_error,
            "architecture": "184 globally sorted primary chunks + 5 secondary inverted indexes",
            "searchable_headers": ["mobile", "id", "alt", "email", "oid", "name", "fname", "address", "circle"],
            "storage": "0 GB local disk (In-Memory HTTP Range Streaming)",
            "memory_limit": DUCKDB_MEMORY_LIMIT,
            "threads": DUCKDB_THREADS,
            "cached_queries": len(self._cache),
        }
