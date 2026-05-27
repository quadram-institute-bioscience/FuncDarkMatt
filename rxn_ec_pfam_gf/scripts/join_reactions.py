import csv
import click
from pathlib import Path


def parse_reactions(path):
    rows = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            uid = row["UNIQUE-ID"].strip()
            rows[uid] = {
                "EC-NUMBER": row.get("EC-NUMBER", "").strip(),
                "ENZYMATIC-REACTION": row.get("ENZYMATIC-REACTION", "").strip(),
            }
    return rows


def parse_links(path):
    rows = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#") or not line.strip():
                continue
            parts = line.split("\t")
            uid = parts[0].strip()
            ec_numbers = "|".join(p.strip() for p in parts[1:] if p.strip())
            rows[uid] = {"LINKS-EC-NUMBERS": ec_numbers}
    return rows


@click.command()
@click.argument("reactions", type=click.Path(exists=True, dir_okay=False))
@click.argument("links", type=click.Path(exists=True, dir_okay=False))
@click.argument("output", type=click.Path(dir_okay=False))
def merge(reactions, links, output):
    """Outer-join REACTIONS (reactions.txt) and LINKS (reactions-links.dat)
    on reaction ID, writing a merged TSV to OUTPUT."""

    rxn = parse_reactions(reactions)
    lnk = parse_links(links)

    all_ids = sorted(set(rxn) | set(lnk))
    fieldnames = ["UNIQUE-ID", "EC-NUMBER", "ENZYMATIC-REACTION"]

    with open(output, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter="\t",
                                extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for uid in all_ids:
            r = rxn.get(uid, {})
            l = lnk.get(uid, {})

            ec_parts = [r.get("EC-NUMBER", "")] + l.get("LINKS-EC-NUMBERS", "").split("|")
            # Flatten any pipe-separated values within each part, then deduplicate
            all_ecs = (ec for part in ec_parts for ec in part.split("|"))
            unique_ecs = "|".join(dict.fromkeys(e for e in all_ecs if e))

            writer.writerow({
                "UNIQUE-ID": uid,
                "EC-NUMBER": unique_ecs,
                "ENZYMATIC-REACTION": r.get("ENZYMATIC-REACTION", ""),
            })

    only_rxn = len(set(rxn) - set(lnk))
    only_lnk = len(set(lnk) - set(rxn))
    both     = len(set(rxn) & set(lnk))

    click.echo(f"Written {len(all_ids)} rows to {output}")
    click.echo(f"  From reactions only:       {only_rxn}")
    click.echo(f"  From links only:           {only_lnk}")
    click.echo(f"  Present in both:           {both}")


if __name__ == "__main__":
    merge()