# Front-end VoyaRAG

Deux pages statiques en HTML/CSS/JS, sans build ni dépendance :

- `index.html` : accueil (question libre, idées, cartes de destinations)
- `chat.html?q=...` : conversation (réponse, fil d'Ariane géographique, fiches par rubrique, sources)

## Lancer le site avec les vraies données

Qdrant doit tourner dans Docker (une fois chargé, il garde ses données) :

```
docker run -d --name voyarag-qdrant --restart unless-stopped -p 127.0.0.1:6333:6333 -v voyarag_qdrant:/qdrant/storage qdrant/qdrant:v1.20.0
python -m retrieval.index --model bge-m3
```

Puis, sous Windows, avec `PYTHONUTF8=1` :

```
python -m api.server
```

Le site est alors sur http://localhost:8765. `api/server.py` utilise `retrieval.search` sans LLM : `answer` contient des extraits bruts, c'est ici que l'étape 3 branche la génération.

En ouvrant directement `index.html` (double-clic), l'interface passe en **mode démo** avec les données d'exemple de `js/mock.js` (Lyon, Marseille, Corse, Alpes). Une question contenant « erreur » simule une panne.

## Format de l'API

```http
POST /ask
{"question": "Que faire à Lyon ?", "history": [{"question": "...", "answer": "...", "place": "Lyon"}], "place": null}
```

`place` est rempli quand l'utilisateur clique sur un niveau du fil d'Ariane (ex. `"France"` pour élargir).

Réponse attendue :

```json
{
  "status": "ok",
  "breadcrumb": ["Europe", "France", "Auvergne-Rhône-Alpes", "Lyon"],
  "place": "Lyon",
  "answer": "Texte de la réponse, **gras** et listes « - » acceptés.",
  "listings": {
    "voir": [{"name": "...", "description": "...", "address": "...", "info": "..."}]
  },
  "sources": [{"title": "Lyon", "url": "https://fr.wikivoyage.org/wiki/Lyon"}],
  "suggestions": ["Et s’il pleut ?"]
}
```

- `status` : `"ok"` ou `"introuvable"` (aucun passage pertinent ; `answer` explique, `suggestions` propose d'autres questions)
- `listings` : facultatif ; rubriques possibles `voir`, `faire`, `manger`, `sortir`, `dormir`, `pratique`
- `breadcrumb` : correspond au champ `breadcrumb` des résultats de `retrieval.search`
