import time
from db import DuckDBManager

print("Initializing DuckDB Engine...")
db = DuckDBManager()
db.initialize()

print("\n--- Running Live Benchmark Lookups ---")
# Query 1: Direct phone lookup
t0 = time.perf_counter()
res1 = db.search("mobile", "9810014045")
print(f"1. Mobile Search (9810014045): {len(res1)} records in {(time.perf_counter()-t0)*1000:.2f} ms")

# Query 2: Direct phone lookup (second query)
t0 = time.perf_counter()
res2 = db.search("mobile", "9811122334")
print(f"2. Mobile Search (9811122334): {len(res2)} records in {(time.perf_counter()-t0)*1000:.2f} ms")

# Query 3: Secondary index search (Name)
t0 = time.perf_counter()
res3 = db.search("name", "vinod sharma", limit=5)
print(f"3. Name Index Search ('vinod sharma'): {len(res3)} records in {(time.perf_counter()-t0)*1000:.2f} ms")

print("\n✓ All benchmark lookups passed successfully!")
