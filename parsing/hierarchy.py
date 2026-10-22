from __future__ import annotations
from .extract import normalize_title

MAX_DEPTH = 15


def resolve(title: str, redirects: dict[str, str]) -> str:
    seen = set()
    title = normalize_title(title)
    while title in redirects and title not in seen:
        seen.add(title)
        title = normalize_title(redirects[title])
    return title


def build_breadcrumbs(parents: dict[str, str | None], redirects: dict[str, str]) -> tuple[dict[str, list[str]], dict]:
    """Renvoie {titre: [racine, ..., titre]} et des statistiques de qualité."""
    stats = {"parent_missing": 0, "parent_not_found": 0, "cycles": 0, "too_deep": 0}
    not_found: set[tuple[str, str]] = set()   
    resolved = {
        t: (resolve(p, redirects) if p else None) for t, p in parents.items()
    }
    breadcrumbs: dict[str, list[str]] = {}

    for title in parents:
        chain = [title]
        current = title
        while True:
            parent = resolved.get(current)
            if parent is None:
                if current == title:
                    stats["parent_missing"] += 1
                break
            if parent not in parents:
                not_found.add((current, parent))
                chain.append(parent)  
                break
            if parent in chain:
                stats["cycles"] += 1
                break
            chain.append(parent)
            current = parent
            if len(chain) > MAX_DEPTH:
                stats["too_deep"] += 1
                break
        breadcrumbs[title] = list(reversed(chain))

    stats["parent_not_found"] = len(not_found)
    stats["parent_not_found_examples"] = sorted(not_found)[:20]
    return breadcrumbs, stats
