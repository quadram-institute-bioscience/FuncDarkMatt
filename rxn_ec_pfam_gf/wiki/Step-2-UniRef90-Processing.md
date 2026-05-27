# Step 2: UniRef90 Processing

## Step 2.1: Extract UniRef Files

```bash
tar -xzvf uniref2019_01.tar.gz
```

**Expected directory structure:**
```
uniref2019_01/
├── uniref90.xml.gz
└── uniref100.xml.gz
```

## Step 2.2: Build UniRef90 Mapping Databases

Two databases are built in this step:

1. **EC/Pfam annotation database** (`uniref90_pf_ec.db`) — links UniRef90 clusters to EC numbers and Pfam domains. Used in Step 4 for RXN→GF mapping.
2. **Members database** (`uniref90_members`) — links UniRef90 cluster representatives to their member UniProt accessions.

**Expected output:** `uniref90_map_pf_ec.csv`  
**Columns:** `ID, UniRef100_ID, UniRef90_ID, UniRef50_ID, ncbi_taxonomy_id_uniref, accession, ncbi_taxonomy_id_protein, pfam_ids, ec_number`

```bash
# Parse UniRef90 XML for cluster information
python3 parse_uniref.py \
    -i uniref90.xml.gz \
    -o uniref90_map.csv

# Annotate clusters with EC numbers and Pfam domains
python3 map_uniref90_ecpfam_v02.py \
    -u uniref90_map.csv \
    -p protein_accession-combined.csv \
    -o uniref90_map_pf_ec.csv \
    -l 16 \
    -c 50000

# Build EC/Pfam SQLite database
python3 build_uniref90sql_db.py \
    --mapping uniref90_map_pf_ec.csv \
    --db uniref90_pf_ec.db

# Extract cluster member accessions
python3 get_uniref90_members.py \
    -i uniref90.xml.gz \
    -o uniref90_members.csv \
    --log-every 1000000

# Build members SQLite database
python3 uniref_sqlite_cli.py build \
    -m uniref90_members.csv \
    -d uniref90_members
```

**Parameters:**
- `-l 16` — number of parallel processes
- `-c 50000` — chunk size for processing

---

**Next:** [Step 3 — BioCyc Processing](Step-3-BioCyc-Processing)
