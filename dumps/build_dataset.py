"""Construit le dataset structuré à partir du dump Wikivoyage FR

Usage :
    python dumps/build_dataset.py                       
    python dumps/build_dataset.py --dump chemin.xml.bz2 --out data/processed
    python dumps/build_dataset.py --limit 200          

Sorties (JSON Lines, une ligne = un enregistrement) :
    pages.jsonl      métadonnées par page + fil d'Ariane géographique
    sections.jsonl   sections de texte (prose, et prose + fiches rendues)
    listings.jsonl   fiches de lieux (musées, restaurants, hôtels...)
    redirects.json   alias -> page cible (utile pour les noms de lieux)
    stats.json       statistiques et contrôles qualité (pour le rapport)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parsing.dump import iter_pages 
from parsing.extract import normalize_title, parse_page, to_dict 
from parsing.hierarchy import build_breadcrumbs 

SKIP_TITLES = {"Accueil"}


def find_dump() -> Path:
    candidates = sorted((ROOT / "data" / "raw").glob("frwikivoyage-*-pages-articles.xml*"))
    if not candidates:
        sys.exit("Aucun dump trouvé dans data/raw/. Lancez d'abord dumps/download_dump.py.")
    return candidates[-1]


def write_jsonl(path: Path, rows) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--limit", type=int, default=None, help="nombre max d'articles (pour tester)")
    args = ap.parse_args()

    dump = args.dump or find_dump()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "parsing_errors.jsonl").unlink(missing_ok=True)
    print(f"Dump : {dump}")

    t0 = time.time()
    pages, sections, listings = [], [], []
    redirects: dict[str, str] = {}
    skipped = Counter()
    unwrapped = Counter()   
    errors: list[dict] = []

    for raw in iter_pages(dump):
        if raw.namespace != 0:
            skipped["autre_espace_de_noms"] += 1
            continue
        if raw.redirect_to:
            redirects[normalize_title(raw.title)] = normalize_title(raw.redirect_to)
            continue
        if raw.title in SKIP_TITLES:
            skipped["page_speciale"] += 1
            continue
        try:
            parsed = parse_page(raw.page_id, raw.title, raw.text, raw.revision_timestamp)
        except Exception as exc:  # une page mal formée ne doit pas tout arrêter
            errors.append({"page_id": raw.page_id, "title": raw.title, "error": repr(exc)})
            continue
        if parsed.is_disambiguation:
            skipped["homonymie"] += 1
            continue
        if not parsed.sections:
            skipped["page_vide"] += 1
            continue
        unwrapped.update(parsed.unwrapped)
        pages.append(parsed.page)
        sections.extend(parsed.sections)
        listings.extend(parsed.listings)
        if len(pages) % 500 == 0:
            print(f"  {len(pages)} articles, {len(listings)} fiches... ({time.time() - t0:.0f} s)")
        if args.limit and len(pages) >= args.limit:
            break

    # Fil d'Ariane géographique
    parents = {normalize_title(p.title): p.parent for p in pages}
    breadcrumbs, hier_stats = build_breadcrumbs(parents, redirects)
    crumb = lambda title: breadcrumbs.get(normalize_title(title), [title])  

    def page_rows():
        for p in pages:
            yield {**to_dict(p), "breadcrumb": crumb(p.title)}

    def section_rows():
        for s in sections:
            yield {**to_dict(s), "breadcrumb": crumb(s.page_title)}

    def listing_rows():
        for l in listings:
            row = to_dict(l)
            fields = row.pop("fields")
            yield {**row, **fields, "breadcrumb": crumb(l.page_title)}

    n_pages = write_jsonl(args.out / "pages.jsonl", page_rows())
    n_sections = write_jsonl(args.out / "sections.jsonl", section_rows())
    n_listings = write_jsonl(args.out / "listings.jsonl", listing_rows())
    (args.out / "redirects.json").write_text(json.dumps(redirects, ensure_ascii=False, indent=0))

    field_fill = Counter(k for l in listings for k in l.fields)
    stats = {
        "dump": dump.name,
        "duree_s": round(time.time() - t0, 1),
        "articles": n_pages,
        "sections": n_sections,
        "fiches": n_listings,
        "redirections": len(redirects),
        "pages_ignorees": dict(skipped),
        "erreurs_parsing": len(errors),
        "conteneurs_deballes": unwrapped.most_common(30),
        "types_de_page": Counter(p.page_type or "(inconnu)" for p in pages).most_common(),
        "statuts": Counter(p.status or "(inconnu)" for p in pages).most_common(),
        "types_de_fiche": Counter(l.type for l in listings).most_common(),
        "taux_remplissage_champs": {
            k: round(v / max(n_listings, 1), 3) for k, v in field_fill.most_common()
        },
        "sections_les_plus_frequentes": Counter(s.heading for s in sections).most_common(40),
        "hierarchie": hier_stats,
        "profondeur_fil_ariane": Counter(len(b) for b in breadcrumbs.values()).most_common(),
    }
    (args.out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    if errors:
        write_jsonl(args.out / "parsing_errors.jsonl", errors)

    print(f"\nTerminé en {stats['duree_s']} s : {n_pages} articles, {n_sections} sections, "
          f"{n_listings} fiches, {len(redirects)} redirections, {len(errors)} erreurs.")
    print(f"Sorties dans {args.out}/ (voir stats.json pour les contrôles qualité)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
