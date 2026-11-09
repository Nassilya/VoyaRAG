from __future__ import annotations

import argparse
import os
import sys
import time
from itertools import islice
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.chunking import PROCESSED, read_jsonl
from retrieval.embeddings import MODELS
from retrieval.geo import Gazetteer, parse_coord

INDEX = ROOT / "data" / "index"
COLLECTION = "chunks"
BATCH = 512
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


def payload(chunk: dict) -> dict:
    row = dict(chunk)
    lat, lon = parse_coord(row.pop("latitude", None)), parse_coord(row.pop("longitude", None))
    if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
        row["location"] = {"lat": lat, "lon": lon}
    return row


def build(model: str, index_dir: Path = INDEX) -> int:
    from qdrant_client import QdrantClient, models

    folder = index_dir / model
    vectors = np.load(folder / "vectors.npy", mmap_mode="r")
    n_chunks = sum(1 for _ in read_jsonl(folder / "chunks.jsonl"))
    if n_chunks != len(vectors):
        raise ValueError(f"{n_chunks} chunks mais {len(vectors)} vecteurs dans {folder}")

    client = QdrantClient(url=QDRANT_URL, timeout=120)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(COLLECTION, vectors_config=models.VectorParams(
        size=int(vectors.shape[1]), distance=models.Distance.COSINE, on_disk=True))
    client.create_payload_index(COLLECTION, "breadcrumb", models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION, "location", models.PayloadSchemaType.GEO)
    rows = read_jsonl(folder / "chunks.jsonl")
    for start in range(0, n_chunks, BATCH):
        batch = list(islice(rows, BATCH))
        client.upsert(COLLECTION, points=models.Batch(
            ids=list(range(start, start + len(batch))),
            vectors=vectors[start:start + len(batch)].tolist(),
            payloads=[payload(c) for c in batch],
        ))
    client.close()
    return n_chunks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, default="bge-m3")
    ap.add_argument("--index", type=Path, default=INDEX)
    args = ap.parse_args()

    t0 = time.time()
    gazetteer = Gazetteer.build(PROCESSED)
    gazetteer.save(args.index / "gazetteer.json")
    print(f"Gazetteer : {len(gazetteer.names)} noms de lieux, {len(gazetteer.ambiguous)} ambigus")

    n = build(args.model, args.index)
    print(f"Qdrant : {n} chunks indexés dans {QDRANT_URL} ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
