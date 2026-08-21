document.addEventListener("DOMContentLoaded", () => {
  const tabs = Array.from(document.querySelectorAll("[data-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-panel]"));

  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      for (const item of tabs) item.classList.toggle("active", item === tab);
      for (const panel of panels) {
        panel.classList.toggle("active", panel.dataset.panel === tab.dataset.tab);
      }
    });
  }
});
