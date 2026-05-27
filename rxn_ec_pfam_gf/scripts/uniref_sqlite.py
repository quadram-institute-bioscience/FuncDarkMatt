#!/usr/bin/env python3
"""
Two-command CLI for UniRef90 SQLite index management.

Commands:
  build  --  Parse uniref90_members.csv once and store UniProtKB -> entry_id
             mappings in a SQLite database for fast repeated lookups.
  join   --  Match UNIPROT IDs from one or more enzrxn_expanded.csv files
             against the pre-built SQLite index and write enriched output CSVs.

Usage:
  # Build the index once (slow, do this once)
  python uniref_sqlite_cli.py build --mapping uniref90_members.csv --db uniref90.db

  # Join any number of enzrxn files instantly
  python uniref_sqlite_cli.py join --db uniref90.db --enzrxn file1.csv --enzrxn file2.csv
"""

import sys
import csv
import sqlite3
import click
from pathlib import Path
from typing import List

csv.field_size_limit(sys.maxsize)

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS uniref_members (
    uniprot_id TEXT PRIMARY KEY,
    entry_id   TEXT NOT NULL
);
"""

BATCH_SIZE = 100_000  # rows per INSERT batch


# ── helpers ───────────────────────────────────────────────────────────────────

def open_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous  = NORMAL;")
    conn.execute("PRAGMA cache_size   = -64000;")  # 64 MB page cache
    return conn


# ── build command ─────────────────────────────────────────────────────────────

@click.command("build")
@click.option(
    "--mapping", "-m",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to uniref90_members.csv"
)
@click.option(
    "--db", "-d",
    required=True,
    type=click.Path(writable=True),
    help="Output SQLite database file (will be created/overwritten)"
)
def build(mapping, db):
    """
    Build a SQLite index from uniref90_members.csv.

    Reads the UniProtKB column (semicolon-separated accessions) and maps
    each accession to its entry_id. Run this once; reuse the .db file forever.
    """
    click.echo("━" * 80)
    click.echo("UniRef90 SQLite Index Builder")
    click.echo("━" * 80)

    if Path(db).exists():
        click.confirm(f"\n⚠️  '{db}' already exists. Overwrite?", abort=True)
        Path(db).unlink()

    conn = open_db(db)
    conn.execute(DB_SCHEMA)
    conn.commit()

    line_count = 0
    insert_count = 0
    current_entry_id = None
    batch: List[tuple] = []

    click.echo(f"\n📖 Reading: {mapping}")
    click.echo("   Indexing (this will take several minutes for 87M-line files)...")

    try:
        with open(mapping, "r", encoding="utf-8", buffering=8192 * 16) as f:
            header = f.readline()

            for raw_line in f:
                line_count += 1

                try:
                    row = next(csv.DictReader([header.strip(), raw_line.strip()]))
                except csv.Error as e:
                    click.echo(
                        f"❌ CSV error at line {line_count + 1} "
                        f"(last entry_id: {current_entry_id!r}): {e}",
                        err=True,
                    )
                    conn.close()
                    raise click.Abort()

                current_entry_id = row["entry_id"].strip()
                uniprot_kb = row.get("UniProtKB", "").strip()

                if current_entry_id and uniprot_kb:
                    for uid in uniprot_kb.split(";"):
                        uid = uid.strip()
                        if uid:
                            batch.append((uid, current_entry_id))

                if len(batch) >= BATCH_SIZE:
                    conn.executemany(
                        "INSERT OR IGNORE INTO uniref_members (uniprot_id, entry_id) VALUES (?, ?)",
                        batch,
                    )
                    conn.commit()
                    insert_count += len(batch)
                    batch.clear()

                if line_count % 1_000_000 == 0:
                    click.echo(f"   Processed {line_count:,} lines, {insert_count:,} accessions inserted...")

        # flush remaining batch
        if batch:
            conn.executemany(
                "INSERT OR IGNORE INTO uniref_members (uniprot_id, entry_id) VALUES (?, ?)",
                batch,
            )
            conn.commit()
            insert_count += len(batch)

    except FileNotFoundError:
        click.echo(f"❌ Mapping file not found: {mapping}", err=True)
        conn.close()
        raise click.Abort()
    except Exception as e:
        click.echo(
            f"❌ Error at line {line_count + 1} (entry_id: {current_entry_id!r}): {e}",
            err=True,
        )
        conn.close()
        raise click.Abort()

    conn.close()

    click.echo(f"\n✅ Index built successfully!")
    click.echo(f"   Lines scanned:       {line_count:,}")
    click.echo(f"   Accessions indexed:  {insert_count:,}")
    click.echo(f"   Database:            {db}")
    click.echo("━" * 80)


# ── join command ──────────────────────────────────────────────────────────────

@click.command("join")
@click.option(
    "--db", "-d",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to the pre-built SQLite database"
)
@click.option(
    "--enzrxn", "-e",
    required=True,
    type=click.Path(exists=True, readable=True),
    help="Path to a single enzrxn_expanded.csv file"
)
@click.option(
    "--output", "-o",
    type=click.Path(writable=True),
    default=None,
    help="Output CSV file path (default: <input_stem>_uniref_joined.csv)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show sample matched entries"
)
def join(db, enzrxn, output, verbose):
    """
    Join a single enzrxn_expanded.csv against the pre-built SQLite index.

    Designed to be called once per file, e.g. via SLURM array jobs.
    All UNIPROT IDs in the file are collected first, then resolved in one
    bulk SQLite query — no per-row DB calls.

    Output: <input_stem>_uniref_joined.csv (or specify with --output)
    """
    click.echo("━" * 80)
    click.echo("ENZRXN - UniRef90 Join (SQLite)")
    click.echo("━" * 80)

    output_file = output or f"{Path(enzrxn).stem}_uniref_joined.csv"

    # ── Step 1: read the enzrxn file ─────────────────────────────────────────
    click.echo(f"\n📖 Reading: {enzrxn}")
    rows = []
    uniprot_ids = set()

    try:
        with open(enzrxn, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                uid = row["UNIPROT"].strip()
                rows.append({
                    "ENZRXN":  row["ENZRXN"].strip(),
                    "MONOMER": row["MONOMER"].strip(),
                    "PFAM":    row["PFAM"].strip(),
                    "UNIPROT": uid,
                })
                for single_uid in uid.split(";"):
                    single_uid = single_uid.strip()
                    if single_uid:
                        uniprot_ids.add(single_uid)
    except FileNotFoundError:
        click.echo(f"❌ File not found: {enzrxn}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error reading {enzrxn}: {e}", err=True)
        raise click.Abort()

    click.echo(f"   ✓ {len(rows):,} rows | {len(uniprot_ids):,} unique UNIPROT IDs")

    # ── Step 2: bulk query SQLite ─────────────────────────────────────────────
    click.echo(f"\n🗄️  Querying index: {db}")
    SQLITE_VAR_LIMIT = 900
    uniref_map = {}
    id_list = list(uniprot_ids)

    try:
        conn = open_db(db)
        for i in range(0, len(id_list), SQLITE_VAR_LIMIT):
            batch = id_list[i:i + SQLITE_VAR_LIMIT]
            placeholders = ",".join("?" * len(batch))
            cur = conn.execute(
                f"SELECT uniprot_id, entry_id FROM uniref_members "
                f"WHERE uniprot_id IN ({placeholders})",
                batch,
            )
            for uniprot_id, entry_id in cur.fetchall():
                uniref_map[uniprot_id] = entry_id
        conn.close()
    except Exception as e:
        click.echo(f"❌ SQLite error: {e}", err=True)
        raise click.Abort()

    click.echo(f"   ✓ {len(uniref_map):,} IDs resolved to entry_id")

    # ── Step 3: join and write output ─────────────────────────────────────────
    joined_data = []
    matched = 0
    unmatched = 0

    for row in rows:
        entry_ids = [
            uniref_map[uid.strip()]
            for uid in row["UNIPROT"].split(";")
            if uid.strip() and uid.strip() in uniref_map
        ]
        entry_id = ";".join(entry_ids)
        if entry_id:
            matched += 1
        else:
            unmatched += 1
        joined_data.append({**row, "entry_id": entry_id})

    with open(output_file, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(
            out, fieldnames=["ENZRXN", "MONOMER", "PFAM", "UNIPROT", "entry_id"]
        )
        writer.writeheader()
        writer.writerows(joined_data)

    total = len(rows)
    pct = matched / total * 100 if total else 0
    click.echo(f"\n📊 Results:")
    click.echo(f"   Total:     {total:,}")
    click.echo(f"   Matched:   {matched:,} ({pct:.1f}%)")
    click.echo(f"   Unmatched: {unmatched:,} ({100 - pct:.1f}%)")

    if verbose:
        click.echo(f"\n📋 Sample matched entries (first 5):")
        for entry in [r for r in joined_data if r["entry_id"]][:5]:
            click.echo(f"   UNIPROT={entry['UNIPROT']}  entry_id={entry['entry_id']}")

    click.echo(f"\n💾 Written: {output_file}")
    click.echo("\n✅ Done!")
    click.echo("━" * 80)


# ── CLI group ─────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """UniRef90 SQLite index builder and ENZRXN joiner."""
    pass


cli.add_command(build)
cli.add_command(join)


if __name__ == "__main__":
    cli()
