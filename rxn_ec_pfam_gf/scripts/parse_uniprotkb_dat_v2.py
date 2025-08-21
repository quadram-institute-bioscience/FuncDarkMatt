#!/usr/bin/env python3
"""
UniProt flat file parser to extract specific fields and create a tabular output.
"""

import gzip
import re
import click
import csv
from pathlib import Path


def parse_uniprot_entry(lines):
    """
    Parse a single UniProt entry from a list of lines.
    Returns a dictionary with the extracted fields.
    """
    entry = {
        'id': '',
        'accession': '',
        'ncbi_taxonomy_id': '',
        'pfam_ids': [],
        'ec_number': []
    }
    
    for line in lines:
        if line.startswith('ID   '):
            # Extract the ID (first field after ID)
            entry['id'] = line.split()[1]
            
        elif line.startswith('AC   '):
            # Extract the primary accession (first accession number)
            accessions = line[5:].strip().rstrip(';')
            if accessions:
                entry['accession'] = accessions.split(';')[0].strip()
                
        elif line.startswith('OX   '):
            # Extract NCBI TaxID
            match = re.search(r'NCBI_TaxID=(\d+)', line)
            if match:
                entry['ncbi_taxonomy_id'] = match.group(1)
                
        elif line.startswith('DR   '):
            # Extract Pfam entries
            if 'Pfam;' in line:
                parts = line[5:].strip().split(';')
                if len(parts) >= 2:
                    pfam_id = parts[1].strip()
                    entry['pfam_ids'].append(pfam_id)
                    
        elif line.startswith('DE   '):
            # Extract E.C. numbers
            ec_matches = re.findall(r'EC=([\d\.\-]+)', line)
            entry['ec_number'].extend(ec_matches)
    
    return entry


def parse_uniprot_file(file_handle):
    """
    Parse a UniProt flat file and yield entries.
    """
    current_entry = []
    
    for line in file_handle:
        line = line.rstrip('\n')
        
        if line == '//':
            # End of entry
            if current_entry:
                yield parse_uniprot_entry(current_entry)
                current_entry = []
        else:
            current_entry.append(line)
    
    # Handle last entry if file doesn't end with //
    if current_entry:
        yield parse_uniprot_entry(current_entry)


@click.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True),
              help='Input UniProt flat file in .gz format')
@click.option('--output', '-o', required=True, type=click.Path(),
              help='Output tabular file')
@click.option('--delimiter', '-d', default='\t', 
              help='Output file delimiter (default: tab)')
@click.option('--verbose', '-v', is_flag=True,
              help='Verbose output')
def main(input, output, delimiter, verbose):
    """
    Parse UniProt flat file and extract ID, Accession, NCBI_TaxID, Pfam, and E.C. numbers.
    """
    input_path = Path(input)
    output_path = Path(output)
    
    if not input_path.suffix == '.gz':
        click.echo("Warning: Input file doesn't have .gz extension", err=True)
    
    if verbose:
        click.echo(f"Processing {input_path}...")
    
    entries_processed = 0
    
    try:
        # Open the gzipped file
        with gzip.open(input_path, 'rt', encoding='utf-8') as f:
            # Open output file
            with open(output_path, 'w', newline='') as out_f:
                # Create CSV writer
                if delimiter == '\\t':
                    delimiter = '\t'
                writer = csv.writer(out_f, delimiter=delimiter)
                
                # Write header
                writer.writerow(['ID', 'accession', 'ncbi_taxonomy_id', 'pfam_ids', 'ec_number'])
                
                # Process entries
                for entry in parse_uniprot_file(f):
                    # Join multiple Pfam entries with semicolon
                    pfam_str = ';'.join(entry['pfam_ids']) if entry['pfam_ids'] else 'NA'
                    
                    # Join multiple E.C. numbers with semicolon
                    ec_str = ';'.join(entry['ec_number']) if entry['ec_number'] else 'NA'
                    
                    # Write row
                    writer.writerow([
                        entry['id'] if entry['id'] else 'NA',
                        entry['accession'] if entry['accession'] else 'NA',
                        entry['ncbi_taxonomy_id'] if entry['ncbi_taxonomy_id'] else 'NA',
                        pfam_str,
                        ec_str
                    ])
                    
                    entries_processed += 1
                    
                    if verbose and entries_processed % 10000 == 0:
                        click.echo(f"Processed {entries_processed} entries...")
        
        if verbose:
            click.echo(f"Successfully processed {entries_processed} entries")
            click.echo(f"Output written to {output_path}")
            
    except Exception as e:
        click.echo(f"Error processing file: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()
