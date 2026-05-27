#!/bin/bash
# Master submission script — chains Phase 1 → Phase 2 → Phase 3
# Phase 2 waits for Phase 1 to finish
# Phase 3 waits for ALL Phase 2 array tasks to finish
#
# Usage:
#   bash submit_all.sh
#
# To monitor:
#   squeue -u $USER
#   tail -f /qib/research-projects/darkmatter/mapping_files/rxn_gf/log/phase1.<jobid>.out

set -e

LOG_DIR=/qib/research-projects/darkmatter/mapping_files/rxn_gf/log
mkdir -p $LOG_DIR

# ── Phase 1 ───────────────────────────────────────────────────────────────────
echo "Submitting Phase 1 (partition)..."
PHASE1_JOB=$(sbatch --parsable phase1_submit.sh)
echo "  Phase 1 job ID: $PHASE1_JOB"

# ── Phase 2 (array) — runs after Phase 1 completes successfully ──────────────
echo "Submitting Phase 2 (array, 1024 tasks)..."
PHASE2_JOB=$(sbatch --parsable \
    --dependency=afterok:$PHASE1_JOB \
    phase2_submit.sh)
echo "  Phase 2 job ID: $PHASE2_JOB"

# ── Phase 3 — runs after ALL Phase 2 array tasks complete successfully ────────
echo "Submitting Phase 3 (concat)..."
PHASE3_JOB=$(sbatch --parsable \
    --dependency=afterok:$PHASE2_JOB \
    phase3_submit.sh)
echo "  Phase 3 job ID: $PHASE3_JOB"

echo ""
echo "── All phases submitted ──────────────────────────────────────────────────"
echo "  Phase 1 : $PHASE1_JOB   (partition)"
echo "  Phase 2 : $PHASE2_JOB   (sort+dedup array, 1024 tasks)"
echo "  Phase 3 : $PHASE3_JOB   (concat)"
echo ""
echo "Monitor with:"
echo "  squeue -u $USER"
echo "  tail -f $LOG_DIR/phase1.${PHASE1_JOB}.out"
echo "  tail -f $LOG_DIR/phase2.${PHASE2_JOB}_0.out   # first array task"
