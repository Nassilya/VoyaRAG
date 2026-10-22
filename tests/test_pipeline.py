"""Tests du pipeline de données.

Le fichier fixtures/thouars.wikicode est un vrai article de Wikivoyage FR
(Thouars), repris des tests du projet wikivoyage-listings. Les valeurs
attendues (28 fiches, détail du camping) sont celles de ce projet de référence

Lancer :  python -m pytest -q
"""

import bz2
import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parsing.extract import parse_page  
from parsing.wikitext import clean, render_horaire  

THOUARS = (ROOT / "tests" / "fixtures" / "thouars.wikicode").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def thouars():
    return parse_page(42, "Thouars", THOUARS, "2026-09-01T10:00:00Z")


# ---- Fiches de lieux -------------------------------------------------------

def test_listing_count_matches_reference(thouars):
    assert len(thouars.listings) == 28


def test_listing_detail(thouars):
    camping = thouars.listings[25]
    assert camping.type == "se loger"
    assert camping.section == "Se loger"
    f = camping.fields
    assert f["nom"] == "Camping municipal"
    assert f["adresse"] == "13 Rue de la Grande Côte de Crevant"
    assert f["telephone"] == "+33 5 49 66 17 99"
    assert f["prix"] == "3.2 €"
    assert f["latitude"] == "46.979967" and f["longitude"] == "-0.219622"
    assert f["description"].startswith("Situé au bord de la rivière")
    assert "alt" not in f  


def test_listing_types(thouars):
    types = {l.type for l in thouars.listings}
    assert {"voir", "faire", "manger", "sortir", "se loger"} <= types


def test_empty_placeholder_values_dropped(thouars):
    hoggar = next(l for l in thouars.listings if l.fields["nom"] == "Le Hoggar")
    assert "wifi" not in hoggar.fields  # non défini 
    assert hoggar.fields["mise_a_jour"] == "2015/03/18"


# ---- Métadonnées de page ---------------------------------------------------

def test_page_metadata(thouars):
    p = thouars.page
    assert p.parent == "Deux-Sèvres"
    assert p.page_type == "ville" and p.status == "esquisse"
    assert p.infobox_type == "info ville"
    assert (p.latitude, p.longitude) == ("46.9758", "-0.2142")
    assert p.url == "https://fr.wikivoyage.org/wiki/Thouars"


# ---- Sections ----------------------------------------------------------------

def test_sections(thouars):
    headings = [s.heading for s in thouars.sections]
    assert headings[0] == "Introduction"
    assert headings[1:5] == ["Comprendre", "Aller", "Circuler", "Voir"]
    assert "Se loger" in headings


def test_section_text_has_no_wiki_markup(thouars):
    for s in thouars.sections:
        for marker in ("{{", "}}", "[[", "]]", "'''", "==", "<!--"):
            assert marker not in s.text_with_listings, (s.heading, marker)


def test_prose_vs_listings(thouars):
    voir = next(s for s in thouars.sections if s.heading == "Voir")
    assert voir.text == ""                      # section uniquement faite de fiches
    assert "Château des ducs de La Trémoille" in voir.text_with_listings
    assert len(voir.listing_ids) == 8
    manger = next(s for s in thouars.sections if s.heading == "Manger")
    assert "melons" in manger.text and "Le Hoggar" not in manger.text


def test_intro_link_text_kept(thouars):
    assert thouars.sections[0].text == "Thouars est une ville des Deux-Sèvres."


# ---- Petits modèles ----------------------------------------------------------

@pytest.mark.parametrize("args, expected", [
    (["lu", "je", "8", "30", "22", ""], "lun. - jeu.: 8 h 30 - 22 h"),
    (["", "", "8", "30", "22", ""], "8 h 30 - 22 h"),
    (["", "", "8", "30", "", ""], "8 h 30"),
    (["lu", "je", "", "", "", ""], "lun. - jeu."),
    (["lu", "je", "8", "30", "12", "30", "13", "", "15", "45"],
     "lun. - jeu.: 8 h 30 - 12 h 30 et 13 h - 15 h 45"),
])
def test_horaire(args, expected):
    # Mêmes cas que les tests du projet de référence
    assert render_horaire(args) == expected


def test_clean_misc():
    assert clean("Voir [[Fichier:x.jpg|thumb|légende]]le [[Musée d'Art|musée]].") == "Voir le musée."
    assert clean("Prix : {{Prix|1.50|€}} à {{Prix|4|€}}") == "Prix : 1.50 € à 4 €"
    assert clean("[http://exemple.fr site officiel] <!-- caché --> ok<ref>source</ref>") == "site officiel ok"
    assert clean("[[en:Thouars]][[Catégorie:Ville]]Texte") == "Texte"


# ---- Modèles porteurs de texte (exemples réels tirés du dump) ---------------

@pytest.mark.parametrize("wikitext, expected", [
    ("desservies par le {{Abréviation|TGV|train à grande vitesse}} :", "desservies par le TGV :"),
    ("par l'{{Autoroute française|A13}}/E46, via Caen ({{Heure|2|15}})", "par l'A13/E46, via Caen (2 h 15)"),
    ("{{Aéroport|code=NAP}}, {{Aéroport|code=NCL}}", "NAP, NCL"),
    ("le séisme du {{Date|21|11|2004}}", "le séisme du 21 novembre 2004"),
    ("le {{Date|1|10|1795}}", "le 1er octobre 1795"),
    ("vers {{Date|||-1100}}", "vers 1100 av. J.-C."),
    ("de la 59{{e}} à la 96{{e}} Rue, du 18{{E}}", "de la 59e à la 96e Rue, du 18e"),
    ("lundi à vendredi {{Heure|09|00}} à {{Heure|16|00}}", "lundi à vendredi 9 h à 16 h"),
    ("vers {{Heure|8}}, {{Heure|24}} sur 24, {{Heure|2|53|durée=oui}}", "vers 8 h, 24 h sur 24, 2 h 53"),
    ("{{IATA|OAX}}, {{OACI|MMOX}}", "IATA OAX, OACI MMOX"),
    ("L'{{Marqueur|nom=aéroport international du Kansai|alt={{IATA|KIX}}|type=aller|latitude=34.4}} est",
     "L'aéroport international du Kansai (IATA KIX) est"),
    ("{{Métro de Paris|2}}{{Métro de Paris|13}} Place de Clichy", "métro ligne 2 métro ligne 13 Place de Clichy"),
    ("{{RER d'Île-de-France|A}} Auber", "RER A Auber"),
    ("{{Nom local|ber|{{abréviation|ⵎⵔⵉⵞ|Mrič}}}}", "ⵎⵔⵉⵞ"),
    ("au {{s|XVIII}}, au {{s|I}}", "au XVIIIe siècle, au Ier siècle"),
    ("Limeuil {{Symbole|Plus beaux villages France}}", "Limeuil (Plus Beaux Villages de France)"),
    ("{{Symbole|Handicap oui}} Érigé", "Accessible aux personnes handicapées. Érigé"),
    ("{{Traduction|plus tard|لاحقا|laħiqan|}}", "plus tard : لاحقا (laħiqan)"),
    ("{{Traduction|...de dentifrice.||}}", "...de dentifrice."),
    ("De Montréal ({{Unité|279|km|abr=kilomètres}})", "De Montréal (279 km)"),
    ("mont ({{unité|4095|mètres}})", "mont (4095 mètres)"),
    ("langues {{w|bas francique}}, {{W|ETB 3|ETB 3/K|fr}}", "langues bas francique, ETB 3/K"),
    ("{{Compagnie aérienne|pays=MEX|{{Lang|es-mx|Aeroméxico}}}}", "Aeroméxico"),
    # 2e série d'exemples (exemples2.txt)
    ("Style gothique - {{sp|XIII|e|au|XIX|e|s}} -", "Style gothique - XIIIe au XIXe siècles -"),
    ("date plutôt du {{sp|XV|e|ou|XVI|e}}.", "date plutôt du XVe ou XVIe."),
    ("durant les {{sp|XVIII|e| et |XIX|e|s}}.", "durant les XVIIIe et XIXe siècles."),
    ("{{Pays|Albanie}}, {{Pays|Bulgarie}}", "Albanie, Bulgarie"),
    ("(Lignes {{Ligne DPMK|71}}, {{Ligne DPMK|72}})", "(Lignes 71, 72)"),
    ("|| {{retrait|2}}{{Unité|96|km|abr=kilomètres}} ||", "|| 96 km ||"),
    ("{{formatnum:34.4}} km", "34.4 km"),
    ("et {{Route nationale française|158}}", "et N158"),
    # 3e série : repérée en relisant l'échantillon de check_quality.py
    ("Ce sera à {{Heure||10}} à pied", "Ce sera à 10 min à pied"),
    ("moins de {{Heure||30|durée=oui}}.", "moins de 30 min."),
    ("{{Heure|||}}", ""),
    ("superficie de {{Unité|2670|km|2}}", "superficie de 2670 km²"),
])
def test_text_templates(wikitext, expected):
    assert clean(wikitext) == expected


@pytest.mark.parametrize("wikitext, expected", [
    ("{{infobox numéro d'appel d'urgence|police=122|ambulance=124|pompier=123}}",
     "Numéros d'urgence : police 122, ambulance 124, pompiers 123."),
    ("{{Infobox numéro d'appel d'urgence |général = 911 }}", "Numéros d'urgence : numéro général 911."),
    ("{{Infobox numéro d'appel d'urgence |général = |ambulance = 14 |pompier = 14 "
     "|police = 17 ou 1548 depuis un portable |autre1 = 1055 |nomautre1 = Gendarmerie nationale "
     "|nomautre2 = |autre2 = }}",
     "Numéros d'urgence : police 17 ou 1548 depuis un portable, ambulance 14, pompiers 14, "
     "Gendarmerie nationale 1055."),
])
def test_emergency_numbers(wikitext, expected):
    assert clean(wikitext) == expected


def test_table_rendering():
    text = clean('Distances :\n{| class="wikitable"\n|-\n! Ville !! Distance !! Durée\n|-\n'
                 '| [[Bordeaux]] || {{Unité|347|km}} || {{Heure|3|30}}\n|-\n'
                 '| [[Rennes]] || {{Unité|110|km}} || {{Heure|1|15}}\n|}\nFin.')
    assert text == ("Distances :\n\n• Bordeaux — Distance : 347 km ; Durée : 3 h 30\n"
                    "• Rennes — Distance : 110 km ; Durée : 1 h 15\n\nFin.")


def test_table_caption_and_row_headers():
    text = clean('{| class="wikitable"\n|+ Climat de Lyon\n! Mois !! Janv. !! Févr.\n|-\n'
                 '! scope="row" | Max (°C)\n| 6 || 8\n|}')
    assert text == "Climat de Lyon :\n• Max (°C) — Janv. : 6 ; Févr. : 8"


def test_line_breaks_do_not_glue_words():
    assert clean("Ligne 1<br />Ligne 2<br>Ligne 3") == "Ligne 1\nLigne 2\nLigne 3"
    assert clean("Avant<div>bloc</div>après") == "Avant\nbloc\naprès"


def test_liste_regions():
    text = clean("{{ListeRegions | carte=x.png | nomregion1=[[Bhoutan central]] | elementsregion1= "
                 "| descriptionregion1= | nomregion2=[[Bhoutan occidental]] | elementsregion2=Paro "
                 "| descriptionregion2=Une belle région. }} Suite")
    assert text == "• Bhoutan central\n• Bhoutan occidental : Une belle région. (lieux : Paro)\nSuite"


def test_twitter_field_kept():
    from parsing.extract import parse_page as pp
    page = pp(1, "X", "== Voir ==\n* {{Voir | nom=Musée | twitter=https://twitter.com/musee }}")
    assert page.listings[0].fields["twitter"] == "https://twitter.com/musee"


# ---- Bout en bout : mini-dump XML ------------------------------------------

def _page_xml(pid, title, text, redirect=None):
    red = f'<redirect title="{escape(redirect)}" />' if redirect else ""
    return (f"<page><title>{escape(title)}</title><ns>0</ns><id>{pid}</id>{red}"
            f"<revision><id>{pid * 10}</id><timestamp>2026-09-01T10:00:00Z</timestamp>"
            f'<text xml:space="preserve">{escape(text)}</text></revision></page>')


def test_end_to_end(tmp_path):
    pages = [
        _page_xml(1, "France", "'''France''' est un pays.\n== Comprendre ==\nTexte.\n{{Avancement|statut=guide|type=pays}}"),
        _page_xml(2, "Nouvelle-Aquitaine", "Une région.\n{{Avancement|statut=utilisable|type=région}}\n{{Dans|France}}"),
        # Le parent passe par une redirection : Deux-Sevres -> Deux-Sèvres
        _page_xml(3, "Deux-Sèvres", "Un département.\n{{Dans|Nouvelle-Aquitaine}}"),
        _page_xml(4, "Thouars", THOUARS.replace("{{Dans|Deux-Sèvres}}", "{{Dans|Deux-Sevres}}")),
        _page_xml(5, "Deux-Sevres", "#REDIRECTION [[Deux-Sèvres]]", redirect="Deux-Sèvres"),
        _page_xml(6, "Saint-Martin", "{{Homonymie}}\n* [[Saint-Martin (île)]]"),
    ]
    xml = ('<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/" xml:lang="fr">'
           + "".join(pages) + "</mediawiki>")
    dump = tmp_path / "frwikivoyage-20260901-pages-articles.xml.bz2"
    dump.write_bytes(bz2.compress(xml.encode("utf-8")))
    out = tmp_path / "out"

    subprocess.run([sys.executable, str(ROOT / "dumps" / "build_dataset.py"),
                    "--dump", str(dump), "--out", str(out)], check=True, capture_output=True)

    read = lambda name: [json.loads(l) for l in (out / name).read_text(encoding="utf-8").splitlines()]  
    pages_out = {p["title"]: p for p in read("pages.jsonl")}
    assert set(pages_out) == {"France", "Nouvelle-Aquitaine", "Deux-Sèvres", "Thouars"}
    assert pages_out["Thouars"]["breadcrumb"] == ["France", "Nouvelle-Aquitaine", "Deux-Sèvres", "Thouars"]

    listings = read("listings.jsonl")
    assert len(listings) == 28
    assert listings[0]["breadcrumb"][-1] == "Thouars"

    stats = json.loads((out / "stats.json").read_text(encoding="utf-8"))
    assert stats["pages_ignorees"]["homonymie"] == 1
    assert stats["redirections"] == 1
    assert stats["erreurs_parsing"] == 0
    assert stats["conteneurs_deballes"] == []
    assert stats["hierarchie"]["parent_not_found"] == 0
    assert stats["hierarchie"]["parent_missing"] == 1  


def test_labels_and_parent_normalized():
    p = parse_page(1, "X", "Texte.\n{{Avancement|statut=Utilisable|type=cours d’eau}}\n{{Dans|État libre\u200e}}").page
    assert p.status == "utilisable"
    assert p.page_type == "cours d'eau"
    assert p.parent == "État libre"    


EUROPE = (
    '{{Bannière page}}\n{{Accueil contenu|1=<div class="accueil_cadre color9">\n== Comprendre ==\n'
    "L''''Europe''' est une région de {{formatnum:10400000}} km².\n</div>}}\n"
    '{{Accueil contenu|1=<div class="portail-gauche"><div class="accueil_cadre color9">\n'
    '== Régions ==\n{{:Europe/Régions}}\n</div></div><div class="portail-droite">\n'
    "== Villes ==\n* {{Ville | nom=[[Paris]] | description=Capitale de la France.}}\n</div>}}"
)


def test_continent_layout_pages():
    """Les continents mettent tout leur contenu dans {{Accueil contenu|1=...}}."""
    page = parse_page(7, "Europe", EUROPE)
    headings = [s.heading for s in page.sections]
    assert "Comprendre" in headings and "Villes" in headings
    comprendre = next(s for s in page.sections if s.heading == "Comprendre")
    assert comprendre.text == "L'Europe est une région de 10400000 km²."
    assert page.listings[0].fields["nom"] == "Paris"
    for s in page.sections:
        assert "<div" not in s.text_with_listings and "{{" not in s.text_with_listings


def test_listings_inside_wrappers():
    """Des fiches rangées dans {{colonnes|...}} (ou un conteneur inconnu) ne doivent pas disparaître."""
    text = ("== Villes ==\n{{colonnes|nombre=2|\n* {{Ville | nom=[[Lyon]] | description=Capitale des Gaules.}}\n"
            "* {{Ville | nom=[[Grenoble]] }}\n}}\n"
            "== Aéroports ==\n{{Bidule inconnu|\n* {{Aller | nom=Aéroport X }}\n}}\n"
            "{{Climat|tmax-jan=5|tmax-fev=7}}\n"
            "== Voir ==\n* {{Voir | nom=Musée A }}\n")
    page = parse_page(1, "Test", text)
    assert [l.fields["nom"] for l in page.listings] == ["Lyon", "Grenoble", "Aéroport X", "Musée A"]
    assert page.unwrapped == {"colonnes": 1, "bidule inconnu": 1}
    villes = next(s for s in page.sections if s.heading == "Villes")
    assert villes.text_with_listings == "Lyon. Capitale des Gaules.\nGrenoble"
    assert all("tmax" not in s.text_with_listings for s in page.sections)  


def test_missing_parent_counted_once():
    from parsing.hierarchy import build_breadcrumbs
    crumbs, stats = build_breadcrumbs({"Thouars": "Deux-Sèvres", "Deux-Sèvres": "Région absente"}, {})
    assert crumbs["Thouars"] == ["Région absente", "Deux-Sèvres", "Thouars"]
    assert stats["parent_not_found"] == 1