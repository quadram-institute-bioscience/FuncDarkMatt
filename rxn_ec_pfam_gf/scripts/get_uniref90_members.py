#!/usr/bin/env python3

import os
import gzip
import csv
import xml.etree.ElementTree as ET
import click

NS = "http://uniprot.org/uniref"


def get_prop(element, prop_type):
    """Extract a <property> value by its type attribute."""
    el = element.find(f"{{{NS}}}property[@type='{prop_type}']")
    return el.get("value") if el is not None else "NA"


def get_member_id(member_el):
    """Extract the dbReference id attribute from a <member> or <representativeMember>."""
    dbref = member_el.find(f"{{{NS}}}dbReference")
    if dbref is None:
        return None
    return dbref.get("id")


def get_uniprot_accessions(member_el):
    """Extract all UniProtKB accession values from a <member> dbReference."""
    dbref = member_el.find(f"{{{NS}}}dbReference")
    if dbref is None:
        return []
    return [
        p.get("value")
        for p in dbref.findall(f"{{{NS}}}property[@type='UniProtKB accession']")
        if p.get("value")
    ]


@click.command()
@click.option(
    "-i", "--input-file",
    required=True,
    type=click.Path(exists=True),
    help="Input UniRef90 XML gzipped file (e.g. uniref90.xml.gz)",
)
@click.option(
    "-o", "--output-file",
    required=True,
    type=click.Path(),
    help="Output CSV file path",
)
@click.option(
    "--log-every",
    default=100000,
    show_default=True,
    help="Log progress every N entries",
)
def parse_uniref90(input_file, output_file, log_every):
    """
    Parse a gzipped UniRef90 XML file and write a summary CSV.

    Columns: entry_id, member_count, common_taxon, common_taxon_id, member_ids
    """
    # Warn if output file already exists
    if os.path.exists(output_file):
        click.confirm(
            f"⚠️  '{output_file}' already exists. Overwrite?",
            abort=True
        )

    click.echo(f"📂 Input  : {input_file}")
    click.echo(f"📄 Output : {output_file}")
    click.echo("🔄 Parsing... (this may take a while for large files)")

    fieldnames = [
        "entry_id",
        "member_count",
        "common_taxon_id",
        "member_ids",
        "UniProtKB",
    ]

    count = 0

    with gzip.open(input_file, "rb") as fh_in, \
         open(output_file, "w", newline="", encoding="utf-8") as fh_out:

        writer = csv.DictWriter(fh_out, fieldnames=fieldnames)
        writer.writeheader()

        # Streaming parse — memory efficient for large files
        for event, elem in ET.iterparse(fh_in, events=("end",)):
            if elem.tag != f"{{{NS}}}entry":
                continue

            entry_id     = elem.get("id", "NA")
            member_count = get_prop(elem, "member count")
            common_taxon_id = get_prop(elem, "common taxon ID")

            # Extract representative's dbRef id and UniProtKB accessions
            rep = elem.find(f"{{{NS}}}representativeMember")
            rep_id = get_member_id(rep) if rep is not None else None
            all_accessions = get_uniprot_accessions(rep) if rep is not None else []

            # Collect member IDs starting with the representative's dbRef id
            member_ids = [rep_id] if rep_id else []
            for member in elem.findall(f"{{{NS}}}member"):
                mid = get_member_id(member)
                if mid and mid != rep_id:
                    member_ids.append(mid)
                all_accessions.extend(get_uniprot_accessions(member))

            try:
                mc_int = int(member_count)
            except (ValueError, TypeError):
                mc_int = 0

            # Deduplicate while preserving order
            member_ids      = list(dict.fromkeys(member_ids))
            all_accessions  = list(dict.fromkeys(all_accessions))

            member_ids_str  = ";".join(member_ids)    if member_ids                   else "NA"
            uniprot_str     = ";".join(all_accessions) if all_accessions               else "NA"

            writer.writerow({
                "entry_id":        entry_id,
                "member_count":    member_count,
                "common_taxon_id": common_taxon_id,
                "member_ids":      member_ids_str,
                "UniProtKB":       uniprot_str,
            })

            count += 1
            if count % log_every == 0:
                click.echo(f"  ↳ Processed {count:,} entries...")

            # Free memory — critical for large XML files
            elem.clear()

    click.echo(f"✅ Done! {count:,} entries written to {output_file}")


if __name__ == "__main__":
    parse_uniref90()
