# FuncDarkMatt
Unravelling Microbial Dark Matter: Advancing the Paradigm of Function-Based Microbiome Research

## Rationale

Microbiome research largely relies on taxonomic profiling, but this approach is highly variable due to factors like diet, lifestyle, and host/environment conditions. In contrast, emerging evidence suggests that microbiome function, particularly metabolic activity, is more conserved across individuals and environments. This functional redundancy highlights the need to shift from taxonomy-based analyses to a functional perspective for more relevant insights and a move toward causation rather than mere associations.

However, a major challenge in functional microbiome research is the lack of robust functional annotation, with much of metagenomic data classified as "microbial functional dark matter" - unknown genes and functions. This project aims to address this gap by improving the functional annotation at the level of Gene-Protein-Reaction (GPR) associations, paving the way for a deeper understanding of microbiome function.

To achieve this, we will refine the HUMAnN pipeline, a widely used tool for microbiome functional profiling. Currently, HUMAnN establishes GPR associations for only approximately 20% of metagenomic reads even for a well-studied gut microbiome. Approximately 60% of reads are assigned to genefamilies without functional annotations at the metabolic level while the rest remain unclassified. Although not all genes encode metabolic functions, preliminary analysis indicates that many genefamilies lacking GPR associations are indeed metabolic, creating significant gaps and potential misinterpretations.

## Objectives

### Objective 1: Improving gene prediction in metagenomics

**Tasks:**
- **T1.1** Extract unmapped reads (use sample from Bioproject PRJNA749645)
- **T1.2** De novo assembly, gene-prediction and annotation

**Deliverable:**
- **D1:** Robust pipeline to identify and annotate unmapped reads

### Objective 2: Map Gene-Protein-Reaction

**Tasks:**
- **T2.1** Map Gene (UniRef) - Protein (UniProt)
- **T2.2** Map Protein (UniProt) - Reaction (MetaCyc)

**Deliverable:**
- **D2:** Gene-Protein-Reaction Mapping file for all genes

### Objective 3: Reporting

**Tasks:**
- **T3.1** Compare before and after functional annotation at Gene, Protein, Reaction levels (use sample from Bioproject PRJNA749645)
- **T3.2** Present findings at QIB DataScience Working Group

**Deliverable:**
- **D3:** Submit report