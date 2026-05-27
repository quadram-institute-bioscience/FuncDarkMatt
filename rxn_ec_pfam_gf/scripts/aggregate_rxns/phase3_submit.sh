#!/bin/bash
#SBATCH -p qib-compute
#SBATCH -N 1
#SBATCH -t 7-00:00:00
#SBATCH --mem=100G
#SBATCH -c 1
#SBATCH -J rxn_phase3
#SBATCH -o log/phase3.%j.out
#SBATCH -e log/phase3.%j.err

cd /qib/research-projects/darkmatter/mapping_files/rxn_gf
SCRIPT_DIR="scripts/aggregate_rxns"
python $SCRIPT_DIR/phase3_concat.py \
    --output-dir   $DEDUP_DIR \
    --final-output $OUTPUT_DIR/rxn_uniref90.txt \
    --n-buckets 512
