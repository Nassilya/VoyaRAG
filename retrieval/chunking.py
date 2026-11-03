from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

SECTION_KEYWORDS = {
    "se loger": "hébergement, hôtel, dormir, nuit",
    "hotels": "hébergement, dormir, nuit",
    "camping": "camper, tente, hébergement",
    "campings": "camper, tente, hébergement",
    "gites, chalets": "location, hébergement, dormir",
    "bon marche": "pas cher, petit budget, économique",
    "prix moyen": "budget moyen, prix raisonnable",
    "classe moyenne": "budget moyen, prix raisonnable",
    "luxe": "haut de gamme, cher, prestige",
    "manger": "restaurant, cuisine, où manger, spécialités",
    "restaurants": "manger, cuisine",
    "boire un verre / sortir": "bar, café, vie nocturne, soirée",
    "boire un verre": "bar, café, vie nocturne, soirée",
    "sortir": "vie nocturne, soirée, spectacles",
    "voir": "à visiter, sites, monuments, attractions",
    "faire": "activités, loisirs, que faire",
    "acheter": "shopping, magasins, souvenirs",
    "aller": "venir, arriver, s'y rendre, accès",
    "circuler": "se déplacer, transports sur place",
    "securite": "danger, dangereux, risques, sûr, vols",
    "sante": "médecin, hôpital, pharmacie, vaccins",
    "comprendre": "présentation, contexte",
    "climat": "météo, temps, saison, quand partir",
    "parler": "langue, vocabulaire",
    "communiquer": "téléphone, internet, wifi",
    "argent": "monnaie, devise, change, distributeur",
    "formalites": "visa, passeport, papiers, douane",
    "respecter": "coutumes, savoir-vivre, à éviter",
    "aux environs": "alentours, excursions, à proximité",
}


def _key(heading: str) -> str:
    text = unicodedata.normalize("NFKD", heading.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def section_keywords(path: list[str]) -> str:
    words = [SECTION_KEYWORDS[k] for k in map(_key, path) if k in SECTION_KEYWORDS]
    return " ; ".join(words)


def header(page_title: str, breadcrumb: list[str], path: list[str], keywords: bool = True) -> str:
    ancestors = [b for b in breadcrumb if b != page_title]
    place = f"{page_title} ({' > '.join(ancestors)})" if ancestors else page_title
    head = " > ".join([place, *path])
    extra = section_keywords(path) if keywords else ""
    return f"{head} ({extra})" if extra else head


def split_words(words: list[str], size: int, overlap: int) -> list[list[str]]:
    step = max(1, size - overlap)
    out = []
    for start in range(0, len(words), step):
        out.append(words[start:start + size])
        if start + size >= len(words):
            break
    return out


def split_lines(text: str, size: int, overlap: int) -> list[str]:
    units: list[list[str]] = []
    for line in text.split("\n"):
        words = line.split()
        if len(words) > size:
            units.extend(split_words(words, size, overlap))
        elif words:
            units.append(words)

    chunks: list[list[list[str]]] = []
    current: list[list[str]] = []
    n = 0
    for unit in units:
        if current and n + len(unit) > size:
            chunks.append(current)
            kept, k = [], 0
            for prev in reversed(current):
                if k + len(prev) > overlap or k + len(prev) + len(unit) > size:
                    break
                kept.insert(0, prev)
                k += len(prev)
            current, n = kept, k
        current.append(unit)
        n += len(unit)
    if current:
        chunks.append(current)
    return ["\n".join(" ".join(u) for u in c) for c in chunks]


def section_url(page_url: str, heading: str, level: int) -> str:
    if level <= 1:
        return page_url
    return f"{page_url}#{heading.replace(' ', '_')}"


def chunk_section(section: dict, page: dict, size: int = 200, overlap: int = 30,
                  add_header: bool = True, keywords: bool = True) -> list[dict]:
    head = header(section["page_title"], section["breadcrumb"], section["path"], keywords)
    rows = []
    for i, body in enumerate(split_lines(section["text_with_listings"], size, overlap)):
        rows.append({
            "chunk_id": f"{section['section_id']}-C{i:02d}",
            "text": f"{head}\n{body}" if add_header else body,
            "page_id": section["page_id"],
            "page_title": section["page_title"],
            "section": " > ".join(section["path"]),
            "url": section_url(page.get("url", ""), section["heading"], section["level"]),
            "breadcrumb": section["breadcrumb"],
            "page_type": page.get("page_type"),
            "latitude": page.get("latitude"),
            "longitude": page.get("longitude"),
            "listing_ids": section["listing_ids"],
            "n_words": len(body.split()),
        })
    return rows


def read_jsonl(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            yield json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=PROCESSED)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--overlap", type=int, default=30)
    ap.add_argument("--no-header", action="store_true")
    ap.add_argument("--no-keywords", action="store_true")
    args = ap.parse_args()

    out = args.out or args.data / "chunks.jsonl"
    pages = {p["page_id"]: p for p in read_jsonl(args.data / "pages.jsonl")}

    n_sections = n_chunks = 0
    with open(out, "w", encoding="utf-8") as fh:
        for section in read_jsonl(args.data / "sections.jsonl"):
            n_sections += 1
            for row in chunk_section(section, pages.get(section["page_id"], {}),
                                     args.size, args.overlap, not args.no_header,
                                     not args.no_keywords):
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_chunks += 1

    print(f"{n_sections} sections -> {n_chunks} chunks dans {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
