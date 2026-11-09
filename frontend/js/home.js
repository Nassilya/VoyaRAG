(() => {
  const SURPRISES = [
    "Que voir à Lyon s’il pleut ?",
    "Où manger à Marseille ?",
    "Plages calmes en Corse",
    "Randonnées dans les Alpes",
    "Lyon avec un petit budget",
  ];

  const form = document.getElementById("vr-ask-form");
  const input = document.getElementById("vr-ask");
  form.addEventListener("submit", () => {
    if (!input.value.trim()) input.value = input.placeholder;
  });

  document.getElementById("vr-surprise").addEventListener("click", (e) => {
    e.preventDefault();
    const q = SURPRISES[Math.floor(Math.random() * SURPRISES.length)];
    location.href = `chat.html?q=${encodeURIComponent(q)}`;
  });
})();
