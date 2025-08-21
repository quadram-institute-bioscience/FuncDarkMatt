#!/usr/bin/env python3
"""
UniRef90 XML Parser
Parses UniRef90 XML.gz files and extracts ID information into a table format.

Generated with assistance from Claude AI (Anthropic).
For more information about Claude, visit: https://www.anthropic.com/claude
"""

# ============================================================================
# Code Generation Citation
# ============================================================================
# This script was generated with assistance from Claude AI (Anthropic, 2025).
# Claude Sonnet 4 model was used for code generation and optimization.
# Human input: Requirements for parsing UniRef90 XML files
# AI contribution: Code structure, XML parsing logic, and CLI interface
# Date: June, 2025
# ============================================================================

import click
import gzip
import xml.etree.ElementTree as ET
import csv
import os
from typing import Dict, List, Optional


def extract_entry_data(entry_element) -> Dict[str, Optional[str]]:
    """
    Extract relevant data from a single entry element.
    
    Args:
        entry_element: XML element representing a UniRef entry
        
    Returns:
        Dictionary with extracted data
    """
    # Initialize result dictionary
    result = {
        'ID': None,
        'UniRef100_ID': None,
        'UniRef90_ID': None,
        'UniRef50_ID': None,
        'ncbi_taxonomy_id': None
    }
    
    # Get UniRef90 ID from entry id attribute
    result['UniRef90_ID'] = entry_element.get('id')
    
    # Find representative member
    rep_member = entry_element.find('.//{http://uniprot.org/uniref}representativeMember')
    
    if rep_member is not None:
        # Look for dbReference elements
        db_refs = rep_member.findall('.//{http://uniprot.org/uniref}dbReference')
        
        for db_ref in db_refs:
            db_type = db_ref.get('type')
            db_id = db_ref.get('id')
            
            # Set the main ID (prioritize UniParc, but could be other types)
            if result['ID'] is None:
                result['ID'] = db_id
            
            # Look for properties within this dbReference
            properties = db_ref.findall('.//{http://uniprot.org/uniref}property')
            
            for prop in properties:
                prop_type = prop.get('type')
                prop_value = prop.get('value')
                
                if prop_type == 'UniRef100 ID':
                    result['UniRef100_ID'] = prop_value
                elif prop_type == 'UniRef50 ID':
                    result['UniRef50_ID'] = prop_value
                elif prop_type == 'NCBI taxonomy':
                    result['ncbi_taxonomy_id'] = prop_value
    
    return result


def parse_uniref_xml(file_path: str) -> List[Dict[str, Optional[str]]]:
    """
    Parse UniRef90 XML file and extract entry data.
    
    Args:
        file_path: Path to the XML or XML.gz file
        
    Returns:
        List of dictionaries containing extracted data
    """
    results = []
    
    try:
        # Determine if file is gzipped
        if file_path.endswith('.gz'):
            file_handle = gzip.open(file_path, 'rt', encoding='iso-8859-1')
        else:
            file_handle = open(file_path, 'r', encoding='iso-8859-1')
        
        with file_handle as f:
            # Parse XML iteratively to handle large files
            context = ET.iterparse(f, events=('start', 'end'))
            context = iter(context)
            
            # Get root element
            event, root = next(context)
            
            entry_count = 0
            for event, elem in context:
                if event == 'end' and elem.tag.endswith('entry'):
                    # Process entry
                    entry_data = extract_entry_data(elem)
                    results.append(entry_data)
                    
                    entry_count += 1
                    if entry_count % 10000 == 0:
                        click.echo(f"Processed {entry_count} entries...")
                    
                    # Clear the element to save memory
                    elem.clear()
                    root.clear()
            
            click.echo(f"Total entries processed: {entry_count}")
            
    except Exception as e:
        click.echo(f"Error parsing XML file: {e}", err=True)
        raise
    
    return results


@click.command()
@click.option('--input-file', '-i', 
              required=True,
              type=click.Path(exists=True),
              help='Path to the UniRef90 XML or XML.gz file')
@click.option('--output-file', '-o',
              default='uniref90_parsed.csv',
              type=click.Path(),
              help='Output CSV file name (default: uniref90_parsed.csv)')
@click.option('--output-format', '-f',
              type=click.Choice(['csv', 'tsv'], case_sensitive=False),
              default='csv',
              help='Output format: csv or tsv (default: csv)')
@click.option('--max-entries', '-m',
              type=int,
              help='Maximum number of entries to process (for testing)')
def main(input_file: str, output_file: str, output_format: str, max_entries: Optional[int]):
    """
    Parse UniRef90 XML file and extract ID information into a table.
    
    This script parses UniRef90 XML files (compressed or uncompressed) and extracts:
    - Main ID (from dbReference)
    - UniRef100 ID
    - UniRef90 ID
    - UniRef50 ID
    - NCBI taxon ID
    
    The output is saved as a CSV or TSV file.
    """
    click.echo(f"Parsing UniRef90 XML file: {input_file}")
    click.echo(f"Output file: {output_file}")
    click.echo(f"Output format: {output_format.upper()}")
    
    if max_entries:
        click.echo(f"Maximum entries to process: {max_entries}")
    
    # Parse the XML file
    try:
        entries = parse_uniref_xml(input_file)
        
        if max_entries:
            entries = entries[:max_entries]
        
        if not entries:
            click.echo("No entries found in the XML file.", err=True)
            return
        
        # Determine delimiter
        delimiter = '\t' if output_format.lower() == 'tsv' else ','
        
        # Write to output file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ID', 'UniRef100_ID', 'UniRef90_ID', 'UniRef50_ID', 'ncbi_taxonomy_id']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=delimiter)
            
            writer.writeheader()
            writer.writerows(entries)
        
        click.echo(f"Successfully wrote {len(entries)} entries to {output_file}")
        
        # Show sample of results
        if entries:
            click.echo("\nSample of parsed data:")
            click.echo("-" * 80)
            for i, entry in enumerate(entries[:3]):
                click.echo(f"Entry {i+1}:")
                for key, value in entry.items():
                    click.echo(f"  {key}: {value}")
                click.echo()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1

if __name__ == '__main__':
    main()