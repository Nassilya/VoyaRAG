from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from retrieval.chunking import PROCESSED, read_jsonl

MAX_NGRAM = 6
AMBIGUOUS_MIN_COUNT = 20
_WORD = re.compile(r"[\w'’-]+")
_PAREN = re.compile(r"\s*\([^)]*\)\s*$")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.replace("’", "'"))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().replace("-", " ").split())


def parse_coord(value) -> float | None:
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


@dataclass
class Place:
    title: str
    matched: str
    latitude: float | None
    longitude: float | None


class Gazetteer:
    def __init__(self, names: dict[str, list[str]], ambiguous: set[str], coords: dict[str, list]):
        self.names = names
        self.ambiguous = ambiguous
        self.coords = coords

    @classmethod
    def build(cls, processed: Path = PROCESSED) -> "Gazetteer":
        names: dict[str, set[str]] = defaultdict(set)
        coords = {}
        for p in read_jsonl(processed / "pages.jsonl"):
            title = p["title"]
            names[normalize(title)].add(title)
            names[normalize(_PAREN.sub("", title))].add(title)
            lat, lon = parse_coord(p.get("latitude")), parse_coord(p.get("longitude"))
            if lat is not None and lon is not None:
                coords[title] = [lat, lon]
        known = {t for ts in names.values() for t in ts}
        redirects = json.loads((processed / "redirects.json").read_text(encoding="utf-8"))
        for alias, target in redirects.items():
            if target in known:
                names[normalize(alias)].add(target)

        lowercase = Counter()
        for s in read_jsonl(processed / "sections.jsonl"):
            lowercase.update(w for w in _WORD.findall(s["text"]) if w.islower())
        ambiguous = {n for n in names if " " not in n and lowercase[n] >= AMBIGUOUS_MIN_COUNT}
        return cls({n: sorted(t) for n, t in names.items()}, ambiguous, coords)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"names": self.names, "ambiguous": sorted(self.ambiguous),
                                    "coords": self.coords}, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Gazetteer":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data["names"], set(data["ambiguous"]), data["coords"])

    def find(self, question: str) -> list[Place]:
        words = _WORD.findall(question)
        found: list[Place] = []
        used: set[int] = set()
        for n in range(min(MAX_NGRAM, len(words)), 0, -1):
            for start in range(len(words) - n + 1):
                span = range(start, start + n)
                if used & set(span):
                    continue
                for variant in self._variants(words[start:start + n]):
                    key = normalize(" ".join(variant))
                    if key not in self.names:
                        continue
                    if key in self.ambiguous and not variant[0][:1].isupper():
                        continue
                    used.update(span)
                    for title in self.names[key]:
                        lat, lon = self.coords.get(title, [None, None])
                        found.append(Place(title, " ".join(variant), lat, lon))
                    break
        return found

    @staticmethod
    def _variants(words: list[str]):
        yield words
        first = words[0]
        for prefix in ("l'", "d'", "l’", "d’"):
            if first.lower().startswith(prefix) and len(first) > len(prefix):
                yield [first[len(prefix):], *words[1:]]
