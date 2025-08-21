#!/usr/bin/env python3
"""
Script to process rxn_ec_pfam.txt files from multiple directories
and merge entries with the same RXN by combining unique EC numbers and PFAM values.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

def read_directory_list(input_file):
    """Read list of directories from input file."""
    try:
        with open(input_file, 'r') as f:
            directories = [line.strip() for line in f if line.strip()]
        return directories
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

def parse_rxn_file(file_path):
    """Parse a single rxn_ec_pfam.txt file and return data."""
    data = []
    try:
        with open(file_path, 'r') as f:
            # Skip header line
            next(f)
            for line_num, line in enumerate(f, 2):
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split('\t')
                if len(parts) != 3:
                    print(f"Warning: Invalid line format in {file_path} at line {line_num}: {line}")
                    continue
                
                rxn, ec_number, pfam = parts
                data.append({
                    'rxn': rxn,
                    'ec_number': ec_number,
                    'pfam': pfam,
                    'source_file': file_path
                })
    except FileNotFoundError:
        print(f"Warning: File not found: {file_path}")
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
    
    return data

def merge_rxn_data(all_data):
    """Merge data by RXN, combining unique EC numbers and PFAM values."""
    merged_data = defaultdict(lambda: {'ec_numbers': set(), 'pfams': set(), 'sources': set()})
    
    for entry in all_data:
        rxn = entry['rxn']
        ec_number = entry['ec_number']
        pfam = entry['pfam']
        source = entry['source_file']
        
        merged_data[rxn]['ec_numbers'].add(ec_number) # Add EC number
        merged_data[rxn]['pfams'].add(pfam) # Add PFAM value
        merged_data[rxn]['sources'].add(source) # Track source file
    
    return merged_data

def format_output(merged_data):
    """Format merged data for output."""
    results = []
    
    for rxn in sorted(merged_data.keys()):
        data = merged_data[rxn]
        
        # Format EC numbers and keep unique values only
        ec_numbers = sorted(data['ec_numbers']) if data['ec_numbers'] else ['NA']
        ec_str = ';'.join(ec_numbers)
        ec_str = ';'.join(sorted(set(ec_str.split(';'))))
        # Replace NA; or ;NA with empty string
        ec_str = ec_str.replace('NA;', '').replace(';NA', '').replace(';NA;','')
        
        # Format PFAM values
        pfams = sorted(data['pfams']) if data['pfams'] else ['NA']
        pfam_str = ';'.join(pfams)
        pfam_str = ';'.join(sorted(set(pfam_str.split(';'))))
        pfam_str = pfam_str.replace('NA;', '').replace(';NA', '').replace(';NA;','')
        
        results.append({
            'rxn': rxn,
            'ec_numbers': ec_str,
            'pfams': pfam_str,
            'source_count': len(data['sources'])
        })
    
    return results

def write_output(results, output_file):
    """Write results to output file."""
    try:
        with open(output_file, 'w') as f:
            # Write header
            f.write("RXN\tEC_NUMBERS\tPFAM\tSOURCE_COUNT\n")
            
            # Write data
            for result in results:
                f.write(f"{result['rxn']}\t{result['ec_numbers']}\t{result['pfams']}\t{result['source_count']}\n")
        
        print(f"Results written to: {output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

def main():
    """Main function."""
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python script.py <directory_list_file> <output_file>")
        print("Example: python script.py directories.txt merged_rxn_data.txt")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Read directory list
    print(f"Reading directories from: {input_file}")
    directories = read_directory_list(input_file)
    print(f"Found {len(directories)} directories to process")
    
    # Process all files
    all_data = []
    processed_files = 0
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Warning: Directory not found: {directory}")
            continue
        
        rxn_file = dir_path / "rxn_ec_pfam.txt"
        if rxn_file.exists():
            print(f"Processing: {rxn_file}")
            file_data = parse_rxn_file(rxn_file)
            all_data.extend(file_data)
            processed_files += 1
        else:
            print(f"Warning: rxn_ec_pfam.txt not found in {directory}")
    
    if not all_data:
        print("No data found to process.")
        sys.exit(1)
    
    print(f"Processed {processed_files} files with {len(all_data)} total entries")
    
    # Merge data
    print("Merging data by RXN...")
    merged_data = merge_rxn_data(all_data)
    print(f"Merged into {len(merged_data)} unique RXNs")
    
    # Format output
    results = format_output(merged_data)
    
    # Write output
    write_output(results, output_file)
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Processed files: {processed_files}")
    print(f"- Total entries: {len(all_data)}")
    print(f"- Unique RXNs: {len(merged_data)}")
    print(f"- Output file: {output_file}")

if __name__ == "__main__":
    main()