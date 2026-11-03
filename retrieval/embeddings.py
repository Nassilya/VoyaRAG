from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.chunking import PROCESSED, read_jsonl

MODELS = {
    "e5-small": {"name": "intfloat/multilingual-e5-small", "query": "query: ", "passage": "passage: "},
    "bge-m3": {"name": "BAAI/bge-m3", "query": "", "passage": ""},
}

_LOADED = {}


def load_model(key: str):
    if key not in _LOADED:
        from sentence_transformers import SentenceTransformer
        _LOADED[key] = SentenceTransformer(MODELS[key]["name"], device="cpu")
    return _LOADED[key]


def embed_passages(texts: list[str], key: str, batch_size: int = 32) -> np.ndarray:
    prefix = MODELS[key]["passage"]
    return load_model(key).encode([prefix + t for t in texts], batch_size=batch_size,
                                  normalize_embeddings=True, show_progress_bar=True)


def embed_queries(queries: list[str], key: str) -> np.ndarray:
    prefix = MODELS[key]["query"]
    return load_model(key).encode([prefix + q for q in queries], normalize_embeddings=True)


def sample_chunks(chunks_path: Path, titles: list[str], n_pages: int, seed: int) -> list[dict]:
    chunks = list(read_jsonl(chunks_path))
    all_titles = sorted({c["page_title"] for c in chunks})
    others = [t for t in all_titles if t not in titles]
    random.Random(seed).shuffle(others)
    keep = set(titles) | set(others[:n_pages])
    return [c for c in chunks if c["page_title"] in keep]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, default="e5-small")
    ap.add_argument("--chunks", type=Path, default=PROCESSED / "chunks.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "index")
    ap.add_argument("--titles", default="", help="pages toujours gardées, séparées par des virgules")
    ap.add_argument("--n-pages", type=int, default=None, help="nombre de pages tirées au hasard (défaut : tout)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    titles = [t.strip() for t in args.titles.split(",") if t.strip()]
    if args.n_pages is None:
        chunks = list(read_jsonl(args.chunks))
    else:
        chunks = sample_chunks(args.chunks, titles, args.n_pages, args.seed)
    print(f"{len(chunks)} chunks, {len({c['page_title'] for c in chunks})} pages, modèle {MODELS[args.model]['name']}")

    t0 = time.time()
    vectors = embed_passages([c["text"] for c in chunks], args.model, args.batch_size)
    duration = time.time() - t0

    out = args.out / args.model
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "vectors.npy", vectors.astype(np.float32))
    with open(out / "chunks.jsonl", "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    info = {"model": MODELS[args.model]["name"], "n_chunks": len(chunks), "dim": int(vectors.shape[1]),
            "duree_s": round(duration, 1), "chunks_par_s": round(len(chunks) / max(duration, 1e-9), 1)}
    (out / "info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"Terminé en {info['duree_s']} s ({info['chunks_par_s']} chunks/s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
