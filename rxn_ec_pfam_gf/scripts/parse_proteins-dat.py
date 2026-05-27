#!/usr/bin/env python3
"""
Parse proteins.dat file and extract UNIQUE-ID, CATALYZES, and DBLINKS information.
Uses Click for command-line interface.
"""

import click
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple


def parse_proteins_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parse the proteins.dat file and extract relevant information.
    
    Args:
        file_path: Path to the proteins.dat file
        
    Returns:
        List of dictionaries containing parsed protein information
    """
    proteins = []
    
    # Try different encodings to handle special characters
    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    content = None
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    
    if content is None:
        raise click.ClickException(f"Could not decode file with encodings: {encodings}")

    
    # Split by '//' to separate individual protein entries
    entries = content.split('//')
    
    for entry in entries:
        if not entry.strip():
            continue
            
        protein_info = {
            'UNIQUE-ID': '',
            'CATALYZES': '',
            'PFAM': '',
            'UNIPROT': ''
        }
        
        lines = entry.strip().split('\n')
        catalyzes_list = []
        pfam_list = []
        uniprot_list = []
        
        for line in lines:
            line = line.rstrip()
            
            # Extract UNIQUE-ID
            if line.startswith('UNIQUE-ID'):
                match = re.match(r'UNIQUE-ID\s*-\s*(.+)', line)
                if match:
                    protein_info['UNIQUE-ID'] = match.group(1).strip()
            
            # Extract CATALYZES
            elif line.startswith('CATALYZES'):
                match = re.match(r'CATALYZES\s*-\s*(.+)', line)
                if match:
                    catalyzes_list.append(match.group(1).strip())
            
            # Extract DBLINKS
            elif line.startswith('DBLINKS'):
                # Parse DBLINKS format: (DATABASE "ID" ...)
                # Looking for PFAM and UNIPROT entries
                match = re.match(r'DBLINKS\s*-\s*\((\w+)\s+"([^"]+)"', line)
                if match:
                    db_type = match.group(1).upper()
                    db_id = match.group(2).strip()
                    
                    if db_type == 'PFAM':
                        pfam_list.append(db_id)
                    elif db_type == 'UNIPROT':
                        uniprot_list.append(db_id)
        
        # Join multiple values with semicolon
        protein_info['CATALYZES'] = ';'.join(catalyzes_list) if catalyzes_list else ''
        protein_info['PFAM'] = ';'.join(pfam_list) if pfam_list else ''
        protein_info['UNIPROT'] = ';'.join(uniprot_list) if uniprot_list else ''
        
        # Only add entries that have a UNIQUE-ID
        if protein_info['UNIQUE-ID']:
            proteins.append(protein_info)
    
    return proteins


def write_to_csv(proteins: List[Dict[str, str]], output_file: str) -> None:
    """
    Write parsed protein information to a CSV file.
    
    Args:
        proteins: List of protein dictionaries
        output_file: Path to the output CSV file
    """
    fieldnames = ['UNIQUE-ID', 'CATALYZES', 'PFAM', 'UNIPROT']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(proteins)
    
    click.echo(f"✓ Successfully wrote {len(proteins)} proteins to {output_file}")


@click.command()
@click.option(
    '--input',
    '-i',
    type=click.Path(exists=True, file_okay=True, readable=True),
    prompt='Enter path to proteins.dat file',
    help='Path to the proteins.dat file'
)
@click.option(
    '--output',
    '-o',
    type=click.Path(file_okay=True, writable=True),
    prompt='Enter output CSV file path',
    default='parsed_proteins.csv',
    help='Path to the output CSV file'
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Show detailed parsing information'
)
def main(input, output, verbose):
    """
    Parse proteins.dat file and extract information into a CSV file.
    
    This tool extracts:
    - UNIQUE-ID
    - CATALYZES (concatenated with semicolon if multiple)
    - PFAM identifiers (concatenated with semicolon if multiple)
    - UNIPROT identifiers (concatenated with semicolon if multiple)
    """
    click.echo("━" * 50)
    click.echo("Proteins.dat Parser")
    click.echo("━" * 50)
    
    try:
        click.echo(f"\n📖 Reading file: {input}")
        proteins = parse_proteins_file(input)
        
        if verbose:
            click.echo(f"\n📊 Parsed {len(proteins)} protein entries:")
            for i, protein in enumerate(proteins[:5], 1):
                click.echo(f"\n  Entry {i}:")
                click.echo(f"    UNIQUE-ID: {protein['UNIQUE-ID']}")
                click.echo(f"    CATALYZES: {protein['CATALYZES']}")
                click.echo(f"    PFAM: {protein['PFAM']}")
                click.echo(f"    UNIPROT: {protein['UNIPROT']}")
            if len(proteins) > 5:
                click.echo(f"\n  ... and {len(proteins) - 5} more entries")
        
        click.echo(f"\n💾 Writing results to: {output}")
        write_to_csv(proteins, output)
        
        click.echo("\n✅ Parsing completed successfully!")
        click.echo("━" * 50)
        
    except FileNotFoundError as e:
        click.echo(f"\n❌ Error: File not found - {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"\n❌ Error during parsing: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
