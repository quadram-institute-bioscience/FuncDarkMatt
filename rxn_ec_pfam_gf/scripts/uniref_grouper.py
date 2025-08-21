#!/usr/bin/env python3

import click
import pandas as pd
import sys
from pathlib import Path


@click.command()
@click.option(
    '--uniref-file',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to uniref90_map_pf_ec.csv file'
)
@click.option(
    '--group-by',
    type=click.Choice(['ec_number', 'pfam_ids'], case_sensitive=False),
    default='ec_number',
    show_default=True,
    help='Group by ec_number or pfam_ids'
)
@click.option(
    '--output-file',
    type=click.Path(path_type=Path),
    default='ec_grouped',
    help='Output file (default: ec_grouped)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def main(uniref_file, output_file, group_by, verbose):
    """
    Parse and process uniref90_map_pf_ec.csv file.
    
    This script reads the uniref90_map_pf_ec.csv file and creates two grouped outputs:
    - EC number groups: UniRef90 IDs grouped by EC number
    - PFAM ID groups: UniRef90 IDs grouped by individual PFAM IDs
    """
    
    if verbose:
        click.echo("Starting file processing...")
    
    try:
        # Read uniref90_map_pf_ec.csv
        if verbose:
            click.echo(f"Reading UniRef file: {uniref_file}")
        
        uniref_df = pd.read_csv(uniref_file)
        
        # Expected columns for uniref file
        expected_uniref_cols = [
            'ID', 'UniRef100_ID', 'UniRef90_ID', 'UniRef50_ID', 
            'ncbi_taxonomy_id_uniref', 'accession', 'ncbi_taxonomy_id_protein',
            'pfam_ids', 'ec_number'
        ]
        
        # Validate columns
        missing_cols = set(expected_uniref_cols) - set(uniref_df.columns)
        if missing_cols:
            click.echo(f"Warning: Missing columns in UniRef file: {missing_cols}", err=True)
        
        # Process UniRef data
        if verbose:
            click.echo("\n--- Processing UniRef Data ---")
        
        if group_by == 'ec_number':
            if verbose:
                click.echo("\n--- Grouping by EC Number ---")
            
            # Keep only required columns
            uniref_processed = uniref_df[['UniRef90_ID', 'ec_number']].copy()
        
            # Filter out rows with null EC numbers for this grouping
            ec_grouped_data = uniref_processed.dropna(subset=['ec_number'])
        
            if len(ec_grouped_data) > 0:
                # Split multiple EC numbers in a row and explode
                ec_grouped_data = ec_grouped_data.assign(ec_number=ec_grouped_data['ec_number'].str.split(';')).explode('ec_number')
                ec_grouped_data['ec_number'] = ec_grouped_data['ec_number'].str.strip()
                # Normalize EC numbers: remove trailing dots/underscores, then pad
                def normalize_ec(ec):
                    ec = ec.rstrip('.-')  # Remove trailing . and -
                    parts = ec.split('.')
                    # Pad to 4 parts with '_'
                    while len(parts) < 4:
                        parts.append('_')
                    return '.'.join(parts)
                
                ec_grouped_data['ec_number'] = ec_grouped_data['ec_number'].apply(normalize_ec)
                ec_grouped = ec_grouped_data.groupby('ec_number')['UniRef90_ID'].apply(lambda x: ';'.join(sorted(x.unique()))).reset_index()
                ec_grouped.columns = ['ec_number', 'uniref90_ids']
                
                if verbose:
                    click.echo(f"EC number groups: {len(ec_grouped)}")
                    click.echo(f"Sample: {ec_grouped.head()}")
            
            else:
                ec_grouped = pd.DataFrame(columns=['ec_number', 'uniref90_ids'])
                if verbose:
                    click.echo("No records with EC numbers found")
        
        elif group_by == 'pfam_ids':
            if verbose:
                click.echo("\n--- Grouping by PFAM IDs ---")
            # Keep only required columns
            # In uniref_df retain the rows where only pfam_ids are present, not both pfam_ids and ec_number
            uniref_df = uniref_df[uniref_df['pfam_ids'].notna() & uniref_df['ec_number'].isna()]
            uniref_df.to_csv("uniref_file.csv", index=False)
            if not uniref_df.empty:
                uniref_processed = uniref_df[['UniRef90_ID', 'pfam_ids']].copy()
                # Filter out rows with null PFAM IDs for this grouping
                pfam_grouped_data = uniref_processed.dropna(subset=['pfam_ids'])
            if len(pfam_grouped_data) > 0:
                pfam_grouped_data['pfam_ids'] = (pfam_grouped_data['pfam_ids'].str.split(';').apply(lambda x: sorted(set(x))).str.join(';'))
                grouped = pfam_grouped_data.groupby('pfam_ids')['UniRef90_ID'].apply(lambda x: ';'.join(sorted(x.unique()))).reset_index()
                grouped.columns = ['pfam_id', 'uniref90_ids']
            else:
                grouped = pd.DataFrame(columns=['pfam_id', 'uniref90_ids'])
                if verbose:
                    click.echo("No records with PFAM IDs found")
            if verbose:
                click.echo(f"PFAM ID groups: {len(grouped)}")
                click.echo(f"Sample: {grouped.head()}")

        # Write output
        grouped.to_csv(output_file, index=False)
        
    except FileNotFoundError as e:
        click.echo(f"Error: File not found - {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error processing files: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()