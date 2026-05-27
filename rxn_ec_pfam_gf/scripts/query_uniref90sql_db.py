#!/usr/bin/env python3
"""
query_mapping_db.py — Query the UniRef90 SQLite database against a RXN input file
                      to propagate UniRef90 IDs via three matching strategies.

Usage:
  python query_mapping_db.py --db mapping.db --input rxn.tsv --output out.tsv --mode ec_propagation
  python query_mapping_db.py --db mapping.db --input rxn.tsv --output out.tsv --mode pfam_exact_propagation
  python query_mapping_db.py --db mapping.db --input rxn.tsv --output out.tsv --mode pfam_relaxed_propagation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUTURE CHANGES — update this block when input format or logic evolves
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[INPUT FORMAT]
  Expected tab-separated columns: RXN, EC_NUMBERS, PFAM, uniref90_ids
  - EC_NUMBERS : multiple ECs separated by ";"  (e.g. 1.1.1.191;1.1.1.2)
  - PFAM       : one or more Pfam sets separated by "|"; within each set,
                 individual Pfam IDs are separated by ";"
                 (e.g. PF00613;PF00454|PF00454 → two sets)
  - uniref90_ids: existing UniRef90 IDs (not used for querying; preserved
                  in output for reference)
  If the delimiter, column names, or NA sentinel change, update the
  COL_* constants and split_* helpers at the top of this file.

[MODULES / MODES]
  Three propagation modes are implemented:
  1. ec_propagation            — looks up ec_index by EC number(s)
  2. pfam_exact_propagation    — looks up pfam_index by sorted Pfam signature;
                                 each "|"-separated set is screened independently
                                 and results are unioned
  3. pfam_relaxed_propagation  — looks up pfam_index by individual Pfam ID;
                                 any single overlap is a hit; all Pfam IDs
                                 across all "|"-separated sets are pooled
  To add a new mode (e.g. go_propagation), write a query function with
  signature fn(conn, raw_value) -> set[str] and register it in MODES.

[RESIDUAL OUTPUT]
  An optional --residual FILE argument writes a second output in the original
  input format (RXN, EC_NUMBERS, PFAM, uniref90_ids) containing two categories
  of unpropagated rows for the current mode:
    Category A — queried but no hits : lookup column had a value but the DB
                 returned no matching UniRef90 IDs.
    Category B — not used in this mode: lookup column was NA/empty so the row
                 was never queried at all.
  To build a cross-mode residual (rows unpropagated across ALL three modes),
  run all three modes with --residual, then intersect the three residual files
  on the RXN column downstream (e.g. with pandas or a shell join).

[NORMALISATION]
  - EC numbers: "-" replaced with "_" at query time to match the ingest
    normalisation in build_mapping_db.py. Keep these in sync.
  - Pfam signatures: sorted lexicographically and joined with ";" — must
    match exactly how pfam_signature was computed at build time.

[OUTPUT FORMAT]
  Tab-separated: RXN \t propagated_uniref90_ids
  - propagated_uniref90_ids: sorted, ";"-joined UniRef90 IDs, or "NA" if
    no match was found.
  If additional columns are needed in output (e.g. EC_NUMBERS, PFAM,
  original uniref90_ids), extend the writer.writerow() call in run_query().
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import argparse
import csv
import os
import sqlite3
import sys
from typing import Optional

# ── Tuning ────────────────────────────────────────────────────────────────────
PAGE_CACHE_KB = 512_000   # SQLite page cache (~512 MB)

# ── Column names expected in the input TSV ────────────────────────────────────
COL_RXN  = "RXN"
COL_EC   = "EC_NUMBERS"
COL_PFAM = "PFAM"


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalise_ec(ec: str) -> str:
    """Replace '-' with '_' in EC numbers — must mirror build_mapping_db.py."""
    return ec.strip().replace("-", "_")


def split_semicolon(value: str) -> list[str]:
    """Split a semicolon-delimited field; return [] for NA / empty."""
    v = value.strip()
    if not v or v.upper() == "NA":
        return []
    return [tok.strip() for tok in v.split(";") if tok.strip()]


def parse_pfam_sets(value: str) -> list[frozenset[str]]:
    """
    Parse the PFAM column into a list of independent Pfam sets.

    "|" separates independent sets (each screened separately in exact mode).
    ";" separates individual Pfam IDs within a set.

    Examples:
      "PF00106"              → [{PF00106}]
      "PF00984;PF03720"      → [{PF00984, PF03720}]
      "PF00613;PF00454|PF00454" → [{PF00613, PF00454}, {PF00454}]
    """
    v = value.strip()
    if not v or v.upper() == "NA":
        return []
    sets = []
    for group in v.split("|"):
        members = frozenset(p.strip() for p in group.split(";") if p.strip())
        if members:
            sets.append(members)
    return sets


def configure_conn(conn: sqlite3.Connection) -> None:
    """Apply read-optimised PRAGMAs."""
    #conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous  = NORMAL")
    conn.execute(f"PRAGMA cache_size  = -{PAGE_CACHE_KB}")
    conn.execute("PRAGMA temp_store   = MEMORY")


# ── Propagation modules ───────────────────────────────────────────────────────

def ec_propagation(conn: sqlite3.Connection, ec_raw: str) -> set[str]:
    """
    Match UniRef90 IDs via EC number(s).
    Multiple ECs (";"-separated) are all looked up; results are unioned.
    EC normalisation ("-" → "_") is applied before querying.
    """
    ecs = [normalise_ec(e) for e in split_semicolon(ec_raw)]
    if not ecs:
        return set()
    ph   = ",".join("?" * len(ecs))
    rows = conn.execute(
        f"SELECT DISTINCT uniref90_id FROM ec_index WHERE ec_number IN ({ph})", ecs
    ).fetchall()
    return {r[0] for r in rows}


def pfam_exact_propagation(conn: sqlite3.Connection, pfam_raw: str) -> set[str]:
    """
    Match UniRef90 IDs via exact Pfam set equality.

    Each "|"-separated Pfam set is screened independently against
    pfam_index.pfam_signature (a sorted, ";"-joined canonical form).
    Results across all sets are unioned.
    Order of Pfam IDs within a set does not matter — sorting normalises it.
    """
    pfam_sets = parse_pfam_sets(pfam_raw)
    if not pfam_sets:
        return set()
    hits: set[str] = set()
    for pf_set in pfam_sets:
        sig  = ";".join(sorted(pf_set))   # must match build-time signature logic
        rows = conn.execute(
            "SELECT DISTINCT uniref90_id FROM pfam_index WHERE pfam_signature = ?",
            (sig,)
        ).fetchall()
        hits.update(r[0] for r in rows)
    return hits


def pfam_relaxed_propagation(conn: sqlite3.Connection, pfam_raw: str) -> set[str]:
    """
    Match UniRef90 IDs via any single overlapping Pfam term.

    All Pfam IDs across all "|"-separated sets are pooled into one
    collection and looked up in a single IN query.
    """
    pfam_sets = parse_pfam_sets(pfam_raw)
    if not pfam_sets:
        return set()
    all_pfams = list({pf for pf_set in pfam_sets for pf in pf_set})
    ph        = ",".join("?" * len(all_pfams))
    rows      = conn.execute(
        f"SELECT DISTINCT uniref90_id FROM pfam_index WHERE pfam_id IN ({ph})",
        all_pfams
    ).fetchall()
    return {r[0] for r in rows}


# ── Mode registry — add new modes here ────────────────────────────────────────
# Tuple: (query_fn, lookup_col, skip_if_existing)
# skip_if_existing=True  → rows that already carry pre-existing GFs are skipped
#                          entirely (not queried, not written to main output).
#                          Use for last-resort modes (e.g. pfam_relaxed) where a
#                          broad match should only fire when no GF exists at all.
# skip_if_existing=False → pre-existing GFs are preserved but do not suppress
#                          the lookup; mode still runs regardless.
MODES: dict[str, tuple] = {
    "ec_propagation":           (ec_propagation,           COL_EC,   False),
    "pfam_exact_propagation":   (pfam_exact_propagation,   COL_PFAM, False),
    "pfam_relaxed_propagation": (pfam_relaxed_propagation, COL_PFAM, True),
}


# ── Runner ────────────────────────────────────────────────────────────────────

def run_query(
    db_file: str,
    input_file: str,
    output_file: str,
    mode: str,
    residual_file: Optional[str] = None,
) -> None:
    query_fn, lookup_col, skip_if_existing = MODES[mode]

    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    configure_conn(conn)

    # Original input columns preserved for residual output
    INPUT_COLS = [COL_RXN, COL_EC, COL_PFAM, "uniref90_ids"]

    n_hit = n_miss = n_skipped = n_has_existing = 0

    with open(input_file,  newline="", encoding="utf-8") as fh_in,  \
         open(output_file, "w", newline="", encoding="utf-8") as fh_out, \
         (open(residual_file, "w", newline="", encoding="utf-8")
          if residual_file else open(os.devnull, "w")) as fh_res:

        reader = csv.DictReader(fh_in, delimiter="\t")

        if lookup_col not in (reader.fieldnames or []):
            sys.exit(
                f"[{mode}] Column '{lookup_col}' not found in {input_file}.\n"
                f"         Available columns: {reader.fieldnames}"
            )

        # Main output writer
        main_writer = csv.writer(fh_out, delimiter="\t")
        main_writer.writerow(["RXN", "propagated_uniref90_ids"])

        # Residual writer — original input format
        res_writer = csv.DictWriter(
            fh_res, fieldnames=INPUT_COLS, delimiter="\t", extrasaction="ignore"
        )
        if residual_file:
            res_writer.writeheader()

        for row in reader:
            lookup_val   = row[lookup_col].strip()
            is_na        = not lookup_val or lookup_val.upper() == "NA"
            existing_ids = set(split_semicolon(row.get("uniref90_ids", "")))

            if skip_if_existing and existing_ids:
                # This mode is last-resort only — skip RXNs that already have GFs;
                # pass them to the residual so downstream processing can still use them
                if residual_file:
                    res_writer.writerow(row)
                n_has_existing += 1
                continue

            if is_na:
                # Category B — not used in this mode (lookup column is NA);
                # do NOT write to main output — pass to residual so PFAM modes
                # can attempt propagation downstream.
                if residual_file:
                    res_writer.writerow(row)
                n_skipped += 1
            else:
                hits = query_fn(conn, lookup_val)
                if hits:
                    # EC lookup contributed GFs — write to main output (union with existing)
                    combined = hits | existing_ids
                    main_writer.writerow(
                        [row[COL_RXN], ";".join(sorted(combined))]
                    )
                    n_hit += 1
                else:
                    # Category A — queried but no hits (includes Scenario 3: has
                    # pre-existing GFs but EC added nothing); pass to residual so
                    # other modes can attempt further propagation
                    if residual_file:
                        res_writer.writerow(row)
                    n_miss += 1

    conn.close()
    existing_note = f"  |  skipped (has existing GFs): {n_has_existing:,}" if skip_if_existing else ""
    print(
        f"[{mode}] Done — "
        f"hits: {n_hit:,}  |  misses: {n_miss:,}  |  skipped (NA): {n_skipped:,}"
        f"{existing_note}"
        f"  →  {output_file}"
    )
    if residual_file:
        residual_total = n_miss + n_skipped + n_has_existing
        residual_detail = (
            f"{n_miss:,} no-hit + {n_skipped:,} NA"
            + (f" + {n_has_existing:,} has-existing-GFs" if skip_if_existing else "")
        )
        print(f"[{mode}] Residual ({residual_total:,} rows: {residual_detail})  →  {residual_file}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Propagate UniRef90 IDs into a RXN file via SQLite lookups.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db",     required=True, metavar="FILE",
                        help="SQLite database built by build_mapping_db.py")
    parser.add_argument("--input",  required=True, metavar="FILE",
                        help="Input RXN TSV file")
    parser.add_argument("--output", required=True, metavar="FILE",
                        help="Output TSV: RXN + propagated_uniref90_ids")
    parser.add_argument("--mode",   required=True, choices=list(MODES.keys()),
                        help="Propagation strategy to apply")

    parser.add_argument("--residual", default=None, metavar="FILE",
                        help=(
                            "Optional: write unpropagated rows in original input format. "
                            "Includes Category A (queried, no hits) and "
                            "Category B (lookup column was NA, not used in this mode)."
                        ))

    args = parser.parse_args()
    run_query(args.db, args.input, args.output, args.mode, args.residual)


if __name__ == "__main__":
    main()
