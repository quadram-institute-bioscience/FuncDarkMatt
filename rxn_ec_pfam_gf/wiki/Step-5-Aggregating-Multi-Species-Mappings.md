# Step 5: Aggregating Multi-Species RXN Mappings

After Step 4, each BioCyc species has its own set of mapping files. This step merges all per-species results for each strategy into a single unified file. Duplicate RXN entries across species are collapsed into one entry, with their GF assignments combined.

## EC-Number Based Mapping

Merges all `RXN_GF-*.txt` files from `rxn_ec_uniref90/` into a single file.

```bash
#!/bin/bash
#SBATCH -N 1
#SBATCH -t 2-00:00:00
#SBATCH --mem=8192
#SBATCH -c 4

python ./scripts/rxn_bicoyc_merge.py \
    rxn_ec_uniref90/ \
    --output rxn_gf/rxn_ec_uniref90.txt \
    --pattern "RXN_GF-*.txt" \
    --tmp-dir /path/to/tmp
```

## Exact Pfam Set Based Mapping

Merges all `RXN_GF-*.txt` files from `rxn_exactpfamset_uniref90/`. Due to the volume of per-species files, merging is split into three SLURM phases chained via job dependencies. All scripts live in `scripts/aggregate_rxns/`.

---

### Phase 1 — Partition input files into buckets

Scans `INPUT_DIR=rxn_exactpfamset_uniref90/` for `--pattern=RXN_GF-*.txt` files and distributes them across `--n-buckets=512` bucket files, so Phase 2 array tasks can process one bucket independently.

```bash
sbatch phase1_submit.sh
```

What it runs internally:

```bash
python phase1_partition.py \
    "$INPUT_DIR" \
    --bucket-dir "$CHUNK_DIR" \
    --pattern    "$PATTERN" \
    --n-buckets  "$N_CHUNKS"
```

**SLURM resources:** 1 core, 16 GB RAM, up to 7 days

---

### Phase 2 — Sort and deduplicate each bucket (array job)

Runs as a SLURM array (one task per bucket). Each task reads its bucket file, external-sorts the `(RXN, GF)` pairs, deduplicates them, and writes a per-bucket TSV to `CHUNK_DIR`.

```bash
sbatch --dependency=afterok:<PHASE1_JOB> phase2_submit.sh
```

What each array task runs internally:

```bash
python phase2_dedup_bucket.py \
    --bucket-file "$CHUNK_DIR/bucket_<TASK_ID>.tsv" \
    --output      "$DEDUP_DIR/dedup_<TASK_ID>.tsv" \
    --tmp-dir     /tmp \
    --parallel    4
```

**SLURM resources:** 4 cores, 16 GB RAM, up to 7 day — 512 array tasks (`--array=0-511%50`)

---

### Phase 3 — Concatenate all buckets into the final output

Runs after all Phase 2 tasks complete. Merges all per-bucket deduplicated TSVs into a single sorted output file.

```bash
sbatch --dependency=afterok:<PHASE2_JOB> phase3_submit.sh
```

What it runs internally:

```bash
python phase3_concat.py \
    --dedup-dir   "$DEDUP_DIR" \
    --final-output "$OUTPUT" \
    --n-buckets    "$N_CHUNKS"
```

**SLURM resources:** 1 core, 100 GB RAM, up to 7 days

---


## Protein Accession Based Mapping

Merges all `RXN_GF-*.txt` files from `rxn_proteinaccession_uniref90/` using the same three-phase pipeline as [Exact Pfam Set Based Mapping](#exact-pfam-set-based-mapping). Only `--input-dir`, `--bucket-dir`,  `--output` need to change.

---

**Next:** [Mapping File Usage Guidelines](Mapping-File-Usage-Guidelines)
