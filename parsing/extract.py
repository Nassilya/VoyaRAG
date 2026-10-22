"""Extraction structurée d'une page Wikivoyage FR

Pour une page, on produit :
  - des métadonnées (type, statut d'avancement, parent géographique, infobox) ;
  - des sections (texte en prose + version avec les fiches de lieux rendues) ;
  - des fiches de lieux (Voir, Manger, Se loger...) avec leurs champs
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field

import mwparserfromhell
from mwparserfromhell.nodes import Heading, Template

from .wikitext import RENDERERS, clean, named_args, positional_args, template_name

LISTING_TEMPLATES = {
    "voir": "voir",
    "faire": "faire",
    "acheter": "acheter",
    "manger": "manger",
    "sortir": "sortir",
    "se loger": "se loger",
    "aller": "aller",
    "circuler": "circuler",
    "ville": "ville",
    "destination": "destination",
    "représentation diplomatique": "représentation diplomatique",
    "listing": "autre",
    "autres": "autre",
    "autre": "autre",
}

LISTING_FIELDS = {
    "nom": "nom",
    "alt": "alt",
    "adresse": "adresse",
    "direction": "direction",
    "directions": "direction",
    "latitude": "latitude",
    "longitude": "longitude",
    "téléphone": "telephone",
    "téléphone portable": "telephone_portable",
    "numéro gratuit": "numero_gratuit",
    "fax": "fax",
    "email": "email",
    "url": "url",
    "facebook": "facebook",
    "twitter": "twitter",
    "horaire": "horaire",
    "prix": "prix",
    "arrivée": "arrivee",
    "départ": "depart",
    "wifi": "wifi",
    "handicap": "handicap",
    "wikipédia": "wikipedia",
    "wikidata": "wikidata",
    "image": "image",
    "mise à jour": "mise_a_jour",
    "description": "description",
}
# Champs gardés tels quels (identifiants, URL, coordonnées) sans nettoyage
_RAW_FIELDS = {"latitude", "longitude", "url", "facebook", "twitter", "email", "wikidata", "image", "mise_a_jour"}
# Valeurs vides 
_EMPTY_VALUES = {"", "non défini", "non defini", "?"}

PAGE_URL = "https://fr.wikivoyage.org/wiki/"
LEAD_TITLE = "Introduction"


@dataclass
class Listing:
    listing_id: str
    page_id: int
    page_title: str
    section: str
    type: str
    fields: dict[str, str]


@dataclass
class Section:
    section_id: str
    page_id: int
    page_title: str
    heading: str
    path: list[str]           
    level: int                 
    text: str                 
    text_with_listings: str    
    listing_ids: list[str] = field(default_factory=list)


@dataclass
class Page:
    page_id: int
    title: str
    url: str
    revision_timestamp: str
    page_type: str | None      
    status: str | None         
    parent: str | None        
    infobox_type: str | None   
    infobox: dict[str, str]
    latitude: str | None
    longitude: str | None
    n_sections: int = 0
    n_listings: int = 0


@dataclass
class ParsedPage:
    page: Page
    sections: list[Section]
    listings: list[Listing]
    is_disambiguation: bool = False
    unwrapped: dict[str, int] = field(default_factory=dict)   


def _value(raw, key: str) -> str:
    text = str(raw).strip() if key in _RAW_FIELDS else clean(raw)
    return "" if text.lower() in _EMPTY_VALUES else text


def parse_listing(tpl: Template, page_id: int, page_title: str, section: str, idx: int) -> Listing:
    kind = LISTING_TEMPLATES[template_name(tpl)]
    args = named_args(tpl)
    fields = {}
    for src, dst in LISTING_FIELDS.items():
        if src in args and dst not in fields:
            value = _value(args[src], dst)
            if value:
                fields[dst] = value
    return Listing(
        listing_id=f"{page_id}-L{idx:04d}",
        page_id=page_id,
        page_title=page_title,
        section=section,
        type=kind,
        fields=fields,
    )


def render_listing(listing: Listing) -> str:
    """Rend une fiche en une ligne lisible (utile pour le chunking par section)."""
    f = listing.fields
    head = f.get("nom", "(sans nom)")
    if f.get("alt"):
        head += f" ({f['alt']})"
    parts = [head]
    for key, label in (
        ("adresse", "Adresse"), ("direction", "Accès"), ("telephone", "Tél."),
        ("horaire", "Horaires"), ("prix", "Prix"),
        ("arrivee", "Arrivée"), ("depart", "Départ"), ("url", "Site"),
    ):
        if f.get(key):
            parts.append(f"{label} : {f[key]}")
    line = " — ".join(parts)
    if f.get("description"):
        line += f". {f['description']}"
    return "• " + line
WRAPPER_TEMPLATES = {"accueil contenu", "colonnes"}
_DIV_RE = re.compile(r"</?div\b[^>]*>", re.IGNORECASE)
_HEADING_RE = re.compile(r"^\s*==", re.MULTILINE)
_NOT_WRAPPERS = {"avancement", "dans", "ispartof"}


def _numbered_params(tpl: Template) -> list[str]:
    """Valeurs des paramètres numérotés (positionnels ou « 1= »), dans l'ordre."""
    return [str(p.value) for p in tpl.params if str(p.name).strip().isdigit()]


def _contains_content(value: str) -> bool:
    """Vrai si le texte contient un titre de section ou une fiche de lieu."""
    if _HEADING_RE.search(value):
        return True
    return any(template_name(t) in LISTING_TEMPLATES
               for t in mwparserfromhell.parse(value).filter_templates())


def _is_wrapper(tpl: Template) -> bool:
    name = template_name(tpl)
    if name in WRAPPER_TEMPLATES:
        return True
    # Unmodèle qu'on ne sait pas traiter, mais qui contient des titres ou des fiches de lieux
    # EST traité comme un conteneur
    if (name in LISTING_TEMPLATES or name in RENDERERS or name in _NOT_WRAPPERS
            or name.startswith("info ")):
        return False
    return any(_contains_content(v) for v in _numbered_params(tpl))


def unwrap_layout(wikitext: str) -> tuple[str, Counter]:
    """Sort le contenu des modèles conteneurs et retire les <div> de mise en page.

    Renvoie le wikitext modifié et le nombre de conteneurs « déballés » par nom
    (utile pour mesurer le phénomène dans stats.json).
    """
    unwrapped: Counter = Counter()
    text = wikitext
    for _ in range(5):  
        code = mwparserfromhell.parse(text)
        changed = False
        for tpl in code.filter_templates(recursive=False):
            if _is_wrapper(tpl):
                inner = "\n".join(_numbered_params(tpl))
                code.replace(tpl, "\n" + inner + "\n")
                unwrapped[template_name(tpl)] += 1
                changed = True
        if not changed:
            break
        text = str(code)
    if not unwrapped:
        return wikitext, unwrapped
    return _DIV_RE.sub("\n", text), unwrapped


def parse_page(page_id: int, title: str, wikitext: str, revision_timestamp: str = "") -> ParsedPage:
    unwrapped_text, unwrapped = unwrap_layout(wikitext)
    code = mwparserfromhell.parse(unwrapped_text)

    meta = {"page_type": None, "status": None, "parent": None,
            "infobox_type": None, "infobox": {}}
    is_disambiguation = False

    # 1. Métadonnées 
    for tpl in code.filter_templates(recursive=False):
        name = template_name(tpl)
        if name == "avancement":
            args = named_args(tpl)
            meta["status"] = _label(args["statut"]) if "statut" in args else None
            meta["page_type"] = _label(args["type"]) if "type" in args else None
        elif name in {"dans", "ispartof"}:
            pos = positional_args(tpl)
            if pos:
                meta["parent"] = normalize_title(clean(pos[0])) or None
        elif name.startswith("info "):
            meta["infobox_type"] = name
            meta["infobox"] = {
                k: v for k, raw in named_args(tpl).items()
                if (v := _value(raw, k if k in ("latitude", "longitude") else "_"))
            }
        elif name in {"homonymie", "disambig"}:
            is_disambiguation = True

    page = Page(
        page_id=page_id,
        title=title,
        url=PAGE_URL + title.replace(" ", "_"),
        revision_timestamp=revision_timestamp,
        latitude=meta["infobox"].get("latitude"),
        longitude=meta["infobox"].get("longitude"),
        **meta,
    )

    # 2. Sections (sans leurs sous-sections) + fiches
    sections: list[Section] = []
    listings: list[Listing] = []
    path: list[str] = []

    for s_idx, section in enumerate(code.get_sections(flat=True, include_lead=True)):
        headings = section.filter_headings(recursive=False)
        if headings and section.nodes and isinstance(section.nodes[0], Heading):
            h = headings[0]
            heading = clean(h.title)
            level = h.level
            path = path[: max(level - 2, 0)] + [heading]
            section.remove(h)
        else:
            heading, level, path = LEAD_TITLE, 1, [LEAD_TITLE]

        sec_listings: list[Listing] = []
        rendered_text = mwparserfromhell.parse(str(section))
        prose_text = mwparserfromhell.parse(str(section))

        for tpl in rendered_text.filter_templates(recursive=False):
            if template_name(tpl) in LISTING_TEMPLATES:
                lst = parse_listing(tpl, page_id, title, " > ".join(path), len(listings) + len(sec_listings))
                sec_listings.append(lst)
                rendered_text.replace(tpl, render_listing(lst).lstrip("• "))
        for tpl in prose_text.filter_templates(recursive=False):
            if template_name(tpl) in LISTING_TEMPLATES:
                prose_text.remove(tpl)

        text = clean(prose_text)
        text_with_listings = clean(rendered_text)
        if not text_with_listings:
            continue
        sections.append(Section(
            section_id=f"{page_id}-S{s_idx:03d}",
            page_id=page_id,
            page_title=title,
            heading=heading,
            path=list(path),
            level=level,
            text=text,
            text_with_listings=text_with_listings,
            listing_ids=[l.listing_id for l in sec_listings],
        ))
        listings.extend(sec_listings)

    page.n_sections = len(sections)
    page.n_listings = len(listings)
    return ParsedPage(page, sections, listings, is_disambiguation, dict(unwrapped))


def to_dict(obj) -> dict:
    return asdict(obj)


_WS = re.compile(r"\s+")


# Caractères invisibles parfois collés par erreur dans les titres
_INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u200e\u200f\u2060\ufeff"))


def _label(raw) -> str | None:
    """Valeur catégorielle normalisée : « Utilisable » -> « utilisable », « cours d’eau » -> « cours d'eau »."""
    text = clean(raw).translate(_INVISIBLE).replace("\u2019", "'").strip().lower()
    return text or None


def normalize_title(title: str) -> str:
    """Normalise un titre de page comme MediaWiki (1re lettre majuscule, espaces)."""
    title = _WS.sub(" ", title.translate(_INVISIBLE).replace("_", " ")).strip()
    return title[:1].upper() + title[1:]
