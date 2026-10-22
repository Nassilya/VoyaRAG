# VoyaRAG — un assistant de voyage RAG sur Wikivoyage

Projet de NLP — Master 2 IABD, ESGI

VoyaRAG répond aux questions des voyageurs à partir du contenu de **Wikivoyage en
français**. Pour chaque question, le système recherche les passages pertinents dans
le corpus, puis un LLM rédige une réponse en citant ses sources, ou indique que
l'information n'est pas disponible



## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                 
```

## Utilisation

```bash
# 1) Télécharger le dump (vérification SHA-1 + manifest avec la date du dump)
python dumps/download_dump.py --date 20260101

# 2) (Optionnel) Inspecter le dump pour contrôler le parser
python dumps/inspect_dump.py --limit 2000 > data/inspection.txt
python dumps/inspect_dump.py --limit 2000 --examples "heure,unité" > data/exemples.txt

# 3) Construire le dataset (essai rapide, puis complet)
python dumps/build_dataset.py --limit 200
python dumps/build_dataset.py

# 4) Contrôler la qualité du dataset (restes de wikitext + échantillon à relire)
python dumps/check_quality.py > data/qualite.txt
```

Toute l'équipe utilise le **dump du 1er janvier 2026** (`--date 20260101`), pour que
les résultats restent comparables

## Organisation du code

```
parsing/                le « moteur » (fonctions, jamais lancé directement)
├── dump.py             lit le dump XML page par page (streaming)
├── wikitext.py         nettoie le wikitext ; convertit les modèles (RENDERERS)
├── extract.py          analyse un article : métadonnées, sections, fiches de lieux
└── hierarchy.py        reconstruit le fil d'Ariane géographique
dumps/                  les scripts à lancer
├── download_dump.py    télécharge et vérifie le dump
├── inspect_dump.py     contrôle qualité : modèles et champs les plus fréquents
├── build_dataset.py    construit le dataset dans data/processed/
└── check_quality.py    mesure les restes de wikitext et tire un échantillon à relire
tests/
├── test_pipeline.py    tests automatisés (pytest)
└── fixtures/thouars.wikicode   un vrai article de Wikivoyage pour les tests
```

## Données produites (`data/processed/`)

| Fichier | Contenu |
|---|---|
| `pages.jsonl` | une ligne par article : type, statut, parent, coordonnées, URL, fil d'Ariane |
| `sections.jsonl` | une ligne par section : texte en prose, et prose + fiches rendues en clair |
| `listings.jsonl` | une ligne par lieu : nom, adresse, horaires, prix, téléphone, coordonnées… |
| `redirects.json` | noms alternatifs des pages |
| `stats.json` | volumes et contrôles qualité |

Résultat sur le dump du 1er janvier 2026 : **9 433 articles, 89 233 sections,
136 480 fiches de lieux, 0 erreur de parsing.**

Les fichiers de `data/` ne sont pas versionnés : ils se régénèrent avec les scripts


## Licence et attribution

Le contenu provient de **Wikivoyage** (fr.wikivoyage.org), sous licence **CC BY-SA**.
Le fichier `tests/fixtures/thouars.wikicode` est l'article Thouars de Wikivoyage, repris
des tests du projet [wikivoyage-listings](https://github.com/baturin/wikivoyage-listings).
