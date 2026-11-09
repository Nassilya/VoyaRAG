window.VoyaAPI = (() => {
  const API_URL = location.protocol === "file:" ? null : "";

  async function ask(question, { history = [], place = null } = {}) {
    if (API_URL === null) return fake(question, { history, place });
    const res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history, place }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function fake(question, opts) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        try {
          resolve(window.VoyaMock.answer(question, opts));
        } catch (err) {
          reject(err);
        }
      }, 900 + Math.random() * 700);
    });
  }

  return { ask, demo: API_URL === null };
})();
