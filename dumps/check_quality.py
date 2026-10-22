"""Contrôle qualité du dataset produit (data/processed/)

Deux vérifications complémentaires :
  1. Mesure automatique : sur TOUT le dataset, part des textes qui contiennent
     encore des restes de wikitext ({{ }}, [[ ]], |-, balises HTML...).
     Un chiffre objectif à suivre d'une version du parser à l'autre.
  2. Lecture humaine : un échantillon aléatoire de sections et de fiches,
     à relire à l'œil pour repérer ce qu'aucune règle automatique ne voit.

Usage :
    python dumps/check_quality.py                  # mesure + 10 exemples de chaque
    python dumps/check_quality.py --sample 30      # plus d'exemples à relire
    python dumps/check_quality.py > data/qualite.txt
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RESIDUES = {
    "modèle {{ }}": re.compile(r"\{\{|\}\}"),
    "lien [[ ]]": re.compile(r"\[\[|\]\]"),
    "tableau (|- ou ||)": re.compile(r"^\s*\|-|\|\||^\s*\{\||^\s*\|\}", re.MULTILINE),
    "balise HTML": re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(\s[^<>]*)?/?>"),
    "gras/italique ''": re.compile(r"''"),
    "titre ==": re.compile(r"^\s*==", re.MULTILINE),
}
EXAMPLES_PER_RESIDUE = 3
CONTEXT = 50


def read_jsonl(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def scan(rows, field: str, label: str) -> None:
    total = 0
    hits = Counter()
    examples: dict[str, list[str]] = {k: [] for k in RESIDUES}
    for row in rows:
        text = row.get(field) or ""
        total += 1
        for name, pattern in RESIDUES.items():
            m = pattern.search(text)
            if m:
                hits[name] += 1
                if len(examples[name]) < EXAMPLES_PER_RESIDUE:
                    start = max(0, m.start() - CONTEXT)
                    snippet = text[start: m.end() + CONTEXT].replace("\n", " ⏎ ")
                    title = row.get("page_title", "?")
                    examples[name].append(f"[{title}] …{snippet}…")

    print(f"== {label} : {total} textes analysés (champ « {field} ») ==")
    for name in RESIDUES:
        n = hits[name]
        print(f"  {name:22s} {n:7d}  ({100 * n / max(total, 1):.2f} %)")
        for ex in examples[name]:
            print(f"      {ex}")
    print()


def sample(rows, k: int, rng: random.Random, fmt) -> None:
    rows = list(rows)
    for row in rng.sample(rows, min(k, len(rows))):
        print(fmt(row))
        print("-" * 70)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--sample", type=int, default=10, help="nombre d'exemples aléatoires à relire")
    ap.add_argument("--seed", type=int, default=0, help="graine (même échantillon à chaque lancement)")
    args = ap.parse_args()

    sections_path = args.data / "sections.jsonl"
    listings_path = args.data / "listings.jsonl"
    if not sections_path.exists():
        sys.exit("data/processed/sections.jsonl introuvable : lancez d'abord build_dataset.py.")

    print("#" * 70)
    print("# 1. Restes de wikitext (mesure automatique sur tout le dataset)")
    print("#" * 70 + "\n")
    scan(read_jsonl(sections_path), "text_with_listings", "Sections")
    scan(read_jsonl(listings_path), "description", "Fiches (description)")

    rng = random.Random(args.seed)
    print("#" * 70)
    print(f"# 2. Échantillon aléatoire à relire ({args.sample} sections, {args.sample} fiches)")
    print("#" * 70 + "\n")
    sample(read_jsonl(sections_path), args.sample, rng,
           lambda s: f"[{' > '.join(s['breadcrumb'])}]  §{' > '.join(s['path'])}\n{s['text_with_listings'][:800]}")
    sample(read_jsonl(listings_path), args.sample, rng,
           lambda l: f"[{l['page_title']} — {l['type']}]  " + json.dumps(
               {k: v for k, v in l.items() if k not in ("breadcrumb", "listing_id", "page_id", "page_title", "type")},
               ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())