document.addEventListener("DOMContentLoaded", () => {
  const tabs = Array.from(document.querySelectorAll("[data-tab]"));
  const panels = Array.from(document.querySelectorAll("[data-panel]"));

  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      for (const item of tabs) {
        const selected = item === tab;
        item.classList.toggle("active", selected);
        item.setAttribute("aria-selected", String(selected));
      }
      for (const panel of panels) {
        const selected = panel.dataset.panel === tab.dataset.tab;
        panel.classList.toggle("active", selected);
        panel.hidden = !selected;
      }
    });

    tab.addEventListener("keydown", (event) => {
      const current = tabs.indexOf(tab);
      let next = current;
      if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      tabs[next].focus();
      tabs[next].click();
    });
  }

  for (const panel of panels) {
    const sortButtons = Array.from(panel.querySelectorAll("[data-sort-key]"));
    const displayLimit = Number.parseInt(panel.dataset.displayLimit || "6", 10);

    const sortRows = (selector, key) => {
      const container = panel.querySelector(selector);
      if (!container) return;
      const rows = Array.from(container.children);
      rows.sort((left, right) => {
        const leftValue = Number.parseFloat(left.dataset[key] || "-1");
        const rightValue = Number.parseFloat(right.dataset[key] || "-1");
        return rightValue - leftValue;
      });
      rows.forEach((row, index) => {
        container.appendChild(row);
        row.hidden = index >= displayLimit;
        const rank = row.querySelector("[data-rank-target]");
        if (rank) rank.textContent = String(index + 1);
      });
    };

    const applySort = (key) => {
      sortRows(".bar-chart", key);
      sortRows(".machine-detail-list", key);
      sortButtons.forEach((button) => {
        const selected = button.dataset.sortKey === key;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-pressed", String(selected));
      });
    };

    sortButtons.forEach((button) => {
      button.addEventListener("click", () => applySort(button.dataset.sortKey));
    });
    applySort("performance");
  }
});
