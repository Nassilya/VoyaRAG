(() => {
  const COMPASS = '<svg width="20" height="20" viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" stroke-width="1.6"></circle><path d="M16 6 L19 16 L16 26 L13 16 Z" fill="currentColor"></path></svg>';
  const PIN = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true" style="color: var(--accent)"><path d="M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12z"></path><circle cx="12" cy="9" r="2.5"></circle></svg>';
  const CLOCK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true" style="color: var(--sage)"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path></svg>';
  const ICON = (d) => `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const TABS = [
    { id: "voir", label: "Voir", icon: ICON('<path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12z"></path><circle cx="12" cy="12" r="3"></circle>') },
    { id: "faire", label: "Faire", icon: ICON('<circle cx="12" cy="12" r="9"></circle><path d="M15.5 8.5l-2 5-5 2 2-5z"></path>') },
    { id: "manger", label: "Manger", icon: ICON('<path d="M6 3v7a2 2 0 0 0 4 0V3M8 10v11"></path><path d="M17 21V3c-2 1.5-3 4-3 7s1 4 3 4"></path>') },
    { id: "sortir", label: "Sortir", icon: ICON('<path d="M5 4h14l-7 8z"></path><path d="M12 12v8M8 20h8"></path>') },
    { id: "dormir", label: "Dormir", icon: ICON('<path d="M3 19V6M3 15h18v4M21 15v-3a3 3 0 0 0-3-3h-7v6"></path><circle cx="7" cy="11.5" r="2"></circle>') },
    { id: "pratique", label: "Pratique", icon: ICON('<rect x="3" y="7" width="18" height="13" rx="1.5"></rect><path d="M9 7V4h6v3M3 12h18"></path>') },
  ];

  const thread = document.getElementById("vr-thread");
  const messages = document.getElementById("vr-messages");
  const suggest = document.getElementById("vr-suggest");
  const form = document.getElementById("vr-follow-form");
  const input = document.getElementById("vr-follow");
  const sendBtn = document.getElementById("vr-send");
  const history = [];
  let busy = false;

  document.getElementById("vr-demo").hidden = !window.VoyaAPI.demo;

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  function inline(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function rich(text) {
    return String(text ?? "").trim().split(/\n\s*\n/).map((block) => {
      const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
      if (lines.length && lines.every((l) => /^[-*] /.test(l))) {
        return `<ul class="vr-list">${lines.map((l) => `<li>${inline(l.slice(2))}</li>`).join("")}</ul>`;
      }
      return `<p>${lines.map(inline).join("<br>")}</p>`;
    }).join("");
  }

  function el(html) {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function scrollEnd() {
    requestAnimationFrame(() => thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" }));
  }

  function setBusy(on) {
    busy = on;
    sendBtn.disabled = on;
  }

  function chip(text, onClick) {
    const b = el(`<button type="button" class="vr-chip">${esc(text)}</button>`);
    b.addEventListener("click", onClick);
    return b;
  }

  function setSuggestions(list) {
    suggest.replaceChildren(...(list || []).map((q) => chip(q, () => send(q))));
  }

  function addUser(text) {
    messages.append(el(`<div class="vr-msg vr-user">${esc(text)}</div>`));
  }

  function addBot() {
    const msg = el(`<div class="vr-msg vr-bot"><span class="vr-avatar" aria-hidden="true">${COMPASS}</span><div class="vr-body"></div></div>`);
    messages.append(msg);
    return msg;
  }

  function showLoading(msg) {
    msg.classList.add("vr-loading");
    msg.setAttribute("aria-busy", "true");
    msg.querySelector(".vr-body").innerHTML = `
      <p class="vr-serif" style="font-size: 22px; font-style: italic; padding-top: 4px">Je feuillette les guides…</p>
      <div class="vr-skel" style="width: 90%"></div>
      <div class="vr-skel" style="width: 74%; animation-delay: .15s"></div>
      <div class="vr-skel" style="width: 82%; animation-delay: .3s"></div>`;
  }

  function done(msg) {
    msg.classList.remove("vr-loading");
    msg.removeAttribute("aria-busy");
    msg.removeAttribute("role");
  }

  function sourcesHtml(sources) {
    return (sources || []).map((s) =>
      `<a class="vr-stamp" href="${esc(s.url)}" target="_blank" rel="noopener">Source : ${esc(s.title || "Wikivoyage")} ↗</a>`
    ).join("");
  }

  function crumbs(r, question) {
    const path = r.breadcrumb || [];
    if (!path.length) return null;
    const current = r.place && path.includes(r.place) ? r.place : path[path.length - 1];
    const nav = el('<nav class="vr-crumbs" aria-label="Destination, cliquez pour élargir ou affiner"></nav>');
    path.forEach((name, i) => {
      const span = el(`<span style="display: inline-flex; align-items: center">${i ? '<span class="vr-sep" aria-hidden="true">›</span>' : ""}</span>`);
      const b = el(`<button type="button" class="vr-crumb" aria-current="${name === current ? "location" : "false"}">${esc(name)}</button>`);
      b.addEventListener("click", () => {
        if (name !== current && !busy) ask(question, nav.closest(".vr-bot"), name);
      });
      span.append(b);
      nav.append(span);
    });
    return nav;
  }

  function sheet(r) {
    const tabs = TABS.filter((t) => r.listings && r.listings[t.id] && r.listings[t.id].length);
    if (!tabs.length) return null;
    const place = (r.breadcrumb || []).slice(-1)[0] || "";
    const art = el(`<article class="vr-sheet" aria-label="Adresses${place ? " à " + esc(place) : ""}">
      <div role="tablist" aria-label="Rubriques" class="vr-tabs vr-scroll"></div>
      <ul role="tabpanel" class="vr-panel"></ul>
      <div class="vr-sources">${sourcesHtml(r.sources)}<span class="vr-note">Pensez à vérifier horaires et tarifs avant de partir.</span></div>
    </article>`);
    const list = art.querySelector(".vr-tabs");
    const panel = art.querySelector(".vr-panel");

    function pick(id) {
      list.querySelectorAll(".vr-tab").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === id)));
      panel.setAttribute("aria-label", TABS.find((t) => t.id === id).label);
      panel.innerHTML = r.listings[id].map((f, i) => `
        <li class="vr-fiche">
          <span class="vr-serif vr-num" aria-hidden="true">${String(i + 1).padStart(2, "0")}</span>
          <div style="display: flex; flex-direction: column; gap: 4px; min-width: 0">
            <h3 class="vr-serif">${esc(f.name)}</h3>
            ${f.description ? `<p>${esc(f.description)}</p>` : ""}
            <div class="vr-facts">
              ${f.address ? `<span>${PIN}${esc(f.address)}</span>` : ""}
              ${f.info ? `<span>${CLOCK}${esc(f.info)}</span>` : ""}
            </div>
          </div>
        </li>`).join("");
    }

    tabs.forEach((t) => {
      const b = el(`<button type="button" role="tab" class="vr-tab" data-tab="${t.id}">${t.icon}${t.label}</button>`);
      b.addEventListener("click", () => pick(t.id));
      list.append(b);
    });
    pick(Object.keys(r.listings).find((id) => tabs.some((t) => t.id === id)));
    return art;
  }

  function showAnswer(msg, r, question) {
    const body = msg.querySelector(".vr-body");
    body.replaceChildren();
    const nav = crumbs(r, question);
    if (nav) body.append(nav);
    if (r.answer) body.insertAdjacentHTML("beforeend", rich(r.answer));
    const art = sheet(r);
    if (art) body.append(art);
    else if (r.sources && r.sources.length) body.append(el(`<div class="vr-sources">${sourcesHtml(r.sources)}</div>`));
    setSuggestions(r.suggestions);
  }

  function showNotFound(msg, r) {
    const body = msg.querySelector(".vr-body");
    body.innerHTML = `
      <p class="vr-serif vr-title">Ce coin de la carte reste à explorer.</p>
      <p class="vr-muted">${esc(r.answer || "Je n’ai rien trouvé de précis dans les guides.")} Essayez une question un peu différente :</p>`;
    const chips = el('<div class="vr-chips"></div>');
    (r.suggestions || []).forEach((q) => chips.append(chip(q, () => send(q))));
    if (chips.children.length) body.append(chips);
    setSuggestions([]);
  }

  function showError(msg, retry) {
    msg.setAttribute("role", "alert");
    const body = msg.querySelector(".vr-body");
    body.innerHTML = `
      <p class="vr-serif vr-title">La route est coupée pour l’instant.</p>
      <p class="vr-muted">La réponse n’a pas pu s’afficher. Vérifiez votre connexion, puis réessayez : votre question est gardée.</p>`;
    const b = el('<button type="button" class="vr-btn" style="align-self: flex-start">Réessayer</button>');
    b.addEventListener("click", retry);
    body.append(b);
  }

  async function ask(question, msg, place = null) {
    setBusy(true);
    setSuggestions([]);
    showLoading(msg);
    scrollEnd();
    try {
      const r = await window.VoyaAPI.ask(question, { history: history.slice(-6), place });
      done(msg);
      if (r.status === "introuvable") showNotFound(msg, r);
      else showAnswer(msg, r, question);
      history.push({ question, answer: r.answer || "", place: (r.breadcrumb || []).slice(-1)[0] || null });
    } catch (err) {
      console.error(err);
      done(msg);
      showError(msg, () => !busy && ask(question, msg, place));
    } finally {
      setBusy(false);
      scrollEnd();
    }
  }

  function send(question) {
    question = question.trim();
    if (!question || busy) return;
    addUser(question);
    ask(question, addBot());
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value;
    if (!q.trim() || busy) return;
    input.value = "";
    send(q);
  });

  const first = new URLSearchParams(location.search).get("q");
  if (first) send(first);
  else input.focus();
})();
