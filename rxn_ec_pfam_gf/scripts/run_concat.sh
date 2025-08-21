#!/bin/bash

# CSV File Concatenation Script
# Concatenates protein_accession-sprot.csv and protein_accession-trembl.csv
# Keeps header from first file, appends data from second file without header

set -e  # Exit on any error

# Default file names
FILE1="protein_accession-sprot.csv"
FILE2="protein_accession-trembl.csv"
OUTPUT="protein_accession-combined.csv"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -f1, --file1 FILE     First CSV file (default: protein_accession-sprot.csv)"
    echo "  -f2, --file2 FILE     Second CSV file (default: protein_accession-trembl.csv)"
    echo "  -o,  --output FILE    Output file (default: protein_accession-combined.csv)"
    echo "  -h,  --help           Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -f1 sprot.csv -f2 trembl.csv -o combined.csv"
    exit 1
}

# Function to check if file exists
check_file() {
    if [[ ! -f "$1" ]]; then
        echo "Error: File '$1' not found!"
        exit 1
    fi
}

# Function to get file size in human readable format
get_file_size() {
    if command -v numfmt >/dev/null 2>&1; then
        numfmt --to=iec-i --suffix=B --format="%.1f" $(stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null)
    else
        ls -lh "$1" | awk '{print $5}'
    fi
}

# Function to count lines in file
count_lines() {
    wc -l < "$1"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f1|--file1)
            FILE1="$2"
            shift 2
            ;;
        -f2|--file2)
            FILE2="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Display configuration
echo "=========================================="
echo "CSV File Concatenation Script"
echo "=========================================="
echo "First file:  $FILE1"
echo "Second file: $FILE2"
echo "Output file: $OUTPUT"
echo ""

# Check if input files exist
echo "Checking input files..."
check_file "$FILE1"
check_file "$FILE2"

# Display file information
echo "File information:"
echo "  $FILE1: $(get_file_size "$FILE1") ($(count_lines "$FILE1") lines)"
echo "  $FILE2: $(get_file_size "$FILE2") ($(count_lines "$FILE2") lines)"
echo ""

# Check if output file exists and prompt for confirmation
if [[ -f "$OUTPUT" ]]; then
    echo "Warning: Output file '$OUTPUT' already exists!"
    read -p "Do you want to overwrite it? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 0
    fi
fi

# Estimate total lines in output
file1_lines=$(count_lines "$FILE1")
file2_lines=$(count_lines "$FILE2")
total_lines=$((file1_lines + file2_lines - 1))  # -1 because we skip header from second file

echo "Starting concatenation..."
echo "Expected output: $total_lines lines"
echo ""

# Start timing
start_time=$(date +%s)

# Step 1: Copy first file completely
echo "Step 1: Copying first file..."
cat "$FILE1" > "$OUTPUT"
echo "  ✓ Copied $FILE1 ($(count_lines "$FILE1") lines)"

# Step 2: Append second file without header
echo "Step 2: Appending second file (without header)..."
tail -n +2 "$FILE2" | cat >> "$OUTPUT"
echo "  ✓ Appended data from $FILE2 ($((file2_lines - 1)) lines)"

# End timing
end_time=$(date +%s)
duration=$((end_time - start_time))

# Verify the result
output_lines=$(count_lines "$OUTPUT")
output_size=$(get_file_size "$OUTPUT")

echo ""
echo "=========================================="
echo "Concatenation completed successfully!"
echo "=========================================="
echo "Output file: $OUTPUT"
echo "Final size:  $output_size"
echo "Total lines: $output_lines"
echo "Duration:    ${duration}s"
echo ""

# Verify line count matches expectation
if [[ $output_lines -eq $total_lines ]]; then
    echo "✓ Line count verification: PASSED"
else
    echo "⚠ Line count verification: FAILED"
    echo "  Expected: $total_lines"
    echo "  Actual:   $output_lines"
fi

# Show first and last few lines
echo ""
echo "First 5 lines of output:"
head -n 5 "$OUTPUT"
echo ""
echo "Last 5 lines of output:"
tail -n 5 "$OUTPUT"
echo ""
echo "Done!"
