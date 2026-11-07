/* Experimental Search front end: mountain-peak view, health panel, list, lens editor. No build step. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const ZONES = ["core", "margin", "tail"];
  const ZONE_LABEL = { core: "Core", margin: "Margins", tail: "Long tail" };
  const WIDTH_LABEL = ["Core only", "Core + margins", "Core + margins + long tail"];
  const PALETTE = ["#2b5b96", "#c0622b", "#2f7a4c", "#7a4fa3", "#a8711a", "#1f8a8a", "#b0457a", "#6b7a8f", "#4f6f2a", "#8a5a2b"];
  let state = { data: null, lens: null, selected: null, opened: new Set(), slice: "source_type", width: 2 };

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (x) => `${Math.round(x * 100)}%`;
  function storage() { try { return window.localStorage; } catch (e) { return null; } }

  async function loadLenses() {
    const res = await fetch("/api/lenses");
    const { lenses } = await res.json();
    const saved = readSaved();
    const sel = $("lens");
    sel.innerHTML = lenses.map((l) => `<option value="${esc(l.id)}">${esc(l.name)}</option>`).join("") +
      Object.keys(saved).map((k) => `<option value="saved:${esc(k)}">${esc(saved[k].name)} (saved)</option>`).join("");
    await selectLens(sel.value);
  }
  function readSaved() { const s = storage(); if (!s) return {}; try { return JSON.parse(s.getItem("es.lenses") || "{}"); } catch (e) { return {}; } }

  async function selectLens(id) {
    if (id.startsWith("saved:")) state.lens = readSaved()[id.slice(6)];
    else state.lens = await (await fetch(`/api/lenses/${encodeURIComponent(id)}`)).json();
    $("lensPurpose").textContent = state.lens.purpose || "";
    $("lensJson").value = JSON.stringify(state.lens, null, 2);
    state.slice = state.lens.slice_by || "source_type";
    $("slice").value = state.slice;
    state.width = { core: 0, margin: 1, tail: 2 }[state.lens.width || "tail"];
    $("width").value = state.width; $("widthLabel").textContent = WIDTH_LABEL[state.width];
  }

  async function run(lensObj) {
    const q = $("q").value.trim();
    if (!q) return;
    $("go").disabled = true; $("go").textContent = "Searching…";
    try {
      const res = await fetch("/api/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q, lens: lensObj || state.lens, depth: 50 }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Search failed");
      state.data = data; state.selected = null; state.opened = new Set();
      render();
    } catch (e) {
      $("errors").hidden = false; $("errors").textContent = `Search failed: ${e.message}. Check the server is running.`;
    } finally { $("go").disabled = false; $("go").textContent = "Search"; }
  }

  function sliceOf(r) {
    if (state.slice === "source_type") return r.source_type;
    if (state.slice === "language") return r.language;
    const engs = Object.keys(r.engines);
    return engs.length === 1 ? engs[0] : "several engines";
  }

  function render() {
    const d = state.data;
    $("banner").hidden = !d.synthetic_sample;
    $("errors").hidden = !d.errors.length;
    $("errors").textContent = d.errors.map((e) => `${e.engine}: ${e.error}`).join(" · ");
    renderMountain(); renderHealth(); renderList(); renderDetail();
  }

  function visible(r) { return ZONES.indexOf(r.zone) <= state.width; }

  function renderMountain() {
    const svg = $("mountain"), d = state.data, C = 320, R = [92, 196, 300];
    const items = d.results;
    const slices = [...new Set(items.map(sliceOf))].sort();
    const color = Object.fromEntries(slices.map((s, i) => [s, PALETTE[i % PALETTE.length]]));
    const n = Math.max(1, slices.length), step = (2 * Math.PI) / n;
    let out = "";
    R.forEach((r, i) => { out += `<circle cx="${C}" cy="${C}" r="${r}" fill="none" stroke="var(--edge2)" stroke-width="1" ${i > state.width ? 'stroke-dasharray="3 5" opacity=".5"' : ""}/>`; });
    slices.forEach((s, i) => {
      const a = -Math.PI / 2 + i * step;
      out += `<line x1="${C}" y1="${C}" x2="${C + R[2] * Math.cos(a)}" y2="${C + R[2] * Math.sin(a)}" stroke="var(--edge)" />`;
      const la = a + step / 2, lr = R[2] + 4;
      const x = C + (lr - 30) * Math.cos(la), y = C + (lr - 30) * Math.sin(la);
      out += `<text x="${x}" y="${y}" text-anchor="middle" font-size="12" font-weight="600" fill="${color[s]}" paint-order="stroke" stroke="var(--surface)" stroke-width="4">${esc(s)}</text>`;
    });
    // place dots: radius from zone band + score, angle spread within the slice
    const bySlice = {};
    items.forEach((r) => { (bySlice[sliceOf(r)] ||= []).push(r); });
    Object.entries(bySlice).forEach(([s, arr]) => {
      const i = slices.indexOf(s), a0 = -Math.PI / 2 + i * step;
      arr.forEach((r, j) => {
        const z = ZONES.indexOf(r.zone), inner = z === 0 ? 14 : R[z - 1] + 10, outer = R[z] - 12;
        const rad = inner + (outer - inner) * Math.min(1, Math.max(0, r.radius));
        const a = a0 + step * ((j + 0.5) / arr.length) * 0.9 + step * 0.05;
        const x = C + rad * Math.cos(a), y = C + rad * Math.sin(a);
        const on = visible(r);
        const sel = state.selected === r.key;
        const size = r.zone === "core" ? 8 : r.zone === "margin" ? 6.5 : 5;
        out += `<circle class="dot" data-key="${esc(r.key)}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${sel ? size + 3 : size}" fill="${color[s]}" opacity="${on ? (r.noise_flags.length ? 0.45 : 0.95) : 0.12}" stroke="${sel ? "var(--ink)" : r.noise_flags.length ? "var(--warn)" : "none"}" stroke-width="2" tabindex="${on ? 0 : -1}" role="button" aria-label="${esc(r.title)}"><title>${esc(r.title)}</title></circle>`;
      });
    });
    out += `<circle cx="${C}" cy="${C}" r="40" fill="none" stroke="var(--warn)" stroke-width="2" stroke-dasharray="5 4"/><text x="${C}" y="${C + 56}" text-anchor="middle" font-size="10.5" fill="var(--quiet)" paint-order="stroke" stroke="var(--surface)" stroke-width="3">top-10 area</text>`;
    svg.innerHTML = out;
    svg.querySelectorAll(".dot").forEach((el) => {
      const pick = () => { state.selected = el.dataset.key; renderMountain(); renderDetail(); };
      el.addEventListener("click", pick);
      el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
  }

  function itemHtml(r, full) {
    const ranks = Object.entries(r.engines).map(([e, k]) => `${esc(e)} #${k}`).join(", ");
    return `<div class="tags"><span class="tag z-${r.zone}">${ZONE_LABEL[r.zone]}</span><span class="tag">${esc(r.source_type)}</span><span class="tag">lang: ${esc(r.language)}</span><span class="tag">${ranks}</span>${r.rank_spread != null ? `<span class="tag">rank spread ±${r.rank_spread}</span>` : ""}${r.noise_flags.map((f) => `<span class="tag noise">${esc(f)}</span>`).join("")}</div>` +
      (full ? `<ul class="why">${r.why.map((w) => `<li>${esc(w)}</li>`).join("")}<li>source type: ${esc(r.source_type_reason)}; language: ${esc(r.language_reason)}</li>${r.provenance && r.provenance.fetched ? `<li>own index copy fetched ${esc(r.provenance.fetched)}${r.provenance.truncated ? " (truncated)" : ""}</li>` : ""}</ul>` : "");
  }

  function renderDetail() {
    const el = $("detail"), r = state.data && state.data.results.find((x) => x.key === state.selected);
    if (!r) { el.hidden = true; return; }
    el.hidden = false;
    el.innerHTML = `<h3><a href="${esc(r.url)}" target="_blank" rel="noopener" data-type="${esc(r.source_type)}">${esc(r.title)}</a></h3><div class="note">${esc(r.url)}</div><p>${esc(r.snippet)}</p><strong style="font-size:13px">Why it's here</strong>${itemHtml(r, true)}`;
    el.querySelector("a").addEventListener("click", () => noteOpened(r));
  }

  function bar(mix) {
    const keys = Object.keys(mix);
    return `<div class="stack">${keys.map((k, i) => `<span style="width:${mix[k] * 100}%;background:${PALETTE[i % PALETTE.length]}" title="${esc(k)} ${pct(mix[k])}"></span>`).join("")}</div><div class="legend">${keys.map((k, i) => `<span><i style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(k)} ${pct(mix[k])}</span>`).join("")}</div>`;
  }

  function renderHealth() {
    const h = state.data.health; if (!h) { $("health").innerHTML = "<p>No results.</p>"; return; }
    const agree = Object.entries(h.found_by_n_engines).map(([k, v]) => `${v} by ${k}`).join(" · ");
    const gap = Object.entries(h.language_target_gap || {}).map(([k, v]) => `${k} ${v > 0 ? "+" : ""}${Math.round(v * 100)} pts`).join(", ");
    $("health").innerHTML = `
      <div class="metric"><span>Results · distinct sites</span><b>${h.results_shown} · ${h.distinct_domains}</b></div>
      <div class="metric"><span>Top 3 sites hold</span><b>${pct(h.top3_domain_share)} of results</b></div>
      <div class="metric"><span>Source diversity (0–1)</span><b>${h.domain_diversity}</b></div>
      <div class="metric"><span>Attention concentration (Gini)</span><b>${h.exposure_gini}</b></div>
      <div class="metric"><span>Found by N engines</span><b>${agree}</b></div>
      <div class="metric"><span>Flagged as possible noise</span><b>${pct(h.noise_share)}</b></div>
      ${h.own_index_share ? `<div class="metric"><span>From our own index</span><b>${pct(h.own_index_share)}</b></div>` : ""}
      <div class="metric" style="display:block"><span>Language mix</span>${bar(h.language_mix)}${gap ? `<div class="note">vs your lens target: ${esc(gap)}</div>` : ""}</div>
      <div class="metric" style="display:block;border:0"><span>Source-type mix</span>${bar(h.source_type_mix)}</div>
      <p class="note">Engines: ${esc(h.engines_queried.join(", "))}. ${state.data.discarded_count} result(s) removed by lens rules.</p>`;
    renderNudge();
  }

  function noteOpened(r) { state.opened.add(r.source_type); renderNudge(); }
  function renderNudge() {
    const types = Object.keys(state.data.health.source_type_mix || {});
    const missing = types.filter((t) => !state.opened.has(t));
    const el = $("nudge");
    if (!state.opened.size) { el.hidden = true; return; }
    el.hidden = false;
    el.textContent = missing.length ? `You've opened ${state.opened.size} of ${types.length} source types. Not yet: ${missing.join(", ")}.` : "You've opened every source type in this search.";
  }

  function renderList() {
    const d = state.data;
    $("list").innerHTML = ZONES.map((z, zi) => {
      const rows = d.results.filter((r) => r.zone === z);
      if (!rows.length) return "";
      const off = zi > state.width;
      return `<div class="zone"><h3>${ZONE_LABEL[z]} · ${rows.length}${off ? " (outside your view width; widen to include)" : ""}</h3>${off ? "" : rows.map((r) => `
        <div class="item${r.hidden ? " hidden" : ""}"><a class="t" href="${esc(r.url)}" target="_blank" rel="noopener" data-key="${esc(r.key)}">${esc(r.title)}</a>
        <div class="u">${esc(r.url)}</div><p>${esc(r.snippet)}</p>${itemHtml(r, false)}
        <details><summary>Why it's here</summary>${itemHtml(r, true).split("</div>").slice(1).join("</div>")}</details></div>`).join("")}</div>`;
    }).join("");
    $("list").querySelectorAll("a.t").forEach((a) => a.addEventListener("click", () => noteOpened(d.results.find((r) => r.key === a.dataset.key))));
  }

  // events
  $("form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
  $("lens").addEventListener("change", async (e) => { await selectLens(e.target.value); run(); });
  $("width").addEventListener("input", (e) => { state.width = +e.target.value; $("widthLabel").textContent = WIDTH_LABEL[state.width]; if (state.data) { renderMountain(); renderList(); } });
  $("slice").addEventListener("change", (e) => { state.slice = e.target.value; if (state.data) renderMountain(); });
  function parseLens() { try { return JSON.parse($("lensJson").value); } catch (e) { $("lensMsg").textContent = `That isn't valid JSON: ${e.message}`; return null; } }
  $("runLens").addEventListener("click", () => { const l = parseLens(); if (l) { state.lens = l; $("lensMsg").textContent = "Lens applied."; run(l); } });
  $("saveLens").addEventListener("click", () => {
    const l = parseLens(); if (!l) return; const s = storage();
    if (!s) { $("lensMsg").textContent = "This browser blocks storage; use Copy lens instead."; return; }
    const all = readSaved(); const id = (l.name || "my-lens").toLowerCase().replace(/[^a-z0-9]+/g, "-"); all[id] = l;
    try { s.setItem("es.lenses", JSON.stringify(all)); $("lensMsg").textContent = "Saved in this browser."; loadLenses(); } catch (e) { $("lensMsg").textContent = "Could not save here; use Copy lens."; }
  });
  $("copyLens").addEventListener("click", async () => { try { await navigator.clipboard.writeText($("lensJson").value); $("lensMsg").textContent = "Lens copied."; } catch (e) { $("lensMsg").textContent = "Copy was blocked; select the text and copy it."; } });

  loadLenses().then(() => run());
})();
