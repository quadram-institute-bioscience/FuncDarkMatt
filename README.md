# FuncDarkMatt
The Missing Microbial Metabolic Link: Functional Dark Matter

## Introduction
### Gene-Protein-Reaction (GPR) Mapping Framework
A hierarchical mapping framework that integrates BioCyc reactions with UniRef90 gene families through EC number and Pfam domain-based strategies, enabling multi-resolution functional profiling of metagenomic data.
Standard pathway-based functional profiling misses roughly one-third of known enzymatic reactions that lack pathway annotations. This framework addresses that gap by constructing comprehensive GPR mappings that can be used directly as custom mapping files with tools like HUMAnN.

## Pipeline Overview

```
UniProtKB ──┐
            ├──► UniRef90 mapping DBs ──┐
UniRef90 ───┘                           │
                                        ├──► Per-species RXN→GF ──► Aggregated RXN→GF files
BioCyc (multi-species) ─────────────────┘
```

The pipeline runs in five steps:

| Step | Description |
|------|-------------|
| 1 | **UniProtKB Processing** — parse Swiss-Prot and TrEMBL flat files into a combined protein accession table (ID, accession, NCBI taxonomy, Pfam domains, EC numbers) |
| 2 | **UniRef90 Processing** — build a SQLite annotation database and member-lookup database for UniRef90 clusters |
| 3 | **BioCyc Processing** — extract per-species reaction, enzyme, EC, and Pfam data into `*_RXNS.txt` files |
| 4 | **Mapping RXNs to Gene Families** — apply a three-strategy hierarchical mapping (EC → Pfam → UP-AC) per species via SLURM array job |
| 5 | **Aggregating Multi-Species Mappings** — merge and deduplicate per-species results into three final output files |

### Mapping Strategy (Step 4)

Strategies are applied from most to least specific; reactions unmapped by one strategy are passed to the next.

```
All RXNs with UniProt Accession (UP-AC)  → GF pool assigned
         ↓
EC mapping  → hit: GF assigned (EC + UP-AC pooled)     → File 1
             no hit: residual
         ↓
Pfam mapping (exact set match)
            → hit: GF assigned (Pfam + UP-AC pooled)   → File 2 additions
             no hit: final residual
         ↓
UP-AC only  → GF assigned if UP-AC exists              → File 3 additions
```

## Repository Structure

```
.
├── README.md
└── rxn_ec_pfam_gf
    ├── README.md                        ## Quick-start and database version table
    ├── data
    │   └── directory.list               ## Paths to BioCyc organism directories
    ├── FuncDarkMatt.wiki                ## Step-by-step documentation (Steps 1–6)
    │   ├── Home.md
    │   ├── Step-1-UniProtKB-Processing.md
    │   ├── Step-2-UniRef90-Processing.md
    │   ├── Step-3-BioCyc-Processing.md
    │   ├── Step-4-Mapping-RXNs-to-Gene-Families.md
    │   ├── Step-5-Aggregating-Multi-Species-Mappings.md
    │   └── Step-6-Mapping-File-Usage-Guidelines.md
    └── scripts
        ├── download_databases.sh        ## Download UniProtKB and UniRef90
        ├── run_concat.sh                ## Concatenate Swiss-Prot + TrEMBL outputs
        ├── parse_uniprotkb_dat_v2.py    ## Step 1 — parse UniProtKB flat files
        ├── parse_uniref.py              ## Step 2 — parse UniRef90 XML
        ├── map_uniref90_ecpfam_v02.py   ## Step 2 — annotate UniRef90 clusters with EC/Pfam
        ├── build_uniref90sql_db.py      ## Step 2 — build annotation SQLite DB
        ├── uniref_sqlite.py             ## Step 2/3 — UniRef90 SQLite utilities
        ├── get_uniref90_members.py      ## Step 2 — build member-lookup SQLite DB
        ├── parse_proteins-dat.py        ## Step 3 — parse BioCyc proteins.dat
        ├── parse_enzrxn-dat.py          ## Step 3 — parse BioCyc enzrxns.dat
        ├── parse_reactions-dat.py       ## Step 3 — parse BioCyc reactions.dat
        ├── join_reactions.py            ## Step 3 — join enzyme/reaction tables
        ├── expand_enzrxn.py             ## Step 3 — expand multi-subunit enzyme entries
        ├── merge_enzrxn_pfam_rxn.py     ## Step 3 — merge Pfam annotations into reactions
        ├── merge_rxn_ec_pfam.py         ## Step 3 — merge EC and Pfam into final RXNS table
        ├── merge_enzrxns_proteins.py    ## Step 3 — merge enzyme-reaction and protein tables
        ├── get_rxns.sh                  ## Step 3 — orchestrate per-species extraction
        ├── map_RXNS2GF.sh               ## Step 4 — SLURM array job driver
        ├── query_uniref90sql_db.py      ## Step 4 — query annotation DB for EC/Pfam lookup
        ├── rxn_bicoyc_merge.py          ## Step 5 — merge per-species EC mappings
        └── aggregate_rxns               ## Step 5 — three-phase SLURM pipeline for Pfam/UP-AC
            ├── submit_all.sh
            ├── phase1_partition.py      ## Distribute input files into buckets
            ├── phase1_submit.sh
            ├── phase2_dedup_bucket.py   ## Sort and deduplicate each bucket (array job)
            ├── phase2_submit.sh
            ├── phase3_concat.py         ## Concatenate deduplicated buckets
            └── phase3_submit.sh
```

## Database Versions

| Database | Version |
|----------|---------|
| UniProtKB | 2019_01 (Swiss-Prot + TrEMBL) |
| UniRef90 | 2019_01 |
| BioCyc | v29.0 (December 2024) |

## Citation
If you use this framework, please cite: 
* Identifying Fundamental Gaps in Functional Metagenomics: A Step Towards Unlocking Microbiome Research Potential [https://doi.org/10.64898/2026.01.10.698778]

## License
This work is licensed under a CC-BY 4.0 International License.
