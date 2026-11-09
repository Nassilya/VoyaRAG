window.VoyaMock = (() => {
  const wiki = (title) => ({ title, url: `https://fr.wikivoyage.org/wiki/${encodeURIComponent(title.replace(/ /g, "_"))}` });

  const PLACES = {
    lyon: {
      breadcrumb: ["Europe", "France", "Auvergne-Rhône-Alpes", "Lyon"],
      sources: [wiki("Lyon")],
      main: {
        answer: "Trois jours suffisent pour voir l’essentiel de Lyon à pied et en métro. Je vous propose de commencer par **Fourvière et le Vieux Lyon**, de consacrer le deuxième jour à **la Presqu’île et la Croix-Rousse**, puis de finir par **Confluence et le parc de la Tête d’Or**. Voici les adresses, par rubrique :",
        listings: {
          voir: [
            { name: "Basilique Notre-Dame de Fourvière", description: "Au sommet de la colline, la plus belle vue sur la ville et ses deux fleuves.", address: "8 place de Fourvière, 5e", info: "Entrée libre" },
            { name: "Vieux Lyon et ses traboules", description: "Ruelles Renaissance et passages secrets entre les cours.", address: "Rue Saint-Jean, 5e", info: "Certaines traboules ouvertes en journée" },
            { name: "Théâtres romains de Fourvière", description: "Les gradins antiques de Lugdunum, à deux pas de la basilique.", address: "Rue de l’Antiquaille, 5e", info: "Site en plein air" },
            { name: "Musée des Confluences", description: "Sciences et sociétés dans un bâtiment spectaculaire, à la pointe de la Presqu’île.", address: "86 quai Perrache, 2e", info: "Fermé le lundi" },
          ],
          faire: [
            { name: "Les pentes de la Croix-Rousse", description: "Escaliers, traboules et ateliers dans l’ancien quartier des canuts.", address: "Montée de la Grande-Côte, 1er", info: "Bonnes chaussures conseillées" },
            { name: "Le Mur des Canuts", description: "Une immense fresque en trompe-l’œil sur la vie du quartier.", address: "Boulevard des Canuts, 4e", info: "Visible à toute heure" },
            { name: "Parc de la Tête d’Or", description: "Grand parc avec lac, roseraie et jardin botanique.", address: "Boulevard des Belges, 6e", info: "Entrée gratuite" },
            { name: "Les berges du Rhône", description: "Promenade aménagée au bord de l’eau, à pied ou à vélo.", address: "Quai Claude-Bernard, 7e", info: "Idéal en fin de journée" },
          ],
          manger: [
            { name: "Les Halles de Lyon Paul Bocuse", description: "Produits fins et huîtres au comptoir, pour un déjeuner sur le pouce.", address: "102 cours Lafayette, 3e", info: "€€ · fermé le lundi" },
            { name: "Un bouchon, rue Mercière", description: "Quenelles, saucisson brioché, tarte aux pralines.", address: "Rue Mercière, 2e", info: "€€ · réservez le soir" },
            { name: "Marché du quai Saint-Antoine", description: "Les producteurs de la région, au bord de la Saône.", address: "Quai Saint-Antoine, 2e", info: "Du mardi au dimanche, le matin" },
          ],
          sortir: [
            { name: "Les péniches du Rhône", description: "Bars et concerts sur l’eau, ambiance festive le week-end.", address: "Quai Victor-Augagneur, 3e", info: "Le soir" },
            { name: "Opéra de Lyon", description: "Opéra, danse et jazz sous la grande verrière.", address: "1 place de la Comédie, 1er", info: "Billets en ligne" },
            { name: "Rue Sainte-Catherine", description: "Petite rue animée de bars, près des Terreaux.", address: "Rue Sainte-Catherine, 1er", info: "Jusque tard" },
          ],
          dormir: [
            { name: "Presqu’île", description: "Le plus central : presque tout se fait à pied.", address: "Autour de Bellecour, 2e", info: "€€ à €€€" },
            { name: "Vieux Lyon", description: "Le charme des ruelles pavées, au pied de Fourvière.", address: "5e arrondissement", info: "€€" },
            { name: "Part-Dieu", description: "Pratique en arrivant en train, très bien relié.", address: "3e arrondissement", info: "€ à €€" },
          ],
          pratique: [
            { name: "Arriver en train", description: "Deux grandes gares au centre : Part-Dieu et Perrache.", address: "Gare Part-Dieu, 3e", info: "Liaisons directes depuis Paris" },
            { name: "Depuis l’aéroport", description: "La navette Rhônexpress relie Saint-Exupéry à la Part-Dieu.", address: "Aéroport Lyon-Saint-Exupéry", info: "Navette directe" },
            { name: "Se déplacer", description: "Métro, tram, bus et funiculaires ; la Presqu’île se visite à pied.", address: "Funiculaire depuis Vieux Lyon", info: "Ticket ou pass journée" },
            { name: "Quand venir", description: "Printemps et début d’automne ; la Fête des Lumières anime la ville début décembre.", address: "Toute la ville", info: "Réservez tôt en décembre" },
          ],
        },
        suggestions: ["Et s’il pleut ?", "Et pour un budget serré ?", "Une excursion d’une journée"],
      },
      budget: {
        answer: "Bonne nouvelle : une bonne partie du programme ne coûte rien.\n\n- **Gratuit :** la vue depuis Fourvière, les traboules du Vieux Lyon, les pentes de la Croix-Rousse, les berges du Rhône et le parc de la Tête d’Or.\n- **Manger :** visez les menus du midi dans les bouchons, souvent bien moins chers que le soir, ou un pique-nique avec les produits du marché.\n- **Dormir :** l’auberge de jeunesse du Vieux Lyon, au pied de Fourvière.\n- **Se déplacer :** tout se fait à pied entre les quartiers centraux ; un pass journée suffit pour les trajets plus longs.",
        suggestions: ["Et s’il pleut ?", "Où sortir le soir ?"],
      },
      pluie: {
        answer: "Lyon se visite très bien sous la pluie : les **traboules** du Vieux Lyon et de la Croix-Rousse sont couvertes, et les musées ne manquent pas.",
        listings: {
          voir: [
            { name: "Musée des Confluences", description: "Sciences, sociétés et grandes expositions temporaires.", address: "86 quai Perrache, 2e", info: "Fermé le lundi" },
            { name: "Musée des Beaux-Arts", description: "L’une des plus riches collections de France, dans une ancienne abbaye.", address: "20 place des Terreaux, 1er", info: "Fermé le mardi" },
            { name: "Institut Lumière", description: "Là où le cinéma est né, dans la villa des frères Lumière.", address: "25 rue du Premier-Film, 8e", info: "Séances de films le soir" },
          ],
          manger: [
            { name: "Les Halles de Lyon Paul Bocuse", description: "Tout un marché couvert pour déjeuner au sec.", address: "102 cours Lafayette, 3e", info: "€€ · fermé le lundi" },
          ],
        },
        suggestions: ["Et pour un budget serré ?", "Avec des enfants ?"],
      },
    },
    marseille: {
      breadcrumb: ["Europe", "France", "Provence-Alpes-Côte d’Azur", "Bouches-du-Rhône", "Marseille"],
      sources: [wiki("Marseille")],
      main: {
        answer: "À Marseille, on mange bien autour du **Vieux-Port** et dans le quartier du **Panier**. La bouillabaisse est un plat de fête, assez cher : pour un budget plus serré, essayez la cuisine de rue de **Noailles**.",
        listings: {
          manger: [
            { name: "Une bouillabaisse sur le Vieux-Port", description: "Le plat marseillais par excellence, servi en deux temps : le bouillon puis les poissons.", address: "Quai du Port, 2e", info: "€€€ · réservez" },
            { name: "Le Panier", description: "Le plus vieux quartier de la ville, plein de petites tables et de terrasses.", address: "2e arrondissement", info: "€ à €€" },
            { name: "Marché de Noailles", description: "Épices, cuisine du Maghreb et petits prix, à deux pas de la Canebière.", address: "Rue Longue-des-Capucins, 1er", info: "€ · le midi" },
          ],
          voir: [
            { name: "Notre-Dame-de-la-Garde", description: "La « Bonne Mère » veille sur la ville, vue imprenable sur la rade.", address: "Rue Fort-du-Sanctuaire, 6e", info: "Entrée libre" },
            { name: "Mucem", description: "Musée des civilisations de la Méditerranée, relié au fort Saint-Jean.", address: "7 promenade Robert-Laffont, 2e", info: "Fermé le mardi" },
          ],
        },
        suggestions: ["Et les calanques ?", "Où dormir pas cher ?"],
      },
    },
    corse: {
      breadcrumb: ["Europe", "France", "Corse"],
      sources: [wiki("Corse")],
      main: {
        answer: "Pour des plages calmes, évitez le cœur de l’été ou visez les criques qu’on rejoint **à pied ou en bateau**. Le sud, autour de **Porto-Vecchio**, et le désert des **Agriates** sont les plus réputés.",
        listings: {
          voir: [
            { name: "Plage de Saleccia", description: "Sable blanc et eau turquoise, accessible par une piste ou en bateau depuis Saint-Florent.", address: "Désert des Agriates", info: "Peu fréquentée hors saison" },
            { name: "Plage de la Rondinara", description: "Une baie presque fermée, eau calme et peu profonde.", address: "Entre Porto-Vecchio et Bonifacio", info: "Parking payant en été" },
            { name: "Plage de Palombaggia", description: "Pins parasols et rochers rouges, l’une des plus belles de l’île.", address: "Porto-Vecchio", info: "Arrivez tôt le matin" },
          ],
          pratique: [
            { name: "Quand venir", description: "Juin et septembre : mer chaude et beaucoup moins de monde.", address: "Toute l’île", info: "Juillet-août très chargés" },
          ],
        },
        suggestions: ["Randonnées en Corse", "Comment venir en ferry ?"],
      },
    },
    alpes: {
      breadcrumb: ["Europe", "Alpes"],
      sources: [wiki("Alpes"), wiki("Chamonix-Mont-Blanc")],
      main: {
        answer: "Les Alpes offrent des randonnées pour tous les niveaux. Autour de **Chamonix**, les remontées mécaniques permettent d’atteindre vite les lacs d’altitude ; pour plusieurs jours, le **Tour du Mont-Blanc** passe par la France, l’Italie et la Suisse.",
        listings: {
          faire: [
            { name: "Lac Blanc", description: "Le grand classique face au massif du Mont-Blanc.", address: "Depuis la Flégère, Chamonix", info: "Environ 3 h aller-retour" },
            { name: "Grand Balcon Nord", description: "Sentier en balcon entre le Plan de l’Aiguille et le Montenvers.", address: "Chamonix", info: "Environ 3 h" },
            { name: "Tour du Mont-Blanc", description: "Itinéraire mythique d’environ 170 km autour du massif.", address: "France, Italie, Suisse", info: "7 à 11 jours" },
          ],
          dormir: [
            { name: "Nuit en refuge", description: "Dortoirs et demi-pension en altitude : une expérience à part.", address: "Massif du Mont-Blanc", info: "Réservation indispensable en été" },
          ],
        },
        suggestions: ["Quand partir ?", "Une randonnée facile en famille"],
      },
    },
  };

  const ALIASES = { lyon: "lyon", marseille: "marseille", corse: "corse", alpes: "alpes", chamonix: "alpes" };

  function norm(s) {
    return String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function findPlace(question, history) {
    const q = norm(question);
    for (const [word, key] of Object.entries(ALIASES)) if (q.includes(word)) return key;
    for (let i = history.length - 1; i >= 0; i--) {
      const p = history[i].place && norm(history[i].place);
      if (p && ALIASES[p]) return ALIASES[p];
    }
    return null;
  }

  function answer(question, { history = [], place = null } = {}) {
    const q = norm(question);
    if (q.includes("erreur")) throw new Error("Erreur simulée");
    const key = findPlace(question, history);
    if (!key) {
      return {
        status: "introuvable",
        answer: "En mode démo, je ne connais que Lyon, Marseille, la Corse et les Alpes.",
        suggestions: ["Que faire à Lyon en 3 jours ?", "Plages calmes en Corse", "Où manger à Marseille ?"],
      };
    }
    const p = PLACES[key];
    const leaf = p.breadcrumb[p.breadcrumb.length - 1];
    if (place && place !== leaf) {
      return {
        status: "ok",
        breadcrumb: p.breadcrumb,
        place,
        answer: `En élargissant la recherche à **${place}**, la réponse s’appuierait sur tous les guides de cette zone. (Mode démo : ce résultat viendra de l’API.)`,
        sources: [wiki(place)],
        suggestions: [`Revenir à ${leaf}`],
      };
    }
    let topic = "main";
    if (/budget|pas cher|economique|gratuit/.test(q) && p.budget) topic = "budget";
    else if (/pleu|pluie/.test(q) && p.pluie) topic = "pluie";
    else if (history.length &&!Object.keys(ALIASES).some((w) => q.includes(w))) {
      return {
        status: "introuvable",
        answer: `Je n’ai rien trouvé de précis pour « ${question} » dans les guides.`,
        suggestions: p.main.suggestions,
      };
    }
    return { status: "ok", breadcrumb: p.breadcrumb, sources: p.sources, ...p[topic] };
  }

  return { answer };
})();
