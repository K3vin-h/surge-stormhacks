// Shared helpers for the SURGE government workspace and resident app.
// Served same-origin by FastAPI, so the API base is just "".

const AREAS = ["sunsari", "saptari", "bardiya", "kathmandu_valley"];
const AREA_LABELS = {
  sunsari: "Sunsari",
  saptari: "Saptari",
  bardiya: "Bardiya",
  kathmandu_valley: "Kathmandu Valley",
};

// Rough area centers [lat, lng] for map defaults.
const AREA_CENTERS = {
  sunsari: [26.627, 87.182],
  saptari: [26.616, 86.998],
  bardiya: [28.3, 81.433],
  kathmandu_valley: [27.709, 85.324],
};

function deviceId() {
  let id = localStorage.getItem("surge_device_id");
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) ||
      "dev-" + Math.random().toString(36).slice(2);
    localStorage.setItem("surge_device_id", id);
  }
  return id;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = (body && body.error && body.error.message) || JSON.stringify(body);
    } catch (_) {}
    throw new Error(`${res.status} ${path} ${detail}`.trim());
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

// Resolve the browser's geolocation as {lat, lng}. Only called on an action.
function getLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("No geolocation"));
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      (e) => reject(e),
      { enableHighAccuracy: true, timeout: 8000 }
    );
  });
}

function distanceKm(a, b) {
  const rad = (d) => (d * Math.PI) / 180;
  const dLat = rad(b[0] - a[0]);
  const dLng = rad(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

// Nearest monitored area to {lat, lng}, or null when none is within maxKm.
function nearestArea(loc, maxKm = 75) {
  let best = null;
  for (const id of AREAS) {
    const km = distanceKm([loc.lat, loc.lng], AREA_CENTERS[id]);
    if (km <= maxKm && (!best || km < best.km)) best = { id, km };
  }
  return best;
}

// Resolves to { area, reason } where reason is "detected" | "outside" | "unavailable".
async function detectArea() {
  try {
    const loc = await getLocation();
    const hit = nearestArea(loc);
    return { area: hit ? hit.id : null, loc, reason: hit ? "detected" : "outside" };
  } catch (_) {
    return { area: null, loc: null, reason: "unavailable" };
  }
}

const AREA_HINTS = {
  detecting: "Detecting your location…",
  detected: "Detected from your location",
  outside: "You’re outside the monitored areas. Select an area.",
  unavailable: "Location unavailable. Select an area.",
  manual: "Selected manually",
};

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

let toastTimer;
function toast(message, { error = false } = {}) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    el.setAttribute("role", "status");
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.toggle("error", error);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

// ---- Labels -------------------------------------------------------------

const RISK = {
  severe:   { label: "Extreme",  tone: "red" },
  high:     { label: "High",     tone: "orange" },
  moderate: { label: "Moderate", tone: "olive" },
  low:      { label: "Low",      tone: "teal" },
};

const PRIORITY = {
  critical: { label: "Priority 1", note: "Review now",        tone: "red" },
  high:     { label: "Priority 2", note: "Review soon",       tone: "orange" },
  moderate: { label: "Priority 3", note: "Monitor",           tone: "olive" },
  low:      { label: "Priority 4", note: "Routine",           tone: "teal" },
};

const INSTRUCTION = {
  evacuate:         { label: "Evacuate",         icon: "arrowRight", tone: "red" },
  shelter_in_place: { label: "Shelter in Place", icon: "home",       tone: "orange" },
  advisory:         { label: "Advisory",         icon: "alert",      tone: "olive" },
  all_clear:        { label: "All Clear",        icon: "check",      tone: "teal" },
};

const REPORT_KIND = {
  road_hazard:   { label: "Road blocked",          icon: "road",  tone: "orange" },
  rescue_needed: { label: "Rescue needed",         icon: "sos",   tone: "red" },
  rescue_seen:   { label: "Person needing help",   icon: "eye",   tone: "violet" },
};

const VERIFICATION = {
  unverified: "Unverified",
  reviewed: "Reviewed",
  actioned: "Actioned",
  resolved: "Resolved",
  duplicate: "Duplicate",
  false_report: "False report",
};

function riskInfo(level) { return RISK[level] || { label: level || "Unknown", tone: "neutral" }; }
function priorityInfo(level) { return PRIORITY[level] || { label: level || "—", note: "", tone: "neutral" }; }
function instructionInfo(type) { return INSTRUCTION[type] || { label: type || "—", icon: "alert", tone: "neutral" }; }
function reportInfo(kind) { return REPORT_KIND[kind] || { label: kind, icon: "alert", tone: "neutral" }; }

function damageLabel(pct) {
  if (pct >= 60) return "Widespread";
  if (pct >= 35) return "Significant";
  if (pct >= 15) return "Localized";
  return "Minimal";
}

function pill(text, tone, { dot = true } = {}) {
  return `<span class="pill tone-${tone}">${dot ? '<i class="dot"></i>' : ""}${esc(text)}</span>`;
}

// ---- Time ---------------------------------------------------------------

function fmtClock(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function fmtDay(iso) {
  const d = new Date(iso);
  const now = new Date();
  if (sameDay(d, now)) return "Today";
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (sameDay(d, y)) return "Yesterday";
  return d.toLocaleDateString([], { day: "numeric", month: "short" });
}

function fmtWhen(iso) {
  if (!iso) return "—";
  return `${fmtDay(iso)}, ${fmtClock(iso)}`;
}

function fmtNumber(n) {
  return typeof n === "number" ? n.toLocaleString("en-US") : "—";
}

// ---- Icons (inline SVG, stroke = currentColor) --------------------------

const ICON_PATHS = {
  home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
  map: '<path d="M9 3 3 6v15l6-3 6 3 6-3V3l-6 3-6-3z"/><path d="M9 3v15"/><path d="M15 6v15"/>',
  alert: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 9h8"/><path d="M8 13h5"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  road: '<path d="M4 21 8 3"/><path d="M20 21 16 3"/><path d="M12 5v2"/><path d="M12 11v2"/><path d="M12 17v2"/>',
  plus: '<path d="M12 5v14"/><path d="M5 12h14"/>',
  hospital: '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"/>',
  waves: '<path d="M2 9c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M2 15c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/>',
  satellite: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16"/>',
  exclaim: '<path d="M12 5v9"/><path d="M12 19h.01"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><path d="M12 18v4"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  send: '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  broadcast: '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49"/><path d="M7.76 16.24a6 6 0 0 1 0-8.49"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/><path d="M4.93 19.07a10 10 0 0 1 0-14.14"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  sos: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><path d="m4.93 4.93 4.24 4.24"/><path d="m14.83 14.83 4.24 4.24"/><path d="m14.83 9.17 4.24-4.24"/><path d="m4.93 19.07 4.24-4.24"/>',
  route: '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  phone: '<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/>',
  monitor: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/>',
  locate: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="M2 12h3"/><path d="M19 12h3"/><circle cx="12" cy="12" r="7"/>',
  sparkle: '<path d="M12 3v4"/><path d="M12 17v4"/><path d="M3 12h4"/><path d="M17 12h4"/><path d="m6 6 2 2"/><path d="m16 16 2 2"/><path d="m6 18 2-2"/><path d="m16 8 2-2"/>',
};

function icon(name, size = 18, strokeWidth = 1.8) {
  return `<svg class="icon" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name] || ""}</svg>`;
}

// Resolved against this script so pages in subfolders (rasuwa/) find the same files.
const BRAND_BASE = new URL("assets/brand/", (document.currentScript && document.currentScript.src) || location.href).href;
const LOGO_SVG = `<img class="emblem" src="${BRAND_BASE}emblem.png" alt="" aria-hidden="true">`;

// The brand's final E is three bars; the lower two are sage and the last one tapers to a point.
function wordmark({ tagline = false } = {}) {
  const e = `<svg class="wm-e" viewBox="0 0 66 70" width="0.66em" height="0.7em" aria-hidden="true">
    <rect width="66" height="12.5" fill="currentColor"/>
    <rect y="28.75" width="53" height="12.5" fill="#6f8462"/>
    <path d="M0 57.5h54l12 6.25-12 6.25H0z" fill="#6f8462"/></svg>`;
  return `<span class="wordmark" aria-label="SURGE"><span class="wm-word" aria-hidden="true">SURG${e}</span>${
    tagline ? `<span class="wm-tag">Flood Response Intelligence</span>` : ""}</span>`;
}

(function brandFavicon() {
  if (document.querySelector('link[rel="icon"]')) return;
  const link = document.createElement("link");
  link.rel = "icon";
  link.type = "image/png";
  link.href = `${BRAND_BASE}favicon.png`;
  document.head.appendChild(link);
})();

// ---- Map helpers (Leaflet) ----------------------------------------------

// Pass { controls: false } when the page shows OSM attribution itself.
function baseMap(el, center, zoom = 12, { controls = true } = {}) {
  const map = L.map(el, { zoomControl: false, attributionControl: controls }).setView(center, zoom);
  if (controls) {
    L.control.zoom({ position: "bottomright" }).addTo(map);
    map.attributionControl.setPrefix("");
  }
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "© OpenStreetMap contributors",
  }).addTo(map);
  return map;
}

function pinIcon(kind, size = 30) {
  const glyph = {
    shelter: icon("plus", 15, 3),
    hospital: icon("hospital", 13, 2.2),
    closure: icon("x", 14, 3),
    road_hazard: icon("road", 14, 2.4),
    rescue_needed: '<b>SOS</b>',
    rescue_seen: icon("eye", 14, 2.4),
    me: "",
  }[kind] || "";
  return L.divIcon({
    html: `<div class="map-pin pin-${kind}" style="width:${size}px;height:${size}px">${glyph}</div>`,
    className: "map-pin-wrap",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function latLng(point) {
  return point && point.coordinates ? [point.coordinates[1], point.coordinates[0]] : null;
}

// Approved route drawn as a white-cased amber dashed line, as on the paper maps.
function drawRoute(layer, geometry, popup) {
  if (!geometry || !geometry.coordinates) return null;
  const coords = geometry.coordinates.map((c) => [c[1], c[0]]);
  L.polyline(coords, { color: "#fbfaf5", weight: 10, opacity: 0.95, lineCap: "round" }).addTo(layer);
  const line = L.polyline(coords, { color: "#b8742f", weight: 5, dashArray: "10 9", lineCap: "round" }).addTo(layer);
  if (popup) line.bindPopup(popup);
  return line;
}

const RISK_FILL = { severe: "#a33b32", high: "#b2652a", moderate: "#7d8a3a", low: "#3f7a6e" };

function drawAreaZone(layer, geometry, riskLevel) {
  if (!geometry) return null;
  const color = RISK_FILL[riskLevel] || "#8a8f82";
  return L.geoJSON(geometry, {
    style: { color, weight: 1.5, dashArray: "4 6", fillColor: color, fillOpacity: 0.06 },
    interactive: false,
  }).addTo(layer);
}

function legendHtml() {
  return `<div class="map-legend">
    <span><i class="lg lg-shelter">${icon("plus", 9, 3.4)}</i>Shelter</span>
    <span><i class="lg lg-closure">${icon("x", 9, 3.4)}</i>Closure</span>
    <span><i class="lg lg-route"></i>Approved route</span>
  </div>`;
}

// ---- Legacy helpers kept for compatibility ------------------------------

function emojiIcon(emoji, size = 26) {
  return L.divIcon({
    html: `<div style="font-size:${size}px;line-height:${size}px">${emoji}</div>`,
    className: "emoji-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const MARKERS = {
  shelter: "🏠",
  hospital: "➕",
  sos: "🆘",
  road_hazard: "🚧",
  rescue_seen: "👁️",
  closed_road: "❌",
  me: "📍",
};

function reportEmoji(kind) {
  if (kind === "rescue_needed") return MARKERS.sos;
  if (kind === "rescue_seen") return MARKERS.rescue_seen;
  return MARKERS.road_hazard;
}
