# RXN → UniRef90 Gene Family Mapping

This Wiki documents the end-to-end pipeline for creating reaction-to-gene-family (RXN→GF) mapping files from BioCyc, UniProtKB, and UniRef90 databases.

## Database Versions

| Database | Version | Notes |
|----------|---------|-------|
| **UniProtKB** | 2019_01 | Swiss-Prot and TrEMBL databases |
| **UniRef90** | 2019_01 | Clustered sequences at 90% identity |
| **BioCyc** | v28.5 (December 10, 2024) | Downloaded under necessary license |

## Prerequisites

- Python 3.x
- Bash shell
- SLURM cluster environment (optional, for parallel processing)
- 100 GB+ disk space

**Required Python scripts:**

| Script | Used in |
|--------|---------|
| `parse_uniprotkb_dat_v2.py` | Step 1 |
| `parse_uniref.py` | Step 2 |
| `map_uniref90_ecpfam_v02.py` | Step 2 |
| `build_uniref90sql_db.py` | Step 2 |
| `get_uniref90_members.py` | Step 2 |
| `uniref_sqlite_cli.py` | Step 2 |
| `parse_proteins-dat.py` | Step 3 |
| `parse_enzrxns-dat.py` | Step 3 |
| `merge_enzrxns_proteins.py` | Step 3 |
| `merge_rxn_ec_pfam.py` | Step 3 |
| `combine_rxn_pfam_ec.py` | Step 3 |
| `merge_rxn_uniref90.py` | Step 3 |
| `merge_rxn_pfam_uniref.py` | Step 3 |

## Pipeline Overview

```
UniProtKB ──┐
            ├──► UniRef90 mapping DBs ──┐
UniRef90 ───┘                           │
                                        ├──► Per-species RXN→GF ──► Aggregated RXN→GF files
BioCyc (multi-species) ─────────────────┘
```

## Steps

| Step | Page | Description |
|------|------|-------------|
| 1 | [UniProtKB Processing](Step-1-UniProtKB-Processing) | Extract and parse UniProtKB flat files |
| 2 | [UniRef90 Processing](Step-2-UniRef90-Processing) | Build UniRef90 annotation and member databases |
| 3 | [BioCyc Processing](Step-3-BioCyc-Processing) | Extract per-species reaction and enzyme data |
| 4 | [Mapping RXNs to Gene Families](Step-4-Mapping-RXNs-to-Gene-Families) | SLURM array job mapping each species |
| 5 | [Aggregating Multi-Species Mappings](Step-5-Aggregating-Multi-Species-Mappings) | Merge per-species results into final files |

See [Mapping File Usage Guidelines](Mapping-File-Usage-Guidelines) for guidance on which output file to use.
