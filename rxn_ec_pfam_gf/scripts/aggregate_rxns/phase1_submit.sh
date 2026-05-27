#!/bin/bash
#SBATCH -p qib-compute
#SBATCH -N 1
#SBATCH -t 14-00:00:00
#SBATCH --mem=16384
#SBATCH -c 1
#SBATCH -J rxn_phase1
#SBATCH -o log/phase1.%j.out
#SBATCH -e log/phase1.%j.err


mkdir -p $CHUNK_DIR
mkdir -p $DEDUP_DIR

cd /qib/research-projects/darkmatter/mapping_files/rxn_gf
SCRIPT_DIR="scripts/aggregate_rxns"

python $SCRIPT_DIR/phase1_partition.py \
    $INPUT_DIR \
    --bucket-dir $BUCKET_DIR \
    --pattern $PATTERN \
    --n-buckets $N_CHUNKS
