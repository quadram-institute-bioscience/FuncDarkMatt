#!/usr/bin/env python3
"""
Merge all per-file RXN -> UniRef90 mappings into a single deduplicated table.
Uses an external sort-merge strategy to avoid loading all data into memory.

Usage:
    python rxn_bicoyc_merge.py <input_dir> [--output merged_rxn_uniref90.tsv] [--pattern "*.txt"]
"""

import argparse
import subprocess
import sys
import tempfile
import time
from itertools import groupby
from pathlib import Path


def format_elapsed(seconds: float) -> str:
    """Return a human-readable elapsed time string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m {s:.1f}s"
    elif m > 0:
        return f"{m}m {s:.1f}s"
    else:
        return f"{s:.1f}s"


def stream_pairs(input_dir: Path, pattern: str):
    """Yield (rxn, uniref_id) pairs from all matching files."""
    files = sorted(input_dir.glob(pattern))
    if not files:
        sys.exit(f"No files matching '{pattern}' found in {input_dir}")

    print(f"Found {len(files)} files. Streaming pairs...", flush=True)
    t_start = time.time()

    for i, fpath in enumerate(files, 1):
        if i % 1000 == 0:
            elapsed = time.time() - t_start
            rate = i / elapsed
            remaining = (len(files) - i) / rate
            print(f"  {i}/{len(files)} files processed | "
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
                    for uid in parts[1].split(";"):
                        uid = uid.strip()
                        if uid:
                            yield rxn, uid
        except Exception as e:
            print(f"  WARNING: skipping {fpath.name}: {e}", file=sys.stderr)


def merge_files(input_dir: Path, pattern: str, output: Path, tmp_dir: Path = None):
    t_total = time.time()

    tmpdir_kwargs = {"dir": str(tmp_dir)} if tmp_dir else {}

    with tempfile.TemporaryDirectory(**tmpdir_kwargs) as tmpdir:
        pairs_file = Path(tmpdir) / "pairs.tsv"
        sorted_file = Path(tmpdir) / "pairs_sorted.tsv"

        # ── Phase 1: stream all (rxn, uid) pairs to disk ──────────────────────
        print("\n── Phase 1: writing pairs to temp file ──────────────────────────",
              flush=True)
        t1_start = time.time()
        n_pairs = 0

        with open(pairs_file, "w") as fh:
            for rxn, uid in stream_pairs(input_dir, pattern):
                fh.write(f"{rxn}\t{uid}\n")
                n_pairs += 1

        t1_end = time.time()
        pairs_size_gb = pairs_file.stat().st_size / 1e9
        print(f"  Pairs written  : {n_pairs:,}", flush=True)
        print(f"  Pairs file size: {pairs_size_gb:.2f} GB", flush=True)
        print(f"  Phase 1 time   : {format_elapsed(t1_end - t1_start)}", flush=True)

        # ── Phase 2: external sort (disk-based, low RAM) ───────────────────────
        print("\n── Phase 2: external sort ───────────────────────────────────────",
              flush=True)
        t2_start = time.time()

        subprocess.run(
            ["sort", "--parallel=4", "-T", tmpdir, "-k1,1", "-k2,2",
             "-o", str(sorted_file), str(pairs_file)],
            check=True
        )

        t2_end = time.time()
        sorted_size_gb = sorted_file.stat().st_size / 1e9
        print(f"  Sorted file size: {sorted_size_gb:.2f} GB", flush=True)
        print(f"  Phase 2 time    : {format_elapsed(t2_end - t2_start)}", flush=True)

        pairs_file.unlink()  # free disk space before Phase 3

        # ── Phase 3: stream sorted file, deduplicate, write output ────────────
        print("\n── Phase 3: deduplicating and writing output ────────────────────",
              flush=True)
        t3_start = time.time()
        n_rxns = 0

        with open(sorted_file) as fh, open(output, "w") as out:
            for rxn, group in groupby(fh, key=lambda line: line.split("\t")[0]):
                seen = {}
                for line in group:
                    uid = line.rstrip("\n").split("\t", 1)[1]
                    seen[uid] = None  # insertion-order dict = stable dedup
                out.write(f"{rxn}\t" + "\t".join(seen) + "\n")
                n_rxns += 1
                if n_rxns % 500000 == 0:
                    print(f"  {n_rxns:,} RXNs written so far...", flush=True)

        t3_end = time.time()
        print(f"  Phase 3 time: {format_elapsed(t3_end - t3_start)}", flush=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    t_total_end = time.time()
    output_size_gb = output.stat().st_size / 1e9
    print(f"\n── Done ─────────────────────────────────────────────────────────────")
    print(f"  Unique RXNs written : {n_rxns:,}")
    print(f"  Output file         : {output}")
    print(f"  Output size         : {output_size_gb:.2f} GB")
    print(f"  Total time          : {format_elapsed(t_total_end - t_total)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_dir", type=Path,
                        help="Directory containing input files")
    parser.add_argument("--output", type=Path, default=Path("merged_rxn_uniref90.tsv"),
                        help="Output TSV path (default: merged_rxn_uniref90.tsv)")
    parser.add_argument("--pattern", default="*.txt",
                        help="Glob pattern for input files (default: *.txt)")
    parser.add_argument("--tmp-dir", type=Path, default=None,
                        help="Directory for temporary sort files (default: system /tmp). "
                             "Set to scratch if /tmp is small, e.g. /qib/scratch/users/tiwari/tmp")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        sys.exit(f"Not a directory: {args.input_dir}")

    if args.tmp_dir and not args.tmp_dir.is_dir():
        sys.exit(f"--tmp-dir is not a directory: {args.tmp_dir}")

    merge_files(args.input_dir, args.pattern, args.output, args.tmp_dir)


if __name__ == "__main__":
    main()