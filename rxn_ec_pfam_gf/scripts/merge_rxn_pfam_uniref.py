#!/usr/bin/env python3
import os
import click
import pandas as pd
import sys,csv
from pathlib import Path

@click.command()
@click.option(
    '--pfam-uniref',
    type=click.Path(exists=True, path_type=Path),
    help='Path to ec_uniref_grouped.csv file'
)
@click.option(
    '--rxn-ec-pfam',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to RXN_NO_UNIREF90.txt file'
)
@click.option('--only-pfam',
    is_flag=True,
    help='Process only PFAM data'
)
@click.option('--all-pfam',
    is_flag=True,
    help='get Genefamilies for individual PFAM IDs'
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

def main(pfam_uniref, rxn_ec_pfam, output_dir, only_pfam, all_pfam, verbose):
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
        rxn_ec_pfam = pd.read_csv(rxn_ec_pfam, sep='\t', header=0)
        
        click.echo(f"Reading grouped file: {pfam_uniref}")
        uniref_df = pd.read_csv(pfam_uniref)  # Expected columns: ec_number,uniref90_ids

        if only_pfam:
            click.echo(f"Retaining RXN: with PFAM value and EC_NUMBER is NA or empty")
            rxn_pfam=rxn_ec_pfam[rxn_ec_pfam['PFAM'].notna() & rxn_ec_pfam['EC_NUMBERS'].isna()]
        elif all_pfam:
            click.echo(f"Retaining RXN with PFAM")
            rxn_pfam=rxn_ec_pfam[rxn_ec_pfam['PFAM'].notna()]
        else:
            click.echo(f"Retaining RXN: with PFAM value and EC_NUMBER value")
            rxn_pfam=rxn_ec_pfam[rxn_ec_pfam['PFAM'].notna() & rxn_ec_pfam['EC_NUMBERS'].notna()]


        # Explode the 'EC_NUMBERS' column to separate rows
        if all_pfam:
            # Explode PFAM IDs if all_pfam is True
            click.echo(f"Exploding PFAM IDs for individual PFAM grouping")
            click.echo(f"{rxn_pfam}")
            rxn_pfam = rxn_pfam.assign(pfam_id=rxn_pfam['PFAM'].str.split(';')).explode('pfam_id')

            click.echo(f"Exploding PFAM IDs for individual PFAM grouping")
            uniref_df = (uniref_df.assign(pfam_id=uniref_df['pfam_id'].str.split(';')).explode('pfam_id'))
            # Group and re-aggregate
            uniref_df = (uniref_df.groupby('pfam_id', as_index=False).agg({'uniref90_ids': lambda x: ';'.join(sorted(set(x)))}))
            click.echo(f"{uniref_df}")
        else:
            rxn_pfam = rxn_pfam.assign(pfam_id=rxn_pfam['PFAM'].str.split(';').apply(lambda x: sorted(set(x))).str.join(';'))
        
        # Drop columns that are not needed
        if only_pfam:
            rxn_pfam.drop(columns=['PFAM', 'SOURCE_COUNT','EC_NUMBERS'], inplace=True)
            output1= f"{output_path}/RXN_PFAM_UNIREF90.txt"
            output2=f"{output_path}/RXN_UNIREF90.txt"
            output3= f"{output_path}/RXN_PFAM.txt"

        else:
            rxn_pfam.drop(columns=['PFAM', 'SOURCE_COUNT'], inplace=True)
            output1= f"{output_path}/RXN_EC_PFAM_UNIREF90.txt"
            output2= f"{output_path}/RXN_UNIREF90.txt"
            output3= f"{output_path}/RXN_PFAM.txt"


        click.echo(f"RXN_PFAM columns: {rxn_pfam.columns}")

        # Merge the two DataFrames on ec_number or pfam_ids
        if 'pfam_id' in uniref_df.columns:
            rxn_pfam = pd.merge(rxn_pfam, uniref_df, on='pfam_id', how='left', sort=False)
            # Prepare file handles
            with open(output1, 'w', newline='') as f1, \
                open(output2, 'w', newline='') as f2, \
                open(output3, 'w', newline='') as f3:

                writer1 = csv.writer(f1, delimiter='\t')
                writer2 = csv.writer(f2, delimiter='\t')
                writer3 = csv.writer(f3, delimiter='\t')

                # Write headers
                if only_pfam:
                    writer1.writerow(['RXN', 'uniref90_ids', 'pfam_id'])
                else:
                    writer1.writerow(['RXN', 'ec_number', 'uniref90_ids', 'pfam_id'])
                
                writer2.writerow(['RXN', 'uniref90_ids'])
                writer3.writerow(['RXN', 'pfam_id'])

                rxns_written = set()

                for rxn, group in rxn_pfam.groupby('RXN'):
                    uniref90_ids = sorted(set(i for val in group['uniref90_ids'].dropna() for i in val.split(';') if i))
                    if not uniref90_ids:
                        click.echo(f"Skipping RXN {rxn} as it has no UniRef90 IDs", err=True)
                    else:
                        pfam_id = sorted(set(i for val in group['pfam_id'].dropna() for i in val.split(';') if i))
                        
                        if "EC_NUMBERS" in group.columns:
                            ec_numbers = sorted(set(i for val in group['EC_NUMBERS'].dropna() for i in val.split(';') if i))
                            writer1.writerow([rxn, ';'.join(uniref90_ids), ';'.join(pfam_id), ';'.join(ec_numbers)])
                        else:
                            writer1.writerow([rxn, ';'.join(uniref90_ids), ';'.join(pfam_id)])
                        
                        writer2.writerow([rxn, ';'.join(uniref90_ids)])
                        writer3.writerow([rxn, ';'.join(pfam_id)])
                        # Force flush the files
                        f1.flush()
                        f2.flush()
                        f3.flush()
                        rxns_written.add(rxn)

            click.echo(f"RXN --> PFAM --> GeneFamilies: {output1}")
            click.echo(f"RXN --> GeneFamilies: {output2}")
            click.echo(f"RXN --> pfam_id: {output3}")


            # Handle RXNs without UniRef IDs
            rxn_no_uniref = rxn_ec_pfam[~rxn_ec_pfam['RXN'].isin(rxns_written)].copy()
            rxn_no_uniref.fillna('NA', inplace=True)
            rxn_no_uniref.to_csv(f"{output_path}/RXN_NO_UNIREF90.txt", index=False, sep='\t')
            click.echo(f"RXN without GeneFamilies: {output_path}/RXN_NO_UNIREF90.txt")
            click.echo("File processing completed successfully.")

        else:
            click.echo("The provided EC file does not contain 'ec_number' column.", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"An error occurred: {e}", err=True)
        sys.exit(1)
    

if __name__ == '__main__':
    main()