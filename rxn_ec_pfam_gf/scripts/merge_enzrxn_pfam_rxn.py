import click
import pandas as pd


@click.command()
@click.option(
    "--uniref",
    required=True,
    default="enzrxn_uniref_joined.csv",
    show_default=True,
    help="Path to enzrxn_uniref_joined.csv (columns: ENZRXN, MONOMER, PFAM, UNIPROT, entry_id)",
)
@click.option(
    "--rxn",
    required=True,
    default="enzrxn.txt",
    show_default=True,
    help="Path to enzrxn.txt (columns: ENZYME_RXN, REACTION)",
)
@click.option(
    "--output",
    "-o",
    default="enzrxn_pfam_rxn_merged.csv",
    show_default=True,
    help="Path to the output CSV file",
)
def merge(uniref, rxn, output):
    """Merge enzrxn_uniref_joined.csv with enzrxn_rxn.csv on the ENZRXN key.

    Joins file2 (ENZYME_RXN → REACTION) onto file1 (ENZRXN) and writes
    the columns ENZRXN, REACTION, PFAM, entry_id to the output file.
    """
    df_uniref = pd.read_csv(uniref, dtype=str)
    df_rxn = pd.read_csv(rxn, dtype=str)

    # Rename ENZYME_RXN to ENZRXN so the join key matches
    df_rxn = df_rxn.rename(columns={"ENZYME_RXN": "ENZRXN"})

    merged = df_uniref.merge(df_rxn, on="ENZRXN", how="outer")

    result = merged[["ENZRXN", "REACTION", "PFAM", "entry_id"]]
    # Rename entry_id to uniref90_ids for clarity
    result = result.rename(columns={"entry_id": "uniref90_ids"})

    result.to_csv(output, index=False)
    click.echo(f"Wrote {len(result):,} rows to {output}")


if __name__ == "__main__":
    merge()
