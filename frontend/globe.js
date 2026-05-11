/* globe.js — interactive datacenter globe.
   Data is injected as window.__DC_DATA__ by the build step.
*/

const STATUS_COLOR = {
  operational: "#3fb950",
  under_construction: "#f0b429",
  planned: "#4cc2ff",
  retired: "#f85149",
};

const STATUS_LABEL = {
  operational: "Operational",
  under_construction: "Under construction",
  planned: "Planned",
  retired: "Retired",
};

const state = {
  data: window.__DC_DATA__ || [],
  filteredOperators: new Set(),
  filteredStatuses: new Set(["operational", "under_construction", "planned"]),
  search: "",
};

function visiblePoints() {
  const q = state.search.trim().toLowerCase();
  return state.data.filter(d => {
    if (state.filteredOperators.size && !state.filteredOperators.has(d.operator)) return false;
    if (!state.filteredStatuses.has(d.status)) return false;
    if (q) {
      const hay = `${d.name} ${d.operator} ${d.country || ""} ${d.region || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function updateKPIs() {
  const pts = visiblePoints();
  const total = pts.length;
  const totalMW = pts.reduce((s, d) => s + (d.capacity_mw || 0), 0);
  const construction = pts.filter(d => d.status === "under_construction").length;
  document.getElementById("kpi-count").textContent = total.toLocaleString();
  document.getElementById("kpi-mw").textContent = totalMW.toLocaleString() + " MW";
  const pct = total ? Math.round((construction / total) * 100) : 0;
  document.getElementById("kpi-construction").textContent = `${construction} (${pct}%)`;
}

function refreshGlobe() {
  if (globe) {
    const pts = visiblePoints();
    globe.pointsData(pts);
    globe.ringsData(pts.filter(d => d.status === "under_construction" || d.status === "planned"));
  }
  updateKPIs();
}

function fmtDate(s) {
  if (!s) return "—";
  try { return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); }
  catch { return s; }
}

function openDetail(dc) {
  const panel = document.getElementById("detail-panel");
  const hero = panel.querySelector(".hero");
  if (dc.primary_image_url) {
    hero.style.backgroundImage = `url("${dc.primary_image_url}")`;
    hero.textContent = "";
  } else if (dc.primary_image_local_path) {
    hero.style.backgroundImage = `url("${dc.primary_image_local_path}")`;
    hero.textContent = "";
  } else {
    hero.style.backgroundImage = "";
    hero.textContent = "(no photo yet)";
  }

  panel.querySelector(".dc-name").textContent = dc.name;
  panel.querySelector(".dc-subtitle").innerHTML =
    `${dc.operator} · ${dc.region || dc.country || "—"} ` +
    `<span class="badge ${dc.status}">${STATUS_LABEL[dc.status] || dc.status}</span>`;

  const rows = panel.querySelector(".rows");
  rows.innerHTML = "";
  const addRow = (k, v) => {
    if (v === null || v === undefined || v === "") return;
    const r = document.createElement("div");
    r.className = "row";
    r.innerHTML = `<span class="k">${k}</span><span class="v">${v}</span>`;
    rows.appendChild(r);
  };
  addRow("Operator", dc.operator);
  addRow("Location", [dc.region, dc.country].filter(Boolean).join(", "));
  addRow("Coordinates", `${dc.latitude.toFixed(3)}, ${dc.longitude.toFixed(3)}`);
  addRow("Confidence", dc.confidence || "—");

  // Capacity
  const gauge = panel.querySelector(".capacity-gauge");
  if (dc.capacity_mw) {
    gauge.style.display = "block";
    gauge.querySelector(".mw").textContent = `${dc.capacity_mw.toLocaleString()} MW`;
    gauge.querySelector(".label").textContent = dc.capacity_use || "Capacity";
  } else {
    gauge.style.display = "none";
  }

  // Timeline
  const tl = panel.querySelector(".timeline");
  tl.innerHTML = "";
  const isDone = (s) => dc.status === "operational" || dc.status === "retired" || s === "construction_start_date" || (dc.status === "under_construction" && s === "construction_start_date");
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

  // Sources
  const sources = panel.querySelector(".sources");
  sources.innerHTML = "";
  let urls = [];
  try { urls = JSON.parse(dc.source_urls || "[]"); } catch {}
  if (Array.isArray(urls) && urls.length) {
    urls.forEach(u => {
      const a = document.createElement("a");
      a.href = u; a.target = "_blank"; a.rel = "noopener"; a.textContent = u;
      sources.appendChild(a);
    });
  } else {
    sources.innerHTML = `<span style="color:var(--text-dim)">No sources yet</span>`;
  }

  panel.classList.add("open");

  // Fly the camera to the point
  if (globe) globe.pointOfView({ lat: dc.latitude, lng: dc.longitude, altitude: 1.5 }, 800);
}

function closeDetail() {
  document.getElementById("detail-panel").classList.remove("open");
}

// ---------- Country polygons ----------
function loadCountries() {
  fetch("countries.geojson")
    .then(r => r.json())
    .then(data => {
      globe
        .polygonsData(data.features)
        .polygonCapColor(() => "rgba(12, 22, 44, 0.55)")
        .polygonSideColor(() => "rgba(30, 60, 120, 0.12)")
        .polygonStrokeColor(() => "#1e3d6e")
        .polygonAltitude(0.001)
        .polygonLabel(d => `<div style="background:#11161f;border:1px solid #232a37;padding:4px 8px;border-radius:4px;font-family:sans-serif;font-size:11px;color:#8b97a8">${d.properties.NAME || d.properties.name || ""}</div>`);
    })
    .catch(() => {}); // silently skip if file not present locally
}

// ---------- Globe setup ----------
let globe;
try {
  globe = Globe()
    (document.getElementById("globe-container"))
    .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")
    .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
    .backgroundColor("#00000000")
    // Fix: data uses latitude/longitude, not lat/lng
    .pointLat(d => d.latitude)
    .pointLng(d => d.longitude)
    .pointAltitude(d => Math.max(0.02, Math.min(0.10, (d.capacity_mw || 200) / 22000)))
    .pointRadius(d => 0.45 + Math.min(1.4, (d.capacity_mw || 200) / 1800))
    .pointColor(d => STATUS_COLOR[d.status] || "#888")
    .pointLabel(d => `
      <div style="background:#11161f;border:1px solid #232a37;padding:8px 10px;border-radius:6px;font-family:sans-serif;font-size:12px;color:#e6edf3;max-width:260px">
        <div style="font-weight:600;margin-bottom:2px">${d.name}</div>
        <div style="color:#8b97a8">${d.operator} · ${STATUS_LABEL[d.status] || d.status}</div>
        ${d.capacity_mw ? `<div style="color:#4cc2ff;margin-top:4px">${d.capacity_mw.toLocaleString()} MW</div>` : ""}
      </div>
    `)
    .onPointClick(d => openDetail(d))
    // Pulsing rings for under-construction and planned sites
    .ringLat(d => d.latitude)
    .ringLng(d => d.longitude)
    .ringColor(d => STATUS_COLOR[d.status] || "#888")
    .ringMaxRadius(3.5)
    .ringPropagationSpeed(1.2)
    .ringRepeatPeriod(1400)
    .atmosphereColor("#4cc2ff")
    .atmosphereAltitude(0.28);

  globe.controls().autoRotate = true;
  globe.controls().autoRotateSpeed = 0.35;
  document.getElementById("globe-container").addEventListener("mousedown", () => {
    globe.controls().autoRotate = false;
  }, { once: true });

  loadCountries();

  // Three.js starfield injected into the globe's scene
  if (typeof THREE !== "undefined") {
    const count = 4000;
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
    const mat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.6, transparent: true, opacity: 0.75 });
    globe.scene().add(new THREE.Points(geo, mat));
  }
} catch (e) {
  console.error("Globe init failed:", e);
  document.getElementById("globe-container").innerHTML =
    `<div style="color:#8b97a8;padding:40px;text-align:center">Globe failed to load. Check console for details.</div>`;
}

// ---------- Filter UI ----------
function buildFilters() {
  const operators = [...new Set(state.data.map(d => d.operator))].sort();
  const opBox = document.getElementById("filter-operators");
  opBox.innerHTML = "";
  operators.forEach(op => {
    const id = `op-${op.replace(/\s+/g, "-")}`;
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" id="${id}" checked /><span>${op}</span>`;
    opBox.appendChild(label);
    label.querySelector("input").addEventListener("change", e => {
      if (e.target.checked) state.filteredOperators.delete(op);
      else state.filteredOperators.add(op);
      // We invert: an empty set means "all operators"
      // Rebuild as: keep set of allowed operators
      const allowed = operators.filter(o => document.getElementById(`op-${o.replace(/\s+/g, "-")}`).checked);
      state.filteredOperators = new Set(allowed.length === operators.length ? [] : allowed);
      refreshGlobe();
    });
  });

  const statuses = ["operational", "under_construction", "planned"];
  const stBox = document.getElementById("filter-statuses");
  stBox.innerHTML = "";
  statuses.forEach(st => {
    const id = `st-${st}`;
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" id="${id}" checked />
      <span class="dot" style="background:${STATUS_COLOR[st]}"></span>
      <span>${STATUS_LABEL[st]}</span>`;
    stBox.appendChild(label);
    label.querySelector("input").addEventListener("change", e => {
      if (e.target.checked) state.filteredStatuses.add(st);
      else state.filteredStatuses.delete(st);
      refreshGlobe();
    });
  });
}

document.getElementById("search").addEventListener("input", e => {
  state.search = e.target.value;
  refreshGlobe();
});

document.getElementById("close-detail").addEventListener("click", closeDetail);
document.addEventListener("keydown", e => { if (e.key === "Escape") closeDetail(); });

// Init
buildFilters();
refreshGlobe();
