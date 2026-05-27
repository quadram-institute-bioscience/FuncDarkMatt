#!/bin/bash
#SBATCH -p qib-compute
#SBATCH -N 1
#SBATCH -t 4-00:00:00
#SBATCH --mem=16384
#SBATCH -c 1
#SBATCH -J map_RXNS2GF
#SBATCH -o /qib/research-projects/darkmatter/mapping_files/rxn_gf/logs/map_RXNS2GF.%A_%a.out
#SBATCH -e /qib/research-projects/darkmatter/mapping_files/rxn_gf/logs/map_RXNS2GF.%A_%a.err
set -euo pipefail

BIOCYC_RXNS="/qib/research-projects/darkmatter/mapping_files/rxn_gf/biocyc_rxns"
BASE_DIR="/qib/scratch/users/tiwari/rxn_gf"
SCRIPT_DIR="/qib/research-projects/darkmatter/mapping_files/rxn_gf"
DB="/qib/research-projects/darkmatter/mapping_files/uniref_ec_pfam/uniref90_pf_ec.db"

# Build array of all reaction files
mapfile -t RXN_FILES < <(ls "${BIOCYC_RXNS}"/*.txt)

# Apply offset if provided (to work around MaxArraySize=6000 limit)
OFFSET=${OFFSET:-0}
ACTUAL_INDEX=$((SLURM_ARRAY_TASK_ID + OFFSET))

# Select file for this array task
INPUT="${RXN_FILES[$ACTUAL_INDEX]}"

# Extract organism/db name from filename (e.g. metacyc_RXNS.txt -> metacyc)
NAME=$(basename "$INPUT" _RXNS.txt)

echo "Processing: $NAME (task ${SLURM_ARRAY_TASK_ID}, actual index ${ACTUAL_INDEX})"

# Create output directories
mkdir -p "${BASE_DIR}/rxn_ec_uniref90" \
         "${BASE_DIR}/rxn_exactpfamset_uniref90" \
         "${BASE_DIR}/rxn_anypfamset_uniref90" \
         "${BASE_DIR}/rxn_proteinaccession_uniref90" \
         "${BASE_DIR}/logs"

# --- Step 1: EC propagation ---
if [[ -f "${BASE_DIR}/rxn_ec_uniref90/RXN_GF-${NAME}.txt" ]]; then
    echo "${NAME}: Step 1 already completed, skipping"
else
    echo "${NAME}: Step 1 - EC propagation"
    python3 "${SCRIPT_DIR}/query_uniref90sql_db.py" \
        --db "${DB}" \
        --input "${INPUT}" \
        --output "${BASE_DIR}/rxn_ec_uniref90/RXN_GF-${NAME}.txt" \
        --mode ec_propagation \
        --residual "${BASE_DIR}/rxn_ec_uniref90/RXN_NO_GF-${NAME}.txt"
fi

# --- Step 2: Pfam exact set propagation ---
if [[ -f "${BASE_DIR}/rxn_exactpfamset_uniref90/RXN_GF-${NAME}.txt" ]]; then
    echo "${NAME}: Step 2 already completed, skipping"
else
    echo "${NAME}: Step 2 - Pfam exact set propagation"
    python3 "${SCRIPT_DIR}/query_uniref90sql_db.py" \
        --db "${DB}" \
        --input "${BASE_DIR}/rxn_ec_uniref90/RXN_NO_GF-${NAME}.txt" \
        --output "${BASE_DIR}/rxn_exactpfamset_uniref90/RXN_GF-${NAME}.txt" \
        --mode pfam_exact_propagation \
        --residual "${BASE_DIR}/rxn_exactpfamset_uniref90/RXN_NO_GF-${NAME}.txt"
fi

# --- Step 3: Protein accession extraction ---
if [[ -f "${BASE_DIR}/rxn_proteinaccession_uniref90/RXN_NO_GF-${NAME}.txt" ]]; then
    echo "${NAME}: Step 3 already completed, skipping"
else
    echo "${NAME}: Step 3 - Extracting protein accession residuals"
    awk -F"\t" 'BEGIN{OFS="\t"} {gsub(/\r/, "")} $4!="NA" {print $1,$4}' \
        "${BASE_DIR}/rxn_exactpfamset_uniref90/RXN_NO_GF-${NAME}.txt" \
        > "${BASE_DIR}/rxn_proteinaccession_uniref90/RXN_GF-${NAME}.txt"
fi

# --- Step 4: Pfam relaxed propagation ---
#if [[ -f "${BASE_DIR}/rxn_anypfamset_uniref90/RXN_GF-${NAME}.txt" ]]; then
#    echo "${NAME}: Step 4 already completed, skipping"
#else
#    echo "${NAME}: Step 4 - Pfam relaxed propagation"
#    python3 "${SCRIPT_DIR}/query_uniref90sql_db.py" \
#        --db "${DB}" \
#        --input "${BASE_DIR}/rxn_exactpfamset_uniref90/RXN_NO_GF-${NAME}.txt" \
#        --output "${BASE_DIR}/rxn_anypfamset_uniref90/RXN_GF-${NAME}.txt" \
#        --mode pfam_relaxed_propagation \
#        --residual "${BASE_DIR}/rxn_anypfamset_uniref90/RXN_NO_GF-${NAME}.txt"
#fi

echo "${NAME}: All steps completed"