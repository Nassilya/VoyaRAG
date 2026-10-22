from __future__ import annotations

import bz2
import gzip
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class RawPage:
    page_id: int
    title: str
    namespace: int
    redirect_to: str | None
    revision_timestamp: str
    text: str


def _open(path: Path):
    if path.suffix == ".bz2":
        return bz2.open(path, "rb")
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return open(path, "rb")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def iter_pages(path: str | Path) -> Iterator[RawPage]:
    with _open(Path(path)) as fh:
        context = ET.iterparse(fh, events=("start", "end"))
        _, root = next(context)
        for event, elem in context:
            if event != "end" or _local(elem.tag) != "page":
                continue
            fields = {"redirect": None, "timestamp": "", "text": ""}
            for child in elem.iter():
                tag = _local(child.tag)
                if tag == "title":
                    fields["title"] = child.text or ""
                elif tag == "ns":
                    fields["ns"] = int(child.text or 0)
                elif tag == "id" and "id" not in fields:
                    fields["id"] = int(child.text)  
                elif tag == "redirect":
                    fields["redirect"] = child.get("title")
                elif tag == "timestamp":
                    fields["timestamp"] = child.text or ""
                elif tag == "text":
                    fields["text"] = child.text or ""
            yield RawPage(
                page_id=fields["id"],
                title=fields["title"],
                namespace=fields.get("ns", 0),
                redirect_to=fields["redirect"],
                revision_timestamp=fields["timestamp"],
                text=fields["text"],
            )
            root.clear()  
