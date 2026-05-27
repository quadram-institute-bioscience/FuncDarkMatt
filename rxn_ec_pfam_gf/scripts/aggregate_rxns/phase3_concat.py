#!/usr/bin/env python3
"""
Phase 3: Concatenate all deduplicated bucket outputs into final merged file.
Since buckets contain disjoint RXN sets, no sorting is needed — just cat.

Usage:
    python phase3_concat.py --output-dir <dir> --final-output <path> [--n-buckets 1024]
"""

import argparse
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


def concat(dedup_dir: Path, n_buckets: int, final_output: Path):
    t_start = time.time()

    # Verify all bucket outputs exist before starting
    missing = []
    bucket_files = []
    for i in range(n_buckets):
        p = dedup_dir / f"dedup_{i:04d}.tsv"
        if not p.exists():
            missing.append(p.name)
        else:
            bucket_files.append(p)

    if missing:
        print(f"ERROR: {len(missing)} bucket output(s) missing:", file=sys.stderr)
        for m in missing[:20]:
            print(f"  {m}", file=sys.stderr)
        if len(missing) > 20:
            print(f"  ... and {len(missing)-20} more", file=sys.stderr)
        sys.exit(1)

    print(f"All {n_buckets} bucket outputs found.", flush=True)
    print(f"Concatenating → {final_output}", flush=True)

    total_size_gb = sum(p.stat().st_size for p in bucket_files) / 1e9
    print(f"Total input size: {total_size_gb:.2f} GB", flush=True)

    tmp_output = final_output.with_suffix(".tmp")
    n_rxns = 0
    CHUNK = 256 * 1024  # 256 KB read buffer

    with open(tmp_output, "wb") as out:
        for i, p in enumerate(bucket_files, 1):
            with open(p, "rb") as fh:
                while True:
                    chunk = fh.read(CHUNK)
                    if not chunk:
                        break
                    out.write(chunk)
            if i % 100 == 0:
                elapsed = time.time() - t_start
                print(f"  {i}/{n_buckets} buckets concatenated | "
                      f"elapsed: {format_elapsed(elapsed)}",
                      flush=True)

    # Atomic rename
    tmp_output.rename(final_output)

    elapsed = time.time() - t_start
    final_size_gb = final_output.stat().st_size / 1e9

    print(f"\n── Done ──────────────────────────────────────────────────────────────")
    print(f"  Final output : {final_output}")
    print(f"  Output size  : {final_size_gb:.2f} GB")
    print(f"  Time         : {format_elapsed(elapsed)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dedup-dir",    type=Path, required=True,
                        help="Directory containing dedup_XXXX.tsv bucket outputs")
    parser.add_argument("--final-output",  type=Path, required=True,
                        help="Path for the final merged output file")
    parser.add_argument("--n-buckets",     type=int, default=1024,
                        help="Number of buckets expected (default: 1024)")
    args = parser.parse_args()

    if not args.dedup_dir.is_dir():
        sys.exit(f"Not a directory: {args.dedup_dir}")

    concat(args.dedup_dir, args.n_buckets, args.final_output)


if __name__ == "__main__":
    main()
