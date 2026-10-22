"""Télécharge le dump Wikivoyage FR et vérifie son intégrité (SHA-1).

Usage :
    python dumps/download_dump.py                 
    python dumps/download_dump.py --date 20261001 

Le fichier est enregistré dans data/raw/ avec un manifest.json qui note la date du dump 

"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://dumps.wikimedia.org/frwikivoyage"
USER_AGENT = "VoyaRAG/0.1 (projet etudiant ESGI; https://github.com/Nassilya/VoyaRAG)"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / 1e6:7.1f} / {total / 1e6:.1f} Mo", end="", flush=True)
    print()
    tmp.replace(dest)


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default="latest", help="AAAAMMJJ ou 'latest' (défaut)")
    ap.add_argument("--force", action="store_true", help="re-télécharger même si le fichier existe")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tag = args.date
    sums_url = f"{BASE}/{tag}/frwikivoyage-{tag}-sha1sums.txt"
    print(f"Lecture des sommes de contrôle : {sums_url}")
    sums = fetch(sums_url).decode()

    match = re.search(r"^([0-9a-f]{40})\s+(frwikivoyage-(\d{8}|latest)-pages-articles\.xml\.bz2)$", sums, re.M)
    if not match:
        print("Impossible de trouver pages-articles.xml.bz2 dans les sommes de contrôle.", file=sys.stderr)
        return 1
    expected_sha1, dated_name, dump_date = match.groups()
    if dump_date == "latest":  # date inconnue : on garde la date du jour dans le nom
        dump_date = datetime.now(timezone.utc).strftime("%Y%m%d")
        dated_name = f"frwikivoyage-{dump_date}-pages-articles.xml.bz2"

    # Dans /latest/ le fichier s'appelle ...-latest-..., ailleurs il porte la date
    remote_name = dated_name if tag != "latest" else "frwikivoyage-latest-pages-articles.xml.bz2"
    url = f"{BASE}/{tag}/{remote_name}"
    dest = RAW_DIR / dated_name

    if dest.exists() and not args.force:
        print(f"Déjà présent : {dest.name}")
    else:
        print(f"Téléchargement : {url}")
        download(url, dest)

    print("Vérification SHA-1...")
    actual = sha1(dest)
    if actual != expected_sha1:
        print(f"ÉCHEC : SHA-1 {actual} != attendu {expected_sha1}. Relancez avec --force.", file=sys.stderr)
        return 1

    manifest = {
        "dump_date": dump_date,
        "file": dest.name,
        "source_url": url,
        "sha1": actual,
        "size_bytes": dest.stat().st_size,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license": "CC BY-SA 4.0 — contenu de Wikivoyage (fr.wikivoyage.org)",
    }
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"OK : {dest.name} (dump du {dump_date}), manifest écrit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
