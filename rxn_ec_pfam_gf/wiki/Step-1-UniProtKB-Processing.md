# Step 1: UniProtKB Processing

## Step 1.1: Extract Database Files

```bash
tar -xvzf knowledgebase2019_01.tar.gz
```

**Expected directory structure:**
```
knowledgebase2019_01/
├── uniprot_sprot.dat.gz
├── uniprot_trembl.dat.gz
├── docs/
└── reldate.txt
```

## Step 1.2: Create Protein Mapping File

Generate a mapping file containing UniProt protein accessions with their associated metadata.

**Expected output:** `protein_accession-combined.csv`  
**Columns:** `ID, accession, ncbi_taxonomy_id, pfam_ids, ec_number`

```bash
# Process Swiss-Prot database
python3 parse_uniprotkb_dat_v2.py \
    -i uniprot_sprot.dat.gz \
    -o protein_accession-sprot.csv \
    -d ','

# Process TrEMBL database
python3 parse_uniprotkb_dat_v2.py \
    -i uniprot_trembl.dat.gz \
    -o protein_accession-trembl.csv \
    -d ','

# Combine both files
bash run_concat.sh
```

---

**Next:** [Step 2 — UniRef90 Processing](Step-2-UniRef90-Processing)
