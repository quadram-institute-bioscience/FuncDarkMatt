#!/usr/bin/env python3
"""
Denormalize CATALYZES by ENZRXN.
Takes the aggregated catalyzes CSV and expands so each ENZRXN appears on its own row
with its associated MONOMER, PFAM, and UNIPROT values.
Uses Click for command-line interface.
"""

import click
import csv
from pathlib import Path
from typing import Dict, List


def expand_by_enzrxn(input_file: str) -> List[Dict[str, str]]:
    """
    Read aggregated catalyzes CSV and expand by individual ENZRXN IDs.
    
    Each CATALYZES entry may contain multiple ENZRXN IDs separated by semicolons.
    This function creates a separate row for each ENZRXN, while keeping the
    associated MONOMER, PFAM, and UNIPROT values.
    
    Args:
        input_file: Path to the aggregated catalyzes CSV file
        
    Returns:
        List of dictionaries with one row per ENZRXN
    """
    expanded = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                catalyzes = row['CATALYZES'].strip()
                monomer = row['UNIQUE-ID'].strip()
                pfam = row['PFAM'].strip()
                uniprot = row['UNIPROT'].strip()
                
                # Split CATALYZES by semicolon to get individual ENZRXN IDs
                if catalyzes:
                    enzrxn_ids = [e.strip() for e in catalyzes.split(';') if e.strip()]
                    
                    # Create a row for each ENZRXN
                    for enzrxn_id in enzrxn_ids:
                        expanded.append({
                            'ENZRXN': enzrxn_id,
                            'MONOMER': monomer,
                            'PFAM': pfam,
                            'UNIPROT': uniprot
                        })
    
    except FileNotFoundError:
        click.echo(f"❌ Error: Input file not found - {input_file}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error reading CSV: {e}", err=True)
        raise click.Abort()
    
    return expanded


def write_expanded_csv(expanded_data: List[Dict[str, str]], output_file: str) -> None:
    """
    Write expanded data to a CSV file.
    
    Args:
        expanded_data: List of expanded data dictionaries
        output_file: Path to the output CSV file
    """
    fieldnames = ['ENZRXN', 'MONOMER', 'PFAM', 'UNIPROT']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(expanded_data)
    
    click.echo(f"✓ Successfully wrote {len(expanded_data)} ENZRXN entries to {output_file}")


def get_expansion_stats(expanded_data: List[Dict[str, str]]) -> Dict:
    """
    Calculate statistics about the expansion.
    
    Args:
        expanded_data: List of expanded data dictionaries
        
    Returns:
        Dictionary with statistics
    """
    total_enzrxn = len(expanded_data)
    
    unique_monomers = set(row['MONOMER'] for row in expanded_data if row['MONOMER'])
    unique_pfam = set()
    unique_uniprot = set()
    
    for row in expanded_data:
        if row['PFAM']:
            for pfam_id in row['PFAM'].split(';'):
                unique_pfam.add(pfam_id.strip())
        if row['UNIPROT']:
            for uniprot_id in row['UNIPROT'].split(';'):
                unique_uniprot.add(uniprot_id.strip())
    
    return {
        'total_enzrxn': total_enzrxn,
        'unique_monomers': len(unique_monomers),
        'unique_pfam': len(unique_pfam),
        'unique_uniprot': len(unique_uniprot)
    }


@click.command()
@click.option(
    '--input',
    '-i',
    type=click.Path(exists=True, file_okay=True, readable=True),
    required=True,
    help='Path to the aggregated catalyzes CSV file'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(file_okay=True, writable=True),
    default='enzrxn_expanded.csv',
    help='Path to the output CSV file'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Show detailed statistics and sample entries'
)
def main(input, output, verbose):
    """
    Expand aggregated catalyzes data by individual ENZRXN IDs.
    
    This tool denormalizes the aggregated catalyzes CSV by expanding each row
    so that each ENZRXN appears on its own row with associated MONOMER, PFAM,
    and UNIPROT values.
    
    Input: aggregated_catalyzes.csv (CATALYZES may contain multiple ENZRXN IDs)
    Output: enzrxn_expanded.csv (one row per ENZRXN)
    """
    click.echo("━" * 70)
    click.echo("ENZRXN Expansion Tool")
    click.echo("━" * 70)
    
    try:
        click.echo(f"\n📖 Reading file: {input}")
        expanded_data = expand_by_enzrxn(input)
        
        # Calculate statistics
        stats = get_expansion_stats(expanded_data)
        
        click.echo(f"\n📊 Expansion Statistics:")
        click.echo(f"   Total ENZRXN entries: {stats['total_enzrxn']:,}")
        click.echo(f"   Unique MONOMERs: {stats['unique_monomers']:,}")
        click.echo(f"   Unique PFAM IDs: {stats['unique_pfam']:,}")
        click.echo(f"   Unique UNIPROT IDs: {stats['unique_uniprot']:,}")
        
        if verbose:
            click.echo(f"\n📋 Sample entries (first 15):")
            samples = expanded_data[:15]
            for i, entry in enumerate(samples, 1):
                click.echo(f"\n   Entry {i}:")
                click.echo(f"      ENZRXN: {entry['ENZRXN']}")
                click.echo(f"      MONOMER: {entry['MONOMER']}")
                if entry['PFAM']:
                    click.echo(f"      PFAM: {entry['PFAM'][:80]}")
                if entry['UNIPROT']:
                    click.echo(f"      UNIPROT: {entry['UNIPROT']}")
        
        click.echo(f"\n💾 Writing results to: {output}")
        write_expanded_csv(expanded_data, output)
        
        click.echo("\n✅ Expansion completed successfully!")
        click.echo("━" * 70)
        
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
