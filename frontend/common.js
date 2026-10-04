// Shared helpers for the bare-bones SURGE frontend.
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
    try { detail = JSON.stringify(await res.json()); } catch (_) {}
    throw new Error(`${res.status} ${path} ${detail}`);
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

// Emoji marker via Leaflet divIcon.
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
