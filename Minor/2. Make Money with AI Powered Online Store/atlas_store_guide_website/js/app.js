/* Shopify + Atlas: AI store guide
   Plain JavaScript, no dependencies, works from file:// or any web server. */
(function () {
  "use strict";

  var GUIDE = window.GUIDE;
  var chapters = (GUIDE && GUIDE.chapters) || [];
  var STORAGE_KEY = "atlas-guide:v" + ((GUIDE && GUIDE.version) || 1);

  var state = { done: {}, last: 0 };
  var current = 0;
  var toastTimer = null;

  var $nav = document.getElementById("chapter-nav");
  var $chapter = document.getElementById("chapter");
  var $rail = document.getElementById("rail");
  var $scrim = document.getElementById("scrim");
  var $menuBtn = document.getElementById("menu-btn");
  var $toast = document.getElementById("toast");
  var $print = document.getElementById("print-view");

  if (!chapters.length || !$chapter) { return; }

  /* ---------- Helpers ---------- */

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Escape first, then allow only **bold** and ~~strike~~.
  function fmt(s) {
    return esc(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/~~(.+?)~~/g, "<s>$1</s>");
  }

  function strip(s) {
    return String(s).replace(/\*\*(.+?)\*\*/g, "$1").replace(/~~(.+?)~~/g, "$1");
  }

  function norm(step) {
    return typeof step === "string" ? { t: step } : step;
  }

  function isAction(ch) { return ch.type === "action"; }

  function key(ch, i) { return ch.id + ":" + i; }

  function chapterDone(ch) {
    var n = 0;
    ch.steps.forEach(function (_, i) { if (state.done[key(ch, i)]) { n++; } });
    return n;
  }

  function totals() {
    var done = 0, all = 0;
    chapters.forEach(function (ch) {
      if (!isAction(ch)) { return; }
      all += ch.steps.length;
      done += chapterDone(ch);
    });
    return { done: done, all: all, pct: all ? Math.round((done / all) * 100) : 0 };
  }

  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  /* ---------- Storage (never fatal) ---------- */

  function load() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) { return; }
      var p = JSON.parse(raw);
      if (p && typeof p.done === "object" && p.done) { state.done = p.done; }
      if (p && typeof p.last === "number") { state.last = p.last; }
    } catch (e) { /* private mode or blocked storage: run without saving */ }
  }

  function save() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) { /* ignore */ }
  }

  /* ---------- Rendering ---------- */

  function renderNav() {
    $nav.innerHTML = chapters.map(function (ch, i) {
      return '<a class="chapter-link" href="#chapter-' + ch.id + '" data-index="' + i + '">' +
        '<span class="chapter-num">' + ch.id + "</span>" +
        '<span class="chapter-title">' + esc(ch.title) + "</span>" +
        '<span class="chapter-count"></span></a>';
    }).join("");
  }

  function stepHtml(ch, step, i) {
    var s = norm(step);
    var k = key(ch, i);
    var checked = state.done[k] ? " checked" : "";
    var cls = "step" + (state.done[k] ? " is-done" : "") + (s.fix ? " is-fix" : "");
    var html = '<li class="' + cls + '" data-key="' + k + '">' +
      '<label class="step-label">' +
      '<input class="step-input" type="checkbox" data-key="' + k + '"' + checked + ">" +
      '<span class="box" aria-hidden="true"></span>' +
      '<span class="step-text">' + fmt(s.t) + "</span></label>";
    if (s.sub && s.sub.length) {
      html += '<ul class="sub">' + s.sub.map(function (x) { return "<li>" + fmt(x) + "</li>"; }).join("") + "</ul>";
    }
    if (s.fix) {
      html += '<p class="step-fix"><strong>Fix:</strong> ' + fmt(s.fix) + "</p>";
    }
    return html + "</li>";
  }

  function renderChapter() {
    var ch = chapters[current];
    var prev = chapters[current - 1];
    var next = chapters[current + 1];
    var html = '<header>' +
      '<p class="ch-kicker">Chapter ' + ch.id + " of " + chapters.length + "</p>" +
      '<h2 class="ch-title" id="ch-title" tabindex="-1">' + esc(ch.title) + "</h2></header>";

    if (isAction(ch)) {
      html += '<div class="ch-bar"><div class="ch-meter" aria-hidden="true"><span id="ch-fill"></span></div>' +
        '<p class="ch-count" id="ch-count"></p></div>' +
        '<div class="ch-actions">' +
        '<button class="btn" type="button" data-action="toggle-all" id="toggle-all"></button>' +
        '<button class="btn" type="button" data-action="copy">Copy chapter text</button></div>' +
        '<ol class="steps">' + ch.steps.map(function (s, i) { return stepHtml(ch, s, i); }).join("") + "</ol>";
    } else {
      html += '<p class="ch-note">Overview chapter. Nothing to tick here, just read before you start.</p>' +
        '<div class="ch-actions"><button class="btn" type="button" data-action="copy">Copy chapter text</button></div>' +
        '<ul class="points">' + ch.steps.map(function (s) { return "<li>" + fmt(norm(s).t) + "</li>"; }).join("") + "</ul>";
    }

    html += '<nav class="pager" aria-label="Chapter navigation">';
    if (prev) {
      html += '<a class="pager-prev" href="#chapter-' + prev.id + '"><small>Previous</small><strong>' + esc(prev.title) + "</strong></a>";
    }
    if (next) {
      html += '<a class="pager-next" href="#chapter-' + next.id + '"><small>Next</small><strong>' + esc(next.title) + "</strong></a>";
    }
    html += "</nav>";

    $chapter.innerHTML = html;
    refresh();
  }

  // Updates everything that depends on progress without rebuilding the step list.
  function refresh() {
    var t = totals();
    var ch = chapters[current];

    // Rail
    var links = $nav.querySelectorAll(".chapter-link");
    chapters.forEach(function (c, i) {
      var a = links[i];
      if (!a) { return; }
      var count = a.querySelector(".chapter-count");
      var done = false;
      if (isAction(c)) {
        var n = chapterDone(c);
        done = n === c.steps.length;
        count.textContent = done ? "Done" : n + "/" + c.steps.length;
      } else {
        count.textContent = "Read";
      }
      a.classList.toggle("is-done", done);
      if (i === current) { a.setAttribute("aria-current", "page"); } else { a.removeAttribute("aria-current"); }
    });

    // Storefront sketch
    chapters.forEach(function (c) {
      if (!isAction(c)) { return; }
      var nodes = document.querySelectorAll('[data-block="' + c.id + '"] .lit');
      var ratio = c.steps.length ? chapterDone(c) / c.steps.length : 0;
      for (var i = 0; i < nodes.length; i++) { nodes[i].style.opacity = String(ratio); }
    });

    setText("tracker-pct", t.pct + "%");
    setText("tracker-count", t.done + " of " + plural(t.all, "step") + " done");
    setText("topbar-pct", t.pct + "%");
    setText("topbar-title", "Chapter " + ch.id + " of " + chapters.length);
    var fill = document.getElementById("topbar-fill");
    if (fill) { fill.style.width = t.pct + "%"; }

    // Chapter header
    if (isAction(ch)) {
      var n2 = chapterDone(ch);
      setText("ch-count", n2 + " of " + plural(ch.steps.length, "step") + " done");
      var cf = document.getElementById("ch-fill");
      if (cf) { cf.style.width = Math.round((n2 / ch.steps.length) * 100) + "%"; }
      setText("toggle-all", n2 === ch.steps.length ? "Clear all steps" : "Mark all steps done");
    }
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) { el.textContent = text; }
  }

  /* ---------- Navigation ---------- */

  function indexFromHash() {
    var m = /^#chapter-(\d+)$/.exec(window.location.hash || "");
    if (!m) { return -1; }
    var id = parseInt(m[1], 10);
    for (var i = 0; i < chapters.length; i++) { if (chapters[i].id === id) { return i; } }
    return -1;
  }

  function go(i, focus) {
    current = Math.max(0, Math.min(chapters.length - 1, i));
    state.last = current;
    save();
    renderChapter();
    closeRail();
    window.scrollTo(0, 0);
    if (focus) {
      var h = document.getElementById("ch-title");
      if (h && h.focus) { try { h.focus({ preventScroll: true }); } catch (e) { h.focus(); } }
    }
  }

  function onHashChange() {
    var i = indexFromHash();
    go(i === -1 ? current : i, true);
  }

  /* ---------- Rail drawer (small screens) ---------- */

  function openRail() {
    $rail.classList.add("open");
    $scrim.hidden = false;
    $menuBtn.setAttribute("aria-expanded", "true");
    var cur = $nav.querySelector('[aria-current="page"]');
    if (cur && cur.focus) { cur.focus(); }
  }

  function closeRail() {
    if (!$rail.classList.contains("open")) { return; }
    $rail.classList.remove("open");
    $scrim.hidden = true;
    $menuBtn.setAttribute("aria-expanded", "false");
  }

  /* ---------- Actions ---------- */

  function toast(msg) {
    $toast.textContent = msg;
    $toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { $toast.classList.remove("show"); }, 2400);
  }

  function chapterText(ch) {
    var lines = ["# " + ch.title, ""];
    ch.steps.forEach(function (s, i) {
      var st = norm(s);
      var prefix = isAction(ch) ? (i + 1) + ". " : "- ";
      lines.push(prefix + strip(st.t));
      if (st.sub) { st.sub.forEach(function (x) { lines.push("   - " + strip(x)); }); }
      if (st.fix) { lines.push("   Fix: " + strip(st.fix)); }
    });
    return lines.join("\n");
  }

  function copyText(text) {
    var done = function () { toast("Chapter text copied"); };
    var fail = function () { toast("Copy is blocked here. Select the text and copy it manually."); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fail);
      return;
    }
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand && document.execCommand("copy");
      document.body.removeChild(ta);
      if (ok) { done(); } else { fail(); }
    } catch (e) { fail(); }
  }

  function toggleAll() {
    var ch = chapters[current];
    var all = chapterDone(ch) === ch.steps.length;
    ch.steps.forEach(function (_, i) {
      if (all) { delete state.done[key(ch, i)]; } else { state.done[key(ch, i)] = true; }
    });
    save();
    var boxes = $chapter.querySelectorAll(".step-input");
    for (var i = 0; i < boxes.length; i++) {
      boxes[i].checked = !all;
      boxes[i].closest(".step").classList.toggle("is-done", !all);
    }
    refresh();
  }

  function resetProgress() {
    var ok = window.confirm ? window.confirm("Clear all ticked steps? This cannot be undone.") : true;
    if (!ok) { return; }
    state.done = {};
    save();
    renderChapter();
    toast("Progress cleared");
  }

  function buildPrint() {
    if (!$print) { return; }
    var html = "<h1>" + esc(GUIDE.title || "Guide") + "</h1>";
    chapters.forEach(function (ch) {
      html += "<h2>" + ch.id + ". " + esc(ch.title) + "</h2><ul>";
      ch.steps.forEach(function (s, i) {
        var st = norm(s);
        var mark = isAction(ch) ? (state.done[key(ch, i)] ? "\u2611 " : "\u2610 ") : "\u2022 ";
        html += "<li>" + mark + fmt(st.t);
        if (st.sub) { html += '<ul class="p-sub">' + st.sub.map(function (x) { return "<li>" + fmt(x) + "</li>"; }).join("") + "</ul>"; }
        if (st.fix) { html += '<div class="p-fix">Fix: ' + fmt(st.fix) + "</div>"; }
        html += "</li>";
      });
      html += "</ul>";
    });
    $print.innerHTML = html;
  }

  /* ---------- Events ---------- */

  $chapter.addEventListener("change", function (e) {
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains("step-input")) { return; }
    var k = t.getAttribute("data-key");
    if (t.checked) { state.done[k] = true; } else { delete state.done[k]; }
    var li = t.closest(".step");
    if (li) { li.classList.toggle("is-done", t.checked); }
    save();
    refresh();
  });

  $chapter.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("[data-action]") : null;
    if (!btn) { return; }
    var action = btn.getAttribute("data-action");
    if (action === "toggle-all") { toggleAll(); }
    if (action === "copy") { copyText(chapterText(chapters[current])); }
  });

  document.querySelector(".rail-foot").addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("[data-global]") : null;
    if (!btn) { return; }
    var which = btn.getAttribute("data-global");
    if (which === "print") { buildPrint(); window.print(); }
    if (which === "reset") { resetProgress(); }
  });

  $menuBtn.addEventListener("click", function () {
    if ($rail.classList.contains("open")) { closeRail(); } else { openRail(); }
  });
  $scrim.addEventListener("click", function () { closeRail(); $menuBtn.focus(); });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && $rail.classList.contains("open")) { closeRail(); $menuBtn.focus(); return; }
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) { return; }
    var tag = (e.target && e.target.tagName) || "";
    if (tag === "TEXTAREA" || tag === "SELECT" || (tag === "INPUT" && e.target.type !== "checkbox")) { return; }
    if (e.key === "ArrowRight" && current < chapters.length - 1) { window.location.hash = "#chapter-" + chapters[current + 1].id; }
    if (e.key === "ArrowLeft" && current > 0) { window.location.hash = "#chapter-" + chapters[current - 1].id; }
  });

  window.addEventListener("hashchange", onHashChange);
  window.addEventListener("beforeprint", buildPrint);

  /* ---------- Start ---------- */

  load();
  renderNav();
  var start = indexFromHash();
  if (start === -1) { start = state.last >= 0 && state.last < chapters.length ? state.last : 0; }
  go(start, false);
  buildPrint();
})();
