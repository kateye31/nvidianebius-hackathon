const map = L.map("map").setView([26.62, -82.13], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  { attribution: "© OpenStreetMap" }).addTo(map);
const layer = L.layerGroup().addTo(map);
map.createPane("hubs").style.zIndex = 350;   // under the home markers (overlayPane = 400)
const hubLayer = L.layerGroup().addTo(map);
let why = {};   // unit_id -> Nemotron Nano one-liner (wording only; rank is the scorer's)
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const color = r => r >= 80 ? "#f85149" : r >= 55 ? "#f0883e" : r >= 30 ? "#d29922" : "#3fb950";

async function refresh() {
  let homes;
  try { homes = await (await fetch("/v1/homes")).json(); }
  catch (e) { document.getElementById("status").textContent = "API unreachable"; return; }
  layer.clearLayers();
  const real = homes.filter(h => !h.synthetic).length;
  document.getElementById("status").textContent =
    `${homes.length} homes · ${real} real unit(s) · ${homes.length - real} simulated`;
  const hrs = m => (m / 60).toFixed(1);
  const seen = h => h.synthetic ? "" : h.last_seen_s > 30
    ? ` <span class="stale">offline ${h.last_seen_s}s</span>` : ` <span class="live">live</span>`;
  document.getElementById("rows").innerHTML = homes.slice(0, 50).map((h, i) => `
    <tr class="${h.sos ? "sosrow" : ""}"><td>${i + 1}</td>
    <td>${h.unit_id}${h.synthetic ? ' <span class="sim">SIMULATED</span>' : seen(h)}</td>
    <td style="color:${color(h.risk)}"><b>${h.risk}</b></td>
    <td>${h.grid_present ? "on" : '<b class="off">OFF</b>'}</td><td>${h.heat_index_f}</td>
    <td>${h.grid_present ? "–" : hrs(h.min_dark)}</td><td>${hrs(h.min_since_motion)}</td>
    <td>${h.hours_to_unsafe ?? "–"}</td>
    <td>${h.sos ? '<b class="off">SOS</b> · ' : ""}${h.top_reasons.join(", ")}
      ${why[h.unit_id] ? `<div class="why">${esc(why[h.unit_id])}</div>` : ""}</td></tr>`).join("");
  // draw simulated first and real units last so the real unit is always on top
  [...homes].sort((a, b) => (b.synthetic - a.synthetic) || (a.risk - b.risk)).forEach(h => L.circleMarker([h.lat, h.lon], {
      radius: h.synthetic ? 5 : 11, color: h.grid_present ? color(h.risk) : "#000",
      fillColor: color(h.risk), weight: h.synthetic ? 1 : 3, fillOpacity: h.synthetic ? .6 : .9,
      dashArray: h.sos ? "4 3" : null })
    .bindPopup(`Unit ${h.unit_id}${h.synthetic ? " (simulated)" : " (real unit)"}<br>risk ${h.risk}` +
               `${h.sos ? " · <b>SOS</b>" : ""}<br>HI ${h.heat_index_f} °F · grid ${h.grid_present ? "on" : "OFF"}` +
               ` · dark ${hrs(h.min_dark)} h · still ${hrs(h.min_since_motion)} h` +
               `<br>battery ${h.battery_known ? h.battery_pct + "%" : "unknown"}`)
    .addTo(layer));
}

document.getElementById("brief").onclick = async () => {
  const out = document.getElementById("briefOut");
  out.textContent = "Asking Nemotron…";
  try {
    const b = await (await fetch("/v1/brief")).json();
    out.textContent = (b.source === "nemotron" ? "Nemotron crew brief (ranking from scorer):\n\n" : "") + b.brief;
  }
  catch (e) { out.textContent = "Brief failed: " + e; }
};

document.getElementById("triage").onclick = async e => {
  e.target.disabled = true; e.target.textContent = "Asking Nano…";
  try { why = (await (await fetch("/v1/triage?top=20")).json()).why || {}; await refresh(); }
  finally { e.target.disabled = false; e.target.textContent = "Explain top 20 (Nano)"; }
};

document.getElementById("checkin").onsubmit = async e => {
  e.preventDefault();
  const out = document.getElementById("ciOut");
  out.textContent = "Parsing…";
  const r = await fetch("/v1/checkin", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ unit_id: +document.getElementById("ciUnit").value,
                           text: document.getElementById("ciText").value }) });
  const b = await r.json();
  out.textContent = r.ok ? JSON.stringify(b, null, 2) : (b.detail || "failed");
};

// Simulation results: headline tiles + one comparison (one series, so one hue, direct labels).
const fmt = n => Math.round(n).toLocaleString();
async function loadSim() {
  let s;
  try { s = await (await fetch("/v1/sim")).json(); } catch { return; }
  const tiles = [], r = s.sim_result?.mean_weighted_person_hours;
  const SIM = "SIMULATED", REAL = "REAL DATA";
  if (r) tiles.push([`−${r.reduction_pct}%`, "weighted person-hours above 103 °F vs biggest-feeder-first", SIM]);
  if (s.hubs) tiles.push([`${Math.round(s.hubs.covered_share * 100)}%`, `of danger within ${s.hubs.params.radius_km} km of ${s.hubs.hubs.length} hubs`, SIM]);
  if (s.demand_response) tiles.push([`${s.demand_response.avg_mw_shaved} MW`, `shaved at the heat peak; ${s.demand_response.medical_homes_never_cycled} medical homes never cycled`, SIM]);
  const pm = s.predict_milton;
  if (pm?.mae_peak_pct_out != null) tiles.push([`${pm.mae_peak_pct_out} pts`,
    `MAE, peak % customers out, held-out Milton (baseline ${pm.baseline_mae_peak_pct_out})`, pm.simulated === false ? REAL : SIM]);
  if (!tiles.length) return;
  document.getElementById("simPanel").hidden = false;
  document.getElementById("simTiles").innerHTML = tiles.map(([v, l, tag]) =>
    `<div class="tile"><div class="sim">${tag}</div><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  if (r) {
    const max = Math.max(r.biggest_first, r.nightlight);
    const bar = (label, v) => `<div class="bar" title="${label}: ${fmt(v)} weighted person-hours">
      <span class="bl">${label}</span><span class="track"><span class="fill" style="width:${100 * v / max}%"></span></span>
      <span class="bv">${fmt(v)}</span></div>`;
    const el = document.getElementById("simBars");
    el.setAttribute("aria-label", `Biggest feeder first ${fmt(r.biggest_first)}, Nightlight order ${fmt(r.nightlight)} weighted person-hours`);
    el.innerHTML = `<div class="cap">SIMULATED · weighted person-hours above 103 °F (mean of ${s.sim_result.params.trials} runs)</div>` +
      bar("Biggest feeder first", r.biggest_first) + bar("Nightlight order", r.nightlight);
  }
  hubLayer.clearLayers();
  (s.hubs?.hubs || []).forEach((h, i) => L.marker([h.lat, h.lon], { pane: "hubs",
      icon: L.divIcon({ className: "hub", html: `H${i + 1}`, iconSize: [22, 22] }) })
    .bindPopup(`Hub ${i + 1} (simulated)<br>${h.new_homes} homes · ${h.medical_homes} medical<br>` +
               `${Math.round(h.share_of_danger * 100)}% of danger`).addTo(hubLayer));
}

refresh(); setInterval(refresh, 5000); loadSim();
