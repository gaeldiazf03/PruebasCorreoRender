const statusPanel = document.querySelector("[data-send-status]");
const statusLog = document.querySelector("[data-send-status-log]");

document.querySelectorAll(".modules form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    statusPanel.hidden = false;
    statusLog.replaceChildren();

    const buttons = [...document.querySelectorAll(".modules button")];
    const originalLabels = buttons.map((button) => button.textContent);
    buttons.forEach((button) => {
      button.disabled = true;
    });

    const addStatus = (item) => {
      const entry = document.createElement("li");
      entry.dataset.type = item.type;
      entry.textContent = item.message;
      statusLog.append(entry);
    };

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "text/event-stream" },
      });
      if (!response.ok || !response.body) {
        throw new Error("No se pudo iniciar el proceso de envío.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finished = false;

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const events = buffer.split("\n\n");
        buffer = events.pop();

        for (const rawEvent of events) {
          const data = rawEvent
            .split("\n")
            .find((line) => line.startsWith("data: "))
            ?.slice(6);
          if (!data) continue;

          const item = JSON.parse(data);
          addStatus(item);
          if (item.type === "complete" || item.type === "error") finished = true;
        }

        if (done) break;
      }

      if (!finished) {
        addStatus({ type: "error", message: "La conexión terminó antes de recibir el resultado del envío." });
      }
    } catch (error) {
      addStatus({ type: "error", message: error.message || "Ocurrió un error de conexión." });
    } finally {
      buttons.forEach((button, index) => {
        button.disabled = false;
        button.textContent = originalLabels[index];
      });
    }
  });
});
