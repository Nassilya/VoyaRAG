import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.geo import Gazetteer, normalize, parse_coord
from retrieval.index import payload

GAZ = Gazetteer(
    names={
        "bordeaux": ["Bordeaux"],
        "cher": ["Cher"],
        "nice": ["Nice"],
        "cote d'azur": ["Côte d'Azur"],
        "aachen": ["Aix-la-Chapelle"],
        "luxembourg": ["Luxembourg", "Luxembourg (ville)"],
        "new york": ["New York"],
        "york": ["York"],
    },
    ambiguous={"cher"},
    coords={"Bordeaux": [44.84, -0.58]},
)


def titles(question):
    return [p.title for p in GAZ.find(question)]


def test_normalize():
    assert normalize("Côte-d’Azur") == "cote d'azur"


def test_find_simple_and_lowercase():
    assert titles("Hôtel à Bordeaux") == ["Bordeaux"]
    assert titles("hotel a bordeaux") == ["Bordeaux"]


def test_ambiguous_word_needs_capital():
    assert titles("Hôtel pas cher à Bordeaux") == ["Bordeaux"]
    assert titles("Que voir dans le Cher ?") == ["Cher"]


def test_longest_match_wins():
    assert titles("Où dormir à New York ?") == ["New York"]


def test_alias_and_elision():
    assert titles("Visiter Aachen") == ["Aix-la-Chapelle"]
    assert titles("Plages de la Côte d'Azur") == ["Côte d'Azur"]


def test_homonyms_are_all_returned():
    assert titles("Que voir au Luxembourg ?") == ["Luxembourg", "Luxembourg (ville)"]


def test_coordinates():
    place = GAZ.find("Bordeaux")[0]
    assert (place.latitude, place.longitude) == (44.84, -0.58)
    assert parse_coord("46,97") == 46.97
    assert parse_coord("") is None


def test_payload_location():
    row = payload({"chunk_id": "x", "latitude": "44.84", "longitude": "-0.58"})
    assert row["location"] == {"lat": 44.84, "lon": -0.58}
    assert "latitude" not in row
    assert "location" not in payload({"chunk_id": "x", "latitude": None, "longitude": "2"})
    assert "location" not in payload({"chunk_id": "x", "latitude": "123", "longitude": "2"})
