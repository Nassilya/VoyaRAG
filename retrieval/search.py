from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.embeddings import embed_queries
from retrieval.geo import Gazetteer, Place
from retrieval.index import COLLECTION, INDEX, QDRANT_URL

FIELDS = ("chunk_id", "text", "page_title", "section", "url", "breadcrumb", "page_type", "listing_ids")


class Retriever:
    def __init__(self, model: str = "bge-m3", index_dir: Path = INDEX):
        from qdrant_client import QdrantClient

        self.model = model
        self.client = QdrantClient(url=QDRANT_URL, timeout=60)
        self.gazetteer = Gazetteer.load(index_dir / "gazetteer.json")

    def search(self, question: str, k: int = 5, place: str | None = "auto",
               near: str | tuple[float, float] | None = None, radius_km: float = 20) -> dict:
        places = self._places(question, place)
        center = self._center(near)
        vector = embed_queries([question], self.model)[0].tolist()

        flt = self._filter([p.title for p in places], center, radius_km)
        hits = self._query(vector, k, flt)
        fallback = bool(flt) and not hits
        if fallback:
            hits = self._query(vector, k, None)

        return {
            "question": question,
            "places": [p.title for p in places],
            "near": center,
            "fallback": fallback,
            "results": [{**{f: h.payload.get(f) for f in FIELDS}, "score": round(h.score, 4)} for h in hits],
        }

    def _places(self, question: str, place: str | None) -> list[Place]:
        if place is None:
            return []
        if place == "auto":
            return self.gazetteer.find(question)
        found = self.gazetteer.find(place)
        return found or [Place(place, place, None, None)]

    def _center(self, near) -> tuple[float, float] | None:
        if near is None or isinstance(near, tuple):
            return near
        for p in self.gazetteer.find(near):
            if p.latitude is not None:
                return (p.latitude, p.longitude)
        raise ValueError(f"Coordonnées introuvables pour « {near} »")

    @staticmethod
    def _filter(titles: list[str], center, radius_km: float):
        from qdrant_client import models

        must = []
        if titles:
            must.append(models.FieldCondition(key="breadcrumb", match=models.MatchAny(any=titles)))
        if center:
            must.append(models.FieldCondition(key="location", geo_radius=models.GeoRadius(
                center=models.GeoPoint(lat=center[0], lon=center[1]), radius=radius_km * 1000)))
        return models.Filter(must=must) if must else None

    def _query(self, vector, k, flt):
        return self.client.query_points(COLLECTION, query=vector, query_filter=flt,
                                        limit=k, with_payload=True).points


_DEFAULT: Retriever | None = None


def search(question: str, k: int = 5, **kwargs) -> dict:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Retriever()
    return _DEFAULT.search(question, k, **kwargs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="+")
    ap.add_argument("--model", default="bge-m3")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--no-filter", action="store_true")
    ap.add_argument("--near", default=None)
    ap.add_argument("--radius", type=float, default=20)
    args = ap.parse_args()

    retriever = Retriever(args.model)
    for q in args.question:
        res = retriever.search(q, args.k, place=None if args.no_filter else "auto",
                               near=args.near, radius_km=args.radius)
        print(f"\n### {q}\n    lieux détectés : {res['places'] or 'aucun'}"
              + (f" | près de {res['near']}" if res["near"] else "")
              + (" | aucun résultat filtré, recherche sans filtre" if res["fallback"] else ""))
        for i, r in enumerate(res["results"], 1):
            body = r["text"].split("\n", 1)[-1][:90].replace("\n", " | ")
            print(f"  {i}. {r['score']:.3f}  {r['page_title']} > {r['section']}  :: {body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
