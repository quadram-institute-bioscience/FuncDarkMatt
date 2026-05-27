#!/usr/bin/env python3
"""
Phase 1: Hash-partition all (rxn, uid) pairs into N bucket files.
Each bucket contains a disjoint subset of RXNs.

Usage:
    python phase1_partition.py <input_dir> --bucket-dir <dir> [--pattern "*.txt"] [--n-buckets 1024]
"""

import argparse
import hashlib
import sys
import time
from pathlib import Path


def format_elapsed(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def partition(input_dir: Path, pattern: str, bucket_dir: Path, n_buckets: int):
    files = sorted(input_dir.glob(pattern))
    if not files:
        sys.exit(f"No files found matching '{pattern}' in {input_dir}")

    bucket_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found       : {len(files)} input files", flush=True)
    print(f"Buckets     : {n_buckets}", flush=True)
    print(f"Bucket dir  : {bucket_dir}", flush=True)
    print(f"Est. per bucket: {2850/n_buckets:.2f} GB (assuming ~2.85 TB total input)", flush=True)
    print(flush=True)

    t_start = time.time()
    n_pairs = 0
    n_skipped = 0

    # Open all bucket handles upfront
    handles = [
        open(bucket_dir / f"bucket_{i:04d}.tsv", "w", buffering=8 * 1024 * 1024)
        for i in range(n_buckets)
    ]

    try:
        for i, fpath in enumerate(files, 1):
            if i % 1000 == 0:
                elapsed = time.time() - t_start
                rate = i / elapsed
                remaining = (len(files) - i) / rate
                print(f"  {i}/{len(files)} files | "
                      f"{n_pairs:,} pairs | "
                      f"elapsed: {format_elapsed(elapsed)} | "
                      f"est. remaining: {format_elapsed(remaining)}",
                      flush=True)
            try:
                with open(fpath) as fh:
                    next(fh)  # skip header
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("\t")
                        if len(parts) < 2:
                            continue
                        rxn = parts[0].strip()
                        if not rxn:
                            continue

                        # Deterministic bucket assignment — same RXN always → same bucket
                        bucket = int(hashlib.md5(rxn.encode()).hexdigest(), 16) % n_buckets

                        for uid in parts[1].split(";"):
                            uid = uid.strip()
                            if uid:
                                handles[bucket].write(f"{rxn}\t{uid}\n")
                                n_pairs += 1
            except Exception as e:
                n_skipped += 1
                print(f"  WARNING: skipping {fpath.name}: {e}", file=sys.stderr)

    finally:
        for h in handles:
            h.close()

    elapsed = time.time() - t_start

    # Report summary
    print(flush=True)
    print(f"── Phase 1 complete ─────────────────────────────────────────────────")
    print(f"  Pairs written  : {n_pairs:,}")
    print(f"  Files skipped  : {n_skipped}")
    print(f"  Time           : {format_elapsed(elapsed)}")

    # Bucket size distribution
    sizes = []
    for i in range(n_buckets):
        p = bucket_dir / f"bucket_{i:04d}.tsv"
        sizes.append(p.stat().st_size)

    total_gb = sum(sizes) / 1e9
    min_gb   = min(sizes) / 1e9
    max_gb   = max(sizes) / 1e9
    avg_gb   = total_gb / n_buckets

    print(f"  Total bucket data : {total_gb:.2f} GB")
    print(f"  Per-bucket size   : min={min_gb:.2f} GB  avg={avg_gb:.2f} GB  max={max_gb:.2f} GB")
    print(f"\nNext step: submit phase2_array.sh", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_dir",   type=Path, help="Directory containing input files")
    parser.add_argument("--bucket-dir", type=Path, required=True,
                        help="Directory to write bucket files into")
    parser.add_argument("--pattern",   default="*.txt",
                        help="Glob pattern for input files (default: *.txt)")
    parser.add_argument("--n-buckets", type=int, default=1024,
                        help="Number of buckets (default: 1024)")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        sys.exit(f"Not a directory: {args.input_dir}")

    partition(args.input_dir, args.pattern, args.bucket_dir, args.n_buckets)


if __name__ == "__main__":
    main()
