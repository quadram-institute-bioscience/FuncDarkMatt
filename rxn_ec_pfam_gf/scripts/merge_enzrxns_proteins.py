import click
import pandas as pd

@click.command()
@click.option('--file1', required=True, help='Path to File1 (CSV with UNIQUE-ID, ENZYME_RXN, PFAM)')
@click.option('--file2', required=True, help='Path to File2 (CSV with ENZYME_RXN, REACTION)')
@click.option('--output', required=True, help='Path to output TSV file')
def merge_files(file1, file2, output):
    """
    Merge File1 and File2 on ENZYME_RXN column.
    Each ENZYME_RXN in File2 gets the PFAM from File1.
    If no match exists, PFAM will be NA.
    """
    
    try:
        # Read the files
        click.echo(f"Reading File1: {file1}")
        df1 = pd.read_csv(file1)
        
        click.echo(f"Reading File2: {file2}")
        df2 = pd.read_csv(file2)


        
        # Display basic info about input files
        click.echo(f"File1 shape: {df1.shape}")
        click.echo(f"File2 shape: {df2.shape}")
        
        # Check if required columns exist
        if not all(col in df1.columns for col in ['UNIQUE-ID', 'ENZYME_RXN', 'PFAM']):
            raise ValueError("File1 must contain columns: UNIQUE-ID, ENZYME_RXN, PFAM")
        
        if not all(col in df2.columns for col in ['ENZYME_RXN', 'REACTION']):
            raise ValueError("File2 must contain columns: ENZYME_RXN, REACTION")
        
        # Filter out rows in File1 where ENZYME_RXN is NA or empty
        # These won't be useful for matching
        df1_filtered = df1[df1['ENZYME_RXN'].notna() & (df1['ENZYME_RXN'] != 'NA') & (df1['ENZYME_RXN'] != '')]
        
        click.echo(f"File1 entries with valid ENZYME_RXN: {len(df1_filtered)}")

        # Filtering out rows without reaction id.
        df2_filtered = df2[df2['REACTION'].notna() & (df2['REACTION'] != 'NA') & (df2['REACTION'] != '')]
        click.echo(f"File2 entries with valid ENZYME_RXN: {len(df2)}")
        
        # Perform left join of File2 with File1 on ENZYME_RXN
        # This keeps all entries from File2 and adds PFAM from File1 where matches exist
        # If File1 has multiple PFAMs for the same ENZYME_RXN, it will create multiple rows
        result = pd.merge(df2_filtered, df1_filtered[['ENZYME_RXN', 'PFAM']], 
                         on='ENZYME_RXN', how='left')
        
        # Reorder columns to match expected output format
        result = result[['ENZYME_RXN', 'REACTION', 'PFAM']]
        
        # Fill any remaining NaN values in PFAM with 'NA'
        result['PFAM'] = result['PFAM'].fillna('NA')
        
        # Save to output file
        result.to_csv(output, sep="\t", index=False)

        # Display summary statistics
        click.echo(f"\nMerge completed successfully!")
        click.echo(f"Output saved to: {output}")
        click.echo(f"Total rows in output: {len(result)}")
        
        # Count matches vs non-matches
        matched_count = len(result[result['PFAM'] != 'NA'])
        unmatched_count = len(result[result['PFAM'] == 'NA'])
        
        click.echo(f"Entries with matching PFAM: {matched_count}")
        click.echo(f"Entries with NA PFAM (no match): {unmatched_count}")
        
    except FileNotFoundError as e:
        click.echo(f"Error: Could not find file - {e}", err=True)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)

if __name__ == '__main__':
    merge_files()
