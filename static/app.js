const state = {
  bases: [],
  filteredBases: [],
  selectedBaseId: null,
  affixes: [],
  selectedAffixId: null,
  affixSearch: "",
  affixKind: "",
  onlyCompatible: true,
  includeBench: false,
  prefixes: [],
  suffixes: [],
  debounceHandle: null,
};

const baseListEl = document.querySelector("#base-list");
const baseSearchEl = document.querySelector("#base-search");
const baseCountEl = document.querySelector("#base-count");
const baseNameEl = document.querySelector("#base-name");
const baseClassEl = document.querySelector("#base-class");
const baseInfoEl = document.querySelector("#base-info");
const affixRowsEl = document.querySelector("#affix-rows");
const affixSearchEl = document.querySelector("#affix-search");
const affixKindEl = document.querySelector("#affix-kind");
const affixCountEl = document.querySelector("#affix-count");
const compatibleToggleEl = document.querySelector("#compatible-toggle");
const benchToggleEl = document.querySelector("#bench-toggle");
const affixDetailsEl = document.querySelector("#affix-details");
const addPrefixEl = document.querySelector("#add-prefix");
const addSuffixEl = document.querySelector("#add-suffix");
const prefixListEl = document.querySelector("#prefix-list");
const suffixListEl = document.querySelector("#suffix-list");
const generatePlanEl = document.querySelector("#generate-plan");
const planOutputEl = document.querySelector("#plan-output");
const toastEl = document.querySelector("#toast");
const planTemplate = document.querySelector("#plan-step-template");
const resetFiltersEl = document.querySelector("#reset-filters");

async function fetchJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(payload.error || `Request failed with status ${response.status}`);
  }
  return response.json();
}

function showToast(message, timeout = 4000) {
  toastEl.textContent = message;
  toastEl.hidden = false;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toastEl.hidden = true;
  }, timeout);
}

async function loadMeta() {
  try {
    const meta = await fetchJSON("/api/meta");
    baseCountEl.textContent = `${meta.baseCount} bases · ${meta.affixCount} affixes`;
  } catch (error) {
    baseCountEl.textContent = "Failed to load counts";
    showToast(error.message);
  }
}

async function loadBases() {
  try {
    const bases = await fetchJSON("/api/bases");
    state.bases = bases;
    state.filteredBases = bases;
    renderBaseList();
  } catch (error) {
    baseCountEl.textContent = "Failed to load bases";
    showToast(error.message);
  }
}

function renderBaseList() {
  baseListEl.innerHTML = "";
  state.filteredBases.forEach((base) => {
    const li = document.createElement("li");
    li.dataset.id = base.id;
    const name = document.createElement("div");
    name.textContent = base.name;
    const meta = document.createElement("div");
    meta.classList.add("muted");
    meta.textContent = base.itemClass;
    li.append(name, meta);
    if (base.tags && base.tags.length) {
      const tagRow = document.createElement("div");
      tagRow.classList.add("tag-row");
      base.tags.slice(0, 6).forEach((tag) => {
        const tagChip = document.createElement("span");
        tagChip.classList.add("tag-chip");
        tagChip.textContent = tag.replace(/_/g, " ");
        tagRow.appendChild(tagChip);
      });
      if (base.tags.length > 6) {
        const extra = document.createElement("span");
        extra.classList.add("tag-chip", "tag-chip-more");
        extra.textContent = `+${base.tags.length - 6}`;
        tagRow.appendChild(extra);
      }
      li.appendChild(tagRow);
    }
    if (base.id === state.selectedBaseId) {
      li.classList.add("active");
    }
    li.addEventListener("click", () => selectBase(base.id));
    baseListEl.appendChild(li);
  });
  baseCountEl.textContent = `${state.filteredBases.length} bases shown`;
}

function createInfoRow(label, value) {
  const row = document.createElement("p");
  const strong = document.createElement("strong");
  strong.textContent = `${label}:`;
  row.append(strong, document.createTextNode(` ${value}`));
  return row;
}

function filterBases(query) {
  if (!query) {
    state.filteredBases = state.bases;
    return;
  }
  const term = query.toLowerCase();
  state.filteredBases = state.bases.filter((base) => {
    return (
      base.name.toLowerCase().includes(term) ||
      base.itemClass.toLowerCase().includes(term) ||
      base.tags.some((tag) => tag.toLowerCase().includes(term))
    );
  });
}

async function selectBase(baseId) {
  state.selectedBaseId = baseId;
  state.selectedAffixId = null;
  renderBaseList();
  const base = state.bases.find((entry) => entry.id === baseId);
  if (!base) {
    return;
  }
  baseNameEl.textContent = base.name;
  baseClassEl.textContent = base.itemClass;
  const tags = base.tags.length ? base.tags.join(", ") : "None";
  const influence = base.influence.length ? base.influence.join(", ") : "None";
  baseInfoEl.innerHTML = "";
  baseInfoEl.append(createInfoRow("Tags", tags));
  baseInfoEl.append(createInfoRow("Influence", influence));
  if (base.notes) {
    const notes = document.createElement("p");
    notes.textContent = base.notes;
    baseInfoEl.append(notes);
  }
  if (base.craftTips && base.craftTips.length) {
    const header = document.createElement("h3");
    header.textContent = "Tips";
    baseInfoEl.append(header);
    const list = document.createElement("ul");
    base.craftTips.forEach((tip) => {
      const item = document.createElement("li");
      item.textContent = tip;
      list.appendChild(item);
    });
    baseInfoEl.append(list);
  }
  compatibleToggleEl.disabled = false;
  benchToggleEl.disabled = false;
  affixKindEl.disabled = false;
  affixKindEl.value = state.affixKind;
  affixSearchEl.disabled = false;
  affixSearchEl.value = state.affixSearch;
  generatePlanEl.disabled = false;
  await loadAffixes();
  renderPlan();
}

async function loadAffixes() {
  const params = new URLSearchParams();
  if (state.selectedBaseId && state.onlyCompatible) {
    params.set("base_id", state.selectedBaseId);
    params.set("compatible", "1");
  } else if (state.selectedBaseId) {
    params.set("base_id", state.selectedBaseId);
    params.set("compatible", "0");
  }
  if (state.affixKind) {
    params.set("type", state.affixKind);
  }
  if (state.affixSearch) {
    params.set("search", state.affixSearch);
  }
  if (state.includeBench) {
    params.set("include_master", "1");
  }
  try {
    const affixes = await fetchJSON(`/api/affixes?${params.toString()}`);
    state.affixes = affixes;
    renderAffixes();
  } catch (error) {
    showToast(error.message);
  }
}

function renderAffixes() {
  affixRowsEl.innerHTML = "";
  if (affixCountEl) {
    if (!state.selectedBaseId) {
      affixCountEl.textContent = "Select a base to browse mods";
    } else if (state.affixes.length) {
      affixCountEl.textContent = `${state.affixes.length} mods shown`;
    } else {
      affixCountEl.textContent = "No mods match";
    }
  }
  if (!state.affixes.length) {
    state.selectedAffixId = null;
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.classList.add("muted");
    cell.textContent = "No affixes match the current filters.";
    row.appendChild(cell);
    affixRowsEl.appendChild(row);
    renderEmptyAffixDetails("Adjust filters or pick a different base.");
    return;
  }
  state.affixes.forEach((affix) => {
    const row = document.createElement("tr");
    row.dataset.id = affix.id;
    if (affix.id === state.selectedAffixId) {
      row.classList.add("active");
    }
    const odds = formatChance(affix.chance);
    const nameCell = document.createElement("td");
    nameCell.textContent = affix.name;
    const typeCell = document.createElement("td");
    typeCell.classList.add("col-type");
    typeCell.textContent = affix.type;
    const levelCell = document.createElement("td");
    levelCell.classList.add("col-ilvl");
    levelCell.textContent = affix.level;
    const effectCell = document.createElement("td");
    effectCell.textContent = affix.statTexts && affix.statTexts.length ? affix.statTexts[0] : "—";
    const chanceCell = document.createElement("td");
    chanceCell.classList.add("col-chance");
    chanceCell.textContent = odds;
    row.append(nameCell, typeCell, levelCell, effectCell, chanceCell);
    row.addEventListener("click", () => selectAffix(affix.id));
    affixRowsEl.appendChild(row);
  });
  if (!state.selectedAffixId && state.affixes.length) {
    selectAffix(state.affixes[0].id);
  } else if (state.selectedAffixId) {
    selectAffix(state.selectedAffixId);
  }
}

function selectAffix(affixId) {
  state.selectedAffixId = affixId;
  affixRowsEl.querySelectorAll("tr").forEach((row) => {
    row.classList.toggle("active", row.dataset.id === affixId);
  });
  const affix = state.affixes.find((item) => item.id === affixId);
  if (!affix) {
    renderEmptyAffixDetails();
    return;
  }
  addPrefixEl.disabled = false;
  addSuffixEl.disabled = false;
  affixDetailsEl.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = affix.name;
  const meta = document.createElement("p");
  meta.classList.add("muted");
  meta.textContent = `${affix.type.toUpperCase()} · Item level ${affix.level}+`;
  affixDetailsEl.append(title, meta);

  if (affix.statTexts && affix.statTexts.length) {
    const header = document.createElement("h4");
    header.textContent = "Effect";
    const list = document.createElement("ul");
    affix.statTexts.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      list.appendChild(item);
    });
    affixDetailsEl.append(header, list);
  }

  if (affix.methods && affix.methods.length) {
    const header = document.createElement("h4");
    header.textContent = "Acquisition";
    const list = document.createElement("ul");
    affix.methods.forEach((method) => {
      const item = document.createElement("li");
      item.textContent = method;
      list.appendChild(item);
    });
    affixDetailsEl.append(header, list);
  }

  if (affix.requiredTags && affix.requiredTags.length) {
    affixDetailsEl.append(createInfoRow("Requires", affix.requiredTags.join(", ")));
  }

  if (affix.chance) {
    affixDetailsEl.append(createInfoRow("Alteration odds", formatChance(affix.chance, true)));
  }

  if (affix.spawnWeights && affix.spawnWeights.length) {
    const header = document.createElement("h4");
    header.textContent = "Spawn weights";
    const list = document.createElement("ul");
    affix.spawnWeights.forEach((entry) => {
      const item = document.createElement("li");
      item.textContent = `${entry.tag.replace(/_/g, " ")} → ${entry.weight}`;
      list.appendChild(item);
    });
    affixDetailsEl.append(header, list);
  }

  if (affix.notes) {
    const header = document.createElement("h4");
    header.textContent = "Notes";
    const note = document.createElement("p");
    note.textContent = affix.notes;
    affixDetailsEl.append(header, note);
  }
}

function formatChance(chance, verbose = false) {
  if (!chance || !chance.totalWeight || !chance.weight) {
    return "—";
  }
  const percentage = (chance.chance * 100).toFixed(3);
  const expected = chance.expectedRolls.toLocaleString(undefined, {
    maximumFractionDigits: 1,
  });
  if (verbose) {
    return `${percentage}% (≈1 in ${expected})`;
  }
  return `${percentage}%`;
}

function addAffix(kind) {
  if (!state.selectedAffixId) {
    return;
  }
  const affix = state.affixes.find((item) => item.id === state.selectedAffixId);
  if (!affix) {
    return;
  }
  const target = kind === "prefix" ? state.prefixes : state.suffixes;
  const exists = target.some((entry) => entry.name === affix.name);
  if (exists) {
    showToast(`${affix.name} is already in your ${kind} wishlist.`);
    return;
  }
  target.push({ id: affix.id, name: affix.name });
  renderWishlist();
  renderPlan();
}

function removeAffix(kind, id) {
  const target = kind === "prefix" ? state.prefixes : state.suffixes;
  const index = target.findIndex((entry) => entry.id === id);
  if (index >= 0) {
    target.splice(index, 1);
    renderWishlist();
    renderPlan();
  }
}

function renderWishlist() {
  renderChipList(prefixListEl, state.prefixes, "prefix");
  renderChipList(suffixListEl, state.suffixes, "suffix");
  generatePlanEl.disabled = !state.selectedBaseId;
}

function renderChipList(container, items, kind) {
  container.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("li");
    empty.classList.add("muted");
    empty.textContent = "None selected";
    container.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const chip = document.createElement("li");
    chip.classList.add("chip");
    const label = document.createElement("span");
    label.textContent = item.name;
    const button = document.createElement("button");
    button.type = "button";
    button.innerHTML = "&times;";
    button.addEventListener("click", () => removeAffix(kind, item.id));
    chip.append(label, button);
    container.appendChild(chip);
  });
}

async function generatePlan() {
  if (!state.selectedBaseId) {
    showToast("Select a base before generating a plan.");
    return;
  }
  const payload = {
    base_id: state.selectedBaseId,
    prefixes: state.prefixes.map((entry) => entry.name),
    suffixes: state.suffixes.map((entry) => entry.name),
  };
  try {
    const result = await fetchJSON("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderPlan(result.steps);
  } catch (error) {
    showToast(error.message);
  }
}

function renderPlan(steps = null) {
  if (!steps) {
    planOutputEl.innerHTML = `
      <p class="muted">
        Select a base and add at least one prefix or suffix to generate a crafting walkthrough.
      </p>`;
    return;
  }
  planOutputEl.innerHTML = "";
  steps.forEach((step, index) => {
    const instance = planTemplate.content.cloneNode(true);
    instance.querySelector(".plan-step-title").textContent = `Step ${index + 1}: ${step.title}`;
    instance.querySelector(".plan-step-body").textContent = step.details;
    planOutputEl.appendChild(instance);
  });
}

function debounceAffixSearch(value) {
  clearTimeout(state.debounceHandle);
  state.debounceHandle = setTimeout(() => {
    state.affixSearch = value.trim();
    loadAffixes();
  }, 250);
}

function renderEmptyAffixDetails(message = "Select a mod to inspect details.") {
  affixDetailsEl.innerHTML = "";
  const title = document.createElement("h3");
  title.textContent = "No affix selected";
  const msg = document.createElement("p");
  msg.classList.add("muted");
  msg.textContent = message;
  affixDetailsEl.append(title, msg);
  addPrefixEl.disabled = true;
  addSuffixEl.disabled = true;
}

function resetFilters() {
  state.selectedBaseId = null;
  state.selectedAffixId = null;
  state.prefixes = [];
  state.suffixes = [];
  state.affixSearch = "";
  state.affixKind = "";
  state.onlyCompatible = true;
  state.includeBench = false;
  baseSearchEl.value = "";
  affixSearchEl.value = "";
  affixSearchEl.disabled = true;
  affixKindEl.value = "";
  affixKindEl.disabled = true;
  compatibleToggleEl.checked = true;
  compatibleToggleEl.disabled = true;
  benchToggleEl.checked = false;
  benchToggleEl.disabled = true;
  generatePlanEl.disabled = true;
  addPrefixEl.disabled = true;
  addSuffixEl.disabled = true;
  baseNameEl.textContent = "Select a base";
  baseClassEl.textContent = "";
  baseInfoEl.innerHTML = '<p class="muted">Choose an armour, jewellery, weapon, or off-hand base to begin.</p>';
  renderEmptyAffixDetails("Pick a base to unlock compatible mods.");
  renderWishlist();
  renderPlan();
  filterBases("");
  renderBaseList();
  state.affixes = [];
  renderAffixes();
}

baseSearchEl.addEventListener("input", (event) => {
  filterBases(event.target.value.trim());
  renderBaseList();
});

affixSearchEl.addEventListener("input", (event) => {
  debounceAffixSearch(event.target.value);
});

affixKindEl.addEventListener("change", () => {
  state.affixKind = affixKindEl.value;
  loadAffixes();
});

compatibleToggleEl.addEventListener("change", () => {
  state.onlyCompatible = compatibleToggleEl.checked;
  loadAffixes();
});

benchToggleEl.addEventListener("change", () => {
  state.includeBench = benchToggleEl.checked;
  loadAffixes();
});

addPrefixEl.addEventListener("click", () => addAffix("prefix"));
addSuffixEl.addEventListener("click", () => addAffix("suffix"));

generatePlanEl.addEventListener("click", generatePlan);

resetFiltersEl?.addEventListener("click", () => {
  showToast("Session reset. Start by selecting a base.");
  resetFilters();
});

window.addEventListener("DOMContentLoaded", async () => {
  compatibleToggleEl.disabled = true;
  benchToggleEl.disabled = true;
  affixKindEl.disabled = true;
  affixSearchEl.disabled = true;
  await Promise.all([loadMeta(), loadBases()]);
});
