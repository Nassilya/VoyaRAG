"""Inspecte le dump AVANT de faire confiance au parser

Compte les modèles, titres de sections et paramètres de fiches les plus
fréquents. 
Vérifier que :
  - les modèles de fiches (Voir, Manger...) sont bien ceux de LISTING_TEMPLATES 
  - aucun modèle fréquent porteur de texte n'est supprimé à tort 
  - les paramètres de fiches correspondent à LISTING_FIELDS

Usage :
    python dumps/inspect_dump.py [--dump chemin.xml.bz2] [--limit 1000]

    # Montrer de vrais exemples d'utilisation de certains modèles, en contexte :
    python dumps/inspect_dump.py --limit 2000 --examples "unité,heure,traduction"
"""

from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import mwparserfromhell

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parsing.dump import iter_pages  
from parsing.extract import LISTING_FIELDS, LISTING_TEMPLATES  
from parsing.wikitext import RENDERED_TEMPLATES, template_name 
from dumps.build_dataset import find_dump  

N_EXAMPLES = 8      
CONTEXT = 60       


def _context(text: str, raw: str) -> str:
    i = text.find(raw)
    if i < 0:
        return raw
    before = text[max(0, i - CONTEXT): i]
    after = text[i + len(raw): i + len(raw) + CONTEXT]
    return re.sub(r"\s+", " ", f"…{before}[[[{raw}]]]{after}…")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--examples", default="",
                    help="noms de modèles séparés par des virgules, ex. 'unité,heure'")
    args = ap.parse_args()

    wanted = {n.strip().lower() for n in args.examples.split(",") if n.strip()}
    examples: dict[str, list[tuple[str, str]]] = defaultdict(list)
    seen: Counter = Counter()
    rng = random.Random(0)  

    templates, headings, listing_params, statuses = Counter(), Counter(), Counter(), Counter()
    n = 0
    for raw in iter_pages(args.dump or find_dump()):
        if raw.namespace != 0 or raw.redirect_to:
            continue
        code = mwparserfromhell.parse(raw.text)
        for tpl in code.filter_templates():
            name = template_name(tpl)
            templates[name] += 1
            if name in LISTING_TEMPLATES:
                for p in tpl.params:
                    listing_params[str(p.name).strip().lower()] += 1
            if name == "avancement":
                statuses[str(tpl.get("type").value).strip() if tpl.has("type") else "?"] += 1
            if name in wanted:
                seen[name] += 1
                item = (raw.title, _context(raw.text, str(tpl)))
                if len(examples[name]) < N_EXAMPLES:
                    examples[name].append(item)
                else:
                    j = rng.randrange(seen[name])
                    if j < N_EXAMPLES:
                        examples[name][j] = item
        for h in code.filter_headings():
            headings[(h.level, h.title.strip_code().strip())] += 1
        n += 1
        if args.limit and n >= args.limit:
            break

    if wanted:
        print(f"{n} articles parcourus — exemples de modèles (le modèle est entre [[[ ]]])\n")
        for name in sorted(wanted):
            print(f"== {name} ({seen[name]} occurrences) ==")
            if not examples[name]:
                print("  (aucune occurrence)")
            for title, ctx in examples[name]:
                print(f"  [{title}] {ctx}")
            print()
        return 0

    print(f"{n} articles inspectés\n")
    print("== Modèles les plus fréquents (* = fiche de lieu, + = converti en texte, rien = supprimé) ==")
    for name, c in templates.most_common(args.top):
        mark = "*" if name in LISTING_TEMPLATES else "+" if name in RENDERED_TEMPLATES else " "
        print(f"  {mark} {c:8d}  {name}")
    print("\n== Paramètres de fiches (! = non exploité par extract.py) ==")
    for name, c in listing_params.most_common(args.top):
        print(f"  {' ' if name in LISTING_FIELDS else '!'} {c:8d}  {name}")
    print("\n== Titres de sections ==")
    for (level, title), c in headings.most_common(args.top):
        print(f"  {c:8d}  {'=' * level} {title}")
    print("\n== Types de page (Avancement|type=) ==")
    for t, c in statuses.most_common():
        print(f"  {c:8d}  {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())