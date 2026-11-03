import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.chunking import chunk_section, header, split_lines

SECTION = {
    "section_id": "16372-S005",
    "page_id": 16372,
    "page_title": "Thouars",
    "heading": "Voir",
    "path": ["Voir"],
    "level": 2,
    "breadcrumb": ["Europe", "France", "Deux-Sèvres", "Thouars"],
    "text_with_listings": "Église Saint-Laon — Prix : gratuit.\nÉglise Saint-Médard — Prix : gratuit.",
    "listing_ids": ["16372-L0001", "16372-L0002"],
}
PAGE = {"url": "https://fr.wikivoyage.org/wiki/Thouars", "page_type": "ville",
        "latitude": "46.9758", "longitude": "-0.2142"}


def test_header():
    assert header("Thouars", SECTION["breadcrumb"], ["Voir"], keywords=False) == \
        "Thouars (Europe > France > Deux-Sèvres) > Voir"
    assert header("Europe", ["Europe"], ["Introduction"]) == "Europe > Introduction"


def test_header_keywords():
    head = header("Bordeaux", ["France", "Bordeaux"], ["Se loger", "Bon marché"])
    assert head.startswith("Bordeaux (France) > Se loger > Bon marché (")
    assert "dormir" in head and "pas cher" in head
    assert "danger" in header("Paris", ["Paris"], ["Sécurité"])
    assert header("Paris", ["Paris"], ["Itinéraires"]) == "Paris > Itinéraires"


def test_short_section_is_one_chunk_with_header():
    rows = chunk_section(SECTION, PAGE)
    assert len(rows) == 1
    assert rows[0]["text"].startswith("Thouars (Europe > France > Deux-Sèvres) > Voir (à visiter")
    assert rows[0]["url"] == "https://fr.wikivoyage.org/wiki/Thouars#Voir"
    assert rows[0]["chunk_id"] == "16372-S005-C00"


def test_no_header():
    rows = chunk_section(SECTION, PAGE, add_header=False)
    assert rows[0]["text"].startswith("Église Saint-Laon")


def test_lines_are_never_cut():
    text = "\n".join(f"lieu{i} " + "mot " * 9 for i in range(10))
    chunks = split_lines(text, size=35, overlap=10)
    assert len(chunks) > 1
    for c in chunks:
        for line in c.split("\n"):
            assert line.startswith("lieu") and len(line.split()) == 10
            assert len(c.split()) <= 35


def test_overlap_repeats_last_line():
    text = "\n".join(f"lieu{i} " + "mot " * 9 for i in range(10))
    chunks = split_lines(text, size=35, overlap=10)
    assert chunks[0].split("\n")[-1] == chunks[1].split("\n")[0]


def test_overlap_never_exceeds_size():
    text = "court " * 20 + "\n" + "long " * 195
    assert all(len(c.split()) <= 200 for c in split_lines(text, size=200, overlap=30))


def test_long_line_is_split_by_words():
    chunks = split_lines("mot " * 500, size=200, overlap=30)
    assert all(len(c.split()) <= 200 for c in chunks)
    assert len(chunks) == 3
