#!/usr/bin/env python3
"""
Phase 2: Sort and deduplicate a single bucket file.
Called once per SLURM array task.

Usage:
    python phase2_dedup_bucket.py --bucket-file <path> --output <path> [--tmp-dir /tmp]
"""

import argparse
import subprocess
import sys
import time
from itertools import groupby
from pathlib import Path


def format_elapsed(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def dedup_bucket(bucket_file: Path, output: Path, tmp_dir: str, parallel: int):
    if not bucket_file.exists():
        sys.exit(f"Bucket file not found: {bucket_file}")

    bucket_size_gb = bucket_file.stat().st_size / 1e9
    print(f"Bucket file : {bucket_file.name} ({bucket_size_gb:.2f} GB)", flush=True)
    print(f"Output      : {output}", flush=True)

    t_start = time.time()

    # Stream: sort stdin → Python dedup → output
    # No intermediate sorted file written to disk
    sort_proc = subprocess.Popen(
        ["sort",
         f"--parallel={parallel}",
         "--buffer-size=2G",
         "-T", tmp_dir,
         "-k1,1", "-k2,2",
         str(bucket_file)],
        stdout=subprocess.PIPE,
        text=True,
        bufsize=8 * 1024 * 1024
    )

    t_sort_start = time.time()
    n_rxns = 0
    n_pairs_in = 0
    n_pairs_out = 0
    tmp_output = output.with_suffix(".tmp")

    try:
        with open(tmp_output, "w", buffering=8 * 1024 * 1024) as out:
            for rxn, group in groupby(sort_proc.stdout,
                                      key=lambda line: line.split("\t")[0]):
                seen = {}
                for line in group:
                    uid = line.rstrip("\n").split("\t", 1)[1]
                    seen[uid] = None
                    n_pairs_in += 1
                out.write(f"{rxn}\t" + "\t".join(seen) + "\n")
                n_rxns += 1
                n_pairs_out += len(seen)

        sort_proc.wait()

        if sort_proc.returncode != 0:
            tmp_output.unlink(missing_ok=True)
            sys.exit(f"sort exited with code {sort_proc.returncode}")

        # Atomic rename — only appears on success
        tmp_output.rename(output)

    except Exception as e:
        tmp_output.unlink(missing_ok=True)
        sort_proc.kill()
        sys.exit(f"Error during dedup: {e}")

    elapsed = time.time() - t_start
    output_size_mb = output.stat().st_size / 1e6
    duplication_pct = 100 * (1 - n_pairs_out / max(n_pairs_in, 1))

    print(f"── Done ──────────────────────────────────────────────────────────────")
    print(f"  Unique RXNs      : {n_rxns:,}")
    print(f"  Pairs in         : {n_pairs_in:,}")
    print(f"  Pairs out        : {n_pairs_out:,}")
    print(f"  Duplication rate : {duplication_pct:.1f}%")
    print(f"  Output size      : {output_size_mb:.1f} MB")
    print(f"  Time             : {format_elapsed(elapsed)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bucket-file", type=Path, required=True,
                        help="Path to the bucket .tsv file to process")
    parser.add_argument("--output",      type=Path, required=True,
                        help="Path to write deduplicated output")
    parser.add_argument("--tmp-dir",     default="/tmp",
                        help="Temp dir for sort (default: /tmp)")
    parser.add_argument("--parallel",    type=int, default=4,
                        help="sort --parallel value (default: 4)")
    args = parser.parse_args()

    output_dir = args.output.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    dedup_bucket(args.bucket_file, args.output, args.tmp_dir, args.parallel)


if __name__ == "__main__":
    main()
