#!/bin/bash

################################################################################
# BioCyc Reactions
################################################################################
#
# DESCRIPTION:
#   Processes BioCyc database files to extract and enrich reaction data with
#   protein information, PFAM domains, gene family associations, and EC numbers.
#   This pipeline integrates data from multiple BioCyc flat files with UniRef90
#   protein clusters to create comprehensive reaction-to-gene-family mappings.
#
# USAGE:
#   ./get_rxns.sh <input_dir> <output_name>
#
# ARGUMENTS:
#   <input_dir>   Directory containing BioCyc flat files:
#                 - proteins.dat (protein data with catalyzed reactions)
#                 - enzrxns.dat (enzyme reaction associations)
#                 - reactions.dat (reaction definitions)
#                 - reaction-links.dat (reaction relationships)
#
#   <output_name> Name for the output directory (outputs will be placed in
#                 <output_name>_mapping/)
#
# OUTPUT FILES (in <output_name>_mapping/):
#   - proteins-dat.csv              Parsed proteins with catalyzed reactions
#   - enzrxn.csv                    Enzymerxn-reaction associations
#   - reactions.txt                 Reaction definitions
#   - merged_reactions.txt          Reactions with cross-links
#   - enzrxn_expanded.csv           Expanded enzyme reactions with PFAM/UniProt
#   - enzrxn_uniref_joined.csv      Enzyme reactions mapped to UniRef90 clusters
#   - enzrxn_rxn_pfam_gf.csv        Merged enzyme reactions with PFAM/genes
#   - rxn_ec_pfam_gf.txt            Final output: reactions with EC/PFAM/families
#
# DEPENDENCIES:
#   - Python 3
#   - Parse scripts: parse_proteins-dat.py, parse_enzrxn-dat.py,
#     parse_reactions-dat.py, join_reactions.py, expand_enzrxn.py
#   - UniRef utilities: uniref_sqlite.py
#   - Merge scripts: merge_enzrxn_pfam_rxn.py, merge_rxn_ec_pfam.py
#   - UniRef90 database: /qib/research-projects/darkmatter/databases/uniref/uniref2019_01
#
# EXAMPLE:
#   ./get_rxns.sh /path/to/biocyc/data myproject
#   # Creates: myproject_mapping/ with all output files
#
# NOTES:
#   - This script exits on any error (set -e)
#   - Files are validated for existence and non-empty before use
#   - UniRef90 index is built on first run and cached for subsequent runs
#   - All intermediate files are consolidated into the output directory
#
################################################################################

set -e
INPUT_DIR=$1
OUTPUT=$2
UNIREF_DIR="uniref2019_01" # with uniref90_members.csv and uniref90_members (SQLite index)
SCRIPTS_DIR="scripts" # Directory containing all the Python scripts used in this pipeline (parse_*.py, uniref_sqlite.py, merge_*.py)

# Create output directory if it doesn't exist
BIOCYC_DB="$(basename $INPUT_DIR)"
mkdir -p "$OUTPUT/${BIOCYC_DB}_mapping"
mkdir -p "$OUTPUT/biocyc_rxns"

# Display help if no arguments provided
if [[ -z "$INPUT_DIR" ]] || [[ -z "$OUTPUT" ]]; then
    echo "BioCyc Reaction Data Pipeline"
    echo ""
    echo "USAGE: ./get_rxns.sh <input_dir> <output_name>"
    echo ""
    echo "ARGUMENTS:"
    echo "  <input_dir>   Directory containing BioCyc flat files (proteins.dat, enzrxns.dat,"
    echo "                reactions.dat, reaction-links.dat)"
    echo "  <output_name> Name for the output directory (<output_name>_mapping/)"
    echo ""
    echo "EXAMPLE:"
    echo "  ./get_rxns.sh /path/to/biocyc/data myproject"
    echo ""
    echo "For more information, see the script header comments."
    exit 1
fi

check_file() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Expected file not found: $file" >&2
        exit 1
    fi
    if [[ ! -s "$file" ]]; then
        echo "ERROR: Expected file is empty: $file" >&2
        exit 1
    fi
}

# Step 1: Parse proteins.dat INPUT: proteins.dat OUTPUT: proteins-dat.csv # File contains: UNIQUE-ID (MONOMER), CATALYZES, PFAM, UNIPROT
echo "Running Step 1: Parsing proteins.dat..."
check_file $INPUT_DIR/proteins.dat
python3 $SCRIPTS_DIR/parse_proteins-dat.py \
    -i  $INPUT_DIR/proteins.dat \
    -o $OUTPUT/${BIOCYC_DB}_mapping/proteins-dat.csv
check_file $OUTPUT/${BIOCYC_DB}_mapping/proteins-dat.csv

# Step 2: Parse enzrxn.dat INPUT: enzrxn.dat OUTPUT: enzrxn.csv # File contains: ENZYME_RXN, REACTION
echo "Running Step 2: Parsing enzrxns.dat..."
check_file $INPUT_DIR/enzrxns.dat
python3 $SCRIPTS_DIR/parse_enzrxn-dat.py \
    -i  $INPUT_DIR/enzrxns.dat \
    -o $OUTPUT/${BIOCYC_DB}_mapping/enzrxn.csv
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn.csv

# Step 3: Parse reactions.dat INPUT: reactions.dat OUTPUT: reactions.txt # File contains: UNIQUE-ID (REACTION), EC-NUMBER, ENZYMATIC-REACTION (ENZYME_RXN)
echo "Running Step 3: Parsing reactions.dat..."
check_file $INPUT_DIR/reactions.dat
python3 $SCRIPTS_DIR/parse_reactions-dat.py \
    -i $INPUT_DIR/reactions.dat \
    -o $OUTPUT/${BIOCYC_DB}_mapping/reactions.txt
check_file $OUTPUT/${BIOCYC_DB}_mapping/reactions.txt

# Step 4: Merge reactions with links INPUT: reactions.txt,reaction-links.dat OUTPUT: merged_reactions.txt # File contains: UNIQUE-ID (REACTION), EC-NUMBER, ENZYMATIC-REACTION (ENZYME_RXN)
echo "Running Step 4: Merging reactions with reaction-links.dat..."
check_file $OUTPUT/${BIOCYC_DB}_mapping/reactions.txt
check_file $INPUT_DIR/reaction-links.dat
python3 $SCRIPTS_DIR/join_reactions.py \
    $OUTPUT/${BIOCYC_DB}_mapping/reactions.txt \
    $INPUT_DIR/reaction-links.dat \
    $OUTPUT/${BIOCYC_DB}_mapping/merged_reactions.txt
check_file $OUTPUT/${BIOCYC_DB}_mapping/merged_reactions.txt

# Step 5: Expand ENZRXN entries INPUT: proteins-dat.csv OUTPUT: enzrxn_expanded.csv # File contains: ENZRXN, MONOMER, PFAM, UNIPROT
echo "Running Step 5: Expanding ENZRXN entries..."
check_file $OUTPUT/${BIOCYC_DB}_mapping/proteins-dat.csv
python3 $SCRIPTS_DIR/expand_enzrxn.py \
    --input  $OUTPUT/${BIOCYC_DB}_mapping/proteins-dat.csv \
    --output $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_expanded.csv
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_expanded.csv

# Step 6.1: Build UniRef90 cluster IDs index (one-time setup)
if [[ ! -f "$UNIREF_DIR/uniref90_members" ]]; then
    echo "Running Step 6.1: Building UniRef90 SQLite index..."
    check_file $UNIREF_DIR/uniref90_members.csv
    python3 $SCRIPTS_DIR/uniref_sqlite.py build \
        --mapping $UNIREF_DIR/uniref90_members.csv \
        --db      $UNIREF_DIR/uniref90_members
    check_file $UNIREF_DIR/uniref90_members
else
    echo "Skipping Step 6.1: UniRef90 SQLite index already exists."
fi

# Step 6.2: Join with UniRef90 cluster IDs INPUT: enzrxn_expanded.csv uniref90_members OUTPUT: enzrxn_uniref_joined.csv # File contains: ENZRXN, MONOMER, PFAM, UNIPROT, entry_id (UniRef90 cluster ID)
echo "Running Step 6.2: Joining with UniRef90 cluster IDs..."
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_expanded.csv
check_file $UNIREF_DIR/uniref90_members
python3 $SCRIPTS_DIR/uniref_sqlite.py join \
    --db      $UNIREF_DIR/uniref90_members \
    --enzrxn  $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_expanded.csv \
    --output  $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_uniref_joined.csv
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_uniref_joined.csv

# Step 7: Merge ENZRXN, PFAM, UniRef90 with REACTIONS INPUT: enzrxn_uniref_joined.csv enzrxn.txt OUTPUT: enzrxn_rxn_pfam_gf.csv # File contains: ENZRXN, REACTION, PFAM, uniref90_ids (UniRef90 cluster ID)
echo "Running Step 7: Merging ENZRXN, PFAM, UniRef90 with REACTIONS..."
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_uniref_joined.csv
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn.csv
python3 $SCRIPTS_DIR/merge_enzrxn_pfam_rxn.py \
    --uniref  $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_uniref_joined.csv \
    --rxn     $OUTPUT/${BIOCYC_DB}_mapping/enzrxn.csv \
    --output  $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_rxn_pfam_gf.csv
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_rxn_pfam_gf.csv

# Step 8: Merge Reactions, EC, PFAM, Gene Families INPUT: enzrxn_rxn.csv combined_ec_pfam.txt OUTPUT: combined_rxn_ec_pfam.txt
echo "Running Step 8: Merging Reactions, EC, PFAM, and Gene Families..."
check_file $OUTPUT/${BIOCYC_DB}_mapping/merged_reactions.txt
check_file $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_rxn_pfam_gf.csv
python3 $SCRIPTS_DIR/merge_rxn_ec_pfam.py \
    --file1  $OUTPUT/${BIOCYC_DB}_mapping/merged_reactions.txt \
    --file2  $OUTPUT/${BIOCYC_DB}_mapping/enzrxn_rxn_pfam_gf.csv \
    --output  $OUTPUT/${BIOCYC_DB}_mapping/rxn_ec_pfam_gf.txt
check_file $OUTPUT/${BIOCYC_DB}_mapping/rxn_ec_pfam_gf.txt

# Move all outputs into a directory named after the input dir
#echo "Moving output files to $OUTPUT_DIR/..."
#mv proteins-dat.csv \
#   enzrxn.csv \
#   reactions.txt \
#   merged_reactions.txt \
#   enzrxn_expanded.csv \
#   enzrxn_uniref_joined.csv \
#   enzrxn_rxn_pfam_gf.csv \
#   rxn_ec_pfam_gf.txt \
#   "$OUTPUT/${BIOCYC_DB}_mapping"

echo "Done. All outputs are in ${OUTPUT}/${BIOCYC_DB}_mapping/"

cp "$OUTPUT/${BIOCYC_DB}_mapping/rxn_ec_pfam_gf.txt" "$OUTPUT/biocyc_rxns/${BIOCYC_DB}_RXNS.txt"

echo "Copying done!!! biocyc_rxns/${BIOCYC_DB}_RXNS.txt"