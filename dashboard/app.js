// Nightlight console: Map (ranked homes), Device (the real box, live), Crew (brief + check-ins).
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const motion = !!window.gsap && !matchMedia("(prefers-reduced-motion: reduce)").matches;
const icons = () => window.lucide && lucide.createIcons();
if (window.gsap && window.Flip) gsap.registerPlugin(Flip);
const risk = r => css(r >= 80 ? "--risk-crit" : r >= 55 ? "--risk-high" : r >= 30 ? "--risk-mid" : "--risk-low");
const hrs = m => (m / 60).toFixed(1);
const REAL_UNIT = 1;

// ---------- theme ----------
const darkNow = () => document.documentElement.dataset.theme
  ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
function paintThemeButton() {
  const d = darkNow();
  $("theme").innerHTML = `<i data-lucide="${d ? "sun" : "moon"}"></i>`;
  $("theme").setAttribute("aria-label", d ? "Switch to light mode" : "Switch to dark mode");
  icons();
}
$("theme").onclick = () => {
  const next = darkNow() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("nl-theme", next); } catch (e) {}
  paintThemeButton(); refresh(); drawDevice();
};

// ---------- tabs (segmented control, hash-routed) ----------
const TABS = ["map", "device", "crew"];
function movePill(animate) {
  const btn = document.querySelector('.tabs button[aria-selected="true"]'), pill = document.querySelector(".tab-pill");
  const to = { x: btn.offsetLeft - 3, width: btn.offsetWidth };
  if (motion && animate) gsap.to(pill, { ...to, duration: 0.35, ease: "power3.out" });
  else if (window.gsap) gsap.set(pill, to);
  else Object.assign(pill.style, { width: to.width + "px", transform: `translateX(${to.x}px)` });
}
function show(tab, animate = true) {
  if (!TABS.includes(tab)) tab = "map";
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
  TABS.forEach(t => { $("view-" + t).hidden = t !== tab; });
  movePill(animate);
  if (tab === "map") setTimeout(() => map.invalidateSize(), 0);
  if (tab === "device") loadDevice();
  if (motion && animate) gsap.fromTo("#view-" + tab, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: 0.3, ease: "power3.out", clearProps: "opacity,transform" });
}
document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => { location.hash = b.dataset.tab; });
addEventListener("hashchange", () => show(location.hash.slice(1)));
addEventListener("resize", () => { movePill(false); drawDevice(); });

// ---------- map ----------
const map = L.map("map", { zoomControl: true }).setView([26.62, -82.13], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap" }).addTo(map);
const layer = L.layerGroup().addTo(map);
map.createPane("hubs").style.zIndex = 350;   // under the home markers (overlayPane = 400)
const hubLayer = L.layerGroup().addTo(map);
const rippleLayer = L.layerGroup().addTo(map);
let prev = {};   // unit_id -> {risk, grid, sos} from the last refresh, to animate what changed
let why = {};    // unit_id -> Nemotron Nano one-liner (wording only; rank is the scorer's)
let lastHomes = [];

// A ring that pulses out of a home on the map when it loses power or calls SOS.
function ripple(h) {
  if (!motion) return;
  const ring = L.circleMarker([h.lat, h.lon], { radius: 11, color: css("--bad"), weight: 2, fill: false, interactive: false }).addTo(rippleLayer);
  const s = { r: 11, a: 0.9 };
  gsap.to(s, { r: 44, a: 0, duration: 1.3, ease: "power2.out", repeat: 1,
    onUpdate: () => { ring.setRadius(s.r); ring.setStyle({ opacity: s.a }); },
    onComplete: () => rippleLayer.removeLayer(ring) });
}

const ago = s => s < 90 ? `${s}s` : s < 5400 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`;
const seenTag = h => h.synthetic ? '<span class="sim">SIMULATED</span>' : h.last_seen_s > 30
  ? `<span class="stale">offline ${ago(h.last_seen_s)}</span>` : '<span class="live">live</span>';
const unsafeIn = v => v == null ? "–" : v === 0 ? '<b class="off">now</b>' : `${v} h`;

// One <tbody> per home: the numbers, then the scorer's reasons (and Nano's wording) full width underneath.
const homeRows = (h, rank) => `<tbody class="home${h.sos ? " sosrow" : ""}${h.synthetic ? "" : " real"}" data-flip-id="u${h.unit_id}">
  <tr><td>${rank}</td><td><b>${h.unit_id}</b></td>
    <td class="risk" style="color:${risk(h.risk)}"><b>${h.risk.toFixed(1)}</b></td>
    <td>${h.grid_present ? "on" : '<b class="off">OFF</b>'}</td><td>${h.heat_index_f.toFixed(1)}</td>
    <td class="opt">${h.grid_present ? "–" : hrs(h.min_dark)}</td><td class="opt">${hrs(h.min_since_motion)}</td>
    <td>${unsafeIn(h.hours_to_unsafe)}</td></tr>
  <tr class="reasons"><td></td><td colspan="7">${seenTag(h)}
    ${(h.reasons_plain || h.top_reasons || []).map(r => `<span class="rs">${r === "SOS pressed" ? '<b class="off">SOS pressed</b>' : esc(r)}</span>`).join(" · ") || "no risk factors yet"}
    ${why[h.unit_id] ? `<div class="why">Nano: ${esc(why[h.unit_id])}</div>` : ""}</td></tr></tbody>`;

async function refresh() {
  let homes;
  try { homes = await (await fetch("/v1/homes")).json(); }
  catch (e) { $("status").textContent = "API unreachable"; return; }
  lastHomes = homes;
  layer.clearLayers();
  const real = homes.filter(h => !h.synthetic).length;
  const zips = [...new Set(homes.map(h => h.zip).filter(Boolean))].sort();
  $("status").textContent = (zips.length ? `ZIP${zips.length > 1 ? "s" : ""} ${zips.join(", ")} · ` : "") +
    `${homes.length} homes · ${real} real unit${real === 1 ? "" : "s"} · ${homes.length - real} simulated`;

  // Ranked table: top 50, plus any real unit below that (shown at its true rank).
  // Rows glide to their new rank (GSAP Flip).
  const rowsEl = $("rank"), TOP = 50;
  const pinned = homes.map((h, i) => [h, i + 1]).filter(([h, r]) => !h.synthetic && r > TOP);
  const before = motion && window.Flip ? Flip.getState(rowsEl.querySelectorAll("tbody.home")) : null;
  rowsEl.querySelectorAll("tbody").forEach(b => b.remove());
  rowsEl.insertAdjacentHTML("beforeend", homes.slice(0, TOP).map((h, i) => homeRows(h, i + 1)).join("") +
    (pinned.length ? `<tbody class="divider"><tr><td colspan="8">Real unit${pinned.length > 1 ? "s" : ""} below the top ${TOP}</td></tr></tbody>` : "") +
    pinned.map(([h, r]) => homeRows(h, r)).join("") ||
    '<tbody><tr><td colspan="8" class="empty">No homes yet. Start the box or run the simulator.</td></tr></tbody>');
  if (before) Flip.from(before, { targets: rowsEl.querySelectorAll("tbody.home"), duration: 0.6, ease: "power3.out" });
  if (motion) homes.forEach(h => {
    const p = prev[h.unit_id], row = rowsEl.querySelector(`[data-flip-id="u${h.unit_id}"]`);
    if (!p || !row) return;
    if (p.risk !== h.risk) {   // count the risk number to its new value
      const b = row.querySelector(".risk b"), n = { v: p.risk };
      gsap.to(n, { v: h.risk, duration: 0.8, ease: "power3.out", onUpdate: () => { b.textContent = n.v.toFixed(1); } });
    }
    if ((p.grid && !h.grid_present) || (!p.sos && h.sos)) {   // grid just cut or SOS just pressed
      gsap.fromTo(row, { backgroundColor: css("--bad-flash") }, { backgroundColor: h.sos ? css("--bad-soft") : css("--panel"), duration: 1.6, ease: "power2.out", clearProps: "backgroundColor" });
      ripple(h);
    }
  });
  prev = Object.fromEntries(homes.map(h => [h.unit_id, { risk: h.risk, grid: h.grid_present, sos: h.sos }]));

  // Markers: simulated first, real units last so the real one is always on top.
  [...homes].sort((a, b) => (b.synthetic - a.synthetic) || (a.risk - b.risk)).forEach(h => L.circleMarker([h.lat, h.lon], {
      radius: h.synthetic ? 5 : 11, color: h.grid_present ? risk(h.risk) : css("--fg"),
      fillColor: risk(h.risk), weight: h.synthetic ? 1 : 3, fillOpacity: h.synthetic ? .6 : .9,
      dashArray: h.sos ? "4 3" : null })
    .bindPopup(`<b>Unit ${h.unit_id}</b> ${h.synthetic ? "(simulated)" : "(real unit)"}` +
               `${h.zip ? ` · ZIP ${h.zip}` : ""}<br>risk ${h.risk}` +
               `${h.sos ? " · <b>SOS</b>" : ""}<br>HI ${h.heat_index_f} °F · grid ${h.grid_present ? "on" : "OFF"}` +
               `${h.grid_present ? "" : ` · dark ${hrs(h.min_dark)} h`} · still ${hrs(h.min_since_motion)} h` +
               `<br>battery ${h.battery_known ? h.battery_pct + "%" : "unknown"}`)
    .addTo(layer));

  // Crew tab: the first homes to reach, straight from the scorer.
  $("crewTop").innerHTML = homes.slice(0, 6).map((h, i) => `<li><span class="n">${i + 1}</span>
    <span>Unit ${h.unit_id} ${h.synthetic ? '<span class="sim">SIMULATED</span>' : '<span class="live">real</span>'}
      <div class="d">${h.zip ? `ZIP ${h.zip} · ` : ""}${h.sos ? "SOS · " : ""}${h.grid_present ? "grid on" : `dark ${hrs(h.min_dark)} h`} · HI ${h.heat_index_f} °F</div></span>
    <span class="r" style="color:${risk(h.risk)}">${h.risk.toFixed(1)}</span></li>`).join("") || '<li class="empty">No homes yet.</li>';
}

// ---------- device tab: the one real box ----------
let devRows = [];
async function loadDevice() {
  try { devRows = await (await fetch(`/v1/history?unit_id=${REAL_UNIT}&limit=120`)).json(); } catch (e) { return; }
  drawDevice();
}
const tfmt = t => new Date(t * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
function drawDevice() {
  if ($("view-device").hidden) return;
  const r = devRows, last = r[r.length - 1];
  const age = last ? Math.round(Date.now() / 1000 - last.received) : null;
  $("devState").innerHTML = !last ? '<span class="sim">no packets yet</span>'
    : age > 30 ? `<span class="stale">offline ${ago(age)}</span>` : '<span class="live">live</span>';
  $("readings").innerHTML = !last ? "" : [
    ["thermometer", "Temperature", last.temp_f, "°F"], ["droplets", "Humidity", last.humidity_pct, "%"],
    ["sun", "Heat index", last.heat_index_f, "°F"],
    ["plug", "Wall power", last.grid_present ? "On" : '<span class="off">Off</span>', ""],
    ["siren", "SOS", last.sos ? '<span class="off">Active</span>' : "None", ""],
    ["radio", "Packets shown", r.length, ""]]
    .map(([ic, l, v, u]) => `<div class="reading"><div class="l"><i data-lucide="${ic}"></i>${l}</div><div class="v">${v}${u ? `<small>${u}</small>` : ""}</div></div>`).join("");
  icons();
  lineChart($("chTemp").querySelector(".plot"), r, [["Temperature", "temp_f", "--series-1", "°F"], ["Heat index", "heat_index_f", "--series-2", "°F"]]);
  lineChart($("chHum").querySelector(".plot"), r, [["Humidity", "humidity_pct", "--series-1", "%"]]);
  gridStrip($("chGrid").querySelector(".plot"), r);
  $("logRows").innerHTML = r.slice(-12).reverse().map(p => `<tr><td>${tfmt(p.received)}</td><td>${p.seq}</td><td>${p.hex}</td>
    <td>${p.temp_f}</td><td>${p.humidity_pct}</td><td>${p.grid_present ? "on" : '<b class="off">OFF</b>'}</td><td>${p.sos ? '<b class="off">SOS</b>' : "–"}</td></tr>`).join("")
    || '<tr><td colspan="7" class="empty">No packets from the box yet.</td></tr>';
}

// Line chart: thin lines, recessive grid, end labels, crosshair tooltip. One unit per chart.
function lineChart(el, rows, series) {
  const W = el.clientWidth, H = el.clientHeight, m = { l: 36, r: 64, t: 8, b: 22 };
  if (rows.length < 2 || W < 50) { el.innerHTML = '<div class="empty">Waiting for packets from the box…</div>'; return; }
  const xs = rows.map(p => p.received), t0 = xs[0], t1 = xs[xs.length - 1] || t0 + 1;
  const vals = series.flatMap(([, k]) => rows.map(p => p[k]));
  // Three equal whole-number steps, so tick labels are evenly spaced (not 45, 47, 48, 50).
  const vmin = Math.min(...vals), vmax = Math.max(...vals), step = Math.max(1, Math.ceil((vmax - vmin + 2) / 3));
  const lo = Math.floor(vmin - 1 - (3 * step - (vmax - vmin + 2)) / 2), hi = lo + 3 * step;
  const X = t => m.l + (t - t0) / Math.max(1, t1 - t0) * (W - m.l - m.r), Y = v => m.t + (hi - v) / (hi - lo) * (H - m.t - m.b);
  const ticks = [0, 1, 2, 3].map(i => lo + step * i);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${series.map(s => s[0]).join(" and ")} over time">`;
  ticks.forEach(v => { svg += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text class="axis" x="${m.l - 8}" y="${Y(v) + 4}" text-anchor="end">${Math.round(v)}</text>`; });
  [t0, (t0 + t1) / 2, t1].forEach((t, i) => { svg += `<text class="axis" x="${X(t)}" y="${H - 4}" text-anchor="${["start", "middle", "end"][i]}">${new Date(t * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</text>`; });
  const ends = [];
  series.forEach(([name, k, col]) => {
    const c = css(col), d = rows.map((p, i) => `${i ? "L" : "M"}${X(p.received).toFixed(1)},${Y(p[k]).toFixed(1)}`).join("");
    const lp = rows[rows.length - 1];
    svg += `<path d="${d}" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    svg += `<circle cx="${X(lp.received)}" cy="${Y(lp[k])}" r="4" fill="${c}" stroke="${css("--panel")}" stroke-width="2"/>`;
    ends.push([Y(lp[k]), `${lp[k]}`]);
  });
  ends.sort((a, b) => a[0] - b[0]).forEach(([y], i, arr) => { if (i && y - arr[i - 1][0] < 14) arr[i][0] = arr[i - 1][0] + 14; });
  ends.forEach(([y, t]) => { svg += `<text x="${W - m.r + 10}" y="${y + 4}" fill="${css("--fg")}" font-size="12" font-weight="600">${t}</text>`; });
  svg += `<line class="xh" x1="0" x2="0" y1="${m.t}" y2="${H - m.b}" stroke="${css("--muted")}" stroke-dasharray="3 3" visibility="hidden"/>`;
  svg += `<rect x="${m.l}" y="0" width="${W - m.l - m.r}" height="${H}" fill="transparent"/></svg>`;
  el.innerHTML = svg;
  const xh = el.querySelector(".xh"), tip = $("tip");
  el.querySelector("rect").onpointermove = e => {
    const bx = el.getBoundingClientRect(), px = e.clientX - bx.left;
    let i = 0, best = Infinity; rows.forEach((p, j) => { const d = Math.abs(X(p.received) - px); if (d < best) { best = d; i = j; } });
    const p = rows[i], x = X(p.received);
    xh.setAttribute("x1", x); xh.setAttribute("x2", x); xh.setAttribute("visibility", "visible");
    tip.innerHTML = `<b>${tfmt(p.received)}</b><br>` + series.map(([n, k, col, u]) => `<i style="background:${css(col)}"></i>${n} ${p[k]} ${u}`).join("<br>");
    tip.hidden = false;
    tip.style.left = Math.min(innerWidth - tip.offsetWidth - 8, e.clientX + 14) + "px"; tip.style.top = (e.clientY - tip.offsetHeight - 12) + "px";
  };
  el.querySelector("rect").onpointerleave = () => { xh.setAttribute("visibility", "hidden"); tip.hidden = true; };
}

// Grid strip: on = quiet gray, off = red with a label. Same time window as the charts.
function gridStrip(el, rows) {
  const W = el.clientWidth, H = el.clientHeight, m = { l: 36, r: 64 };
  if (rows.length < 2 || W < 50) { el.innerHTML = '<div class="empty">Waiting for packets…</div>'; return; }
  const t0 = rows[0].received, t1 = rows[rows.length - 1].received;
  const X = t => m.l + (t - t0) / Math.max(1, t1 - t0) * (W - m.l - m.r);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Wall power on and off over time">`;
  for (let i = 0, j; i < rows.length - 1; i = j) {
    for (j = i + 1; j < rows.length - 1 && rows[j].grid_present === rows[i].grid_present; j++);
    const on = rows[i].grid_present, x = X(rows[i].received), w = Math.max(2, X(rows[j].received) - x - 2);
    svg += `<rect x="${x}" y="6" width="${w}" height="24" rx="4" fill="${css(on ? "--grid-on" : "--bad")}"><title>${on ? "Power on" : "Power OFF"} · ${tfmt(rows[i].received)} – ${tfmt(rows[j].received)}</title></rect>`;
    if (!on && w > 34) svg += `<text x="${x + 8}" y="22" fill="#fff" font-size="11" font-weight="700">OFF</text>`;
  }
  svg += `<text class="axis" x="${m.l}" y="${H - 4}">${tfmt(t0)}</text><text class="axis" x="${W - m.r}" y="${H - 4}" text-anchor="end">${tfmt(t1)}</text></svg>`;
  el.innerHTML = svg;
}

// ---------- actions ----------
$("brief").onclick = async () => {
  const btn = $("brief"), out = $("briefOut"), label = btn.querySelector("span");
  btn.disabled = true; label.textContent = "Writing…"; $("briefEmpty").hidden = true;
  out.textContent = "Asking Nemotron…";
  try {
    const b = await (await fetch("/v1/brief")).json();
    // The prompt asks for plain text; strip any markdown that slips through anyway.
    const text = b.brief.replace(/\*\*/g, "").replace(/^#+\s*/gm, "").replace(/\n{3,}/g, "\n\n").trim();
    out.textContent = (b.source === "nemotron" ? "Nemotron crew brief (ranking from scorer):\n\n" : "") + text;
    if (motion) gsap.from(out, { opacity: 0, y: 6, duration: 0.35, ease: "power3.out", clearProps: "opacity,transform" });
  } catch (e) { out.textContent = "Brief failed: " + e; }
  finally { btn.disabled = false; label.textContent = "Write brief (Nemotron)"; }
};

$("triage").onclick = async () => {
  const btn = $("triage"), label = btn.querySelector("span");
  btn.disabled = true; label.textContent = "Asking Nano…";
  try { why = (await (await fetch("/v1/triage?top=20")).json()).why || {}; await refresh(); }
  catch (e) { $("status").textContent = "Nano explanations failed; ranking unchanged"; }
  finally { btn.disabled = false; label.textContent = "Explain top 20 (Nano)"; }
};

$("checkin").onsubmit = async e => {
  e.preventDefault();
  const out = $("ciOut");
  const text = $("ciText").value.trim();
  if (!text) { out.textContent = "Type the resident's message first."; return; }
  out.textContent = "Parsing…";
  try {
    const r = await fetch("/v1/checkin", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_id: +$("ciUnit").value, text }) });
    const b = await r.json();
    out.textContent = r.ok ? JSON.stringify(b, null, 2) : (typeof b.detail === "string" ? b.detail : "Check-in rejected: check the unit id.");
  } catch (err) { out.textContent = "Check-in failed: API unreachable"; }
};

// ---------- simulation results (one series, one hue, direct labels) ----------
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
  $("simPanel").hidden = false;
  $("simTiles").innerHTML = tiles.map(([v, l, tag]) =>
    `<div class="tile"><span class="sim">${tag}</span><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  if (r) {
    const max = Math.max(r.biggest_first, r.nightlight);
    const bar = (label, v) => `<div class="bar" title="${label}: ${fmt(v)} weighted person-hours">
      <span class="bl">${label}</span><span class="track"><span class="fill" style="width:${100 * v / max}%"></span></span>
      <span class="bv">${fmt(v)}</span></div>`;
    const el = $("simBars");
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

// ---------- start ----------
icons(); paintThemeButton();
show(location.hash.slice(1) || "map", false);
if (motion) gsap.from("header > *", { opacity: 0, y: -4, duration: 0.5, ease: "power3.out", stagger: 0.05, clearProps: "opacity,transform" });
refresh(); loadSim();
setInterval(() => { refresh(); if (!$("view-device").hidden) loadDevice(); }, 2000);   // 2 s: an SOS shows up fast
