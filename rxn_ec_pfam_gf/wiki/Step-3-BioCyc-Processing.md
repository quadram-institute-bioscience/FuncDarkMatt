# Step 3: BioCyc Processing

## Step 3.1: Extract BioCyc Data

```bash
# Extract BioCyc database files
tar -xvzf biocyc-flatfiles.tar.gz -C /path/to/Biocyc

# Create a list of all organism directories with full paths
readlink -f Biocyc/* > directory.list
```

## Step 3.2: Process Per-Species Database Files

For each BioCyc organism database, extract enzyme-reaction, EC number, reaction, and Pfam information.

**Expected output:** One `*_RXNS.txt` file per species  
**Columns:** `RXN`, `EC_NUMBERS`, `PFAM`, `uniref90_ids`

```bash
for CURRENT_DIR in $(cat directory.list); do
    echo "Processing: $CURRENT_DIR"
    bash get_rxns.sh $CURRENT_DIR OUTPUT_DIR
done
```

For large BioCyc releases, this can be parallelised as a SLURM array job — one task per organism directory.

---

**Next:** [Step 4 — Mapping RXNs to Gene Families](Step-4-Mapping-RXNs-to-Gene-Families)
