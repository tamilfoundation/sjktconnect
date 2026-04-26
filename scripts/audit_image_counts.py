"""Audit SchoolImage row counts across every school via the public API.

Walks all 528 schools in production, tallies images per school, and prints
schools with more than the threshold (default 5 — useful for verifying
the "View all N photos" lightbox overlay added in Sprint 15).

Usage:
    python scripts/audit_image_counts.py            # default >5
    python scripts/audit_image_counts.py --min 3    # show all >=3
    python scripts/audit_image_counts.py --top 50   # show top 50 by count

Requires no auth — hits public endpoints. Sends a non-default User-Agent
so the Sprint 8.3 scraper-blocker middleware lets the requests through.
"""

import argparse
import concurrent.futures
import json
import sys
import urllib.request

BASE = "https://api.tamilschool.org/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (SJKTConnect/audit_image_counts)"}


def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def count_for(moe: str) -> tuple[str, int]:
    try:
        data = fetch_json(f"{BASE}/schools/{moe}/images/", timeout=15)
        return moe, len(data)
    except Exception:
        return moe, -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min", type=int, default=6,
                        help="Show schools with at least this many images (default 6 = >5)")
    parser.add_argument("--top", type=int, default=20,
                        help="Cap how many rows to print (default 20)")
    args = parser.parse_args()

    schools = fetch_json(f"{BASE}/schools/map/")
    print(f"{len(schools)} schools total")

    results: list[tuple[str, int]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(count_for, s["moe_code"]) for s in schools]
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            results.append(f.result())
            if (i + 1) % 100 == 0:
                print(f"  ...{i+1}/{len(schools)}", file=sys.stderr)

    failed = [r for r in results if r[1] < 0]
    above = sorted([r for r in results if r[1] >= args.min], key=lambda x: -x[1])

    print()
    print(f"Failed lookups: {len(failed)}")
    print(f"Schools with >= {args.min} images: {len(above)}")
    for moe, n in above[: args.top]:
        print(f"  {moe}  {n} images")


if __name__ == "__main__":
    main()
