"""
Parse reactions.dat and aggregate UNIQUE-ID, EC-NUMBER, and ENZYMATIC-REACTION.
Records are separated by '//' lines; fields may have multiple values.
"""

from collections import defaultdict
import csv
import click


def parse_dat(filepath):
    records = []
    current = defaultdict(list)

    with open(filepath, "r", encoding="latin-1") as fh:
        for line in fh:
            line = line.rstrip("\n")

            # Skip comments
            if line.startswith("#"):
                continue

            # Record separator
            if line.strip() == "//":
                if current:
                    records.append(dict(current))
                    current = defaultdict(list)
                continue

            # Skip attribute-modifier lines (start with '^')
            if line.startswith("^"):
                continue

            # Parse "KEY - VALUE" lines
            if " - " in line:
                key, _, value = line.partition(" - ")
                key = key.strip()
                value = value.strip()
                if key in ("UNIQUE-ID", "EC-NUMBER", "ENZYMATIC-REACTION"):
                    current[key].append(value)

    # Flush last record if file doesn't end with '//'
    if current:
        records.append(dict(current))

    return records


def aggregate(records):
    """
    Aggregate by UNIQUE-ID.
    Each UNIQUE-ID should appear once, but EC-NUMBER and ENZYMATIC-REACTION
    may have multiple values per record — collect them all as sorted unique sets.
    """
    aggregated = {}

    for rec in records:
        uid_list = rec.get("UNIQUE-ID", [])
        if not uid_list:
            continue
        uid = uid_list[0]  # UNIQUE-ID is always a single value

        if uid not in aggregated:
            aggregated[uid] = {"EC-NUMBER": set(), "ENZYMATIC-REACTION": set()}

        for ec in rec.get("EC-NUMBER", []):
            aggregated[uid]["EC-NUMBER"].add(ec)
        for er in rec.get("ENZYMATIC-REACTION", []):
            aggregated[uid]["ENZYMATIC-REACTION"].add(er)

    return aggregated


def write_tsv(aggregated, outfile):
    writer = csv.writer(outfile, delimiter="\t")
    writer.writerow(["UNIQUE-ID", "EC-NUMBER", "ENZYMATIC-REACTION"])
    for uid, vals in sorted(aggregated.items()):
        ec = "|".join(sorted(vals["EC-NUMBER"]))
        er = "|".join(sorted(vals["ENZYMATIC-REACTION"]))
        writer.writerow([uid, ec, er])


@click.command()
@click.option("-i", "--input", type=click.Path(exists=True, dir_okay=False), default="reactions.dat", show_default=True, help="Path to reactions.dat file.")
@click.option("-o", "--output", type=click.File("w"), default="reactions_aggregated.tsv", show_default=True, help="Output TSV file path.")
def main(input, output):
    """Parse a BioCyc reactions.dat file and write a TSV with UNIQUE-ID,
    EC-NUMBER, and ENZYMATIC-REACTION aggregated by UNIQUE-ID."""
    records = parse_dat(input)
    click.echo(f"Parsed {len(records)} reaction records")

    aggregated = aggregate(records)
    click.echo(f"Unique UNIQUE-IDs: {len(aggregated)}")

    with_ec = sum(1 for v in aggregated.values() if v["EC-NUMBER"])
    with_er = sum(1 for v in aggregated.values() if v["ENZYMATIC-REACTION"])
    click.echo(f"  with EC-NUMBER:          {with_ec}")
    click.echo(f"  with ENZYMATIC-REACTION: {with_er}")

    write_tsv(aggregated, output)
    click.echo(f"Written to {output.name}")


if __name__ == "__main__":
    main()
