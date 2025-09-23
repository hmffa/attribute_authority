(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const claimsEl = $("#claims-data");
  const sub = claimsEl?.dataset.sub || "";
  const iss = claimsEl?.dataset.iss || "";
  const storageKey = `hiddenAttrs:${sub}@${iss}`;

  const state = {
    hidden: loadHidden(),
    rawOpen: false,
    pendingAction: null,
  };

  const listEl = $("#attr-list");
  const searchEl = $("#attr-search");
  const toastEl = $("#toast");
  const modalEl = $("#confirm-modal");
  const modalCancel = $("#modal-cancel");
  const modalConfirm = $("#modal-confirm");
  const toggleRawBtn = $("#toggle-raw");
  const collapseBtn = $("#collapse-all");
  const expandBtn = $("#expand-all");
  const resetHiddenBtn = $("#reset-hidden");

  function loadHidden() {
    try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); }
    catch { return {}; }
  }
  function saveHidden() {
    localStorage.setItem(storageKey, JSON.stringify(state.hidden));
  }
  function hideKey(key) {
    state.hidden[key] = "__all__";
    saveHidden();
  }
  function hideValue(key, id) {
    if (state.hidden[key] === "__all__") return; // already hidden
    if (!Array.isArray(state.hidden[key])) state.hidden[key] = [];
    if (!state.hidden[key].includes(id)) state.hidden[key].push(id);
    saveHidden();
  }
  function isHidden(key) {
    return state.hidden[key] === "__all__";
  }
  function isValueHidden(key, value) {
    return Array.isArray(state.hidden[key]) && state.hidden[key].includes(String(value));
  }
  function resetHidden() {
    state.hidden = {};
    saveHidden();
    render();
    toast("Hidden attributes reset");
  }

  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 1600);
  }

  function confirmAction({ title = "Confirm", text = "Are you sure?", onConfirm }) {
    $("#confirm-title").textContent = title;
    $("#confirm-text").textContent = text;
    state.pendingAction = onConfirm;
    modalEl.classList.add("show");
    modalEl.setAttribute("aria-hidden", "false");
  }
  function closeModal() {
    modalEl.classList.remove("show");
    modalEl.setAttribute("aria-hidden", "true");
    state.pendingAction = null;
  }

  function render() {
    // apply hidden rules to DOM
    $$(".attr-item").forEach(item => {
      const key = item.dataset.key;
      item.style.display = isHidden(key) ? "none" : "";
      if (item.style.display === "none") return;

      // hide individual chips
      $$(".chip", item).forEach(chip => {
        const value = chip.dataset.value ?? chip.textContent.trim();
        chip.style.display = isValueHidden(key, value) ? "none" : "";
      });
      // if all chips gone, you may want to auto-hide the attribute row
      const chips = $$(".chip", item);
      const visibleChips = chips.filter(c => c.style.display !== "none");
      if (chips.length && visibleChips.length === 0) {
        item.style.display = "none";
      }
    });

    // search filter
    const q = (searchEl.value || "").toLowerCase().trim();
    if (q) {
      $$(".attr-item").forEach(item => {
        if (item.style.display === "none") return; // already hidden
        const key = item.dataset.key.toLowerCase();
        const text = item.textContent.toLowerCase();
        item.style.display = (key.includes(q) || text.includes(q)) ? "" : "none";
      });
    }

    // raw toggles
    $$(".raw").forEach(d => {
      d.open = state.rawOpen ? true : d.classList.contains("open");
    });
  }

  function tryServerDelete({ id }) {
    // Optional: call server if wired; fall back to client-side hide.
    return fetch(`/api/v1/user/myattributes/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    }).then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    });
  }

  // Event wiring
  listEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    const item = e.target.closest(".attr-item");
    const key = item?.dataset.key;

    switch (btn.dataset.action) {
      case "toggle": {
        const body = item.querySelector(".attr-body .raw");
        body.open = !body.open;
        break;
      }
      case "remove-key": {
        confirmAction({
          title: "Remove attribute",
          text: `Remove all values for "${key}"?`,
          onConfirm: async () => {
            try {
              await tryServerDelete({ key });
            } catch { /* ignore if not wired */ }
            hideKey(key);
            render();
            toast(`Removed "${key}"`);
          }
        });
        break;
      }
      case "remove-value": {
        const id = btn.dataset.id;
        confirmAction({
          title: "Remove value",
          text: `Remove value from "${key}"?`,
          onConfirm: async () => {
            try {
              await tryServerDelete({ id });
            } catch { /* ignore if not wired */ }
            hideValue(key, id);
            render();
            toast(`Removed value from "${key}"`);
          }
        });
        break;
      }
    }
  });

  modalCancel.addEventListener("click", closeModal);
  modalConfirm.addEventListener("click", () => {
    if (typeof state.pendingAction === "function") state.pendingAction();
    closeModal();
  });
  modalEl.addEventListener("click", (e) => {
    if (e.target === modalEl) closeModal();
  });

  searchEl?.addEventListener("input", render);
  toggleRawBtn?.addEventListener("click", () => { state.rawOpen = !state.rawOpen; render(); });
  collapseBtn?.addEventListener("click", () => { state.rawOpen = false; render(); });
  expandBtn?.addEventListener("click", () => { state.rawOpen = true; render(); });
  resetHiddenBtn?.addEventListener("click", resetHidden);

  // First paint
  render();
})();