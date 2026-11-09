"""
cli.py — Standalone CLI & Terminal Search Tool for OSINT Intelligence Dataset
Allows instant lookups from terminal / command prompt across Windows, Ubuntu, Mac, and VMs.
Zero local disk required. Queries remote Hugging Face dataset in sub-second latency.
"""

import sys
import os
import argparse
import time
import json

# Ensure UTF-8 output across Windows and Linux terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv

# Ensure local portal modules are in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import DuckDBManager

load_dotenv()


def print_banner():
    banner = r"""
========================================================================
     _   _  _____ __  __ _   _ ____    ___ ____ ___ _   _ _____ 
    | \ | || ____|\ \/ /| | | / ___|  / _ \/ ___|_ _| \ | |_   _|
    |  \| ||  _|   \  / | | | \___ \ | | | \___ \| ||  \| | | |  
    | |\  || |___  /  \ | |_| |___) || |_| |___) | || |\  | | |  
    |_| \_||_____|/_/\_\ \___/|____/  \___/|____/___|_| \_| |_|  
              Data Intelligence & Verification Engine
========================================================================
    """
    print(banner)


def format_table(results):
    if not results:
        print("\n❌ No records found.")
        return

    print(f"\n✅ Found {len(results)} matching records:")
    print("-" * 120)
    for i, r in enumerate(results, 1):
        print(f"[{i}] Mobile: {r.get('mobile', 'N/A')} | Name: {r.get('name', 'N/A')} | Father: {r.get('fname', 'N/A')}")
        print(f"    ID: {r.get('id', 'N/A')} | Alt Phone: {r.get('alt', 'N/A')} | Email: {r.get('email', 'N/A')}")
        print(f"    Circle: {r.get('circle', 'N/A')} | Auxiliary ID: {r.get('oid', 'N/A')}")
        print(f"    Address: {r.get('address', 'N/A')}")
        print("-" * 120)


def interactive_mode(db: DuckDBManager):
    print("\n🔍 Interactive Search Prompt (Type 'exit' or 'quit' to close)")
    print("   Prefix syntax supported: id:1234..., email:test@..., alt:98..., name:john..., or just type phone number\n")
    
    while True:
        try:
            q = input("nexus-search> ").strip()
            if not q:
                continue
            if q.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            qtype = "mobile"
            val = q
            if ":" in q:
                parts = q.split(":", 1)
                qtype = parts[0].strip().lower()
                val = parts[1].strip()
            elif "@" in q:
                qtype = "email"
            elif q.isdigit():
                if len(q) == 12:
                    qtype = "id"
                else:
                    qtype = "mobile"
            else:
                qtype = "name"

            t0 = time.perf_counter()
            res = db.search(qtype, val, limit=20)
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"⏱️ Search finished in {elapsed:.1f} ms")
            format_table(res)
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break


def main():
    parser = argparse.ArgumentParser(description="Nexus OSINT CLI Search Engine")
    parser.add_argument("query", nargs="?", help="Direct phone number or search string")
    parser.add_argument("--type", choices=["mobile", "id", "alt", "email", "oid", "name", "address"], help="Explicit search type")
    parser.add_argument("--limit", type=int, default=20, help="Max results to return (default: 20)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted table")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive search shell")

    args = parser.parse_args()

    print_banner()
    print("⚡ Initializing remote DuckDB streaming connection...")
    db = DuckDBManager()
    db.initialize()
    print("✓ Ready!")

    if args.interactive or not args.query:
        interactive_mode(db)
        return

    qtype = args.type
    val = args.query.strip()

    if not qtype:
        if ":" in val:
            parts = val.split(":", 1)
            qtype = parts[0].strip().lower()
            val = parts[1].strip()
        elif "@" in val:
            qtype = "email"
        elif val.isdigit() and len(val) == 12:
            qtype = "id"
        elif val.isdigit():
            qtype = "mobile"
        else:
            qtype = "name"

    t0 = time.perf_counter()
    results = db.search(qtype, val, limit=args.limit)
    elapsed = (time.perf_counter() - t0) * 1000

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n⏱️ Query executed in {elapsed:.1f} ms")
        format_table(results)


if __name__ == "__main__":
    main()
