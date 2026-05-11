/* globe.js — interactive datacenter map (investor tear sheet view).
   Data is injected as window.__DC_DATA__ by the build step. */

// ----- Constants -----

const STATUS_COLOR = {
  operational:        "#4f9e58",
  under_construction: "#d4a017",
  planned:            "#5b87b8",
  retired:            "#c14b46",
};
const STATUS_LABEL = {
  operational:        "Operational",
  under_construction: "Under construction",
  planned:            "Planned",
  retired:            "Retired",
};

// Operator → parent company / ticker. Private companies have ticker:null.
// Used for grouping filter pills + linking to public quote pages.
// Phase 4 will deepen this (capex, fleet financials) — for now it's just identity.
const OPERATOR_INFO = {
  "AWS":       { parent: "Amazon",     ticker: "AMZN", quote: "https://www.google.com/finance/quote/AMZN:NASDAQ" },
  "Azure":     { parent: "Microsoft",  ticker: "MSFT", quote: "https://www.google.com/finance/quote/MSFT:NASDAQ" },
  "GCP":       { parent: "Alphabet",   ticker: "GOOGL", quote: "https://www.google.com/finance/quote/GOOGL:NASDAQ" },
  "Meta":      { parent: "Meta",       ticker: "META", quote: "https://www.google.com/finance/quote/META:NASDAQ" },
  "Oracle":    { parent: "Oracle",     ticker: "ORCL", quote: "https://www.google.com/finance/quote/ORCL:NYSE" },
  "Apple":     { parent: "Apple",      ticker: "AAPL", quote: "https://www.google.com/finance/quote/AAPL:NASDAQ" },
  "ByteDance": { parent: "ByteDance",  ticker: null,   quote: null },
  "Tencent":   { parent: "Tencent",    ticker: "0700", quote: "https://www.google.com/finance/quote/0700:HKG" },
  "Alibaba":   { parent: "Alibaba",    ticker: "BABA", quote: "https://www.google.com/finance/quote/BABA:NYSE" },
  "Baidu":     { parent: "Baidu",      ticker: "BIDU", quote: "https://www.google.com/finance/quote/BIDU:NASDAQ" },
};
function operatorInfo(op) {
  return OPERATOR_INFO[op] || { parent: op, ticker: null, quote: null };
}

// Tenant extraction — heuristic, runs against the free-text capacity_use prose.
// Phase 2 replaces this with a real `tenants` schema + LLM enrichment.
const TENANT_PATTERNS = [
  { name: "Anthropic",         re: /\bAnthropic\b/i },
  { name: "OpenAI",            re: /\bOpenAI\b/i },
  { name: "xAI",               re: /\bxAI\b|\bGrok\b/i },
  { name: "Meta AI",           re: /\bMeta AI\b|\bLlama\b/i },
  { name: "Google DeepMind",   re: /\bDeepMind\b|\bGemini\b/i },
  { name: "Apple Intelligence",re: /\bApple Intelligence\b/i },
  { name: "Microsoft Copilot", re: /\bCopilot\b/i },
  { name: "ByteDance / TikTok",re: /\bTikTok\b/i },
  { name: "Amazon Bedrock",    re: /\bBedrock\b/i },
];
const COMMITMENT_RE = /\$\d{1,3}(?:\.\d+)?\s*(?:B(?:illion)?|M(?:illion)?|T(?:rillion)?)\+?/g;

function extractTenants(text) {
  if (!text) return [];
  const found = new Set();
  for (const { name, re } of TENANT_PATTERNS) {
    if (re.test(text)) found.add(name);
  }
  return [...found];
}
function extractCommitments(text) {
  if (!text) return [];
  return [...new Set((text.match(COMMITMENT_RE) || []).map(s => s.replace(/\s+/g, "")))];
}

// ----- State -----

const state = {
  data: window.__DC_DATA__ || [],
  filteredOperators: new Set(), // empty = all
  filteredStatuses: new Set(["operational", "under_construction", "planned"]),
  filteredTenants: new Set(),   // empty = all
  search: "",
  activeTab: "overview",
};

// Cache tenant list per record so we don't re-regex
state.data.forEach(d => {
  d._tenants = extractTenants(d.capacity_use);
  d._commitments = extractCommitments(d.capacity_use);
});

// Operator fleet max MW — for the capacity-vs-fleet bar
const OPERATOR_MAX_MW = {};
state.data.forEach(d => {
  if (!d.capacity_mw) return;
  const k = d.operator;
  if (!OPERATOR_MAX_MW[k] || d.capacity_mw > OPERATOR_MAX_MW[k]) OPERATOR_MAX_MW[k] = d.capacity_mw;
});

function visiblePoints() {
  const q = state.search.trim().toLowerCase();
  return state.data.filter(d => {
    if (state.filteredOperators.size && !state.filteredOperators.has(d.operator)) return false;
    if (!state.filteredStatuses.has(d.status)) return false;
    if (state.filteredTenants.size) {
      const has = d._tenants.some(t => state.filteredTenants.has(t));
      if (!has) return false;
    }
    if (q) {
      const hay = `${d.name} ${d.operator} ${d.country || ""} ${d.region || ""} ${d._tenants.join(" ")} ${d.capacity_use || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

// ----- Top-bar metrics -----

function fmtMW(mw) {
  if (mw == null) return "—";
  if (mw >= 1000) return (mw / 1000).toFixed(mw >= 10000 ? 0 : 2) + " GW";
  return Math.round(mw).toLocaleString() + " MW";
}

function updateMetrics() {
  const pts = visiblePoints();
  const totalMW = pts.reduce((s, d) => s + (d.capacity_mw || 0), 0);
  const construction = pts.filter(d => d.status === "under_construction").length;
  const operational  = pts.filter(d => d.status === "operational").length;

  document.getElementById("m-sites").textContent = pts.length.toLocaleString();
  document.getElementById("m-mw").textContent = fmtMW(totalMW);
  document.getElementById("m-construction").textContent = construction.toLocaleString();
  document.getElementById("m-operational").textContent = operational.toLocaleString();

  document.getElementById("fc-count").textContent = state.data.length.toLocaleString();

  // Brand tag — current ISO week, derived from build date if present
  const tag = document.getElementById("brand-tag");
  const buildDate = window.__BUILD_DATE__;
  let wk = "—";
  try {
    const d = buildDate ? new Date(buildDate) : new Date();
    const target = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
    const dayNum = (target.getUTCDay() + 6) % 7;
    target.setUTCDate(target.getUTCDate() - dayNum + 3);
    const firstThursday = new Date(Date.UTC(target.getUTCFullYear(), 0, 4));
    wk = String(1 + Math.round((target - firstThursday) / 604800000)).padStart(2, "0");
  } catch {}
  tag.textContent = `v1.0 · WK ${wk}`;
}

function refreshGlobe() {
  if (globe) {
    const pts = visiblePoints();
    globe.pointsData(pts);
    globe.ringsData(pts.filter(d => d.status === "under_construction" || d.status === "planned"));
  }
  updateMetrics();
}

// ----- Date / source formatting -----

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); }
  catch { return s; }
}

function urlHost(u) {
  try { return new URL(u).host.replace(/^www\./, ""); } catch { return u; }
}
function urlPath(u) {
  try { return new URL(u).pathname + new URL(u).search; } catch { return ""; }
}

// ----- Tabs -----

function showTab(name) {
  state.activeTab = name;
  document.querySelectorAll(".tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".tab-pane").forEach(p => {
    p.hidden = p.dataset.pane !== name;
  });
  // Scroll back to top of body when switching
  const body = document.querySelector(".panel-body");
  if (body) body.scrollTop = 0;
}

// ----- Detail panel -----

function openDetail(dc) {
  const panel = document.getElementById("detail-panel");
  panel.setAttribute("aria-hidden", "false");

  // Hero image
  const hero = document.getElementById("dc-hero");
  const img = dc.primary_image_url || dc.primary_image_local_path;
  if (img) {
    hero.style.backgroundImage = `url("${img}")`;
    hero.classList.remove("empty");
  } else {
    hero.style.backgroundImage = "";
    hero.classList.add("empty");
  }

  // Header
  panel.querySelector(".dc-name").textContent = dc.name;
  panel.querySelector(".dc-operator").textContent = dc.operator;

  const info = operatorInfo(dc.operator);
  const tickerWrap = panel.querySelector(".dc-ticker-wrap");
  tickerWrap.innerHTML = "";
  if (info.ticker) {
    const a = document.createElement("a");
    a.className = "ticker-chip";
    a.href = info.quote || "#";
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = info.ticker;
    a.title = `${info.parent} · open quote`;
    tickerWrap.appendChild(a);
  } else {
    const span = document.createElement("span");
    span.className = "ticker-chip private";
    span.textContent = "PRIVATE";
    span.title = `${info.parent} — not publicly traded`;
    tickerWrap.appendChild(span);
  }

  const badgeWrap = panel.querySelector(".dc-badge-wrap");
  badgeWrap.innerHTML = `<span class="badge ${dc.status}">${STATUS_LABEL[dc.status] || dc.status}</span>`;

  // ---- Overview tab ----

  document.getElementById("dc-mw").textContent = dc.capacity_mw ? fmtMW(dc.capacity_mw) : "—";
  document.getElementById("dc-cpm").textContent = "—"; // populated in P4
  document.getElementById("dc-loc").textContent = [dc.region, dc.country].filter(Boolean).join(", ") || "—";
  document.getElementById("dc-conf").textContent = (dc.confidence || "—").toUpperCase();

  // Capacity vs operator fleet
  const fleetMax = OPERATOR_MAX_MW[dc.operator] || 0;
  const capPct = fleetMax > 0 && dc.capacity_mw ? Math.min(100, (dc.capacity_mw / fleetMax) * 100) : 0;
  document.getElementById("dc-capfill").style.width = `${capPct}%`;
  document.getElementById("dc-cappct").textContent = capPct > 0 ? `${capPct.toFixed(0)}%` : "—";
  document.getElementById("dc-capref").textContent = fleetMax > 0
    ? `of ${dc.operator} fleet max (${fmtMW(fleetMax)})`
    : "no fleet reference";

  // Tenants
  const tenants = dc._tenants || [];
  const tBox = document.getElementById("dc-tenants");
  tBox.innerHTML = "";
  if (tenants.length === 0) {
    tBox.classList.add("empty");
  } else {
    tBox.classList.remove("empty");
    tenants.forEach(t => tBox.appendChild(makeTenantChip(t, false)));
  }
  const tBoxLarge = document.getElementById("dc-tenants-large");
  tBoxLarge.innerHTML = "";
  if (tenants.length === 0) {
    tBoxLarge.classList.add("empty");
  } else {
    tBoxLarge.classList.remove("empty");
    tenants.forEach(t => tBoxLarge.appendChild(makeTenantChip(t, false)));
  }

  // Commitments
  const cBox = document.getElementById("dc-commitments");
  const cItems = document.getElementById("dc-commitments-items");
  const commitments = dc._commitments || [];
  if (commitments.length > 0) {
    cBox.style.display = "block";
    cItems.innerHTML = commitments
      .map(c => `<span class="cc-item"><span class="cc-v">${c}</span></span>`)
      .join("");
  } else {
    cBox.style.display = "none";
  }

  document.getElementById("dc-use").textContent = dc.capacity_use || "No capacity-use narrative yet.";

  // ---- Build tab ----

  const tl = document.getElementById("dc-timeline");
  tl.innerHTML = "";
  const addStep = (k, dateField, current = false) => {
    const v = fmtDate(dc[dateField]);
    const cls = current ? "current" : (dc[dateField] ? "done" : "");
    tl.innerHTML += `<div class="step ${cls}"><span class="dot"></span><span class="k">${k}</span><span class="v">${v}</span></div>`;
  };
  addStep("Construction start", "construction_start_date");
  if (dc.status === "under_construction" || dc.status === "planned") {
    addStep("Expected completion", "expected_completion_date", true);
  } else {
    addStep("Completed", "actual_completion_date");
  }
  if (dc.build_duration_months) {
    tl.innerHTML += `<div class="step"><span class="dot"></span><span class="k">Build duration</span><span class="v">${dc.build_duration_months.toFixed(1)} months</span></div>`;
  }

  const rows = document.getElementById("dc-rows");
  rows.innerHTML = "";
  const addRow = (k, v) => {
    if (v === null || v === undefined || v === "") return;
    rows.innerHTML += `<div class="row"><span class="k">${k}</span><span class="v">${v}</span></div>`;
  };
  addRow("Operator", `${dc.operator} (${info.parent})`);
  addRow("Ticker", info.ticker || "Private");
  addRow("Country", dc.country);
  addRow("Region", dc.region);
  addRow("Coordinates", `${dc.latitude.toFixed(3)}, ${dc.longitude.toFixed(3)}`);
  addRow("Address", dc.address);
  addRow("Confidence", (dc.confidence || "—").toUpperCase());

  // ---- Sources tab ----

  const sources = document.getElementById("dc-sources");
  sources.innerHTML = "";
  let urls = [];
  try { urls = JSON.parse(dc.source_urls || "[]"); } catch {}
  if (Array.isArray(urls) && urls.length) {
    urls.forEach(u => {
      const a = document.createElement("a");
      a.className = "src-row";
      a.href = u; a.target = "_blank"; a.rel = "noopener";
      a.innerHTML = `<span class="src-host">${urlHost(u)}</span><span class="src-path">${urlPath(u) || "/"}</span>`;
      sources.appendChild(a);
    });
  } else {
    sources.innerHTML = `<div class="src-empty">No sources cited</div>`;
  }

  // Reset to overview tab when opening
  showTab("overview");
  panel.classList.add("open");

  // Fly camera
  if (globe) globe.pointOfView({ lat: dc.latitude, lng: dc.longitude, altitude: 1.5 }, 800);
}

function makeTenantChip(name, large) {
  const chip = document.createElement("span");
  chip.className = "tenant-chip";
  chip.innerHTML = `<span class="tc-dot"></span><span>${name}</span>`;
  chip.title = `Filter to facilities mentioning ${name}`;
  if (state.filteredTenants.has(name)) chip.classList.add("active");
  chip.addEventListener("click", () => {
    if (state.filteredTenants.has(name)) state.filteredTenants.delete(name);
    else state.filteredTenants.add(name);
    refreshGlobe();
    rebuildTenantFilterPills();
    chip.classList.toggle("active");
  });
  return chip;
}

function closeDetail() {
  const panel = document.getElementById("detail-panel");
  panel.classList.remove("open");
  panel.setAttribute("aria-hidden", "true");
}

// ----- Country polygons -----

function loadCountries() {
  fetch("countries.geojson")
    .then(r => r.json())
    .then(data => {
      globe
        .polygonsData(data.features)
        .polygonCapColor(() => "rgba(20, 24, 30, 0.45)")
        .polygonSideColor(() => "rgba(50, 70, 100, 0.08)")
        .polygonStrokeColor(() => "#2a3140")
        .polygonAltitude(0.001)
        .polygonLabel(d => `<div class="gl-tooltip"><div class="gt-name">${d.properties.NAME || d.properties.name || ""}</div></div>`);
    })
    .catch(() => {});
}

// ----- Globe init -----

let globe;
try {
  globe = Globe()
    (document.getElementById("globe-container"))
    .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")
    .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
    .backgroundColor("#00000000")
    .showGraticules(true)
    .pointLat(d => d.latitude)
    .pointLng(d => d.longitude)
    .pointAltitude(d => Math.max(0.02, Math.min(0.10, (d.capacity_mw || 200) / 22000)))
    .pointRadius(d => 0.45 + Math.min(1.4, (d.capacity_mw || 200) / 1800))
    .pointColor(d => STATUS_COLOR[d.status] || "#888")
    .pointLabel(d => {
      const tenants = (d._tenants || []).slice(0, 3).join(" · ");
      return `
        <div class="gl-tooltip">
          <div class="gt-name">${d.name}</div>
          <div class="gt-meta">${d.operator} · ${STATUS_LABEL[d.status] || d.status}</div>
          ${d.capacity_mw ? `<div class="gt-mw">${fmtMW(d.capacity_mw)}</div>` : ""}
          ${tenants ? `<div class="gt-meta" style="margin-top:4px">${tenants}</div>` : ""}
        </div>
      `;
    })
    .onPointClick(d => openDetail(d))
    .ringLat(d => d.latitude)
    .ringLng(d => d.longitude)
    .ringColor(d => STATUS_COLOR[d.status] || "#888")
    .ringMaxRadius(3.5)
    .ringPropagationSpeed(1.2)
    .ringRepeatPeriod(1400)
    .atmosphereColor("#d4a017")
    .atmosphereAltitude(0.22);

  globe.controls().autoRotate = true;
  globe.controls().autoRotateSpeed = 0.32;
  document.getElementById("globe-container").addEventListener("mousedown", () => {
    globe.controls().autoRotate = false;
  }, { once: true });

  loadCountries();

  // Subtle starfield
  if (typeof THREE !== "undefined") {
    const count = 3500;
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 500 + Math.random() * 400;
      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    const mat = new THREE.PointsMaterial({ color: 0xe8e6e3, size: 0.55, transparent: true, opacity: 0.55 });
    globe.scene().add(new THREE.Points(geo, mat));
  }
} catch (e) {
  console.error("Globe init failed:", e);
  document.getElementById("globe-container").innerHTML =
    `<div style="color:var(--text-dim);padding:40px;text-align:center;font-family:var(--font-mono);font-size:11px;letter-spacing:0.08em">GLOBE FAILED TO LOAD · CHECK CONSOLE</div>`;
}

// ----- Filter UI (pills) -----

function buildStatusFilters() {
  const box = document.getElementById("filter-statuses");
  box.innerHTML = "";
  const statuses = ["operational", "under_construction", "planned"];
  statuses.forEach(st => {
    const count = state.data.filter(d => d.status === st).length;
    const pill = document.createElement("span");
    pill.className = "pill" + (state.filteredStatuses.has(st) ? " active" : "");
    pill.innerHTML = `<span class="dot" style="background:${STATUS_COLOR[st]}"></span><span>${STATUS_LABEL[st]}</span><span class="count">${count}</span>`;
    pill.addEventListener("click", () => {
      if (state.filteredStatuses.has(st)) state.filteredStatuses.delete(st);
      else state.filteredStatuses.add(st);
      pill.classList.toggle("active");
      refreshGlobe();
    });
    box.appendChild(pill);
  });
}

function buildOperatorFilters() {
  const box = document.getElementById("filter-operators");
  box.innerHTML = "";

  const operators = [...new Set(state.data.map(d => d.operator))].sort();

  // Group by parent
  const byParent = {};
  operators.forEach(op => {
    const info = operatorInfo(op);
    const key = info.parent + (info.ticker ? ` · ${info.ticker}` : " · PRIVATE");
    (byParent[key] = byParent[key] || []).push(op);
  });

  const sortedParents = Object.keys(byParent).sort();
  sortedParents.forEach(parentKey => {
    const group = document.createElement("div");
    group.className = "parent-group";

    const label = document.createElement("div");
    label.className = "parent-label";
    label.textContent = parentKey;
    group.appendChild(label);

    const row = document.createElement("div");
    row.className = "pill-row";

    byParent[parentKey].forEach(op => {
      const count = state.data.filter(d => d.operator === op).length;
      const active = state.filteredOperators.size === 0 || state.filteredOperators.has(op);
      const pill = document.createElement("span");
      pill.className = "pill" + (active ? " active" : "");
      pill.innerHTML = `<span>${op}</span><span class="count">${count}</span>`;
      pill.addEventListener("click", () => {
        const allOps = [...new Set(state.data.map(d => d.operator))];
        // If currently "all", clicking flips to "only this one"
        if (state.filteredOperators.size === 0) {
          state.filteredOperators = new Set([op]);
        } else if (state.filteredOperators.has(op) && state.filteredOperators.size === 1) {
          // Clicking the only-active one returns to "all"
          state.filteredOperators.clear();
        } else if (state.filteredOperators.has(op)) {
          state.filteredOperators.delete(op);
          if (state.filteredOperators.size === 0) {
            // never end up with "nothing visible" — interpret empty as "all"
          }
        } else {
          state.filteredOperators.add(op);
          if (state.filteredOperators.size === allOps.length) state.filteredOperators.clear();
        }
        buildOperatorFilters();
        refreshGlobe();
      });
      row.appendChild(pill);
    });

    group.appendChild(row);
    box.appendChild(group);
  });
}

function buildTenantFilters() {
  rebuildTenantFilterPills();
}
function rebuildTenantFilterPills() {
  const box = document.getElementById("filter-tenants");
  box.innerHTML = "";

  // Collect unique tenants across all DCs
  const tenantCounts = {};
  state.data.forEach(d => (d._tenants || []).forEach(t => {
    tenantCounts[t] = (tenantCounts[t] || 0) + 1;
  }));
  const tenants = Object.keys(tenantCounts).sort((a, b) => tenantCounts[b] - tenantCounts[a]);

  if (tenants.length === 0) {
    box.innerHTML = `<span style="font-family:var(--font-mono);font-size:9.5px;color:var(--text-mute);letter-spacing:0.1em">NONE PARSED</span>`;
    return;
  }
  tenants.forEach(t => {
    const pill = document.createElement("span");
    pill.className = "pill" + (state.filteredTenants.has(t) ? " active" : "");
    pill.innerHTML = `<span class="dot" style="background:var(--accent)"></span><span>${t}</span><span class="count">${tenantCounts[t]}</span>`;
    pill.addEventListener("click", () => {
      if (state.filteredTenants.has(t)) state.filteredTenants.delete(t);
      else state.filteredTenants.add(t);
      pill.classList.toggle("active");
      refreshGlobe();
    });
    box.appendChild(pill);
  });
}

// ----- Wire UI -----

document.getElementById("search").addEventListener("input", e => {
  state.search = e.target.value;
  refreshGlobe();
});

document.getElementById("close-detail").addEventListener("click", closeDetail);
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDetail(); });

document.querySelectorAll(".tab").forEach(t => {
  t.addEventListener("click", () => showTab(t.dataset.tab));
});

// Init
buildStatusFilters();
buildOperatorFilters();
buildTenantFilters();
refreshGlobe();
