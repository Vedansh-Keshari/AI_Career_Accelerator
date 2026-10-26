"use strict";

const $ = (s, r = document) => r.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const S = {
  boot: null, projects: [], p: null, page: 0, tab: "content", count: 1,
  canva: { demo: true, signed_in: false, name: "" }, saveTimer: null, saving: null, newTab: "example",
  newType: "presentation", recent: null, pushing: false,
};

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
  toastTimer = setTimeout(() => t.classList.remove("show"), bad ? 7000 : 5000);
}
const run = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(esc(e.message), true); } };

/* ---------- project loading and saving ---------- */
function setPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  for (let i = 0; i < keys.length - 1; i++) o = o[keys[i]];
  o[keys[keys.length - 1]] = value;
}

function scheduleSave() {
  clearTimeout(S.saveTimer);
  S.saveTimer = setTimeout(() => flushSave().catch((e) => toast(esc(e.message), true)), 450);
}

async function flushSave() {
  clearTimeout(S.saveTimer);
  S.saveTimer = null;
  if (S.saving) await S.saving;
  if (!S.p) return;
  const snapshot = S.p;
  S.saving = api("PUT", `/api/projects/${snapshot.id}`, snapshot);
  try {
    const saved = await S.saving;
    snapshot.updated = saved.updated;
    updateList(saved);
  } finally { S.saving = null; }
  await refreshPreview();
}

function updateList(p) {
  const row = S.projects.find((x) => x.id === p.id);
  if (row) { row.title = p.title; row.updated = p.updated; }
  renderList();
}

async function openProject(id) {
  if (S.p) await flushSave();
  S.p = await api("GET", `/api/projects/${id}`);
  S.page = 0;
  S.count = S.p.type === "presentation" ? Math.max(1, S.p.slides.length) : S.p.type === "logo" ? 4 : 1;
  S.recent = null;
  S.tab = "content";
  localStorage.setItem("studio.last", id);
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

/* ---------- rendering ---------- */
function renderAll() {
  renderList(); renderTop(); renderStage(); renderTabs(); renderPanel();
}

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
  title.value = S.p ? S.p.title : "";
  const chip = $("#canvaChip");
  const c = S.canva;
  chip.className = "chip" + (c.signed_in ? " on" : "");
  chip.innerHTML = c.signed_in ? `<i></i>${c.demo ? "Demo Canva" : "Canva"}: ${esc(c.name || "signed in")}` : `<i></i>${c.demo ? "Demo Canva" : "Canva"}: sign in`;
  const push = $("#pushBtn");
  push.disabled = !S.p || S.pushing;
  push.textContent = S.pushing ? "Pushing..." : c.signed_in ? "Push to Canva" : "Sign in to push";
  const banner = $("#banner");
  banner.hidden = !c.demo;
  banner.textContent = c.demo ? "Demo mode: sign-in and pushes go to a local stand-in for Canva, not canva.com. Add your Canva keys to connect your real account (see the Canva tab)." : "";
  const links = $("#downloadLinks");
  if (!S.p) { links.innerHTML = "<p>Open a project first.</p>"; return; }
  const id = S.p.id;
  links.innerHTML = S.p.type === "logo"
    ? `<a href="/api/projects/${id}/export.png" download>Logo as PNG</a>`
    : `<a href="/api/projects/${id}/export.pdf" download>All pages as PDF</a><a href="/api/projects/${id}/export.zip" download>Pages as PNG images (zip)</a>`;
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
  $("#strip").innerHTML = thumbs.map((t, i) => `<button class="thumb" role="listitem" data-action="page" data-i="${i}" ${t.current ? 'aria-current="true"' : ""}><img src="${t.src}" alt="" loading="lazy"><span>${esc(t.label)}</span></button>`).join("");
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

function contentTab() {
  const p = S.p;
  if (p.type === "presentation") {
    const i = S.page, s = p.slides[i];
    if (!s) return `<p class="hint">This deck has no slides.</p><button class="btn" data-action="add-slide">Add a slide</button>`;
    return `
      <h3>Slide ${i + 1} of ${p.slides.length}</h3>
      <label class="field"><span>Title</span><input type="text" data-bind="slides.${i}.title" value="${esc(s.title)}"></label>
      <label class="field"><span>Text</span><textarea data-bind="slides.${i}.body" rows="6">${esc(s.body)}</textarea></label>
      <p class="hint">Start a line with - to make a bullet.</p>
      <label class="field"><span>Layout</span><select data-bind="slides.${i}.layout">${["auto", "title", "bullets", "statement", "cta"].map((x) => `<option value="${x}" ${x === s.layout ? "selected" : ""}>${{ auto: "Automatic", title: "Title", bullets: "Bullet list", statement: "Big statement", cta: "Call to action" }[x]}</option>`).join("")}</select></label>
      <div class="row">
        <button class="btn small" data-action="pick-image">${s.image ? "Replace image" : "Add image"}</button>
        ${s.image ? '<button class="btn small" data-action="remove-image">Remove image</button>' : ""}
        <input type="file" id="imgInput" accept="image/png,image/jpeg,image/webp,image/gif" hidden>
      </div>
      <h3>Slides</h3>
      <div class="row">
        <button class="btn small" data-action="add-slide">Add slide after</button>
        <button class="btn small" data-action="dup-slide">Duplicate</button>
        <button class="btn small" data-action="move-slide" data-dir="-1" ${i === 0 ? "disabled" : ""}>Move earlier</button>
        <button class="btn small" data-action="move-slide" data-dir="1" ${i === p.slides.length - 1 ? "disabled" : ""}>Move later</button>
        <button class="btn small danger" data-action="del-slide" ${p.slides.length < 2 ? "disabled" : ""}>Delete</button>
      </div>`;
  }
  if (p.type === "document") {
    return `
      <label class="field"><span>Document type</span><select data-bind="doc.doc_type" data-rerender="1">${opt(S.boot.options.doc_types, p.doc.doc_type)}</select></label>
      <p class="hint">Caption, Tweet and Social post become a square post; everything else is a paged document.</p>
      ${p.doc.sections.map((s, i) => `
        <div class="card">
          <label class="field"><span>Heading ${s.heading ? "" : "(optional)"}</span><input type="text" data-bind="doc.sections.${i}.heading" value="${esc(s.heading)}"></label>
          <label class="field"><span>Text</span><textarea data-bind="doc.sections.${i}.body" rows="5">${esc(s.body)}</textarea></label>
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
  const p = S.p, o = p.options, pal = S.boot.options.palettes;
  return `
    <label class="field"><span>Style</span><select data-bind="options.style">${opt(S.boot.options.styles, o.style)}</select></label>
    <div class="field"><span>Colour</span></div>
    <div class="swatches">${S.boot.options.colors.map((c) => `<button class="sw" type="button" data-action="color" data-color="${c}" style="background:${pal[c].primary}" aria-label="${c}" title="${c}" aria-pressed="${c === o.color}"></button>`).join("")}</div>
    ${p.type === "presentation" ? `<label class="field"><span>Format</span><select data-bind="options.format">${opt(S.boot.options.formats, o.format)}</select></label>` : ""}
    <label class="field"><span>Colour intensity: ${["Soft", "Brighter", "Bold", "Vivid"][p.tune.boldness]}</span><input type="range" min="0" max="3" step="1" value="${p.tune.boldness}" data-bind="tune.boldness" data-num="1" data-label="1"></label>
    <label class="field"><span>Text size: ${Math.round(p.tune.text_scale * 100)}%</span><input type="range" min="0.7" max="1.6" step="0.05" value="${p.tune.text_scale}" data-bind="tune.text_scale" data-num="1" data-label="1"></label>`;
}

function refineTab() {
  const p = S.p;
  const ideas = ["Make it brighter and bolder", "Bigger text, fill up slides that look too empty", "Use a different colour palette", "Make it elegant", "Come up with a more interesting title", "Make it blue"];
  return `
    <p class="hint">Describe a change in plain words, then apply it. Keep refining until it matches your vision.</p>
    <label class="field"><span>What should change?</span><textarea id="refineText" rows="3" placeholder="e.g. make the colours brighter and the text bigger"></textarea></label>
    <div class="chips">${ideas.map((t) => `<button type="button" data-action="idea" data-text="${esc(t)}">${esc(t)}</button>`).join("")}</div>
    <button class="btn primary" data-action="refine">Apply change</button>
    <h3>What you've changed</h3>
    ${p.history.length ? `<ul class="log">${p.history.slice().reverse().map((h) => `<li><q>${esc(h.prompt)}</q>${(h.changes || []).map(esc).join("; ")}</li>`).join("")}</ul>` : '<p class="hint">Nothing yet.</p>'}
    <p class="hint">These tweaks are rule-based (colour, boldness, size, style, title), not an AI model. Photos are added with Add image on a slide.</p>`;
}

function canvaTab() {
  const c = S.canva, p = S.p;
  const howto = `
    <details class="how"><summary>Connect your real Canva account</summary>
      <ol class="steps">
        <li>Go to <code>canva.com/developers</code> and create an integration (it needs a Canva account; some features need a Canva plan that allows it).</li>
        <li>Under Authentication, add this redirect URL: <code>${esc(location.origin)}/oauth/callback</code></li>
        <li>Enable scopes: design:meta:read, design:content:read, design:content:write, asset:read, asset:write, profile:read.</li>
        <li>Copy <code>shared/config.example.json</code> to <code>shared/config.json</code> and paste your client id and secret.</li>
        <li>Restart the app. The chip at the top will say Canva (not Demo Canva). Use Sign in to sign in on Canva's own page with your email.</li>
      </ol></details>`;
  const status = c.signed_in
    ? `<div class="status"><b>${c.demo ? "Signed in to demo Canva" : "Signed in to Canva"}${c.name ? ` as ${esc(c.name)}` : ""}</b>Pushes create a new design in this account.</div><div class="row"><button class="btn small" data-action="signout">Sign out</button></div>`
    : `<div class="status"><b>Not signed in</b>${c.demo ? "Demo mode uses a local stand-in with an email box." : "You'll sign in with your email on Canva's own page; this app never sees your password."}</div><div class="row"><button class="btn primary" data-action="signin">Sign in${c.demo ? " (demo)" : " with Canva"}</button></div>`;
  const pushes = (p.pushes || []).map((x) => `<li><span>${esc(x.title)} - ${esc(x.kind)}</span>${x.edit_url ? `<a href="${esc(x.edit_url)}" target="_blank" rel="noopener">Open</a>` : ""}</li>`).join("");
  return `
    ${status}
    <label class="field"><span>Planned finishing touch in Canva</span><select data-bind="options.feature">${opt(S.boot.options.features, p.options.feature)}</select></label>
    <p class="hint">Animation, audio and video are added inside Canva after you push.</p>
    <button class="btn primary" data-action="push" ${S.pushing ? "disabled" : ""}>${c.signed_in ? "Push this project to Canva" : "Sign in to push"}</button>
    <p class="hint" style="margin-top:8px">${p.type === "logo" ? "Logos arrive as an image design." : "Decks and documents arrive as a multi-page design built from the pages you see (pages are images, so recreate text in Canva if you need to edit it)."}</p>
    <h3>Pushed from this project</h3>
    ${pushes ? `<ul class="dlist">${pushes}</ul>` : '<p class="hint">Nothing pushed yet.</p>'}
    ${c.signed_in ? `<h3>Your recent Canva designs</h3><div id="recent">${recentHtml()}</div>` : ""}
    ${howto}`;
}

function recentHtml() {
  if (S.recent === null) return '<p class="hint">Loading...</p>';
  if (S.recent.error) return `<p class="err">${esc(S.recent.error)}</p>`;
  if (!S.recent.length) return '<p class="hint">No designs found.</p>';
  return `<ul class="dlist">${S.recent.map((d) => `<li><span>${esc(d.title)}</span>${d.edit_url ? `<a href="${esc(d.edit_url)}" target="_blank" rel="noopener">Open</a>` : ""}</li>`).join("")}</ul>`;
}

async function loadRecent() {
  try { S.recent = (await api("GET", "/api/canva/designs")).designs; }
  catch (e) { S.recent = { error: e.message }; }
  const box = $("#recent");
  if (box) box.innerHTML = recentHtml();
}

/* ---------- new project dialog ---------- */
function renderNew() {
  const body = $("#newBody");
  document.querySelectorAll("#newTabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.newtab === S.newTab)));
  if (S.newTab === "example") {
    const kind = { presentation: "Presentation", document: "Document", logo: "Logo" };
    body.innerHTML = `<p class="hint" style="margin-top:0">Each one comes from a scenario in the notes. Open one, then change anything.</p><div class="ex-grid">${S.boot.examples.map((e) => `<button class="ex" data-action="start-example" data-id="${e.id}"><b>${esc(e.name)}</b>${esc(e.description)}<em>${kind[e.kind]}</em></button>`).join("")}</div>`;
    return;
  }
  const O = S.boot.options, t = S.newType;
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
    <p class="hint">This builds an editable starter from your words using templates (it is not an AI). Replace everything with your own text.</p>
    <button class="btn primary" data-action="create-idea">Create project</button>`;
}

function openNew() { renderNew(); $("#newDlg").showModal(); }

async function afterCreate(project) {
  S.projects.unshift({ id: project.id, type: project.type, title: project.title, updated: project.updated, pushed: false });
  $("#newDlg").close();
  await openProject(project.id);
}

/* ---------- actions ---------- */
const actions = {
  "open-new": () => openNew(),
  "close-new": () => $("#newDlg").close(),
  open: (el) => openProject(el.dataset.id),
  delete: async (el) => {
    const row = S.projects.find((x) => x.id === el.dataset.id);
    if (!confirm(`Delete "${row ? row.title : "this project"}"? This cannot be undone.`)) return;
    await api("DELETE", `/api/projects/${el.dataset.id}`);
    S.projects = S.projects.filter((x) => x.id !== el.dataset.id);
    if (S.p && S.p.id === el.dataset.id) { S.p = null; if (S.projects.length) await openProject(S.projects[0].id); else renderAll(); }
    else renderList();
  },
  page: (el) => {
    const i = Number(el.dataset.i);
    if (S.p.type === "logo") { S.p.logo.variant = i; scheduleSave(); renderStage(); renderPanel(); return; }
    S.page = i; renderStage(); if (S.tab === "content" && S.p.type === "presentation") renderPanel();
  },
  "add-slide": () => { const p = S.p; p.slides.splice(S.page + 1, 0, { title: "New slide", body: "- Add a point", layout: "auto", image: "" }); S.page = Math.min(S.page + 1, p.slides.length - 1); changed(true); },
  "dup-slide": () => { const p = S.p; p.slides.splice(S.page + 1, 0, { ...p.slides[S.page] }); S.page++; changed(true); },
  "move-slide": (el) => { const d = Number(el.dataset.dir), p = S.p, j = S.page + d; [p.slides[S.page], p.slides[j]] = [p.slides[j], p.slides[S.page]]; S.page = j; changed(true); },
  "del-slide": () => { S.p.slides.splice(S.page, 1); S.page = Math.max(0, S.page - 1); changed(true); },
  "add-sec": () => { S.p.doc.sections.push({ heading: "New section", body: "" }); changed(true); },
  "del-sec": (el) => { S.p.doc.sections.splice(Number(el.dataset.i), 1); changed(true); },
  "move-sec": (el) => { const i = Number(el.dataset.i), j = i + Number(el.dataset.dir), a = S.p.doc.sections; [a[i], a[j]] = [a[j], a[i]]; changed(true); },
  "pick-image": () => $("#imgInput").click(),
  "remove-image": () => { S.p.slides[S.page].image = ""; changed(true); },
  color: (el) => { S.p.options.color = el.dataset.color; changed(true); },
  idea: (el) => { $("#refineText").value = el.dataset.text; $("#refineText").focus(); },
  refine: async () => {
    const text = $("#refineText").value.trim();
    if (!text) { toast("Describe the change you want first.", true); return; }
    await flushSave();
    const r = await api("POST", `/api/projects/${S.p.id}/refine`, { text });
    S.p = r.project; updateList(S.p);
    toast(esc(r.changes.join(" - ")));
    renderAll(); await refreshPreview();
  },
  signin: async () => { await flushSave(); location.href = "/auth/login"; },
  signout: async () => { await api("POST", "/auth/logout", {}); S.canva = { ...S.canva, signed_in: false, name: "" }; S.recent = null; renderTop(); renderPanel(); toast("Signed out of Canva."); },
  push: async () => {
    if (!S.canva.signed_in) { await actions.signin(); return; }
    S.pushing = true; renderTop(); renderPanel();
    try {
      await flushSave();
      const r = await api("POST", `/api/projects/${S.p.id}/push`, {});
      S.p.pushes = r.project.pushes; S.recent = null;
      const row = S.projects.find((x) => x.id === S.p.id); if (row) row.pushed = true;
      toast(`Pushed "${esc(r.result.title)}" as a ${esc(r.result.kind)}. ${r.result.edit_url ? `<a href="${esc(r.result.edit_url)}" target="_blank" rel="noopener">Open it in Canva</a>` : ""}`);
    } catch (e) {
      if (e.data && e.data.needs_login) { S.canva.signed_in = false; toast(esc(e.message) + " Use Sign in to continue.", true); }
      else throw e;
    } finally { S.pushing = false; renderTop(); renderList(); renderPanel(); }
  },
  "start-example": async (el) => afterCreate(await api("POST", "/api/projects", { mode: "example", example_id: el.dataset.id })),
  newtype: (el) => { S.newType = el.dataset.type; renderNew(); },
  "create-idea": async () => {
    const g = (id) => { const e = $(id); return e ? e.value : undefined; };
    const options = { style: g("#nStyle"), color: g("#nColor"), length: g("#nLength"), format: g("#nFormat"), audience: g("#nAudience"), theme: g("#nTheme") };
    Object.keys(options).forEach((k) => options[k] === undefined && delete options[k]);
    await afterCreate(await api("POST", "/api/projects", { mode: "idea", type: S.newType, prompt: g("#nPrompt"), title: g("#nTitle"), options, doc_type: g("#nDoc") || "Blog post" }));
  },
};

function changed(rerenderPanel) {
  scheduleSave();
  renderStage();
  if (rerenderPanel) renderPanel();
}

/* ---------- events ---------- */
document.addEventListener("click", (ev) => {
  const el = ev.target.closest("[data-action]");
  if (!el) return;
  const fn = actions[el.dataset.action];
  if (fn) run(fn)(el);
});

document.addEventListener("input", (ev) => {
  const el = ev.target;
  if (el.id === "title") { S.p.title = el.value; updateList(S.p); scheduleSave(); return; }
  if (!el.dataset || !el.dataset.bind || !S.p) return;
  let v = el.value;
  if (el.dataset.num) v = Number(v);
  setPath(S.p, el.dataset.bind, v);
  if (el.dataset.label) {
    const lab = el.closest("label").querySelector("span");
    if (el.dataset.bind === "tune.boldness") lab.textContent = "Colour intensity: " + ["Soft", "Brighter", "Bold", "Vivid"][v];
    else lab.textContent = "Text size: " + Math.round(v * 100) + "%";
  }
  scheduleSave();
});

document.addEventListener("change", run(async (ev) => {
  const el = ev.target;
  if (el.id === "imgInput" && el.files[0]) {
    await flushSave();
    const fd = new FormData();
    fd.append("file", el.files[0]);
    fd.append("slide", String(S.page));
    S.p = await api("POST", `/api/projects/${S.p.id}/image`, fd, true);
    renderPanel(); await refreshPreview();
    toast("Image added to the slide.");
  } else if (el.dataset && el.dataset.bind && (el.tagName === "SELECT" && el.dataset.rerender)) {
    await flushSave(); renderPanel();
  }
}));

$("#tabs").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-tab]");
  if (b) { S.tab = b.dataset.tab; renderTabs(); renderPanel(); }
});
$("#newTabs").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-newtab]");
  if (b) { S.newTab = b.dataset.newtab; renderNew(); }
});
$("#newBtn").addEventListener("click", openNew);
$("#canvaChip").addEventListener("click", () => { S.tab = "canva"; renderTabs(); renderPanel(); });
$("#pushBtn").addEventListener("click", run(actions.push));
document.addEventListener("click", (ev) => { const m = $("#downloadMenu"); if (m.open && !m.contains(ev.target)) m.open = false; });

/* ---------- start ---------- */
(async function init() {
  try {
    S.boot = await api("GET", "/api/bootstrap");
    S.projects = S.boot.projects;
    S.canva = S.boot.canva;
    const q = new URLSearchParams(location.search);
    if (q.get("signed_in")) toast("Signed in to Canva. You can push now.");
    if (q.get("auth_error")) toast(esc(q.get("auth_error")), true);
    if (q.toString()) history.replaceState({}, "", "/");
    renderAll();
    const last = localStorage.getItem("studio.last");
    const target = S.projects.find((x) => x.id === last) || S.projects[0];
    if (target) await openProject(target.id);
    else openNew();
  } catch (e) {
    toast("Could not start: " + esc(e.message), true);
  }
})();
