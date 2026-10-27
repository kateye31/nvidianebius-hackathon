const map = L.map("map").setView([26.62, -82.13], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  { attribution: "© OpenStreetMap" }).addTo(map);
const layer = L.layerGroup().addTo(map);
const color = r => r >= 80 ? "#f85149" : r >= 55 ? "#f0883e" : r >= 30 ? "#d29922" : "#3fb950";

async function refresh() {
  const homes = await (await fetch("/v1/homes")).json();
  layer.clearLayers();
  const real = homes.filter(h => !h.synthetic).length;
  document.getElementById("status").textContent =
    `${homes.length} homes · ${real} real unit(s) · ${homes.length - real} simulated`;
  document.getElementById("rows").innerHTML = homes.slice(0, 50).map((h, i) => `
    <tr><td>${i + 1}</td><td>${h.unit_id}${h.synthetic ? ' <span class="sim">SIMULATED</span>' : ""}</td>
    <td style="color:${color(h.risk)}">${h.risk}</td><td>${h.heat_index_f}</td>
    <td>${h.hours_to_unsafe ?? "–"}</td><td>${h.top_reasons.join(", ")}${h.sos ? " · SOS" : ""}</td></tr>`).join("");
  homes.forEach(h => L.circleMarker([h.lat, h.lon], {
      radius: h.synthetic ? 5 : 10, color: color(h.risk), weight: h.synthetic ? 1 : 3, fillOpacity: .7 })
    .bindPopup(`Unit ${h.unit_id}${h.synthetic ? " (simulated)" : ""}<br>risk ${h.risk}<br>` +
               `HI ${h.heat_index_f} °F · dark ${h.min_dark} min · grid ${h.grid_present ? "on" : "OFF"}`)
    .addTo(layer));
}

document.getElementById("brief").onclick = async () => {
  const out = document.getElementById("briefOut");
  out.textContent = "Asking Nemotron…";
  try { out.textContent = (await (await fetch("/v1/brief")).json()).brief; }
  catch (e) { out.textContent = "Brief failed: " + e; }
};

refresh(); setInterval(refresh, 5000);
