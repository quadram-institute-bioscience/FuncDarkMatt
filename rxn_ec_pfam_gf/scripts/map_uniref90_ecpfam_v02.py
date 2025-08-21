#!/usr/bin/env python3
"""
Memory-efficient CSV file merger for large files (15GB+).
Merges protein_accession-sprot.csv with uniref90_map.csv based on ID column.
"""

import pandas as pd
import click
import os
from typing import Optional, Dict, Set
import sys
import gc
from pathlib import Path


def get_file_size_gb(filepath: str) -> float:
    """Get file size in GB."""
    return os.path.getsize(filepath) / (1024**3)


def create_id_index(filepath: str, chunksize: int = 50000) -> Dict[str, int]:
    """
    Create an index mapping ID to chunk number for efficient lookup.
    This helps us know which chunk contains each ID.
    """
    click.echo(f"Creating ID index for {filepath}...")
    id_to_chunk = {}
    chunk_num = 0
    
    try:
        for chunk in pd.read_csv(filepath, chunksize=chunksize, usecols=['ID'], low_memory=False):
            for idx, row_id in enumerate(chunk['ID']):
                id_to_chunk[row_id] = chunk_num
            chunk_num += 1
            
            if chunk_num % 100 == 0:
                click.echo(f"  Processed {chunk_num} chunks...")
                
    except Exception as e:
        click.echo(f"Error creating index: {str(e)}", err=True)
        sys.exit(1)
    
    click.echo(f"  Index created: {len(id_to_chunk)} unique IDs across {chunk_num} chunks")
    return id_to_chunk


def get_common_ids(file1: str, file2: str, chunksize: int = 50000) -> Set[str]:
    """
    Find common IDs between two files without loading entire files.
    """
    click.echo("Finding common IDs...")
    
    # Get IDs from first file
    ids1 = set()
    chunk_count = 0
    for chunk in pd.read_csv(file1, chunksize=chunksize, usecols=['ID'], low_memory=False):
        ids1.update(chunk['ID'].astype(str))
        chunk_count += 1
        if chunk_count % 100 == 0:
            click.echo(f"  File 1: Processed {chunk_count} chunks, {len(ids1)} unique IDs so far")
    
    click.echo(f"  File 1 total: {len(ids1)} unique IDs")
    
    # Find common IDs with second file
    common_ids = set()
    chunk_count = 0
    for chunk in pd.read_csv(file2, chunksize=chunksize, usecols=['ID'], low_memory=False):
        chunk_ids = set(chunk['ID'].astype(str))
        common_ids.update(ids1.intersection(chunk_ids))
        chunk_count += 1
        if chunk_count % 100 == 0:
            click.echo(f"  File 2: Processed {chunk_count} chunks, {len(common_ids)} common IDs so far")
    
    click.echo(f"  Found {len(common_ids)} common IDs")
    return common_ids


def merge_large_files_method1(uniref_file: str, protein_file: str, output_file: str, 
                             chunksize: int = 50000) -> None:
    """
    Memory-efficient merge using chunked processing.
    Best for when both files are very large.
    """
    click.echo("Using Method 1: Chunked processing for both files")
    
    # Get common IDs first
    common_ids = get_common_ids(uniref_file, protein_file, chunksize)
    
    if not common_ids:
        click.echo("No common IDs found. Creating empty output file.")
        pd.DataFrame().to_csv(output_file, index=False)
        return
    
    # Process files in chunks and write results incrementally
    first_chunk = True
    total_written = 0
    
    click.echo("Processing UniRef file in chunks...")
    for chunk_num, uniref_chunk in enumerate(pd.read_csv(uniref_file, chunksize=chunksize, low_memory=False)):
        # Filter chunk to only common IDs
        uniref_filtered = uniref_chunk[uniref_chunk['ID'].isin(common_ids)]
        
        if len(uniref_filtered) == 0:
            continue
        
        # Handle duplicate column names
        uniref_filtered = uniref_filtered.rename(columns={
            'ncbi_taxonomy_id': 'ncbi_taxonomy_id_uniref'
        })
        
        # Process protein file to find matching IDs
        protein_matches = []
        for protein_chunk in pd.read_csv(protein_file, chunksize=chunksize, low_memory=False):
            protein_filtered = protein_chunk[protein_chunk['ID'].isin(uniref_filtered['ID'])]
            if len(protein_filtered) > 0:
                protein_filtered = protein_filtered.rename(columns={
                    'ncbi_taxonomy_id': 'ncbi_taxonomy_id_protein'
                })
                protein_matches.append(protein_filtered)
        
        if protein_matches:
            protein_combined = pd.concat(protein_matches, ignore_index=True)
            
            # Merge current chunks
            merged_chunk = pd.merge(uniref_filtered, protein_combined, on='ID', how='inner')
            
            # Write to output
            if len(merged_chunk) > 0:
                mask = ~(
                    (merged_chunk['pfam_ids'].isna() | (merged_chunk['pfam_ids'] == '') | (merged_chunk['pfam_ids'] == 'NA')) &
                    (merged_chunk['ec_number'].isna() | (merged_chunk['ec_number'] == '') | (merged_chunk['ec_number'] == 'NA'))
                )
                merged_chunk = merged_chunk[mask]
                merged_chunk.to_csv(output_file, mode='a', header=first_chunk, index=False, na_rep='NA')
                first_chunk = False
                total_written += len(merged_chunk)
                click.echo(f"  Processed chunk {chunk_num + 1}, wrote {len(merged_chunk)} rows (total: {total_written})")
        
        # Clean up memory
        del uniref_filtered
        if 'protein_combined' in locals():
            del protein_combined
        if 'merged_chunk' in locals():
            del merged_chunk
        gc.collect()
    
    click.echo(f"✓ Merge completed. Total rows written: {total_written}")


def merge_large_files_method2(uniref_file: str, protein_file: str, output_file: str, 
                             chunksize: int = 50000) -> None:
    """
    Memory-efficient merge by loading smaller file into memory.
    Best when one file is significantly smaller than the other.
    """
    click.echo("Using Method 2: Load smaller file in memory")
    
    # Determine which file is smaller
    uniref_size = get_file_size_gb(uniref_file)
    protein_size = get_file_size_gb(protein_file)
    
    if uniref_size <= protein_size:
        small_file, large_file = uniref_file, protein_file
        small_is_uniref = True
    else:
        small_file, large_file = protein_file, uniref_file
        small_is_uniref = False
    
    click.echo(f"  Smaller file: {small_file} ({get_file_size_gb(small_file):.2f} GB)")
    click.echo(f"  Larger file: {large_file} ({get_file_size_gb(large_file):.2f} GB)")
    
    # Load smaller file into memory
    click.echo("Loading smaller file into memory...")
    try:
        small_df = pd.read_csv(small_file, low_memory=False)
        
        # Handle column renaming based on which file is smaller
        if small_is_uniref:
            small_df = small_df.rename(columns={'ncbi_taxonomy_id': 'ncbi_taxonomy_id_uniref'})
        else:
            small_df = small_df.rename(columns={'ncbi_taxonomy_id': 'ncbi_taxonomy_id_protein'})
        
        click.echo(f"  Loaded {len(small_df)} rows from smaller file")
        
    except MemoryError:
        click.echo("Cannot load smaller file into memory. Using Method 1 instead.")
        return merge_large_files_method1(uniref_file, protein_file, output_file, chunksize)
    
    # Process larger file in chunks
    click.echo("Processing larger file in chunks...")
    first_chunk = True
    total_written = 0
    
    for chunk_num, large_chunk in enumerate(pd.read_csv(large_file, chunksize=chunksize, low_memory=False)):
        # Handle column renaming
        if not small_is_uniref:
            large_chunk = large_chunk.rename(columns={'ncbi_taxonomy_id': 'ncbi_taxonomy_id_uniref'})
        else:
            large_chunk = large_chunk.rename(columns={'ncbi_taxonomy_id': 'ncbi_taxonomy_id_protein'})
        
        # Merge with smaller file
        if small_is_uniref:
            merged_chunk = pd.merge(small_df, large_chunk, on='ID', how='inner')
        else:
            merged_chunk = pd.merge(large_chunk, small_df, on='ID', how='inner')
        
        # Write results
        if len(merged_chunk) > 0:
            mask = ~(
                (merged_chunk['pfam_ids'].isna() | (merged_chunk['pfam_ids'] == '') | (merged_chunk['pfam_ids'] == 'NA')) &
                (merged_chunk['ec_number'].isna() | (merged_chunk['ec_number'] == '') | (merged_chunk['ec_number'] == 'NA'))
            )
            merged_chunk = merged_chunk[mask]
            merged_chunk.to_csv(output_file, mode='a', header=first_chunk, index=False, na_rep='NA')
            first_chunk = False
            total_written += len(merged_chunk)
            click.echo(f"  Processed chunk {chunk_num + 1}, wrote {len(merged_chunk)} rows (total: {total_written})")
        
        # Clean up
        del large_chunk, merged_chunk
        gc.collect()
        
        if chunk_num % 100 == 0:
            click.echo(f"  Memory usage checkpoint at chunk {chunk_num}")
    
    click.echo(f"✓ Merge completed. Total rows written: {total_written}")


@click.command()
@click.option('--uniref-file', '-u', 
              default='uniref90_map.csv',
              help='Path to uniref90_map.csv file')
@click.option('--protein-file', '-p', 
              default='protein_accession-sprot.csv',
              help='Path to protein_accession-sprot.csv file')
@click.option('--output-file', '-o', 
              default='merged_output.csv',
              help='Path to output merged CSV file')
@click.option('--chunksize', '-c',
              type=int,
              default=50000,
              help='Number of rows to process at once (default: 50000)')
@click.option('--method', '-m',
              type=click.Choice(['auto', 'chunked', 'hybrid']),
              default='auto',
              help='Merge method: auto (choose best), chunked (both files), hybrid (smaller in memory)')
@click.option('--memory-limit', '-l',
              type=float,
              default=8.0,
              help='Memory limit in GB for loading files (default: 8.0)')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def main(uniref_file: str, protein_file: str, output_file: str, 
         chunksize: int, method: str, memory_limit: float, verbose: bool):
    """
    Memory-efficient merge for large CSV files (15GB+).
    
    Merges uniref90_map.csv and protein_accession-sprot.csv files based on ID column
    with minimal memory usage.
    """
    
    # Check if input files exist
    if not os.path.exists(uniref_file):
        click.echo(f"Error: UniRef file '{uniref_file}' not found.", err=True)
        sys.exit(1)
    
    if not os.path.exists(protein_file):
        click.echo(f"Error: Protein file '{protein_file}' not found.", err=True)
        sys.exit(1)
    
    # Show file sizes
    uniref_size = get_file_size_gb(uniref_file)
    protein_size = get_file_size_gb(protein_file)
    total_size = uniref_size + protein_size
    
    click.echo(f"File sizes:")
    click.echo(f"  UniRef file: {uniref_size:.2f} GB")
    click.echo(f"  Protein file: {protein_size:.2f} GB")
    click.echo(f"  Total: {total_size:.2f} GB")
    click.echo(f"  Memory limit: {memory_limit:.2f} GB")
    click.echo(f"  Chunk size: {chunksize:,} rows")
    click.echo()
    
    # Choose method
    if method == 'auto':
        smaller_size = min(uniref_size, protein_size)
        if smaller_size <= memory_limit:
            chosen_method = 'hybrid'
        else:
            chosen_method = 'chunked'
    else:
        chosen_method = method
    
    click.echo(f"Using method: {chosen_method}")
    
    # Check if output file already exists
    if os.path.exists(output_file):
        if not click.confirm(f"Output file '{output_file}' already exists. Overwrite?"):
            click.echo("Operation cancelled.")
            sys.exit(0)
    
    # Perform the merge
    try:
        if chosen_method == 'chunked':
            merge_large_files_method1(uniref_file, protein_file, output_file, chunksize)
        else:  # hybrid
            merge_large_files_method2(uniref_file, protein_file, output_file, chunksize)
            
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.")
        if os.path.exists(output_file):
            os.remove(output_file)
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error during merge: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
