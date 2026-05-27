#!/usr/bin/env python3
"""
build_mapping_db.py — Parse the large mapping CSV and build a SQLite database.

Usage:
  python build_mapping_db.py --mapping <mapping.csv> --db <mapping.db>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUTURE DATABASE CHANGES — update this block when the schema or logic evolves
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SCHEMA]
  - ec_index   : stores one (uniref90_id, ec_number) row per exploded EC term.
  - pfam_index : stores one (uniref90_id, pfam_id, pfam_signature) row per
                 exploded Pfam term. pfam_signature is the full sorted Pfam set
                 for that UniRef90 entry, used for set-equality (exact) matching.

  If additional mapping axes are needed in future (e.g. GO terms, KEGG
  orthology, CAZy families), follow the same pattern: add a new table
  <axis>_index with (uniref90_id, <axis>_id) and a corresponding index.

[NORMALISATION]
  - EC numbers: "-" is replaced with "_" at ingest (e.g. 1.1.1.- → 1.1.1._).
    This must also be applied identically at query time. If the source file
    ever uses a different placeholder (e.g. "*" or "n"), extend normalise_ec().
  - Pfam signatures: IDs are sorted lexicographically and joined with ";".
    The same sort-and-join must be applied at query time for exact matching.
    If the delimiter in the source file changes from ";", update split_field().

[FILTERING]
  - Rows where both ec_number and pfam_ids are "NA" are skipped entirely and
    never inserted. If a third axis is added (e.g. GO terms), the skip
    condition in build_db() must be extended to include that axis.

[INDICES]
  - idx_ec       on ec_index(ec_number)        — supports EC lookup
  - idx_pfam_id  on pfam_index(pfam_id)        — supports Pfam-relaxed lookup
  - idx_pfam_sig on pfam_index(pfam_signature) — supports Pfam-exact lookup
  If new tables are added, create a matching index on the lookup column.
  Consider partial indices (WHERE col != 'NA') if sparse columns are added.

[SOURCE FILE]
  - Expected columns: ID, UniRef100_ID, UniRef90_ID, UniRef50_ID,
    ncbi_taxonomy_id_uniref, accession, ncbi_taxonomy_id_protein,
    pfam_ids, ec_number.
  - COL_UNIREF90, COL_EC, COL_PFAM constants at the top of the file control
    which columns are read. Update these if the source file header changes.

[PERFORMANCE]
  - BATCH_SIZE and PAGE_CACHE_KB are tunable at the top of the file.
    Increase PAGE_CACHE_KB if more RAM is available during the build step.
  - Index creation happens after all inserts are complete (faster than
    incremental index updates). Do not move CREATE INDEX before the insert loop.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import argparse
import csv
import os
import sqlite3

# ── Tuning ────────────────────────────────────────────────────────────────────
BATCH_SIZE        = 500_000    # rows per executemany call
PROGRESS_INTERVAL = 500_000   # print progress every N source rows
PAGE_CACHE_KB     = 8_000_000   # SQLite page cache (~8 GB)

# ── Column names expected in the mapping file ─────────────────────────────────
COL_UNIREF90 = "UniRef90_ID"
COL_EC       = "ec_number"
COL_PFAM     = "pfam_ids"


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise_ec(ec: str) -> str:
    """Replace '-' with '_' in EC numbers (e.g. 1.1.1.- → 1.1.1._)."""
    return ec.strip().replace("-", "_")


def split_field(value: str) -> list[str]:
    """Split a semicolon-separated field; return [] for NA / empty."""
    v = value.strip()
    if not v or v.upper() == "NA":
        return []
    return [tok.strip() for tok in v.split(";") if tok.strip()]


def configure_conn(conn: sqlite3.Connection) -> None:
    """Apply performance PRAGMAs."""
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous  = NORMAL")
    conn.execute(f"PRAGMA cache_size  = -{PAGE_CACHE_KB}")
    conn.execute("PRAGMA temp_store   = MEMORY")


# ── BUILD ─────────────────────────────────────────────────────────────────────

def build_db(mapping_file: str, db_file: str) -> None:
    if os.path.exists(db_file):
        print(f"[build] Removing existing database: {db_file}")
        os.remove(db_file)

    conn = sqlite3.connect(db_file)
    configure_conn(conn)

    # Two normalised tables — one per lookup axis
    conn.executescript("""
        CREATE TABLE ec_index (
            uniref90_id TEXT NOT NULL,
            ec_number   TEXT NOT NULL
        );

        CREATE TABLE pfam_index (
            uniref90_id    TEXT NOT NULL,
            pfam_id        TEXT NOT NULL,
            pfam_signature TEXT NOT NULL   -- sorted, ";"-joined canonical set
        );
    """)

    ec_batch: list[tuple]   = []
    pfam_batch: list[tuple] = []
    n_written = n_skipped = 0

    print(f"[build] Streaming: {mapping_file}")

    with open(mapping_file, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        for row in reader:
            uid    = row[COL_UNIREF90].strip()
            ec_raw = row[COL_EC].strip()
            pf_raw = row[COL_PFAM].strip()

            ec_vals = split_field(ec_raw)
            pf_vals = split_field(pf_raw)

            # Skip rows where both EC and Pfam are absent / NA
            if not ec_vals and not pf_vals:
                n_skipped += 1
                continue

            # EC — normalise "-" → "_" before storing
            for ec in ec_vals:
                ec_batch.append((uid, normalise_ec(ec)))

            # Pfam — compute sorted signature for exact matching
            if pf_vals:
                pfams = sorted(pf_vals)
                sig   = ";".join(pfams)
                for pf in pfams:
                    pfam_batch.append((uid, pf, sig))

            n_written += 1

            # Flush batches
            if len(ec_batch) >= BATCH_SIZE:
                conn.executemany("INSERT INTO ec_index VALUES (?,?)", ec_batch)
                ec_batch.clear()

            if len(pfam_batch) >= BATCH_SIZE:
                conn.executemany("INSERT INTO pfam_index VALUES (?,?,?)", pfam_batch)
                pfam_batch.clear()

            if n_written % PROGRESS_INTERVAL == 0:
                conn.commit()
                print(f"  {n_written:>12,} rows written  |  {n_skipped:>10,} skipped")

    # Flush remainders
    if ec_batch:
        conn.executemany("INSERT INTO ec_index VALUES (?,?)", ec_batch)
    if pfam_batch:
        conn.executemany("INSERT INTO pfam_index VALUES (?,?,?)", pfam_batch)

    conn.commit()
    print(f"\n[build] Insertion done — written: {n_written:,}  |  skipped (NA/NA): {n_skipped:,}")
    print("[build] Building indices …")

    conn.executescript("""
        CREATE INDEX idx_ec       ON ec_index(ec_number);
        CREATE INDEX idx_pfam_id  ON pfam_index(pfam_id);
        CREATE INDEX idx_pfam_sig ON pfam_index(pfam_signature);
    """)

    conn.commit()
    conn.close()
    print(f"[build] Database ready: {db_file}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse the mapping CSV and build the UniRef90 SQLite database.",
    )
    parser.add_argument("--mapping", required=True, metavar="FILE",
                        help="Path to the large mapping CSV (e.g. mapping.csv)")
    parser.add_argument("--db",      required=True, metavar="FILE",
                        help="Output SQLite database path (e.g. mapping.db)")

    args = parser.parse_args()
    build_db(args.mapping, args.db)


if __name__ == "__main__":
    main()
