# Creating RXN --> UniRef90 GeneFamily Mapping File

## 📊 Database Versions

| Database | Version | Notes |
|----------|---------|-------|
| **UniProtKB** | 2019_01 | Swiss-Prot and TrEMBL databases |
| **UniRef90** | 2019_01 | Clustered sequences at 90% identity |
| **BioCyc** | v28.5 (December 10, 2024) | Downloaded under necessary license |

---

## 🔧 Prerequisites

- Python 3.x
- Required Python scripts:
  - `parse_uniprotkb_dat_v2.py`
  - `parse_uniref.py`
  - `map_uniref90_ecpfam_v02.py`
  - `uniref_grouper.py`
  - `parse_proteins-dat.py`
  - `parse_enzrxns-dat.py`
  - `merge_enzrxns_proteins.py`
  - `merge_rxn_ec_pfam.py`
  - `combine_rxn_pfam_ec.py`
  - `merge_rxn_uniref90.py`
  - `merge_rxn_pfam_uniref.py`
- Bash shell
- SLURM cluster environment (optional, for parallel processing)
- Sufficient disk space for processing large database files (100GB+ recommended)

---

## 📝 Step-by-Step Instructions

### 1️⃣ UniProtKB Processing

#### Step 1.1: Extract Database Files

```bash
# Extract the UniProtKB archive
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

#### Step 1.2: Create Protein Mapping File

Generate a mapping file containing protein accessions with their associated metadata.

**Expected output:** `protein_accession-combined.csv`  
**Columns:** `ID,accession,ncbi_taxonomy_id,pfam_ids,ec_number`

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

### 2️⃣ UniRef90 Processing

#### Step 2.1: Extract UniRef Files

```bash
# Extract the UniRef archive
tar -xzvf uniref2019_01.tar.gz
```

**Expected directory structure:**
```
uniref2019_01/
├── uniref90.xml.gz
└── uniref100.xml.gz
```

#### Step 2.2: Create UniRef90 Mapping File

Generate the final UniRef90 mapping file with EC numbers and Pfam annotations.

**Expected output:** `uniref90_map_pf_ec.csv` \
**Columns:** `ID,UniRef100_ID,UniRef90_ID,UniRef50_ID,ncbi_taxonomy_id_uniref,accession,ncbi_taxonomy_id_protein,pfam_ids,ec_number`

```bash
# Parse UniRef90 XML for cluster information
python3 parse_uniref.py \
    -i uniref90.xml.gz \
    -o uniref90_map.csv

# Annotate with EC numbers and Pfam domains
python3 map_uniref90_ecpfam_v02.py \
    -u uniref90_map.csv \
    -p protein_accession-combined.csv \
    -o uniref90_map_pf_ec.csv \
    -l 16 \
    -c 50000
```

**Parameters explained:**
- `-l 16`: Number of parallel processes
- `-c 50000`: Chunk size for processing

#### Step 2.3: Create EC --> GF mapping file
Group the GF based on EC. This results in the GFs assoicated to individual ECs.  

**Expected output:** `ec_uniref_grouped.csv`  
**Columns:** `ec_number,uniref90_ids`

```bash
python3 uniref_grouper.py \
    --uniref-file uniref90_map_pf_ec.csv \
    --output-file ec_uniref_grouped.csv \
    -v
```
#### Step 2.4: Create PFAM --> GF mapping file
Group the GF based on exact PFAM match.
Example:

_Input:_ 
|PFAM|GF|
|----|--|
|PF1|GF1|
|PF1,PF2|GF2,GF3|
|PF1|GF4|

_Output:_ 
|PFAM|GF|
|----|--|
|PF1|GF1,GF4|
|PF1,PF2|GF2,GF3|

```bash
python3 uniref_grouper.py \
    --uniref-file uniref90_map_pf_ec.csv \
    --output-file pfam_uniref_grouped_v03.csv \
    --group-by pfam_ids
    -v
```
---


### 3️⃣ BioCyc Processing

#### Step 3.1: Extract and Process BioCyc Data

```bash
# Extract BioCyc database files
tar -xvzf biocyc-flatfiles.tar.gz -C /qib/research-groups/CoreBioInfo/projects/FuncMeta/Biocyc

# Create a list of directories with full path within Biocyc
readlink -f Biocyc/* >directory.list
```

#### Step 3.2: Process BioCyc Database Files
For each BioCyc organism database, extract enzymereaction, ec, reaction and pfam information. This can be done either sequentially or in parallel using SLURM.

```bash
# Process each BioCyc directory
for CURRENT_DIR in $(cat directory.list); do
    echo "Processing directory: $CURRENT_DIR"
    
    # Step a) Parse proteins.dat to extract protein-enzymereaction-Pfam relationships
    if [[ -f "$CURRENT_DIR/proteins.dat" ]]; then
        python3 "$SCRIPT_DIR/parse_proteins-dat.py" \
            -i "$CURRENT_DIR/proteins.dat" \
            -o "$CURRENT_DIR/proteins_enzrxn_pfam.csv"
    fi
    
    # Step b) Parse enzrxns.dat to extract enzymereaction-rxn relationships
    if [[ -f "$CURRENT_DIR/enzrxns.dat" ]]; then
        python3 "$SCRIPT_DIR/parse_enzrxns-dat.py" \
            -i "$CURRENT_DIR/enzrxns.dat" \
            -o "$CURRENT_DIR/enzrxn_rxn.csv"
    fi
    
    # Step c) Merge protein-enzymereaction-Pfam and enzymereaction-rxn data to create rxn-Pfam mapping
    if [[ -f "$CURRENT_DIR/proteins_enzrxn_pfam.csv" && -f "$CURRENT_DIR/enzrxn_rxn.csv" ]]; then
        python3 "$SCRIPT_DIR/merge_enzrxns_proteins.py" \
            --file1 "$CURRENT_DIR/proteins_enzrxn_pfam.csv" \
            --file2 "$CURRENT_DIR/enzrxn_rxn.csv" \
            --output "$CURRENT_DIR/rxn_pfam.txt"
    fi
    
    # Step d) Merge reaction-pfam data with EC numbers from reaction-links.dat
    if [[ -f "$CURRENT_DIR/rxn_pfam.txt" && -f "$CURRENT_DIR/reaction-links.dat" ]]; then
        python3 "$SCRIPT_DIR/merge_rxn_ec_pfam.py" \
            --file1 "$CURRENT_DIR/reaction-links.dat" \
            --file2 "$CURRENT_DIR/rxn_pfam.txt" \
            --output "$CURRENT_DIR/rxn_ec_pfam.txt"
    fi
done
```

#### Step 3.3: Consolidate BioCyc Results
After processing all organism databases, combine all the `rxn_ec_pfam.txt` into a single mapping file.

**Expected Output**: `combined_rxn_ec_pfam.txt` \
**Columns**: `RXN	EC_NUMBERS	PFAM	SOURCE_COUNT`

```bash
python3 "$SCRIPT_DIR/combine_rxn_pfam_ec.py" directory.list combined_rxn_ec_pfam.txt
```
---

### 4️⃣ Map Reactions (RXN) to Gene-Families (Uniref90)

Create RXN to UniRef90 gene families mappings using a hierarchical matching approach that produces four distinct mapping files based on different levels of evidence and specificity.

##### 📊 Mapping Strategy Overview
The reaction to gene families mapping uses four different matching criteria, from most to least specfic:

1. **EC-Number Based Mapping** - Pair each reaction (RXN) with gene family/families (GF) based on shared EC number(s).
2. **Exact PFAM Mapping** - From the reactions left unmapped reactions in `EC-Number Based Mapping`, pair those with only PFAM based on exact PFAM matches.
3. **EC-Number + Excat PFAM Mapping** - From the reactions left unmapped in `Exact PFAM Mapping`, pair those that have both EC and PFAM (but no GF) to GFs based on exact PFAM matches.
4. **Any PFAM Mapping** - For the rest of the unmapped reactions, pair those with PFAM based on any PFAM matches.

##### Mapping File Generation

**Step 4.1: EC-Number Based Mapping**  
Generate mappings where reactions and gene families share EC numbers.

```bash
python3 merge_rxn_uniref90.py \
    --ec-uniref uniref2019_01/ec_uniref_grouped.csv \
    --rxn-ec-pfam combined_rxn_ec_pfam.txt \
    --output-dir uniref2019_01/rxn_ec_uniref90

# Expected output files:
1. RXN_EC.txt  
2. RXN_EC_UNIREF90.txt  
3. RXN_UNIREF90.txt (Main mapping file)
4. RXN_NO_UNIREF90.txt  
```
**Step4.2: Exact PFAM Mapping**
From the reactions that could not be assigned to any Gene Family (GF) in `Step 4.1`, take those that have only PFAM(s) and assign them to GFs based on exact PFAM matches.

```bash
python3 merge_rxn_pfam_uniref.py \
    --only-pfam \
    --pfam-uniref uniref2019_01/pfam_uniref_grouped_v03.csv \
    --rxn-ec-pfam uniref2019_01/rxn_ec_uniref90/RXN_NO_UNIREF90.txt \
    --output-dir uniref2019_01/rxn_only_pfam

# Expected Output Files:
1. RXN_PFAM.txt 
2. RXN_PFAM_UNIREF90.txt 
3. RXN_UNIREF90.txt 
4. RXN_NO_UNIREF90.txt 
```

**Step 4.3: EC-Number + Excat PFAM Mapping**  
From the reactions that could not be assigned to any Gene Family (GF) in `Step 4.2`, take those that have both EC number(s) and PFAM(s) and assign them to GFs based on exact PFAM matches.

```bash
python3 merge_rxn_pfam_uniref.py \
   --pfam-uniref  uniref2019_01/pfam_uniref_grouped_v03.csv \
   --rxn-ec-pfam rxn_only_pfam/RXN_NO_UNIREF90.txt \
   --output-dir uniref2019_01/rxn_ec_pfam_uniref90

# Expected output Files:
1. RXN_PFAM.txt 
2. RXN_EC_PFAM_UNIREF90.txt 
3. RXN_UNIREF90.txt (Main mapping file)
4. RXN_NO_UNIREF90.txt
```

**Step4.4 Any PFAM Mapping**
For the rest of the reactions (with or without EC) having PFAM(s) from `Step 4.3`, assign them to any GF based on any PFAM match.

```bash
python3 merge_rxn_pfam_uniref.py \
   --all-pfam \
   --pfam-uniref uniref2019_01/pfam_uniref_grouped_v03.csv \
   --rxn-ec-pfam uniref2019_01/rxn_ec_pfam_uniref90/RXN_NO_UNIREF90.txt \
   --output-dir uniref2019_01/rxn_allpfam_uniref90

# Expected output Files:
1. RXN_PFAM.txt 
2. RXN_EC_PFAM_UNIREF90.txt 
3. RXN_UNIREF90.txt (Main mapping file)
4. RXN_NO_UNIREF90.txt
```
---
## 📋 Mapping File Usage Guidelines

**Choosing the Right Mapping File:**
| Use Case | File | Mapping strategy |
|----------|------|------------------|
| High-confidence functional annotation | RXN_UNIREF90.txt | `EC-Number Based Mapping`, `Exact PFAM Mapping`, `EC-Number + Excat PFAM Mapping` |
| Higher coverage |  RXN_UNIREF90.txt | `Any PFAM Mapping` |
