#!/usr/bin/env python3
"""
BioCyc proteins.dat parser
Extracts UNIQUE-ID, ENZYME_RXN, and PFAM information from proteins.dat file
"""

import click
import csv
import re
from typing import List, Dict, Optional


def parse_pfam_from_dblinks(dblinks_line: str) -> Optional[str]:
    """
    Extract PFAM ID from DBLINKS line
    Example: DBLINKS - (PFAM "PF20423" IN-FAMILY |kothari| 3853938300 NIL NIL)
    Returns: PF20423
    """
    pfam_match = re.search(r'PFAM\s+"([^"]+)"', dblinks_line)
    if pfam_match:
        return pfam_match.group(1)
    return None


def parse_catalyzes(catalyzes_line: str) -> Optional[str]:
    """
    Extract enzyme reaction ID from CATALYZES line
    Example: CATALYZES - ENZRXN0-6300
    Returns: ENZRXN0-6300
    """
    parts = catalyzes_line.split(' - ')
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def parse_unique_id(unique_id_line: str) -> Optional[str]:
    """
    Extract unique ID from UNIQUE-ID line
    Example: UNIQUE-ID - EG12016-MONOMER
    Returns: EG12016-MONOMER
    """
    parts = unique_id_line.split(' - ')
    if len(parts) >= 2:
        return parts[1].strip()
    return None


def parse_proteins_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parse the proteins.dat file and extract required information
    """
    proteins = []
    current_protein = {}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        for line in file:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # End of protein entry
            if line == '//':
                if current_protein:
                    proteins.append(current_protein)
                    current_protein = {}
                continue
            
            # Parse UNIQUE-ID
            if line.startswith('UNIQUE-ID'):
                unique_id = parse_unique_id(line)
                if unique_id:
                    current_protein['UNIQUE-ID'] = unique_id
                    current_protein['ENZYME_RXN'] = []
                    current_protein['PFAM'] = []
            
            # Parse CATALYZES
            elif line.startswith('CATALYZES'):
                enzyme_rxn = parse_catalyzes(line)
                if enzyme_rxn and 'ENZYME_RXN' in current_protein:
                    current_protein['ENZYME_RXN'].append(enzyme_rxn)
            
            # Parse DBLINKS for PFAM
            elif line.startswith('DBLINKS') and 'PFAM' in line:
                pfam_id = parse_pfam_from_dblinks(line)
                if pfam_id and 'PFAM' in current_protein:
                    current_protein['PFAM'].append(pfam_id)
    
    # Don't forget the last protein if file doesn't end with //
    if current_protein:
        proteins.append(current_protein)
    
    return proteins


def format_output_data(proteins: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format the parsed data for output
    """
    formatted_data = []
    
    for protein in proteins:
        unique_id = protein.get('UNIQUE-ID', 'NA')
        enzyme_rxns = protein.get('ENZYME_RXN', [])
        pfams = protein.get('PFAM', [])
        
        for enzyme_rxn in enzyme_rxns:
            formatted_data.append({
                'UNIQUE-ID': unique_id,
                'ENZYME_RXN': enzyme_rxn,
                'PFAM': ';'.join(pfams) if pfams else 'NA'
        })
    
    return formatted_data


@click.command()
@click.option('--input-file', '-i', required=True, type=click.Path(exists=True), 
              help='Path to the proteins.dat input file')
@click.option('--output-file', '-o', required=True, type=click.Path(), 
              help='Path to the output CSV file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def main(input_file, output_file, verbose):
    """
    Parse BioCyc proteins.dat file and extract UNIQUE-ID, ENZYME_RXN, and PFAM information.
    
    Example usage:
    python proteins_parser.py -i proteins.dat -o output.csv
    """
    
    if verbose:
        click.echo(f"Reading proteins.dat file: {input_file}")
    
    try:
        # Parse the proteins file
        proteins = parse_proteins_file(input_file)
        
        if verbose:
            click.echo(f"Found {len(proteins)} protein entries")
        
        # Format the output data
        formatted_data = format_output_data(proteins)
        
        if verbose:
            click.echo(f"Generated {len(formatted_data)} output rows")
        
        # Write to CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['UNIQUE-ID', 'ENZYME_RXN', 'PFAM']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(formatted_data)
        
        click.echo(f"Successfully wrote output to: {output_file}")
        
        if verbose:
            # Show some statistics
            unique_proteins = len(set(row['UNIQUE-ID'] for row in formatted_data))
            proteins_with_enzyme = len([row for row in formatted_data if row['ENZYME_RXN'] != 'NA'])
            proteins_with_pfam = len([row for row in formatted_data if row['PFAM'] != 'NA'])
            
            click.echo(f"\nStatistics:")
            click.echo(f"  Unique proteins: {unique_proteins}")
            click.echo(f"  Rows with enzyme reactions: {proteins_with_enzyme}")
            click.echo(f"  Rows with PFAM domains: {proteins_with_pfam}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
