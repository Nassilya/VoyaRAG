"""Nettoyage du wikitext Wikivoyage FR en texte lisible.

Le texte d'une page Wikivoyage est en « wikitext ». On le transforme en texte
brut en :
  - rendant en clair les petits modèles utiles (Horaire, Prix) ;
  - supprimant les images, catégories, liens interlangues, commentaires, <ref> ;
  - gardant le texte visible des liens internes et externes ;
  - supprimant les autres modèles (à affiner avec dumps/inspect_dump.py).
"""

from __future__ import annotations

import re

import mwparserfromhell
from mwparserfromhell.nodes import Comment, ExternalLink, Tag, Template, Wikilink

# Préfixes de liens à supprimer entièrement (images, catégories...)
_DROP_LINK_PREFIXES = (
    "fichier:", "file:", "image:", "media:", "catégorie:", "category:",
)
# Liens interlangues du type [[en:Paris]] : 2-3 lettres puis « : »
_INTERLANG_RE = re.compile(r"^:?[a-z]{2,3}(-[a-z]+)?:", re.IGNORECASE)

# Modèles dont on garde le dernier argument positionnel comme texte
# (ex: {{Lang|en|Old Town}} -> « Old Town »)
KEEP_LAST_ARG_TEMPLATES = {"lang", "langue", "nobr", "nowrap"}

_DAYS = {
    "lun.": ["1", "l", "lu", "lun", "lundi"],
    "mar.": ["2", "ma", "mar", "mardi"],
    "mer.": ["3", "me", "mer", "mercredi"],
    "jeu.": ["4", "j", "je", "jeu", "jeudi"],
    "ven.": ["5", "v", "ve", "ven", "vendredi"],
    "sam.": ["6", "s", "sa", "sam", "samedi"],
    "dim.": ["7", "d", "di", "dim", "dimanche"],
}
_DAY_LOOKUP = {alias: label for label, aliases in _DAYS.items() for alias in aliases}


def template_name(tpl: Template) -> str:
    """Nom normalisé d'un modèle : minuscules, espaces, sans préfixe « Modèle: »."""
    name = tpl.name.strip_code().strip().replace("_", " ")
    name = re.sub(r"^(modèle|template)\s*:", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", name).strip().lower()


def positional_args(tpl: Template) -> list[str]:
    return [str(p.value).strip() for p in tpl.params if not p.showkey]


def named_args(tpl: Template) -> dict[str, mwparserfromhell.wikicode.Wikicode]:
    return {
        str(p.name).strip().lower(): p.value
        for p in tpl.params
        if p.showkey
    }


# --------------------------------------------------------------------------- 
# Rendu des petits modèles
# --------------------------------------------------------------------------- 

def _time(hours: str, minutes: str) -> str:
    if not hours:
        return ""
    return f"{hours} h {minutes}" if minutes else f"{hours} h"


def _gap(h1: str, m1: str, h2: str, m2: str) -> str:
    a, b = _time(h1, m1), _time(h2, m2)
    return f"{a} - {b}" if b else a


def render_horaire(args: list[str]) -> str:
    """{{Horaire|lu|je|8|30|22|}} -> « lun. - jeu.: 8 h 30 - 22 h »."""
    args = args + [""] * (10 - len(args))
    day = lambda d: _DAY_LOOKUP.get(d.lower(), d)  
    days = day(args[0]) if args[0] else ""
    if args[1]:
        days += " - " + day(args[1])
    gaps = [g for g in (_gap(*args[2:6]), _gap(*args[6:10])) if g]
    hours = " et ".join(gaps)
    if days and hours:
        return f"{days}: {hours}"
    return days or hours


def render_prix(args: list[str]) -> str:
    """{{Prix|13|€}} -> « 13 € »."""
    return " ".join(a for a in args if a)


# --------------------------------------------------------------------------- 
# Nettoyage
# --------------------------------------------------------------------------- 


_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]

# {{Symbole|...}} : pictogrammes
_SYMBOLS = {
    "unesco": "(patrimoine mondial de l'UNESCO)",
    "classé mh": "(classé monument historique)",
    "inscrit mh": "(inscrit monument historique)",
    "plus beaux villages france": "(Plus Beaux Villages de France)",
    "plus beaux villages wallonie": "(Plus Beaux Villages de Wallonie)",
    "wi-fi oui": "Wi-Fi disponible.",
    "wi-fi non": "Pas de Wi-Fi.",
    "handicap oui": "Accessible aux personnes handicapées.",
    "handicap non": "Non accessible aux personnes handicapées.",
}


def _first(args: list[str]) -> str:
    return next((a for a in args if a), "")


def _last(args: list[str]) -> str:
    return next((a for a in reversed(args) if a), "")


def _join(args: list[str]) -> str:
    return " ".join(a for a in args if a)


def _named(tpl: Template, key: str) -> str:
    return clean(tpl.get(key).value) if tpl.has(key) else ""


def render_heure(args: list[str], tpl=None) -> str:
    """{{Heure|1|30}} -> « 1 h 30 » ; {{Heure|09|00}} -> « 9 h » ;
    {{Heure||25}} -> « 25 min » (durée sans heures) ; {{Heure|||}} -> «  »."""
    args = args + ["", ""]
    hours, minutes = args[0], args[1]
    if not hours:
        # Case des heures vide : c'est une durée en minutes (ex: à 10 min à pied)
        minutes = minutes.lstrip("0")
        return f"{minutes} min" if minutes else ""
    hours = hours.lstrip("0") or "0"
    return f"{hours} h {minutes}" if minutes and minutes != "00" else f"{hours} h"


_SUPERSCRIPTS = {"2": "²", "3": "³"}


def render_unite(args: list[str], tpl=None) -> str:
    """{{Unité|279|km|abr=kilomètres}} -> « 279 km » ; {{Unité|2670|km|2}} -> « 2670 km² »."""
    args = [a for a in args if a]
    if len(args) >= 3 and args[2] in _SUPERSCRIPTS:
        return f"{args[0]} {args[1]}{_SUPERSCRIPTS[args[2]]}" + "".join(f" {a}" for a in args[3:])
    return " ".join(args)


def render_date(args: list[str], tpl=None) -> str:
    """{{Date|5|3|2007}} -> « 5 mars 2007 » ; {{Date|||-1100}} -> « 1100 av. J.-C. »."""
    args = args + ["", "", ""]
    day, month, year = args[0], args[1], args[2]
    if month.isdigit() and 1 <= int(month) <= 12:
        month = _MONTHS[int(month) - 1]
    if day == "1":
        day = "1er"
    if year.startswith("-"):
        year = year[1:] + " av. J.-C."
    return _join([day, month, year])


def render_siecle(args: list[str], tpl=None) -> str:
    """{{s|XVIII}} -> « XVIIIe siècle » ; {{s|I}} -> « Ier siècle »."""
    num = _first(args)
    if not num:
        return ""
    suffix = "er" if num.upper() in {"I", "1"} else "e"
    return f"{num}{suffix} siècle"


def render_traduction(args: list[str], tpl=None) -> str:
    """{{Traduction|matin|صباح|sˁabaħ|}} -> « matin : صباح (sˁabaħ) »."""
    args = args + ["", "", ""]
    fr, foreign, pron = args[0], args[1], args[2]
    if not foreign:
        return fr
    text = f"{fr} : {foreign}"
    return f"{text} ({pron})" if pron else text


def render_w(args: list[str], tpl=None) -> str:
    """{{w|Arly}} -> « Arly » ; {{W|ETB 3|ETB 3/K|fr}} -> « ETB 3/K » (2e arg = libellé)."""
    return args[1] if len(args) > 1 and args[1] else _first(args)


def render_aeroport(args: list[str], tpl) -> str:
    """{{Aéroport|code=NAP}} -> « NAP »."""
    return _named(tpl, "code") or _join(args)


def render_symbole(args: list[str], tpl=None) -> str:
    key = _first(args).lower()
    if key in _SYMBOLS:
        return _SYMBOLS[key]
    if key.startswith("étoiles "):
        return f"({key.split()[1]} étoiles)"
    return f"({_first(args)})" if key else ""


def render_marqueur(args: list[str], tpl) -> str:
    """{{Marqueur|nom=aéroport du Kansai|alt={{IATA|KIX}}|...}} -> « aéroport du Kansai (IATA KIX) »."""
    name, alt = _named(tpl, "nom"), _named(tpl, "alt")
    return f"{name} ({alt})" if name and alt else name


def render_autoroute(args: list[str], tpl=None) -> str:
    """{{Autoroute française|A13}} -> « A13 » (ajoute le « A » s'il manque)."""
    road = _first(args)
    return f"A{road}" if road.isdigit() else road


def render_liste_regions(args: list[str], tpl) -> str:
    """{{ListeRegions|nomregion1=..|descriptionregion1=..|elementsregion1=..}} -> une ligne par région."""
    lines = []
    for i in range(1, 60):
        name = _named(tpl, f"nomregion{i}")
        if not name:
            if not tpl.has(f"nomregion{i}") and not tpl.has(f"nomregion{i + 1}"):
                break
            continue
        line = name
        desc = _named(tpl, f"descriptionregion{i}")
        elements = _named(tpl, f"elementsregion{i}")
        if desc:
            line += f" : {desc}"
        if elements:
            line += f" (lieux : {elements})"
        lines.append("• " + line)
    return "\n" + "\n".join(lines) + "\n" if lines else ""


def render_siecles(args: list[str], tpl=None) -> str:
    """{{sp|XIII|e|au|XIX|e|s}} -> « XIIIe au XIXe siècles » ; {{sp|XV|e|ou|XVI|e}} -> « XVe ou XVIe »."""
    args = args + [""] * 6
    n1, s1, conj, n2, s2, plural = args[:6]
    text = _join([f"{n1}{s1}", conj, f"{n2}{s2}"])
    return f"{text} siècles" if plural else text


_URGENCES = [("général", "numéro général"), ("police", "police"),
             ("ambulance", "ambulance"), ("pompier", "pompiers")]


def render_urgences(args: list[str], tpl) -> str:
    """{{Infobox numéro d'appel d'urgence|police=122|ambulance=124|pompier=123}}
    -> « Numéros d'urgence : police 122, ambulance 124, pompiers 123. »"""
    parts = [f"{label} {v}" for key, label in _URGENCES if (v := _named(tpl, key))]
    for i in range(1, 6):
        number, name = _named(tpl, f"autre{i}"), _named(tpl, f"nomautre{i}")
        if number:
            parts.append(f"{name or 'autre'} {number}")
    return f"\nNuméros d'urgence : {', '.join(parts)}.\n" if parts else ""


def render_route_nationale(args: list[str], tpl=None) -> str:
    """{{Route nationale française|158}} -> « N158 »."""
    road = _first(args)
    return f"N{road}" if road.isdigit() else road


def _wrap(fn):
    """Adapte une fonction à 1 argument (args) à la signature (args, tpl)."""
    return lambda args, tpl: fn(args)


# Nom de modèle 
RENDERERS = {
    "horaire": _wrap(render_horaire),
    "prix": _wrap(render_prix),
    "unité": render_unite,                 # {{Unité|279|km|abr=kilomètres}} -> 279 km
    "heure": render_heure,
    "date": render_date,
    "s": render_siecle,
    "siècle": render_siecle,
    "e": lambda a, t: "e",                 # 59{{e}} -> 59e
    "er": lambda a, t: "er",
    "re": lambda a, t: "re",
    "ème": lambda a, t: "e",
    "exp": _wrap(_join),                   # exposant
    "traduction": render_traduction,
    "abréviation": _wrap(_first),          # {{Abréviation|TGV|train à grande vitesse}} -> TGV
    "w": render_w,
    "nom local": _wrap(_last),             # {{Nom local|da|København}} -> København
    "aéroport": render_aeroport,
    "compagnie aérienne": _wrap(_last),    # {{Compagnie aérienne|pays=Pérou|LATAM}} -> LATAM
    "iata": lambda a, t: f"IATA {_first(a)}" if _first(a) else "",
    "oaci": lambda a, t: f"OACI {_first(a)}" if _first(a) else "",
    "symbole": render_symbole,
    "marqueur": render_marqueur,
    "métro de paris": lambda a, t: f" métro ligne {_first(a)} ",
    "métro de new york": lambda a, t: f" métro ligne {_first(a)} ",
    "rer d'île-de-france": lambda a, t: f" RER {_first(a)} ",
    "autoroute française": render_autoroute,
    "route départementale française": _wrap(_join),
    "route européenne": _wrap(_join),
    "listeregions": render_liste_regions,
    # Ajoutés après la 2e inspection (exemples2.txt)
    "sp": render_siecles,
    "infobox numéro d'appel d'urgence": render_urgences,
    "pays": _wrap(_first),                 # {{Pays|Bulgarie}} -> Bulgarie
    "ligne dpmk": _wrap(_first),           # {{Ligne DPMK|72}} -> 72 (bus de Košice)
    "route nationale française": render_route_nationale,
    "retrait": lambda a, t: " ",           # simple espacement dans les tableaux
}
for _name in KEEP_LAST_ARG_TEMPLATES:
    RENDERERS[_name] = _wrap(_last)

# Utilisé par inspect_dump.py pour signaler les modèles déjà gérés
RENDERED_TEMPLATES = set(RENDERERS)


def _render_template(tpl: Template) -> str | None:
    """Texte de remplacement pour un modèle, ou None pour le supprimer."""
    name = template_name(tpl)
    # Fonction d'analyse MediaWiki : {{formatnum:34.4}} -> « 34.4 »
    if name.startswith("formatnum:"):
        return name.split(":", 1)[1].strip()
    renderer = RENDERERS.get(name)
    if renderer is None:
        return None
    args = [clean(a) for a in positional_args(tpl)]
    return renderer(args, tpl)


def clean(wikitext: str | mwparserfromhell.wikicode.Wikicode) -> str:
    """Convertit un fragment de wikitext en texte brut propre."""
    code = mwparserfromhell.parse(str(wikitext))

    for node in list(code.nodes):
        _clean_node(code, node)

    text = code.strip_code(normalize=True, collapse=True)
    return _tidy(text)


def _clean_node(code, node) -> None:
    if isinstance(node, Comment):
        code.remove(node)
    elif isinstance(node, Template):
        rendered = _render_template(node)
        if rendered is None:
            code.remove(node)
        else:
            code.replace(node, rendered)
    elif isinstance(node, Wikilink):
        title = node.title.strip_code().strip()
        if title.lower().startswith(_DROP_LINK_PREFIXES) or _INTERLANG_RE.match(title):
            code.remove(node)
        else:
            label = node.text if node.text else title
            code.replace(node, clean(label))
    elif isinstance(node, ExternalLink):
        # [http://x Titre] -> « Titre » ; URL nue -> l'URL elle-même
        code.replace(node, clean(node.title) if node.title else str(node.url))
    elif isinstance(node, Tag):
        tag = str(node.tag).lower()
        if tag in {"ref", "gallery", "references", "math", "timeline"}:
            code.remove(node)
        elif tag == "table":
            code.replace(node, render_table(node))
        elif tag == "br":
            # <br /> = retour à la ligne si nn les mots se collent
            code.replace(node, "\n")
        elif node.contents is not None and tag in _BLOCK_TAGS and not node.wiki_markup:
            code.replace(node, "\n" + clean(node.contents) + "\n")
        elif node.contents is not None:
            # Nettoie récursivement le contenu des balises (<b>, <span>...)
            code.replace(node, clean(node.contents))


# Balises « bloc » : leur contenu doit rester séparé du texte voisin
_BLOCK_TAGS = {"div", "p", "center", "blockquote", "li", "ul", "ol", "dl", "dd", "dt"}


def _cell_text(cell: Tag) -> str:
    return clean(cell.contents).replace("\n", " ").strip() if cell.contents else ""


def render_table(table: Tag) -> str:
    """Tableau wiki -> une ligne lisible par rangée, avec les en-têtes.

    {| ! Ville !! Distance !! Durée |- | Bordeaux || 347 km || 3 h 30 |}
    -> « • Bordeaux — Distance : 347 km ; Durée : 3 h 30 »
    """
    caption = ""
    rows: list[list[tuple[str, str]]] = []
    first_row: list[tuple[str, str]] = []   # cellules avant le premier « |- »
    for node in table.contents.nodes:
        if not isinstance(node, Tag):
            continue
        tag = str(node.tag).lower()
        if tag in ("td", "th"):
            raw = str(node.contents).lstrip()
            if tag == "td" and raw.startswith("+"):          # « |+ » = légende du tableau
                caption = clean(raw[1:]).strip()
            else:
                first_row.append((tag, _cell_text(node)))
        elif tag == "tr" and node.contents is not None:
            cells = [(str(c.tag).lower(), _cell_text(c))
                     for c in node.contents.filter_tags(recursive=False)
                     if str(c.tag).lower() in ("td", "th")]
            if cells:
                rows.append(cells)
    if first_row:
        rows.insert(0, first_row)

    lines = [f"{caption} :"] if caption else []
    headers: list[str] | None = None
    for cells in rows:
        texts = [text for _, text in cells]
        if all(kind == "th" for kind, _ in cells):           
            headers = texts
            continue
        if not any(texts):
            continue
        if headers and len(headers) == len(texts) and len(texts) > 1:
            parts = [f"{h} : {t}" for h, t in zip(headers[1:], texts[1:]) if t]
            line = texts[0] + (" — " + " ; ".join(parts) if parts else "")
        else:
            line = " ; ".join(t for t in texts if t)
        lines.append("• " + line)
    return "\n" + "\n".join(lines) + "\n" if lines else ""


def _tidy(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*[*#:;]+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[*#]+\s*", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()