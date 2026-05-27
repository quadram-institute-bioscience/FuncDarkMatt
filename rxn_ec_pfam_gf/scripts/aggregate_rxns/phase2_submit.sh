#!/bin/bash
#SBATCH -p qib-compute
#SBATCH -N 1
#SBATCH -t 1-00:00:00
#SBATCH --mem=16384
#SBATCH -c 4
#SBATCH -J rxn_phase2
#SBATCH --array=0-511%50
#SBATCH -o log/phase2.%A_%a.out
#SBATCH -e log/phase2.%A_%a.err

BUCKET_ID=$(printf "%04d" $SLURM_ARRAY_TASK_ID)

SCRIPT_DIR="scripts/aggregate_rxns"
BUCKET_FILE=$BUCKET_DIR/bucket_${BUCKET_ID}.tsv
OUTPUT_FILE=$DEDUP_DIR/dedup_${BUCKET_ID}.tsv

echo "Task         : $SLURM_ARRAY_TASK_ID"
echo "Bucket file  : $BUCKET_FILE"
echo "Output file  : $OUTPUT_FILE"


python $SCRIPT_DIR/phase2_dedup_bucket.py \
    --bucket-file $BUCKET_FILE \
    --output      $OUTPUT_FILE \
    --tmp-dir     /tmp \
    --parallel    4
