#!/usr/bin/env python3
import os
import click
import pandas as pd
import sys
from pathlib import Path

@click.command()
@click.option(
    '--ec-uniref',
    type=click.Path(exists=True, path_type=Path),
    help='Path to ec_uniref_grouped.csv file'
)
@click.option(
    '--rxn-ec-pfam',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to combined_rxn_ec_pfam.txt file'
)
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path),
    required=True,
    help='Output file directory'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)

def main(ec_uniref, rxn_ec_pfam, output_dir, verbose):
    """
    Merge reaction data with UniRef90 grouped data.
    
    This script merges reaction data from combined_rxn_ec_pfam.txt with UniRef90
    grouped data from ec_uniref_grouped.csv or pfam_uniref_grouped.csv.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = Path(output_dir)

    if verbose:
        click.echo("Starting file processing...")
    
    try:
        
        click.echo(f"Reading reaction data file: {rxn_ec_pfam}")
        rxn_ec_pfam_df = pd.read_csv(rxn_ec_pfam, sep='\t', header=0)
        
        click.echo(f"Reading grouped file: {ec_uniref}")
        uniref_df = pd.read_csv(ec_uniref)  # Expected columns: ec_number,uniref90_ids

        # RXN_EC_UNIFERF90
        # drop rows with missing values if 'EC_NUMBERS' and PFAM IDs are not present at the same time if EC_NUMBER is empty.
        rxn_ec_pfam_df.dropna(subset=['EC_NUMBERS', 'PFAM'], how='all', inplace=True)

        rxn_ec = rxn_ec_pfam_df.dropna(subset=['EC_NUMBERS'])
        rxn_ec = rxn_ec[['RXN', 'EC_NUMBERS']]


        # Explode the 'EC_NUMBERS' column to separate rows
        rxn_ec = rxn_ec.assign(ec_number=rxn_ec['EC_NUMBERS'].str.split(';'))
        rxn_ec = rxn_ec[['RXN', 'ec_number']].explode('ec_number')

        # Ensure the 'ec_number' column is of string type for matching
        rxn_ec['ec_number'] = rxn_ec['ec_number'].astype(str)

        # Merge the two DataFrames on ec_number or pfam_ids
        if 'ec_number' in uniref_df.columns:
            rxn_ec = pd.merge(rxn_ec, uniref_df, on='ec_number', how='left', sort=False)
            
            # Group by RXN and aggregate both uniref90_ids and ec_number
            df = rxn_ec.groupby('RXN', as_index=False).agg({
                'uniref90_ids': lambda x: ';'.join(sorted(set(i for val in x.dropna() for i in val.split(';') if i))),
                'ec_number': lambda x: ';'.join(sorted(set(i for val in x.dropna() for i in val.split(';') if i)))
            })
            # Drop rxns without UniRef90 IDs
            # Exclude rows where 'uniref90_ids' is empty
            df = df[df['uniref90_ids'].str.strip().astype(bool)]
            df.dropna(subset=['uniref90_ids'], inplace=True)
            
            # 1. Write RXN --> EC --> GENEFAMILIES
            df.to_csv(f"{output_path}/RXN_EC_UNIREF90.txt", index=False, sep='\t')
            click.echo(f"RXN --> EC --> GeneFamilies: {output_path}/RXN_EC_UNIREF90.txt")

            # 2. Write RXN --> GENEFAMILIES
            df[['RXN', 'uniref90_ids']].to_csv(f"{output_path}/RXN_UNIREF90.txt", index=False, sep='\t')
            click.echo(f"RXN --> GeneFamilies: {output_path}/RXN_UNIREF90.txt")
            
            # 3. Write RXN --> EC
            df[['RXN', 'ec_number']].to_csv(f"{output_path}/RXN_EC.txt", index=False, sep='\t')
            click.echo(f"RXN --> EC: {output_path}/RXN_EC.txt")
            
            # 4. Write RXN without GeneFamilies assigned to it.
            rxn_no_uniref = rxn_ec_pfam_df[~rxn_ec_pfam_df['RXN'].isin(df['RXN'])].copy()
            rxn_no_uniref.fillna('NA', inplace=True)
            rxn_no_uniref.to_csv(f"{output_path}/RXN_NO_UNIREF90.txt", index=False, sep='\t')
            click.echo(f"RXN without GeneFamilies: {output_path}/RXN_NO_UNIREF90.txt")

        else:
            click.echo("The provided EC file does not contain 'ec_number' column.", err=True)
            sys.exit(1)

        click.echo("File processing completed successfully.")

    except Exception as e:
        click.echo(f"An error occurred: {e}", err=True)
        sys.exit(1)
    

if __name__ == '__main__':
    main()