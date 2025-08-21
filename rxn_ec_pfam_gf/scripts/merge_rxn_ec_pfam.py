import click
import pandas as pd
import numpy as np

@click.command()
@click.option('--file1', required=True, help='Path to reaction-links.dat (TSV with no header)')
@click.option('--file2', required=True, help='Path to rxn_pfam.tsv (TSV with header)')
@click.option('--output', required=True, help='Path to output CSV file')
def merge_reaction_files(file1, file2, output):
    """
    Merge reaction files based on RXN/REACTION columns.
    
    File1 (reactions_links.dat): TSV with variable columns
    - First column: RXN ID
    - Remaining columns: EC numbers (can be 0, 1, or multiple)
    
    File2 (rxn_pfam.tsv): TSV with fixed 3 columns (header included)
    - ENZYME_RXN (discarded)
    - REACTION 
    - PFAM
    
    Keep ALL reactions from both files, including:
    - Reactions that have PFAM only
    - Reactions that have EC numbers only  
    - Reactions that have both PFAM and EC numbers
    - Reactions that have neither PFAM nor EC numbers
    """
    
    try:
        # Read File1 (reactions_links.dat) - no header, tab-separated, variable columns
        click.echo(f"Reading File1: {file1}")
        
        # Read the file line by line to handle variable number of columns
        with open(file1, 'r') as f:
            lines = f.readlines()
        
        # Process each line to extract RXN and EC numbers
        file1_data = []
        
        for line in lines:
            line = line.strip()
            # Skip line starting with '#' or empty lines
            if line and not line.startswith('#'):
                rxn_id, *ec = line.split('\t')
                # if *ec is empty then replace with NA
                if not ec:
                    ec = ['NA']
                else:
                    # each EC should have have 3 decimal places like this one EC-2.7.1.221
                    # If there are EC with less than 3 decimal places, pad them with _ for each decimal missing for example EC-2.7.1 becomes EC-2.7.1._
                    # If EC has 2 decimal places, it will be EC-2.3._._
                    # If EC has 1 decimal place, it will be EC-2._._._
                    # If EC has no decimal places, it will be EC-2._._._
                    # Remove EC- prefix if present
                    ec = [e.strip() for e in ec if e.strip()]  # Remove whitespace
                    ec = [e.replace('EC-', '') for e in ec]
                    ec = [e if e.count('.') == 3 else e + '._' * (3 - e.count('.')) for e in ec]
                    ec = [';'.join(ec)]
                
                file1_data.append([rxn_id] + ec)
        
        # Create DataFrame with two columns: RXN and EC numbers
        df1_cols = ['RXN'] + ['EC_NUMBERS']
        df1 = pd.DataFrame(file1_data, columns=df1_cols)
        
        click.echo(f"File1 processed: {len(df1)} reactions found")
        rxn_with_ec = len(df1[df1['EC_NUMBERS'] != ''])
        rxn_without_ec = len(df1[df1['EC_NUMBERS'] == 'NA'])
        click.echo(f"  - Reactions with EC numbers: {rxn_with_ec}")
        click.echo(f"  - Reactions without EC numbers: {rxn_without_ec}")
        
        # Read File2 (rxn_pfam.tsv) - has header, tab-separated
        click.echo(f"Reading File2: {file2}")
        df2 = pd.read_csv(file2, sep='\t')
        
        # Check if required columns exist in File2
        if not all(col in df2.columns for col in ['ENZYME_RXN', 'REACTION', 'PFAM']):
            raise ValueError("File2 must contain columns: ENZYME_RXN, REACTION, PFAM")
        
        # Keep only REACTION and PFAM columns (discard ENZYME_RXN)
        df2 = df2[['REACTION', 'PFAM']]
        
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
        final_result = result[['FINAL_RXN', 'EC_NUMBERS', 'PFAM']].copy()
        final_result.columns = ['RXN', 'EC_NUMBERS', 'PFAM']
        
        # IMPORTANT: Keep ALL reactions, including those with neither PFAM nor EC
        # No filtering based on presence of PFAM or EC numbers
        
        # Remove any completely duplicate rows
        final_result = final_result.drop_duplicates()
        
        # Sort by RXN for better readability
        final_result = final_result.sort_values('RXN')

        # Group by RXN and aggregate EC_NUMBERS and PFAM, combining EC_NUMBERS and PFAM into lists
        # This ensures we keep all unique EC numbers and PFAM IDs for each RXN
        final_result = final_result.groupby('RXN').agg({
            'EC_NUMBERS': lambda x: ';'.join(x) if x.any() else 'NA',
            'PFAM': lambda x: ';'.join(x) if x.any() else 'NA'
        }).reset_index()

        # Now remove duplicates within EC_NUMBERS and PFAM columns for each RXN
        final_result['EC_NUMBERS'] = final_result['EC_NUMBERS'].apply(lambda x  : ';'.join(sorted(set(x.split(';')))) if x else 'NA')
        final_result['PFAM'] = final_result['PFAM'].apply(lambda x: ';'.join(sorted(set(x.split(';')))) if x else 'NA')

        # Replace NA in EC_NUMBERS and PFAM with nothing if they are not empty
        final_result['EC_NUMBERS'] = final_result['EC_NUMBERS'].str.replace('NA;', '', regex=False)
        final_result['PFAM'] = final_result['PFAM'].str.replace('NA;', '', regex=False)

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
        has_ec = len(final_result[final_result['EC_NUMBERS'] != ''])
        has_pfam = len(final_result[final_result['PFAM'] != 'NA'])
        has_both = len(final_result[(final_result['EC_NUMBERS'] != '') & (final_result['PFAM'] != 'NA')])
        has_neither = len(final_result[(final_result['EC_NUMBERS'] == '') & (final_result['PFAM'] == 'NA')])
        
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