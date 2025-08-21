#!/usr/bin/env python3
"""
BioCyc enzrxns.dat parser
Extracts UNIQUE-ID and REACTION information from enzrxns.dat file
"""

import click
import csv
from typing import List, Dict, Optional


def parse_reaction(reaction_line: str) -> Optional[str]:
    """
    Extract reaction ID from REACTION line
    Example: REACTION - RXN0-6300
    Returns: RXN0-6300
    """
    parts = reaction_line.split(' - ')
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def parse_unique_id(unique_id_line: str) -> Optional[str]:
    """
    Extract unique ID from UNIQUE-ID line
    Example: UNIQUE-ID - ENZRXN0-6300
    Returns: ENZRXN0-6300
    """
    parts = unique_id_line.split(' - ')
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def parse_enzrxns_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parse the enzrxns.dat file and extract required information
    """
    enzrxns = []
    current_enzrxn = {}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # End of enzyme reaction entry
            if line == '//':
                if current_enzrxn:
                    enzrxns.append(current_enzrxn)
                    current_enzrxn = {}
                continue
            
            # Parse UNIQUE-ID
            if line.startswith('UNIQUE-ID'):
                unique_id = parse_unique_id(line)
                if unique_id:
                    current_enzrxn['ENZYME_RXN'] = unique_id
                    current_enzrxn['REACTION'] = []
            
            # Parse REACTION
            elif line.startswith('REACTION - '):
                reaction = parse_reaction(line)
                if reaction and 'REACTION' in current_enzrxn:
                    current_enzrxn['REACTION'].append(reaction)
    
    # Don't forget the last enzyme reaction if file doesn't end with //
    if current_enzrxn:
        enzrxns.append(current_enzrxn)
    
    return enzrxns


def format_output_data(enzrxns: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format the parsed data for output
    """
    formatted_data = []
    
    for enzrxn in enzrxns:
        unique_id = enzrxn.get('ENZYME_RXN', 'NA')
        reactions = enzrxn.get('REACTION', [])
        if reactions:
            for reaction in reactions:
                formatted_data.append({
                    'ENZYME_RXN': unique_id,
                    'REACTION': reaction
            })

    return formatted_data


@click.command()
@click.option('--input-file', '-i', required=True, type=click.Path(exists=True), 
              help='Path to the enzrxns.dat input file')
@click.option('--output-file', '-o', required=True, type=click.Path(), 
              help='Path to the output CSV file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def main(input_file, output_file, verbose):
    """
    Parse BioCyc enzrxns.dat file and extract UNIQUE-ID and REACTION information.
    
    Example usage:
    python enzrxns_parser.py -i enzrxns.dat -o output.csv -f concatenated
    """
    
    if verbose:
        click.echo(f"Reading enzrxns.dat file: {input_file}")
    
    try:
        # Parse the enzrxns file
        enzrxns = parse_enzrxns_file(input_file)
        
        if verbose:
            click.echo(f"Found {len(enzrxns)} enzyme reaction entries")
        
        # Format the output data
        formatted_data = format_output_data(enzrxns)
        
        if verbose:
            click.echo(f"Generated {len(formatted_data)} output rows")
        
        # Write to CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ENZYME_RXN', 'REACTION']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(formatted_data)
        
        click.echo(f"Successfully wrote output to: {output_file}")
        
        if verbose:
            # Show some statistics
            unique_enzrxns = len(set(row['ENZYME_RXN'] for row in formatted_data))
            enzrxns_with_reaction = len([row for row in formatted_data if row['REACTION'] != 'NA'])
            
            click.echo(f"\nStatistics:")
            click.echo(f"  Unique enzyme reactions: {unique_enzrxns}")
            click.echo(f"  Rows with reactions: {enzrxns_with_reaction}")
            click.echo(f"  Rows without reactions: {len(formatted_data) - enzrxns_with_reaction}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
