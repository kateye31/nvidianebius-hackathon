const map = L.map("map").setView([26.62, -82.13], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  { attribution: "© OpenStreetMap" }).addTo(map);
const layer = L.layerGroup().addTo(map);
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
    <td>${h.sos ? '<b class="off">SOS</b> · ' : ""}${h.top_reasons.join(", ")}</td></tr>`).join("");
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

refresh(); setInterval(refresh, 5000);
