# FuncDarkMatt
The Missing Microbial Metabolic Link: Functional Dark Matter

## Introduction
### Gene-Protein-Reaction (GPR) Mapping Framework
A hierarchical mapping framework that integrates BioCyc reactions with UniRef90 gene families through EC number and Pfam domain-based strategies, enabling multi-resolution functional profiling of metagenomic data.
Standard pathway-based functional profiling misses roughly one-third of known enzymatic reactions that lack pathway annotations. This framework addresses that gap by constructing comprehensive GPR mappings that can be used directly as custom mapping files with tools like HUMAnN.

## Repository structure:
```.
├── README.md
└── rxn_ec_pfam_gf            ## Scripts and step-by-step guide
    ├── data
    │   └── directory.list
    ├── README.md             ## Detailed procedure for building the
    └── scripts
        ├── combine_rxn_pfam_ec.py
        ├── download_databases.sh
        ├── map_uniref90_ecpfam_v02.py
        ├── merge_enzrxns_proteins.py
        ├── merge_rxn_ec_pfam.py
        ├── merge_rxn_pfam_uniref.py
        ├── merge_rxn_uniref90.py
        ├── parse_enzrxns-dat.py
        ├── parse_proteins-dat.py
        ├── parse_uniprotkb_dat_v2.py
        ├── parse_uniref.py
        ├── run_concat.sh
        └── uniref_grouper.py
```
## Citation
If you use this framework, please cite: 
* Identifying Fundamental Gaps in Functional Metagenomics: A Step Towards Unlocking Microbiome Research Potential [https://doi.org/10.64898/2026.01.10.698778]

## License
This work is licensed under a CC-BY 4.0 International License.

