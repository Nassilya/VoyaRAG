from __future__ import annotations

import argparse
import shutil
import sys
import time
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


def payload(chunk: dict) -> dict:
    row = dict(chunk)
    lat, lon = parse_coord(row.pop("latitude", None)), parse_coord(row.pop("longitude", None))
    if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
        row["location"] = {"lat": lat, "lon": lon}
    return row


def build(model: str, index_dir: Path = INDEX) -> int:
    from qdrant_client import QdrantClient, models

    folder = index_dir / model
    vectors = np.load(folder / "vectors.npy")
    chunks = list(read_jsonl(folder / "chunks.jsonl"))
    if len(chunks) != len(vectors):
        raise ValueError(f"{len(chunks)} chunks mais {len(vectors)} vecteurs dans {folder}")

    db_path = folder / "qdrant"
    shutil.rmtree(db_path, ignore_errors=True)
    client = QdrantClient(path=str(db_path))
    client.create_collection(COLLECTION, vectors_config=models.VectorParams(
        size=int(vectors.shape[1]), distance=models.Distance.COSINE))
    for start in range(0, len(chunks), BATCH):
        end = start + BATCH
        client.upsert(COLLECTION, points=models.Batch(
            ids=list(range(start, min(end, len(chunks)))),
            vectors=vectors[start:end].tolist(),
            payloads=[payload(c) for c in chunks[start:end]],
        ))
    client.close()
    return len(chunks)


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
    print(f"Qdrant : {n} chunks indexés dans {args.index / args.model / 'qdrant'} ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
