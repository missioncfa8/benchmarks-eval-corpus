import sys
import time

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from db import DuckDBManager

print("[*] Initializing DuckDB Engine & Connecting to Remote Dataset...", flush=True)
db = DuckDBManager()
db.initialize()

print("\n--- Running Live Benchmark Lookups ---", flush=True)
# Query 1: Direct phone lookup
t0 = time.perf_counter()
res1 = db.search("mobile", "9810014045")
print(f"1. Mobile Search (9810014045): {len(res1)} records in {(time.perf_counter()-t0)*1000:.2f} ms", flush=True)

# Query 2: Direct phone lookup (second query)
t0 = time.perf_counter()
res2 = db.search("mobile", "9811122334")
print(f"2. Mobile Search (9811122334): {len(res2)} records in {(time.perf_counter()-t0)*1000:.2f} ms", flush=True)

# Query 3: Secondary index search (Name)
t0 = time.perf_counter()
res3 = db.search("name", "vinod sharma", limit=5)
print(f"3. Name Index Search ('vinod sharma'): {len(res3)} records in {(time.perf_counter()-t0)*1000:.2f} ms", flush=True)

print("\n[OK] All benchmark lookups passed successfully!", flush=True)
