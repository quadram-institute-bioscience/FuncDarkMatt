#!/bin/bash -e
#SBATCH -p nbi-download
#SBATCH -N 1
#SBATCH -c 1
#SBATCH --mem 4G
#SBATCH -t 4-00:00:00
#SBATCH -o download-%j.out
#SBATCH -e download-%j.err
#SBATCH --mail-type=END,FAIL,TIME_LIMIT_80
#SBATCH --mail-user=<Sumeet.Tiwari@quadram.ac.uk>

#1. Download UniProtKB
mkdir -p /qib/platforms/Informatics/transfer/incoming/tiwari/project_FuncMeta/bioinformatics_data/uniref2019_01
curl -O https://ftp.uniprot.org/pub/databases/uniprot/previous_major_releases/release-2019_01/knowledgebase/knowledgebase2019_01.tar.gz && mv knowledgebase2019_01.tar.gz /qib/platforms/Informatics/transfer/incoming/tiwari/project_FuncMeta/bioinformatics_data/uniref2019_01/
#2. Download Uniref2019_01
curl -O https://ftp.uniprot.org/pub/databases/uniprot/previous_major_releases/release-2019_01/uniref/uniref2019_01.tar.gz && mv uniref2019_01.tar.gz /qib/platforms/Informatics/transfer/incoming/tiwari/project_FuncMeta/bioinformatics_data/uniref2019_01


#curl -O https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref100/uniref100.xml.gz && mv uniref100.xml.gz /qib/platforms/Informatics/transfer/incoming/tiwari/project_FuncMeta/bioinformatics_data/uniref100
#curl -O https://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz
#curl -O https://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz.md5
#curl -O https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref90/uniref90.xml.gz
#curl -O https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.xml.gz
#curl -O https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_trembl.xml.gz