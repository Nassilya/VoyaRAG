from __future__ import annotations

import argparse
import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval.chunking import PROCESSED, read_jsonl
from retrieval.search import Retriever

FRONTEND = ROOT / "frontend"
K = 8
EXCERPTS = 3
PER_TAB = 6
MIN_SCORE = 0.5
TABS = {"voir": "voir", "faire": "faire", "acheter": "faire", "manger": "manger", "sortir": "sortir",
        "se loger": "dormir", "aller": "pratique", "circuler": "pratique"}
KEEP = ("nom", "description", "adresse", "horaire", "prix", "type")


def load_listings(path: Path = PROCESSED / "listings.jsonl") -> dict[str, dict]:
    return {row["listing_id"]: {k: row[k] for k in KEEP if row.get(k)}
            for row in read_jsonl(path) if row.get("type") in TABS and row.get("nom")}


def excerpt(text: str, words: int = 45) -> str:
    body = text.split("\n", 1)[-1].replace("\n", " ").split()
    return " ".join(body[:words]) + (" …" if len(body) > words else "")


class Backend:
    def __init__(self):
        self.retriever = Retriever()
        self.listings = load_listings()
        self.lock = threading.Lock()

    def ask(self, question: str, history: list[dict], place: str | None) -> dict:
        if not place and not self.retriever.gazetteer.find(question):
            place = next((h.get("place") for h in reversed(history) if h.get("place")), None)
        with self.lock:
            res = self.retriever.search(question, K, place=place or "auto")
        hits = res["results"]
        if not hits or res["fallback"] or hits[0]["score"] < MIN_SCORE:
            return {
                "status": "introuvable",
                "answer": f"Je n’ai rien trouvé de précis dans les guides pour « {question} ».",
                "suggestions": [f"{p} : que voir ?" for p in res["places"][:1]] or ["Que faire à Lyon ?"],
            }

        top = hits[0]
        breadcrumb = top["breadcrumb"] or [top["page_title"]]
        detected = next((p for p in res["places"] if p in breadcrumb), None)
        if detected and not place:
            breadcrumb = breadcrumb[:breadcrumb.index(detected) + 1]
        current = place if place in breadcrumb else breadcrumb[-1]
        lines = [f"- **{h['page_title']} › {h['section']}** : {excerpt(h['text'])}" for h in hits[:EXCERPTS]]
        answer = "Voici les passages les plus pertinents des guides :\n\n" + "\n".join(lines)

        return {
            "status": "ok",
            "breadcrumb": breadcrumb,
            "place": current,
            "answer": answer,
            "listings": self._listings(hits),
            "sources": self._sources(hits),
            "suggestions": [s.format(current) for s in ("{} : que voir ?", "{} : où manger ?", "{} : où dormir ?")
                            if s.split()[-2] not in question.lower()],
            "results": hits,
        }

    def _listings(self, hits: list[dict]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        seen = set()
        for h in hits:
            for lid in h.get("listing_ids") or []:
                row = self.listings.get(lid)
                if not row or row["nom"] in seen:
                    continue
                tab = out.setdefault(TABS[row["type"]], [])
                if len(tab) >= PER_TAB:
                    continue
                seen.add(row["nom"])
                tab.append({"name": row["nom"], "description": row.get("description", ""),
                            "address": row.get("adresse", ""),
                            "info": " · ".join(v for v in (row.get("horaire"), row.get("prix")) if v)})
        return out

    @staticmethod
    def _sources(hits: list[dict]) -> list[dict]:
        out, seen = [], set()
        for h in hits:
            if h["url"] in seen:
                continue
            seen.add(h["url"])
            out.append({"title": f"{h['page_title']} › {h['section'].split(' > ')[-1]}", "url": h["url"]})
        return out[:4]


class Handler(SimpleHTTPRequestHandler):
    backend: Backend

    def do_POST(self):
        if self.path != "/ask":
            self.send_error(404)
            return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            question = str(data.get("question", "")).strip()
            if not question:
                raise ValueError("question vide")
            body = self.backend.ask(question, data.get("history") or [], data.get("place"))
            self._json(200, body)
        except ValueError as err:
            self._json(400, {"error": str(err)})
        except Exception as err:
            self.log_error("ask: %r", err)
            self._json(500, {"error": "erreur interne"})

    def _json(self, code: int, body: dict):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print("Chargement du modèle, de l'index et des fiches…", flush=True)
    Handler.backend = Backend()
    Handler.backend.ask("Que faire à Lyon ?", [], None)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(FRONTEND)))
    print(f"Prêt : http://localhost:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
