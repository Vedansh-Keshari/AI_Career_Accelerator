"use strict";

const $ = (s, r = document) => r.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

const S = {
  boot: null, projects: [], p: null, page: 0, tab: "content", count: 1, sel: null, desktop: false, settings: null,
  canva: { demo: true, signed_in: false, name: "" }, saveTimer: null, saving: null, newTab: "example",
  newType: "presentation", known: {}, recent: null, pushing: false, saveState: "", hist: { stack: [], idx: -1 }, dragFrom: null,
};
const TOKENS = { text: "Text", heading: "Heading", accent: "Accent", primary: "Primary", on_primary: "On primary", surface: "Surface", bg: "Background", ink: "Ink" };

async function api(method, url, body, isForm) {
  const opts = { method, headers: { "X-Studio": "1" } };
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  }
  const res = await fetch(url, opts);
  let data = {};
  try { data = await res.json(); } catch (_) { /* not JSON */ }
  if (!res.ok) { const e = new Error(data.error || `Something went wrong (${res.status}).`); e.data = data; e.status = res.status; throw e; }
  return data;
}

let toastTimer;
function toast(html, bad = false) {
  const t = $("#toast");
  t.className = "toast show" + (bad ? " bad" : "");
  t.innerHTML = html;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), bad ? 8000 : 5500);
}
const run = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(esc(e.message), true); } };

/* ---------- save state, history (undo/redo), saving ---------- */
function setSave(state) {
  S.saveState = state;
  const el = $("#saveState");
  el.textContent = { saving: "Saving...", saved: "Saved", error: "Not saved", conflict: "Out of date" }[state] || "";
  el.className = "save-state" + (state === "error" || state === "conflict" ? " bad" : "");
}

function content() {
  const { rev, updated, pushes, history, ...rest } = S.p;
  return JSON.stringify(rest);
}
function histReset() { S.hist = { stack: [content()], idx: 0 }; updateUndo(); }
function histPush() {
  if (!S.p) return;
  const h = S.hist, snap = content();
  if (h.stack[h.idx] === snap) return;
  h.stack = h.stack.slice(0, h.idx + 1);
  h.stack.push(snap);
  if (h.stack.length > 80) h.stack.shift();
  h.idx = h.stack.length - 1;
  updateUndo();
}
function updateUndo() {
  $("#undoBtn").disabled = !S.p || S.hist.idx <= 0;
  $("#redoBtn").disabled = !S.p || S.hist.idx >= S.hist.stack.length - 1;
}
async function stepHistory(d) {
  if (!S.p) return;
  if (S.saveTimer) await flushSave();
  const h = S.hist, j = h.idx + d;
  if (j < 0 || j >= h.stack.length) return;
  h.idx = j;
  const { rev, updated, pushes, history } = S.p;
  S.p = { ...JSON.parse(h.stack[j]), rev, updated, pushes, history };
  if (S.sel && !currentElements().some((e) => e.id === S.sel)) S.sel = null;
  S.page = Math.min(S.page, Math.max(0, (S.p.slides || []).length - 1));
  updateUndo();
  renderAll();
  await saveNow(false);
}

function scheduleSave() {
  clearTimeout(S.saveTimer);
  setSave("saving");
  S.saveTimer = setTimeout(() => flushSave().catch(() => {}), 450);
}
async function flushSave() {
  clearTimeout(S.saveTimer);
  S.saveTimer = null;
  await saveNow(true);
}
async function saveNow(record) {
  if (S.saving) await S.saving;
  if (!S.p) return;
  if (record) histPush();
  const snapshot = S.p;
  // a save that was still in flight (or a restored copy of the project) may carry an older revision number
  snapshot.rev = Math.max(snapshot.rev || 0, S.known[snapshot.id] || 0);
  setSave("saving");
  S.saving = api("PUT", `/api/projects/${snapshot.id}`, snapshot);
  try {
    const saved = await S.saving;
    snapshot.updated = saved.updated;
    snapshot.rev = saved.rev;
    S.known[saved.id] = Math.max(S.known[saved.id] || 0, saved.rev);
    setSave("saved");
    updateList(saved);
  } catch (e) {
    if (e.status === 409) { setSave("conflict"); $("#conflict").hidden = false; }
    else { setSave("error"); toast(esc(e.message), true); }
    throw e;
  } finally { S.saving = null; }
  await refreshPreview();
}

function updateList(p) {
  const row = S.projects.find((x) => x.id === p.id);
  if (row) { row.title = p.title; row.updated = p.updated; }
  renderList();
}

async function openProject(id) {
  if (S.p) { try { await flushSave(); } catch (_) { /* conflict shown */ } }
  S.p = await api("GET", `/api/projects/${id}`);
  S.known[id] = S.p.rev;
  S.page = 0; S.sel = null;
  S.count = S.p.type === "presentation" ? Math.max(1, S.p.slides.length) : S.p.type === "logo" ? 4 : 1;
  S.recent = null;
  S.tab = "content";
  $("#conflict").hidden = true;
  localStorage.setItem("studio.last", id);
  histReset();
  setSave("saved");
  renderAll();
  await refreshPreview();
}

async function refreshPreview() {
  const p = S.p;
  if (!p) return;
  if (p.type === "presentation") S.count = Math.max(1, p.slides.length);
  else if (p.type === "logo") S.count = 4;
  else S.count = (await api("GET", `/api/projects/${p.id}/info`)).count;
  S.page = Math.min(S.page, S.count - 1);
  renderStage();
}

const currentSlide = () => (S.p && S.p.type === "presentation" ? S.p.slides[S.page] : null);
const currentElements = () => { const s = currentSlide(); return s && s.free ? s.elements : []; };
const selectedIndex = () => currentElements().findIndex((e) => e.id === S.sel);

/* ---------- rendering ---------- */
function renderAll() { renderList(); renderTop(); renderStage(); renderTabs(); renderPanel(); updateUndo(); }

function renderList() {
  const ul = $("#projectList");
  if (!S.projects.length) { ul.innerHTML = '<li class="hint" style="margin:0">No projects yet.</li>'; return; }
  const label = { presentation: "Presentation", document: "Document", logo: "Logo" };
  ul.innerHTML = S.projects.map((x) => `
    <li><button class="pitem" data-action="open" data-id="${x.id}" ${S.p && S.p.id === x.id ? 'aria-current="true"' : ""}>
      <span>${esc(x.title || "Untitled")}</span><small>${label[x.type] || x.type}${x.pushed ? " - pushed" : ""}</small></button>
      <button class="pdel" data-action="delete" data-id="${x.id}" aria-label="Delete ${esc(x.title || "project")}" title="Delete">&times;</button></li>`).join("");
}

function renderTop() {
  const title = $("#title");
  title.disabled = !S.p;
  if (document.activeElement !== title) title.value = S.p ? S.p.title : "";
  const chip = $("#canvaChip"), c = S.canva;
  chip.className = "chip" + (c.signed_in ? " on" : "");
  chip.innerHTML = c.signed_in ? `<i></i>${c.demo ? "Demo Canva" : "Canva"}: ${esc(c.name || "signed in")}` : `<i></i>${c.demo ? "Demo Canva" : "Canva"}: sign in`;
  const push = $("#pushBtn");
  push.disabled = !S.p || S.pushing;
  if (!S.pushing) push.textContent = c.signed_in ? "Push to Canva" : "Sign in to push";
  const banner = $("#banner");
  banner.hidden = !c.demo;
  banner.textContent = c.demo ? "Demo mode: sign-in and pushes go to a local stand-in for Canva, not canva.com. Add your Canva keys in Settings to connect your real account." : "";
  const links = $("#downloadLinks");
  if (!S.p) { links.innerHTML = "<p>Open a project first.</p>"; return; }
  const id = S.p.id;
  const t = S.p.type;
  links.innerHTML = t === "logo" ? `<a href="/api/projects/${id}/export.png" download>Logo as PNG</a>`
    : `${t === "presentation" ? `<a href="/api/projects/${id}/export.pptx" download>Editable PowerPoint (.pptx)</a>` : `<a href="/api/projects/${id}/export.docx" download>Editable Word (.docx)</a>`}
       <a href="/api/projects/${id}/export.pdf" download>All pages as PDF</a><a href="/api/projects/${id}/export.zip" download>Pages as PNG images (zip)</a>`;
}

function renderStage() {
  const p = S.p;
  $("#empty").hidden = !!p;
  $("#work").hidden = !p;
  if (!p) return;
  const v = encodeURIComponent(p.updated);
  const img = $("#preview");
  let main, thumbs;
  if (p.type === "logo") {
    main = `/api/projects/${p.id}/logo/${p.logo.variant}.png?scale=0.7&v=${v}`;
    thumbs = [0, 1, 2, 3].map((i) => ({ src: `/api/projects/${p.id}/logo/${i}.png?scale=0.22&v=${v}`, label: ["Badge", "Wordmark", "Icon stack", "Monogram"][i], current: i === p.logo.variant }));
  } else {
    main = `/api/projects/${p.id}/page/${S.page}.png?scale=0.6&v=${v}`;
    thumbs = Array.from({ length: S.count }, (_, i) => ({ src: `/api/projects/${p.id}/page/${i}.png?scale=0.18&v=${v}`, label: p.type === "presentation" ? `Slide ${i + 1}` : `Page ${i + 1}`, current: i === S.page }));
  }
  img.alt = p.type === "logo" ? `Logo preview: ${p.logo.brand}` : `Preview of page ${S.page + 1} of ${S.count}`;
  if (img.getAttribute("src") !== main) img.src = main;
  const drag = p.type === "presentation" ? ' draggable="true"' : "";
  $("#strip").innerHTML = thumbs.map((t, i) => `<button class="thumb" role="listitem"${drag} data-action="page" data-i="${i}" ${t.current ? 'aria-current="true"' : ""}><img src="${t.src}" alt="" loading="lazy" draggable="false"><span>${esc(t.label)}</span></button>`).join("");
  renderOverlay();
}

let drag = null;
const HANDLES = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];
function renderOverlay() {
  if (drag) return;  // never rebuild the boxes while one is being dragged (a background save could otherwise cancel the drag)
  const ov = $("#overlay"), s = currentSlide();
  if (!s || !s.free) { ov.hidden = true; ov.innerHTML = ""; return; }
  ov.hidden = false;
  ov.innerHTML = s.elements.map((el) => `<div class="el${el.id === S.sel ? " sel" : ""}" data-id="${el.id}" title="${esc(el.type)}" style="left:${el.x * 100}%;top:${el.y * 100}%;width:${el.w * 100}%;height:${el.h * 100}%">${el.id === S.sel ? HANDLES.map((h) => `<span class="hd" data-h="${h}"></span>`).join("") : ""}</div>`).join("");
}

function renderTabs() {
  document.querySelectorAll("#tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === S.tab)));
}
const opt = (list, cur) => list.map((x) => `<option ${x === cur ? "selected" : ""}>${esc(x)}</option>`).join("");

function renderPanel() {
  const el = $("#panel");
  if (!S.p) { el.innerHTML = '<p class="hint">Create or open a project to start editing.</p>'; return; }
  el.innerHTML = { content: contentTab, look: lookTab, refine: refineTab, canva: canvaTab }[S.tab]();
  if (S.tab === "canva" && S.canva.signed_in && S.recent === null) loadRecent();
}

function colorControl(label, path, value, allowNone) {
  const isToken = value in TOKENS;
  const hex = /^#[0-9a-fA-F]{6}$/.test(value) ? value : "#3250f2";
  return `<div class="field"><span>${label}</span></div><div class="color-row">
    <select data-bind="${path}" aria-label="${label}">${allowNone ? `<option value="" ${!value ? "selected" : ""}>None</option>` : ""}${Object.entries(TOKENS).map(([k, n]) => `<option value="${k}" ${k === value ? "selected" : ""}>${n}</option>`).join("")}${!isToken && value ? `<option value="${esc(value)}" selected>Custom ${esc(value)}</option>` : ""}</select>
    <input type="color" value="${hex}" data-bind="${path}" data-rerender="1" aria-label="${label}: pick any colour"></div>`;
}

function elementPanel() {
  const s = currentSlide(), els = s.elements, base = `slides.${S.page}.elements`;
  const idx = selectedIndex();
  let html = `<h3>Layers</h3><ul class="elist">${els.map((e) => `<li><button data-action="select-el" data-id="${e.id}" ${e.id === S.sel ? 'aria-current="true"' : ""}>${{ text: "Text", rect: "Rectangle", ellipse: "Circle", image: "Picture" }[e.type]}${e.type === "text" ? `: ${esc((e.text || "").slice(0, 28))}` : ""}</button></li>`).reverse().join("")}</ul>`;
  if (idx < 0) return html + '<p class="hint">Click a box on the slide (or a layer above) to edit it. Drag to move, drag the square handles to resize, arrow keys nudge, Delete removes.</p>';
  const el = els[idx], p = `${base}.${idx}`;
  html += `<h3>${{ text: "Text box", rect: "Rectangle", ellipse: "Circle", image: "Picture" }[el.type]}</h3>`;
  if (el.type === "text") {
    html += `<label class="field"><span>Text (start a line with - for a bullet)</span><textarea id="elText" data-bind="${p}.text" rows="4">${esc(el.text)}</textarea></label>
      <label class="field"><span>Largest text size: ${Math.round(el.size)} (shrinks to fit the box)</span><input type="range" min="12" max="240" step="2" value="${el.size}" data-bind="${p}.size" data-num="1" data-label="Largest text size: "></label>
      <label class="check"><input type="checkbox" data-bind="${p}.bold" ${el.bold ? "checked" : ""}> Bold</label>
      <div class="grid2"><label class="field"><span>Align</span><select data-bind="${p}.align">${["left", "center", "right"].map((a) => `<option ${a === el.align ? "selected" : ""}>${a}</option>`).join("")}</select></label>
      <label class="field"><span>Vertical</span><select data-bind="${p}.valign">${["top", "middle", "bottom"].map((a) => `<option ${a === el.valign ? "selected" : ""}>${a}</option>`).join("")}</select></label></div>
      ${colorControl("Text colour", `${p}.color`, el.color, false)}${colorControl("Box fill", `${p}.fill`, el.fill || "", true)}`;
  } else if (el.type === "image") {
    html += `<div class="row"><button class="btn small" data-action="replace-el-image">${el.image ? "Replace picture" : "Choose picture"}</button></div>`;
  } else {
    html += `${colorControl("Fill colour", `${p}.fill`, el.fill, false)}
      <label class="field"><span>Opacity: ${Math.round(el.opacity * 100)}%</span><input type="range" min="0.1" max="1" step="0.05" value="${el.opacity}" data-bind="${p}.opacity" data-num="1" data-label="Opacity: " data-pct="1"></label>
      ${el.type === "rect" ? `<label class="field"><span>Rounded corners</span><input type="range" min="0" max="0.5" step="0.02" value="${el.radius}" data-bind="${p}.radius" data-num="1"></label>` : ""}`;
  }
  html += `<div class="row"><button class="btn small" data-action="el-front">Bring to front</button><button class="btn small" data-action="el-forward">Forward</button>
    <button class="btn small" data-action="el-backward">Backward</button><button class="btn small" data-action="el-back">Send to back</button></div>
    <div class="row"><button class="btn small" data-action="el-dup">Duplicate</button><button class="btn small danger" data-action="el-del">Delete</button></div>`;
  return html;
}

function contentTab() {
  const p = S.p;
  if (p.type === "presentation") {
    const i = S.page, s = p.slides[i];
    if (!s) return `<p class="hint">This deck has no slides.</p><button class="btn" data-action="add-slide">Add a slide</button>`;
    const slideOps = `<h3>Slides</h3>
      <p class="hint">Tip: drag the slide pictures under the preview to reorder them.</p>
      <div class="row">
        <button class="btn small" data-action="add-slide">Add slide after</button>
        <button class="btn small" data-action="dup-slide">Duplicate</button>
        <button class="btn small" data-action="move-slide" data-dir="-1" ${i === 0 ? "disabled" : ""}>Move earlier</button>
        <button class="btn small" data-action="move-slide" data-dir="1" ${i === p.slides.length - 1 ? "disabled" : ""}>Move later</button>
        <button class="btn small danger" data-action="del-slide" ${p.slides.length < 2 ? "disabled" : ""}>Delete</button>
      </div><input type="file" id="imgInput" accept="image/png,image/jpeg,image/webp,image/gif" hidden>`;
    if (s.free) {
      return `<h3>Slide ${i + 1} of ${p.slides.length}: free layout</h3>
        <div class="note">Drag boxes on the slide to move them; drag the square handles to resize.</div>
        <div class="row"><button class="btn small" data-action="add-el" data-kind="text">Add text</button><button class="btn small" data-action="add-el" data-kind="rect">Add rectangle</button>
        <button class="btn small" data-action="add-el" data-kind="ellipse">Add circle</button><button class="btn small" data-action="add-el-image">Add picture</button></div>
        ${elementPanel()}
        <div class="row"><button class="btn small" data-action="free-off">Back to automatic layout</button></div>
        <p class="hint">Going back keeps your free layout saved, so you can return to it.</p>${slideOps}`;
    }
    return `
      <h3>Slide ${i + 1} of ${p.slides.length}</h3>
      <label class="field"><span>Title</span><input type="text" data-bind="slides.${i}.title" value="${esc(s.title)}"></label>
      <label class="field"><span>Text</span><textarea data-bind="slides.${i}.body" rows="6">${esc(s.body)}</textarea></label>
      <p class="hint">Start a line with - to make a bullet.</p>
      <label class="field"><span>Layout</span><select data-bind="slides.${i}.layout">${["auto", "title", "bullets", "statement", "cta"].map((x) => `<option value="${x}" ${x === s.layout ? "selected" : ""}>${{ auto: "Automatic", title: "Title", bullets: "Bullet list", statement: "Big statement", cta: "Call to action" }[x]}</option>`).join("")}</select></label>
      <div class="row">
        <button class="btn small" data-action="pick-image">${s.image ? "Replace image" : "Add image"}</button>
        ${s.image ? '<button class="btn small" data-action="remove-image">Remove image</button>' : ""}
      </div>
      <div class="row"><button class="btn small primary" data-action="free-on">Edit freely (move &amp; resize)</button></div>
      ${slideOps}`;
  }
  if (p.type === "document") {
    return `
      <label class="field"><span>Document type</span><select data-bind="doc.doc_type" data-rerender="1">${opt(S.boot.options.doc_types, p.doc.doc_type)}</select></label>
      <p class="hint">Caption, Tweet and Social post become a square post; everything else is a paged document.</p>
      ${p.doc.sections.map((s, i) => `
        <div class="card">
          <label class="field"><span>Heading ${s.heading ? "" : "(optional)"}</span><input type="text" data-bind="doc.sections.${i}.heading" value="${esc(s.heading)}"></label>
          <label class="field"><span>Text (start a line with - for a bullet)</span><textarea data-bind="doc.sections.${i}.body" rows="5">${esc(s.body)}</textarea></label>
          <div class="row" style="margin:0">
            <button class="btn small" data-action="move-sec" data-i="${i}" data-dir="-1" ${i === 0 ? "disabled" : ""}>Up</button>
            <button class="btn small" data-action="move-sec" data-i="${i}" data-dir="1" ${i === p.doc.sections.length - 1 ? "disabled" : ""}>Down</button>
            <button class="btn small danger" data-action="del-sec" data-i="${i}">Delete</button>
          </div>
        </div>`).join("")}
      <button class="btn" data-action="add-sec">Add section</button>`;
  }
  const l = p.logo;
  return `
    <label class="field"><span>Brand name</span><input type="text" data-bind="logo.brand" value="${esc(l.brand)}" maxlength="60"></label>
    <label class="field"><span>Tagline</span><input type="text" data-bind="logo.tagline" value="${esc(l.tagline)}" maxlength="80"></label>
    <label class="field"><span>What does the brand do? (picks the icon)</span><textarea data-bind="logo.description" rows="4">${esc(l.description)}</textarea></label>
    <label class="field"><span>Icon</span><select data-bind="logo.icon">${S.boot.options.logo_icons.map((x) => `<option value="${x}" ${x === l.icon ? "selected" : ""}>${x === "auto" ? "Automatic (from description)" : x}</option>`).join("")}</select></label>
    <p class="hint">Pick a layout by clicking one of the four options under the preview.</p>`;
}

function lookTab() {
  const p = S.p, o = p.options, pal = S.boot.options.palettes, fm = S.boot.options.font_map;
  const fontLabel = Object.keys(fm).find((k) => fm[k] === p.tune.font) || "Style default";
  const brandSet = S.settings && S.settings.brand && S.settings.brand.primary;
  return `
    <label class="field"><span>Style</span><select data-bind="options.style">${opt(S.boot.options.styles, o.style)}</select></label>
    <label class="field"><span>Font</span><select id="fontPick">${opt(Object.keys(fm), fontLabel)}</select></label>
    <div class="field"><span>Colour</span></div>
    <div class="swatches">${S.boot.options.colors.map((c) => `<button class="sw" type="button" data-action="color" data-color="${c}" style="background:${pal[c].primary}" aria-label="${c}" title="${c}" aria-pressed="${c === o.color}"></button>`).join("")}
      ${p.brand ? `<button class="sw brand" type="button" data-action="color" data-color="Brand" style="--b1:${esc(p.brand.primary)};--b2:${esc(p.brand.accent)}" aria-label="Brand colours" title="Brand colours" aria-pressed="${o.color === "Brand"}"></button>` : ""}</div>
    ${brandSet ? `<div class="row"><button class="btn small" data-action="apply-brand">Apply my brand kit</button></div>` : '<p class="hint">Save brand colours and a font in Settings to apply them here in one click.</p>'}
    ${p.type === "presentation" ? `<label class="field"><span>Format</span><select data-bind="options.format">${opt(S.boot.options.formats, o.format)}</select></label>` : ""}
    <label class="field"><span>Colour intensity: ${["Soft", "Brighter", "Bold", "Vivid"][p.tune.boldness]}</span><input type="range" min="0" max="3" step="1" value="${p.tune.boldness}" data-bind="tune.boldness" data-num="1" data-intensity="1"></label>
    <label class="field"><span>Text size: ${Math.round(p.tune.text_scale * 100)}%</span><input type="range" min="0.7" max="1.6" step="0.05" value="${p.tune.text_scale}" data-bind="tune.text_scale" data-num="1" data-pctnum="1"></label>`;
}

function refineTab() {
  const p = S.p;
  const ideas = ["Make it brighter and bolder", "Bigger text, fill up slides that look too empty", "Use a different colour palette", "Make it elegant", "Come up with a more interesting title", "Make it blue"];
  return `
    <p class="hint">Describe a change in plain words, then apply it. Keep refining until it matches your vision. (Undo brings back the previous version.)</p>
    <label class="field"><span>What should change?</span><textarea id="refineText" rows="3" placeholder="e.g. make the colours brighter and the text bigger"></textarea></label>
    <div class="chips">${ideas.map((t) => `<button type="button" data-action="idea" data-text="${esc(t)}">${esc(t)}</button>`).join("")}</div>
    <button class="btn primary" data-action="refine">Apply change</button>
    <h3>What you've changed</h3>
    ${p.history.length ? `<ul class="log">${p.history.slice().reverse().map((h) => `<li><q>${esc(h.prompt)}</q>${(h.changes || []).map(esc).join("; ")}</li>`).join("")}</ul>` : '<p class="hint">Nothing yet.</p>'}
    <p class="hint">These tweaks are rule-based (colour, boldness, size, style, title), not an AI model. Photos are added with Add image on a slide.</p>`;
}

function canvaTab() {
  const c = S.canva, p = S.p;
  const status = c.signed_in
    ? `<div class="status"><b>${c.demo ? "Signed in to demo Canva" : "Signed in to Canva"}${c.name ? ` as ${esc(c.name)}` : ""}</b>Pushes create a new design in this account.</div><div class="row"><button class="btn small" data-action="signout">Sign out</button></div>`
    : `<div class="status"><b>Not signed in</b>${c.demo ? "Demo mode uses a local stand-in with an email box." : "You'll sign in with your email on Canva's own page; this app never sees your password."}</div><div class="row"><button class="btn primary" data-action="signin">Sign in${c.demo ? " (demo)" : " with Canva"}</button><button class="btn small" data-action="open-settings">Connect real Canva</button></div>`;
  const pushes = (p.pushes || []).map((x) => `<li><span>${esc(x.title)} - ${esc(x.kind)}${x.note ? `<br><small>${esc(x.note)}</small>` : ""}</span>${x.edit_url ? `<a href="${esc(x.edit_url)}" target="_blank" rel="noopener">Open</a>` : ""}</li>`).join("");
  const what = p.type === "logo" ? "Logos arrive as an image design." : p.type === "presentation" ? "Decks arrive as an editable PowerPoint, so text stays editable in Canva." : (["Caption", "Tweet", "Social post"].includes(p.doc.doc_type) ? "Short posts arrive as an image design." : "Documents arrive as an editable Word file, so text stays editable in Canva.");
  return `
    ${status}
    <label class="field"><span>Planned finishing touch in Canva</span><select data-bind="options.feature">${opt(S.boot.options.features, p.options.feature)}</select></label>
    <p class="hint">Animation, audio and video are added inside Canva after you push.</p>
    <button class="btn primary" data-action="push" ${S.pushing ? "disabled" : ""}>${c.signed_in ? "Push this project to Canva" : "Sign in to push"}</button>
    <p class="hint" style="margin-top:8px">${what}</p>
    <h3>Pushed from this project</h3>
    ${pushes ? `<ul class="dlist">${pushes}</ul>` : '<p class="hint">Nothing pushed yet.</p>'}
    ${c.signed_in ? `<h3>Your recent Canva designs</h3><div id="recent">${recentHtml()}</div>` : ""}`;
}

function recentHtml() {
  if (S.recent === null) return '<p class="hint">Loading...</p>';
  if (S.recent.error) return `<p class="err">${esc(S.recent.error)}</p>`;
  if (!S.recent.length) return '<p class="hint">No designs found.</p>';
  return `<ul class="dlist">${S.recent.map((d) => `<li><span>${esc(d.title)}</span>${d.edit_url ? `<a href="${esc(d.edit_url)}" target="_blank" rel="noopener">Open</a>` : ""}</li>`).join("")}</ul>`;
}
async function loadRecent() {
  try { S.recent = (await api("GET", "/api/canva/designs")).designs; } catch (e) { S.recent = { error: e.message }; }
  const box = $("#recent");
  if (box) box.innerHTML = recentHtml();
}

/* ---------- dialogs ---------- */
function renderNew() {
  const body = $("#newBody");
  document.querySelectorAll("#newTabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.newtab === S.newTab)));
  if (S.newTab === "example") {
    const kind = { presentation: "Presentation", document: "Document", logo: "Logo" };
    body.innerHTML = `<p class="hint" style="margin-top:0">Each one comes from a scenario in the notes. Open one, then change anything.</p><div class="ex-grid">${S.boot.examples.map((e) => `<button class="ex" data-action="start-example" data-id="${e.id}"><b>${esc(e.name)}</b>${esc(e.description)}<em>${kind[e.kind]}</em></button>`).join("")}</div>`;
    return;
  }
  const O = S.boot.options, t = S.newType;
  const aiOn = S.settings && S.settings.ai.has_key;
  body.innerHTML = `
    <div class="seg" id="typeSeg">${["presentation", "document", "logo"].map((x) => `<button type="button" data-action="newtype" data-type="${x}" aria-pressed="${x === t}">${{ presentation: "Presentation", document: "Document", logo: "Logo" }[x]}</button>`).join("")}</div>
    <label class="field"><span>${t === "logo" ? "Describe the brand (say 'called Name' to set the name)" : "Describe your idea"}</span><textarea id="nPrompt" rows="4" placeholder="${{ presentation: "e.g. A deck about urban beekeeping for school kids, simple and friendly", document: "e.g. Write a blog post on better sleep, highlighting four benefits", logo: "e.g. A bakery called Rise & Shine, cozy and warm" }[t]}"></textarea></label>
    <label class="field"><span>${t === "logo" ? "Brand name (optional)" : "Title (optional)"}</span><input type="text" id="nTitle" maxlength="120"></label>
    <div class="grid2">
      <label class="field"><span>Style</span><select id="nStyle">${opt(O.styles, "Modern")}</select></label>
      <label class="field"><span>Colour</span><select id="nColor">${opt(O.colors, "Blue")}</select></label>
      ${t === "presentation" ? `<label class="field"><span>Length</span><select id="nLength">${opt(O.lengths, "Balanced (5 to 15 pages)")}</select></label>
      <label class="field"><span>Format</span><select id="nFormat">${opt(O.formats, "Presentation (16:9)")}</select></label>` : ""}
      ${t !== "logo" ? `<label class="field"><span>Audience</span><select id="nAudience">${opt(O.audiences, "Casual")}</select></label>
      <label class="field"><span>Theme</span><select id="nTheme">${opt(O.themes, "Productivity")}</select></label>` : ""}
      ${t === "document" ? `<label class="field"><span>Document type</span><select id="nDoc">${opt(O.doc_types, "Blog post")}</select></label>` : ""}
    </div>
    <p class="${aiOn ? "note" : "hint"}">${aiOn ? "Starter text will be written by the AI (your saved key). If that fails, templates are used." : "Starter text comes from built-in templates. Add an AI key in Settings to have an AI write it instead."} Everything is editable.</p>
    <button class="btn primary" data-action="create-idea">Create project</button>`;
}
function openNew() { renderNew(); $("#newDlg").showModal(); }

function renderSettings() {
  const st = S.settings, c = st.canva, a = st.ai, b = st.brand, fonts = S.boot.options.fonts;
  $("#setBody").innerHTML = `
    <h3 style="margin-top:0">Canva connection</h3>
    <p class="hint">${c.demo ? "Currently in demo mode (no Canva keys saved)." : "Using your Canva integration."} Create an integration at canva.com/developers, add this redirect URL, and enable the scopes design:meta:read, design:content:read, design:content:write, asset:read, asset:write, profile:read.</p>
    <label class="field"><span>Redirect URL to register</span><input type="text" readonly value="${esc(c.redirect_uri)}" onfocus="this.select()"></label>
    ${c.from_env ? '<p class="note">The CANVA_CLIENT_ID environment variable is set and takes priority over these fields.</p>' : ""}
    <label class="field"><span>Client ID</span><input type="text" id="setCid" value="${esc(c.client_id)}" autocomplete="off"></label>
    <label class="field"><span>Client secret ${c.has_secret && !c.demo ? "(saved - leave blank to keep)" : ""}</span><input type="password" id="setCsec" autocomplete="new-password" placeholder="${c.has_secret && !c.demo ? "........" : "paste it here"}"></label>
    <div class="row"><button class="btn primary" data-action="save-canva">Save and use my Canva</button>${c.demo ? "" : '<button class="btn" data-action="clear-canva">Go back to demo mode</button>'}</div>
    <h3>AI-written starter text (optional)</h3>
    <p class="hint">Paste an Anthropic API key to have Claude write outlines for "From my idea". It is stored encrypted on this computer and only ever sent to Anthropic. Without it, built-in templates are used.</p>
    <label class="field"><span>API key ${a.has_key ? "(saved - leave blank to keep)" : ""}</span><input type="password" id="setAi" autocomplete="new-password" placeholder="${a.has_key ? "........" : "sk-ant-..."}"></label>
    <label class="field"><span>Model</span><input type="text" id="setModel" value="${esc(a.model)}"></label>
    <div class="row"><button class="btn primary" data-action="save-ai">Save AI settings</button>${a.has_key ? '<button class="btn" data-action="clear-ai">Remove key</button>' : ""}</div>
    <h3>Brand kit</h3>
    <p class="hint">Saved colours and a font you can apply to any project from its Look tab.</p>
    <label class="field"><span>Brand name</span><input type="text" id="setBname" value="${esc(b.name)}" maxlength="60"></label>
    <div class="grid2"><div class="field"><span>Main colour</span><div class="color-row"><input type="color" id="setB1" value="${esc(b.primary || "#1c6dd0")}"></div></div>
    <div class="field"><span>Accent colour</span><div class="color-row"><input type="color" id="setB2" value="${esc(b.accent || "#4dabf7")}"></div></div></div>
    <label class="field"><span>Font</span><select id="setBfont">${opt(fonts, b.font)}</select></label>
    <div class="row"><button class="btn primary" data-action="save-brand">Save brand kit</button></div>
    <h3>Where secrets are kept</h3>
    <p class="hint">${st.storage.protected_by === "keyring" ? "Your sign-in tokens and keys are encrypted; the encryption key is held by your operating system's credential store." : "Your sign-in tokens and keys are encrypted; the encryption key is in a private file on this computer (your system credential store was not available)."}</p>`;
}

/* ---------- editing helpers ---------- */
function setPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  for (let i = 0; i < keys.length - 1; i++) o = o[keys[i]];
  o[keys[keys.length - 1]] = value;
}
function changed(rerenderPanel) {
  scheduleSave();
  renderStage();
  if (rerenderPanel) renderPanel();
}
async function serverEdit(call) {
  if (S.saveTimer) await flushSave();
  const r = await call();
  S.p = r.project || r;
  S.known[S.p.id] = Math.max(S.known[S.p.id] || 0, S.p.rev);
  histPush();
  updateList(S.p);
  setSave("saved");
  await refreshPreview();
  renderAll();
  return r;
}

const el = () => currentElements()[selectedIndex()];
function moveLayer(to) {
  const els = currentElements(), i = selectedIndex();
  if (i < 0) return;
  const [item] = els.splice(i, 1);
  els.splice(clamp(to === "front" ? els.length : to === "back" ? 0 : to === "fwd" ? i + 1 : i - 1, 0, els.length), 0, item);
  changed(true);
}

/* ---------- actions ---------- */
const actions = {
  "open-new": () => openNew(),
  "close-new": () => $("#newDlg").close(),
  "close-settings": () => $("#setDlg").close(),
  "open-settings": () => { renderSettings(); $("#setDlg").showModal(); },
  "reload-project": async () => { const id = S.p.id; S.p = null; clearTimeout(S.saveTimer); await openProject(id); },
  open: (e) => openProject(e.dataset.id),
  delete: async (e) => {
    const row = S.projects.find((x) => x.id === e.dataset.id);
    if (!confirm(`Delete "${row ? row.title : "this project"}"? This cannot be undone.`)) return;
    await api("DELETE", `/api/projects/${e.dataset.id}`);
    S.projects = S.projects.filter((x) => x.id !== e.dataset.id);
    if (S.p && S.p.id === e.dataset.id) { S.p = null; clearTimeout(S.saveTimer); if (S.projects.length) await openProject(S.projects[0].id); else renderAll(); } else renderList();
  },
  page: (e) => {
    const i = Number(e.dataset.i);
    if (S.p.type === "logo") { S.p.logo.variant = i; changed(true); return; }
    S.page = i; S.sel = null; renderStage(); if (S.tab === "content" && S.p.type === "presentation") renderPanel();
  },
  "add-slide": () => { const p = S.p; p.slides.splice(S.page + 1, 0, { title: "New slide", body: "- Add a point", layout: "auto", image: "", free: false, elements: [] }); S.page = Math.min(S.page + 1, p.slides.length - 1); S.sel = null; changed(true); },
  "dup-slide": () => { const p = S.p; p.slides.splice(S.page + 1, 0, JSON.parse(JSON.stringify(p.slides[S.page]))); S.page++; S.sel = null; changed(true); },
  "move-slide": (e) => { const d = Number(e.dataset.dir), p = S.p, j = S.page + d; [p.slides[S.page], p.slides[j]] = [p.slides[j], p.slides[S.page]]; S.page = j; changed(true); },
  "del-slide": () => { S.p.slides.splice(S.page, 1); S.page = Math.max(0, S.page - 1); S.sel = null; changed(true); },
  "add-sec": () => { S.p.doc.sections.push({ heading: "New section", body: "" }); changed(true); },
  "del-sec": (e) => { S.p.doc.sections.splice(Number(e.dataset.i), 1); changed(true); },
  "move-sec": (e) => { const i = Number(e.dataset.i), j = i + Number(e.dataset.dir), a = S.p.doc.sections; [a[i], a[j]] = [a[j], a[i]]; changed(true); },
  "pick-image": () => { $("#imgInput").dataset.target = ""; $("#imgInput").click(); },
  "add-el-image": () => { $("#imgInput").dataset.target = "new"; $("#imgInput").click(); },
  "replace-el-image": () => { $("#imgInput").dataset.target = S.sel; $("#imgInput").click(); },
  "remove-image": () => { S.p.slides[S.page].image = ""; changed(true); },
  color: (e) => { S.p.options.color = e.dataset.color; changed(true); },
  "apply-brand": async () => { await serverEdit(() => api("POST", `/api/projects/${S.p.id}/apply-brand`, {})); toast("Brand kit applied."); },
  idea: (e) => { $("#refineText").value = e.dataset.text; $("#refineText").focus(); },
  refine: async () => {
    const text = $("#refineText").value.trim();
    if (!text) { toast("Describe the change you want first.", true); return; }
    const r = await serverEdit(() => api("POST", `/api/projects/${S.p.id}/refine`, { text }));
    toast(esc(r.changes.join(" - ")));
  },
  "free-on": async () => { S.sel = null; await serverEdit(() => api("POST", `/api/projects/${S.p.id}/free`, { slide: S.page, enable: true })); },
  "free-off": async () => { S.sel = null; await serverEdit(() => api("POST", `/api/projects/${S.p.id}/free`, { slide: S.page, enable: false })); },
  "add-el": async (e) => {
    const r = await serverEdit(() => api("POST", `/api/projects/${S.p.id}/elements`, { slide: S.page, kind: e.dataset.kind }));
    S.sel = r.element_id; renderAll();
  },
  "select-el": (e) => { S.sel = e.dataset.id; renderOverlay(); renderPanel(); },
  "el-front": () => moveLayer("front"), "el-back": () => moveLayer("back"), "el-forward": () => moveLayer("fwd"), "el-backward": () => moveLayer("bwd"),
  "el-dup": () => { const e = el(); if (!e) return; const c = { ...JSON.parse(JSON.stringify(e)), id: "e_" + Math.random().toString(16).slice(2, 10), x: clamp(e.x + 0.03, -0.2, 0.95), y: clamp(e.y + 0.03, -0.2, 0.95) }; currentElements().push(c); S.sel = c.id; changed(true); },
  "el-del": () => { const i = selectedIndex(); if (i < 0) return; currentElements().splice(i, 1); S.sel = null; changed(true); },
  signin: async () => {
    await flushSave().catch(() => {});
    const r = await api("POST", "/auth/start", { external: S.desktop });
    if (!r.external) { location.href = r.url; return; }
    toast("Your browser opened Canva's sign-in page. Finish there, then come back.");
    for (let n = 0; n < 120; n++) {
      await new Promise((ok) => setTimeout(ok, 2000));
      const st = await api("GET", "/api/canva/status");
      if (st.signed_in) { S.canva = st; S.recent = null; renderTop(); renderPanel(); toast("Signed in to Canva. You can push now."); return; }
    }
    toast("Sign-in timed out. Try again.", true);
  },
  signout: async () => { await api("POST", "/auth/logout", {}); S.canva = { ...S.canva, signed_in: false, name: "" }; S.recent = null; renderTop(); renderPanel(); toast("Signed out of Canva."); },
  push: async () => {
    if (!S.canva.signed_in) { await actions.signin(); return; }
    S.pushing = true; renderTop(); renderPanel();
    try {
      await flushSave();
      const { job_id } = await api("POST", `/api/projects/${S.p.id}/push`, {});
      for (;;) {
        const j = await api("GET", `/api/jobs/${job_id}`);
        if (j.state === "running") { $("#pushBtn").textContent = `${j.stage}${j.step > 1 ? ` (${j.step})` : ""}...`; await new Promise((ok) => setTimeout(ok, 600)); continue; }
        if (j.state === "error") { if (j.needs_login) S.canva.signed_in = false; throw new Error(j.error + (j.needs_login ? " Use Sign in to continue." : "")); }
        S.p.pushes = j.project.pushes; S.recent = null;
        const row = S.projects.find((x) => x.id === S.p.id); if (row) row.pushed = true;
        const r = j.result;
        toast(`Pushed "${esc(r.title)}" as a ${esc(r.kind)}. ${r.note ? esc(r.note) + " " : ""}${r.edit_url ? `<a href="${esc(r.edit_url)}" target="_blank" rel="noopener">Open it in Canva</a>` : ""}`);
        break;
      }
    } finally { S.pushing = false; renderTop(); renderList(); renderPanel(); }
  },
  "start-example": async (e) => afterCreate(await api("POST", "/api/projects", { mode: "example", example_id: e.dataset.id })),
  newtype: (e) => { S.newType = e.dataset.type; renderNew(); },
  "create-idea": async () => {
    const g = (id) => { const x = $(id); return x ? x.value : undefined; };
    const options = { style: g("#nStyle"), color: g("#nColor"), length: g("#nLength"), format: g("#nFormat"), audience: g("#nAudience"), theme: g("#nTheme") };
    Object.keys(options).forEach((k) => options[k] === undefined && delete options[k]);
    $("#newBody").setAttribute("aria-busy", "true");
    try { await afterCreate(await api("POST", "/api/projects", { mode: "idea", type: S.newType, prompt: g("#nPrompt"), title: g("#nTitle"), options, doc_type: g("#nDoc") || "Blog post" })); }
    finally { $("#newBody").removeAttribute("aria-busy"); }
  },
  "save-canva": async () => {
    S.settings = await api("PUT", "/api/settings", { canva: { client_id: $("#setCid").value, client_secret: $("#setCsec").value } });
    S.canva = await api("GET", "/api/canva/status"); renderSettings(); renderAll(); toast("Canva keys saved. Sign in again to use your account.");
  },
  "clear-canva": async () => { S.settings = await api("PUT", "/api/settings", { canva: { clear: true } }); S.canva = await api("GET", "/api/canva/status"); renderSettings(); renderAll(); toast("Back in demo mode."); },
  "save-ai": async () => { S.settings = await api("PUT", "/api/settings", { ai: { api_key: $("#setAi").value, model: $("#setModel").value } }); renderSettings(); toast("AI settings saved."); },
  "clear-ai": async () => { S.settings = await api("PUT", "/api/settings", { ai: { clear_key: true } }); renderSettings(); toast("AI key removed."); },
  "save-brand": async () => {
    S.settings = await api("PUT", "/api/settings", { brand: { name: $("#setBname").value, primary: $("#setB1").value, accent: $("#setB2").value, font: $("#setBfont").value } });
    renderSettings(); renderPanel(); toast("Brand kit saved.");
  },
};

async function afterCreate(project) {
  S.projects.unshift({ id: project.id, type: project.type, title: project.title, updated: project.updated, pushed: false });
  $("#newDlg").close();
  await openProject(project.id);
  (project.notices || []).forEach((n) => toast(esc(n), true));
  if (project.generated_by === "ai") toast("Starter text written by the AI. Edit anything you like.");
}

/* ---------- events ---------- */
document.addEventListener("click", (ev) => {
  const t = ev.target.closest("[data-action]");
  if (!t) return;
  const fn = actions[t.dataset.action];
  if (fn) run(fn)(t);
});

document.addEventListener("input", (ev) => {
  const t = ev.target;
  if (t.id === "title") { S.p.title = t.value; updateList(S.p); scheduleSave(); return; }
  if (t.id === "fontPick") { S.p.tune.font = S.boot.options.font_map[t.value] || "auto"; changed(false); return; }
  if (!t.dataset || !t.dataset.bind || !S.p) return;
  let v = t.type === "checkbox" ? t.checked : t.value;
  if (t.dataset.num) v = Number(v);
  setPath(S.p, t.dataset.bind, v);
  const lab = t.closest("label") && t.closest("label").querySelector("span");
  if (t.dataset.intensity && lab) lab.textContent = "Colour intensity: " + ["Soft", "Brighter", "Bold", "Vivid"][v];
  else if (t.dataset.pctnum && lab) lab.textContent = "Text size: " + Math.round(v * 100) + "%";
  else if (t.dataset.pct && lab) lab.textContent = t.dataset.label + Math.round(v * 100) + "%";
  else if (t.dataset.label && lab) lab.textContent = t.dataset.label + Math.round(v) + " (shrinks to fit the box)";
  scheduleSave();
});

document.addEventListener("change", run(async (ev) => {
  const t = ev.target;
  if (t.id === "imgInput" && t.files[0]) {
    const fd = new FormData();
    fd.append("file", t.files[0]);
    fd.append("slide", String(S.page));
    if (t.dataset.target) fd.append("element", t.dataset.target);
    const target = t.dataset.target;
    t.value = "";
    const r = await serverEdit(() => api("POST", `/api/projects/${S.p.id}/image`, fd, true));
    if (target === "new") { S.sel = r.slides[S.page].elements.slice(-1)[0].id; renderAll(); }
    toast("Picture added.");
  } else if (t.dataset && t.dataset.bind && t.dataset.rerender) {
    await flushSave().catch(() => {}); renderPanel();
  }
}));

$("#tabs").addEventListener("click", (ev) => { const b = ev.target.closest("button[data-tab]"); if (b) { S.tab = b.dataset.tab; renderTabs(); renderPanel(); } });
$("#newTabs").addEventListener("click", (ev) => { const b = ev.target.closest("button[data-newtab]"); if (b) { S.newTab = b.dataset.newtab; renderNew(); } });
$("#newBtn").addEventListener("click", openNew);
$("#settingsBtn").addEventListener("click", actions["open-settings"]);
$("#canvaChip").addEventListener("click", () => { S.tab = "canva"; renderTabs(); renderPanel(); });
$("#pushBtn").addEventListener("click", run(actions.push));
$("#undoBtn").addEventListener("click", run(() => stepHistory(-1)));
$("#redoBtn").addEventListener("click", run(() => stepHistory(1)));
document.addEventListener("click", (ev) => { const m = $("#downloadMenu"); if (m.open && !m.contains(ev.target)) m.open = false; });

/* ---- drag to reorder slides ---- */
const strip = $("#strip");
strip.addEventListener("dragstart", (ev) => { const b = ev.target.closest(".thumb"); if (!b || S.p.type !== "presentation") return; S.dragFrom = Number(b.dataset.i); ev.dataTransfer.effectAllowed = "move"; ev.dataTransfer.setData("text/plain", String(S.dragFrom)); });
strip.addEventListener("dragover", (ev) => { const b = ev.target.closest(".thumb"); if (b && S.dragFrom !== null) { ev.preventDefault(); b.classList.add("dragover"); } });
strip.addEventListener("dragleave", (ev) => { const b = ev.target.closest(".thumb"); if (b) b.classList.remove("dragover"); });
strip.addEventListener("drop", (ev) => {
  const b = ev.target.closest(".thumb");
  if (!b || S.dragFrom === null) return;
  ev.preventDefault();
  const to = Number(b.dataset.i), from = S.dragFrom;
  S.dragFrom = null;
  if (to === from) { renderStage(); return; }
  const [slide] = S.p.slides.splice(from, 1);
  S.p.slides.splice(to, 0, slide);
  S.page = to; S.sel = null;
  changed(true);
});
strip.addEventListener("dragend", () => { S.dragFrom = null; document.querySelectorAll(".thumb.dragover").forEach((x) => x.classList.remove("dragover")); });

/* ---- editor: move and resize boxes on the slide ---- */
const overlay = $("#overlay");
overlay.addEventListener("pointerdown", (ev) => {
  const s = currentSlide();
  if (!s || !s.free) return;
  if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();  // so Delete and arrows act on the box, not a text field
  const handle = ev.target.closest(".hd");
  const box = ev.target.closest(".el");
  if (!box) { S.sel = null; renderOverlay(); renderPanel(); return; }
  const e = s.elements.find((x) => x.id === box.dataset.id);
  if (!e) return;
  if (S.sel !== e.id) { S.sel = e.id; renderOverlay(); renderPanel(); }
  const rect = $("#paper").getBoundingClientRect();
  drag = { id: e.id, mode: handle ? handle.dataset.h : "move", sx: ev.clientX, sy: ev.clientY, rect, start: { x: e.x, y: e.y, w: e.w, h: e.h }, moved: false };
  overlay.setPointerCapture(ev.pointerId);
  ev.preventDefault();
});
overlay.addEventListener("pointermove", (ev) => {
  if (!drag) return;
  const s = currentSlide();
  const e = s && s.elements.find((x) => x.id === drag.id);
  if (!e) return;
  const dx = (ev.clientX - drag.sx) / drag.rect.width, dy = (ev.clientY - drag.sy) / drag.rect.height;
  const st = drag.start, m = drag.mode, MIN = 0.03;
  let { x, y, w, h } = st;
  if (m === "move") {
    x = clamp(st.x + dx, -0.2, 1.2 - st.w); y = clamp(st.y + dy, -0.2, 1.2 - st.h);
    if (Math.abs(x + w / 2 - 0.5) < 0.008) x = 0.5 - w / 2;   // snap to the slide's centre lines
    if (Math.abs(y + h / 2 - 0.5) < 0.008) y = 0.5 - h / 2;
  } else {
    if (m.includes("e")) w = Math.max(MIN, st.w + dx);
    if (m.includes("s")) h = Math.max(MIN, st.h + dy);
    if (m.includes("w")) { w = Math.max(MIN, st.w - dx); x = st.x + (st.w - w); }
    if (m.includes("n")) { h = Math.max(MIN, st.h - dy); y = st.y + (st.h - h); }
  }
  Object.assign(e, { x: +x.toFixed(4), y: +y.toFixed(4), w: +w.toFixed(4), h: +h.toFixed(4) });
  drag.moved = true;
  const node = overlay.querySelector(`.el[data-id="${e.id}"]`);
  if (node) Object.assign(node.style, { left: e.x * 100 + "%", top: e.y * 100 + "%", width: e.w * 100 + "%", height: e.h * 100 + "%" });
});
const endDrag = () => { if (drag && drag.moved) changed(false); drag = null; };
overlay.addEventListener("pointerup", endDrag);
overlay.addEventListener("pointercancel", endDrag);
overlay.addEventListener("dblclick", () => { const t = $("#elText"); if (t) { t.focus(); t.select(); } });

/* ---- keyboard: undo/redo, nudge, delete ---- */
document.addEventListener("keydown", run(async (ev) => {
  const tag = (ev.target.tagName || "").toLowerCase();
  const typing = ["input", "textarea", "select"].includes(tag) || ev.target.isContentEditable;
  const mod = ev.ctrlKey || ev.metaKey;
  if (mod && !typing && ev.key.toLowerCase() === "z") { ev.preventDefault(); await stepHistory(ev.shiftKey ? 1 : -1); return; }
  if (mod && !typing && ev.key.toLowerCase() === "y") { ev.preventDefault(); await stepHistory(1); return; }
  if (typing || !S.sel || !el()) return;
  if (ev.key === "Delete" || ev.key === "Backspace") { ev.preventDefault(); actions["el-del"](); return; }
  const step = ev.shiftKey ? 0.02 : 0.005, e = el();
  const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
  if (moves[ev.key]) { ev.preventDefault(); e.x = +clamp(e.x + moves[ev.key][0], -0.2, 1.2 - e.w).toFixed(4); e.y = +clamp(e.y + moves[ev.key][1], -0.2, 1.2 - e.h).toFixed(4); changed(false); renderOverlay(); }
}));

window.addEventListener("beforeunload", (ev) => { if (S.saveTimer || S.saveState === "error") { ev.preventDefault(); ev.returnValue = ""; } });

/* ---------- start ---------- */
(async function init() {
  try {
    S.boot = await api("GET", "/api/bootstrap");
    S.projects = S.boot.projects; S.canva = S.boot.canva; S.settings = S.boot.settings; S.desktop = S.boot.desktop;
    const q = new URLSearchParams(location.search);
    if (q.get("signed_in")) toast("Signed in to Canva. You can push now.");
    if (q.get("auth_error")) toast(esc(q.get("auth_error")), true);
    if (q.toString()) history.replaceState({}, "", "/");
    renderAll();
    const last = localStorage.getItem("studio.last");
    const target = S.projects.find((x) => x.id === last) || S.projects[0];
    if (target) await openProject(target.id); else openNew();
  } catch (e) {
    toast("Could not start: " + esc(e.message), true);
  }
})();
