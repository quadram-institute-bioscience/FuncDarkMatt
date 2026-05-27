# Step 4: Mapping RXNs to Gene Families

Each per-species `*_RXNS.txt` file from Step 3 is mapped to UniRef90 gene families (GFs) using a hierarchical three-strategy approach.

## Mapping Strategy Overview

Strategies are applied from most to least specific. Reactions unmapped by one strategy are passed to the next.

| Priority | Strategy | Matching key |
|----------|----------|--------------|
| 1 | **Protein Accession** | Direct UniProt accession match (performed in Step 3.2) |
| 2 | **EC-Number** | Shared EC number(s) between reaction and UniRef90 cluster |
| 3 | **Exact Pfam Set** | Identical Pfam domain set (order-independent, exact match only) |

### Exact Pfam Set Matching — Detail

Each reaction can carry one or more Pfam domain sets (reflecting alternative subunit or isoform compositions). A GF is assigned only when its Pfam composition is an **exact set match** to the query.

| Scenario | Pfam sets on reaction | Match result | GF assignment |
|----------|-----------------------|--------------|---------------|
| Single set, full match | `{PF00001}` | `{PF00001}` found | ✅ Assigned |
| Single set, partial match | `{PF00001, PF00002}` | Only `{PF00001}` found | ❌ Not assigned |
| Single set, no match | `{PF00001}` | Not in database | ❌ Not assigned |
| Multiple sets, all match | `{PF00001}`, `{PF00002, PF00003}` | Both found | ✅ GFs from both sets pooled |
| Multiple sets, partial match | `{PF00001}`, `{PF00099}` | Only first found | ✅ GFs from matched set only |

## Running the Mapping

The mapping runs as a SLURM array job — one task per BioCyc organism file.

**Before submitting, set these variables at the top of `scripts/map_RXNS2GF.sh`:**

| Variable | Description |
|----------|-------------|
| `BIOCYC_RXNS` | Directory containing per-organism `*_RXNS.txt` files from Step 3 |
| `BASE_DIR` | Output root directory (subdirectories created automatically) |
| `SCRIPT_DIR` | Directory containing the Python scripts |
| `DB` | Path to `uniref90_pf_ec.db` built in Step 2 |

**Array size:** Set `--array=0-N` where `N = (number of files) - 1`. For clusters with a `MaxArraySize` limit, submit in batches using the `OFFSET` variable:

```bash
# Standard submission
sbatch --array=0-N scripts/map_RXNS2GF.sh

# Batched submission example
OFFSET=6000 sbatch --array=0-5999 scripts/map_RXNS2GF.sh
```

Each task runs all mapping steps sequentially with checkpointing, so incomplete runs can be safely resumed.

## Output

Three directories are created under `BASE_DIR`:

| Directory | Contents |
|-----------|----------|
| `rxn_ec_uniref90/` | EC-number based RXN→GF mappings |
| `rxn_exactpfamset_uniref90/` | Exact Pfam set RXN→GF mappings |
| `rxn_proteinaccession_uniref90/` | Protein-accession based RXN→GF mappings |

Each directory contains:
- `RXN_GF-{NAME}.txt` — reactions successfully mapped to a GF
- `RXN_NO_GF-{NAME}.txt` — unmapped residuals passed to the next strategy

---

**Next:** [Step 5 — Aggregating Multi-Species Mappings](Step-5-Aggregating-Multi-Species-Mappings)
