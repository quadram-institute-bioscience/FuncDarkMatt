import click
import pandas as pd
import numpy as np

@click.command()
@click.option('--file1', required=True, help='Path to merge_reactions.tsv (TSV with header: UNIQUE-ID, EC-NUMBER, ENZYMATIC-REACTION)')
@click.option('--file2', required=True, help='Path to enzrxn_rxn_pfam_gf.csv (CSV with header)')
@click.option('--output', required=True, help='Path to output TSV file')
def merge_reaction_files(file1, file2, output):
    """
    Merge reaction files based on RXN/REACTION columns.
    
    File1 (merge_reactions.tsv): TSV with header and 3 fixed columns
    - UNIQUE-ID: RXN ID
    - EC-NUMBER: pipe-separated EC numbers (can be empty)
    - ENZYMATIC-REACTION: pipe-separated ENZRXN IDs (not used; ENZRXN/PFAM data comes from file2)
    
    File2 (enzrxn_rxn_pfam_gf.csv): CSV with fixed 4 columns (header included)
    - ENZYME_RXN (discarded)
    - REACTION 
    - PFAM
    - uniref90_ids
    
    Keep ALL reactions from both files, including:
    - Reactions that have PFAM only
    - Reactions that have EC numbers only  
    - Reactions that have both PFAM and EC numbers
    - Reactions that have neither PFAM nor EC numbers
    """
    
    try:
        # Read File1 (reactions_links.dat) - no header, tab-separated, variable columns
        click.echo(f"Reading File1: {file1}")
        
        # Read the file line by line; new format has a header and 3 fixed tab-separated columns:
        #   UNIQUE-ID   EC-NUMBER (pipe-separated)   ENZYMATIC-REACTION (pipe-separated, ignored)
        with open(file1, 'r') as f:
            lines = f.readlines()

        # Process each line to extract RXN and EC numbers
        file1_data = []

        for line in lines:
            line = line.strip()
            # Skip empty lines, comment lines, and the header line
            if not line or line.startswith('#') or line.startswith('UNIQUE-ID'):
                continue

            parts = line.split('\t')
            rxn_id = parts[0]
            ec_field = parts[1].strip() if len(parts) > 1 else ''
            # ENZYMATIC-REACTION (parts[2]) is not used here; ENZRXN data comes from file2

            if not ec_field:
                ec = ['NA']
            else:
                # EC numbers are pipe-separated in the new format
                ec = [e.strip() for e in ec_field.split('|') if e.strip()]
                # each EC should have 3 decimal places like EC-2.7.1.221
                # If there are EC with less than 3 decimal places, pad with '._' for each missing decimal
                # Remove EC- prefix before normalising
                ec = [e.replace('EC-', '') for e in ec]
                ec = [e if e.count('.') == 3 else e + '._' * (3 - e.count('.')) for e in ec]
                ec = [';'.join(ec)]

            file1_data.append([rxn_id] + ec)
        
        # Create DataFrame with two columns: RXN and EC numbers
        df1_cols = ['RXN'] + ['EC_NUMBERS']
        df1 = pd.DataFrame(file1_data, columns=df1_cols)
        
        click.echo(f"File1 processed: {len(df1)} reactions found")
        rxn_with_ec = len(df1[~df1['EC_NUMBERS'].isin(['', 'NA'])])
        rxn_without_ec = len(df1[df1['EC_NUMBERS'] == 'NA'])
        click.echo(f"  - Reactions with EC numbers: {rxn_with_ec}")
        click.echo(f"  - Reactions without EC numbers: {rxn_without_ec}")
        
        # Read File2 (rxn_pfam.tsv) - has header, tab-separated
        click.echo(f"Reading File2: {file2}")
        df2 = pd.read_csv(file2, sep=',')
        
        # Check if required columns exist in File2
        if not all(col in df2.columns for col in ["ENZRXN","REACTION","PFAM","uniref90_ids"]):
            raise ValueError("File2 must contain columns: ENZRXN, REACTION, PFAM, uniref90_ids")
        
        # Keep ENZRXN for PFAM sub-grouping later
        df2 = df2[['ENZRXN', 'REACTION', 'PFAM', "uniref90_ids"]]
        
        # Display basic info about input files
        click.echo(f"File1 shape: {df1.shape}")
        click.echo(f"File2 shape: {df2.shape}")
        
        # Perform full outer join to keep ALL reactions from both files
        # This ensures we keep every reaction, even if it has neither PFAM nor EC numbers
        result = pd.merge(df1, df2, left_on='RXN', right_on='REACTION', how='outer')
        
        # Create the final RXN column (use RXN from File1 if available, otherwise use REACTION from File2)
        result['FINAL_RXN'] = result['RXN'].fillna(result['REACTION'])
        
        # Clean up EC_NUMBERS and PFAM columns
        # Keep empty EC_NUMBERS as empty string, and missing PFAM as 'NA'
        result['EC_NUMBERS'] = result['EC_NUMBERS'].fillna('')
        result['PFAM'] = result['PFAM'].fillna('NA')
        
        # Create final output with desired columns
        final_result = result[['FINAL_RXN', 'EC_NUMBERS', 'PFAM', 'uniref90_ids', 'ENZRXN']].copy()
        final_result.columns = ['RXN', 'EC_NUMBERS', 'PFAM', 'uniref90_ids', 'ENZRXN']
        
        # IMPORTANT: Keep ALL reactions, including those with neither PFAM nor EC
        # No filtering based on presence of PFAM or EC numbers
        
        # Remove any completely duplicate rows
        final_result = final_result.drop_duplicates()
        
        # Sort by RXN for better readability
        final_result = final_result.sort_values('RXN')

        # Fill ENZRXN NaN (EC-only reactions with no ENZRXN match) with empty string
        final_result['ENZRXN'] = final_result['ENZRXN'].fillna('')

        def join_semicolon(x):
            """Join non-null, non-empty values with ';', deduplicating while preserving order."""
            vals = [str(v) for v in x if pd.notna(v) and str(v) not in ('', 'NA', 'nan')]
            return ';'.join(dict.fromkeys(vals)) if vals else 'NA'

        def join_semicolon_dedup(x):
            """Join non-null, non-empty values with ';', deduplicating (used within an ENZRXN group)."""
            vals = [str(v) for v in x if pd.notna(v) and str(v) not in ('', 'NA', 'nan')]
            return ';'.join(sorted(set(vals))) if vals else 'NA'

        def join_comma_ordered(x):
            """Join non-null, non-empty values with '|', deduplicating while preserving order (used across ENZRXNs)."""
            vals = [str(v) for v in x if pd.notna(v) and str(v) not in ('', 'NA', 'nan')]
            return '|'.join(dict.fromkeys(vals)) if vals else 'NA'

        # Step 1: within each (RXN, ENZRXN) group, combine PFAMs with ';' and deduplicate
        enzrxn_agg = final_result.groupby(['RXN', 'ENZRXN']).agg({
            'EC_NUMBERS': join_semicolon,
            'PFAM': join_semicolon_dedup,
            'uniref90_ids': join_semicolon,
        }).reset_index()

        # Step 2: group by RXN, joining ENZRXN-level PFAM groups with ','
        # e.g. ENZRXN-1→PF1, ENZRXN-2→PF1;PF2  becomes  PF1,PF1;PF2
        final_result = enzrxn_agg.groupby('RXN').agg({
            'EC_NUMBERS': join_semicolon,
            'PFAM': join_comma_ordered,
            'uniref90_ids': join_semicolon,
        }).reset_index()

        # Deduplicate EC_NUMBERS and uniref90_ids (flat semicolon-separated lists)
        final_result['EC_NUMBERS'] = final_result['EC_NUMBERS'].apply(
            lambda x: ';'.join(sorted(set(x.split(';')))) if x and x != 'NA' else x)
        final_result['uniref90_ids'] = final_result['uniref90_ids'].apply(
            lambda x: ';'.join(sorted(set(x.split(';')))) if x and x != 'NA' else x)

        # Clean up any residual 'NA;' artifacts in flat-joined columns
        final_result['EC_NUMBERS'] = final_result['EC_NUMBERS'].str.replace('NA;', '', regex=False)
        final_result['uniref90_ids'] = final_result['uniref90_ids'].str.replace('NA;', '', regex=False)

        # Remove any completely duplicate rows
        final_result = final_result.drop_duplicates()

        # Sort by RXN for better readability
        final_result = final_result.sort_values('RXN')

        #
        # Save to output file
        final_result.to_csv(output, index=False, sep='\t')
        
        # Display summary statistics
        click.echo(f"\nMerge completed successfully!")
        click.echo(f"Output saved to: {output}")
        click.echo(f"Total rows in output: {len(final_result)}")
        
        # Count different types of entries
        # Both '' and 'NA' mean absent for EC_NUMBERS and PFAM
        no_ec = final_result['EC_NUMBERS'].isin(['', 'NA'])
        no_pfam = final_result['PFAM'].isin(['', 'NA'])
        has_ec = len(final_result[~no_ec])
        has_pfam = len(final_result[~no_pfam])
        has_both = len(final_result[~no_ec & ~no_pfam])
        has_neither = len(final_result[no_ec & no_pfam])
        
        click.echo(f"\nSummary:")
        click.echo(f"Entries with EC numbers: {has_ec}")
        click.echo(f"Entries with PFAM: {has_pfam}")
        click.echo(f"Entries with both EC and PFAM: {has_both}")
        click.echo(f"Entries with neither EC nor PFAM: {has_neither}")
        
        # Show sample of the output
        click.echo(f"\nSample of output (first 5 rows):")
        click.echo(final_result.head().to_string(index=False))
        
        
    except FileNotFoundError as e:
        click.echo(f"Error: Could not find file - {e}", err=True)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)

if __name__ == '__main__':
    merge_reaction_files()
