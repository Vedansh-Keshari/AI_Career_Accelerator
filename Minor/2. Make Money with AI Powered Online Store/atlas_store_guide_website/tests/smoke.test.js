// Smoke tests for the guide. Run with: npm test
// Loads index.html in jsdom, runs the real scripts, and checks behaviour.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");

// Build a page with the local scripts inlined and external links removed.
function pageHtml() {
  return read("index.html")
    .replace(/<link[^>]*>/g, "")
    .replace(/<script src="([^"]+)"><\/script>/g, (_, src) => `<script>${read(src)}</script>`);
}

function boot({ hash = "", storage = null } = {}) {
  const dom = new JSDOM(pageHtml(), {
    url: "http://localhost/" + hash,
    runScripts: "dangerously",
    pretendToBeVisual: true,
    beforeParse(window) {
      window.confirm = () => true;
      window.scrollTo = () => {};
      window.print = () => { window.__printed = true; };
      if (storage) {
        for (const [k, v] of Object.entries(storage)) window.localStorage.setItem(k, v);
      }
    },
  });
  return dom;
}

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms));
const $ = (dom, sel) => dom.window.document.querySelector(sel);
const $$ = (dom, sel) => Array.from(dom.window.document.querySelectorAll(sel));

// ---------- Content ----------

test("content: 11 chapters, ids in order, valid types", () => {
  const dom = boot();
  const { chapters } = dom.window.GUIDE;
  assert.equal(chapters.length, 11);
  chapters.forEach((c, i) => {
    assert.equal(c.id, i + 1, "ids run 1..N with no gaps");
    assert.ok(["action", "overview"].includes(c.type), `chapter ${c.id} type`);
    assert.ok(c.title && c.short, `chapter ${c.id} has title and short label`);
    assert.ok(c.steps.length > 0, `chapter ${c.id} has steps`);
  });
});

test("content: 45 trackable steps across 8 action chapters", () => {
  const dom = boot();
  const action = dom.window.GUIDE.chapters.filter((c) => c.type === "action");
  assert.equal(action.length, 8);
  assert.equal(action.reduce((n, c) => n + c.steps.length, 0), 45);
});

test("content: no leftover source artefacts (stray hyphens, tildes, markdown stars)", () => {
  const src = read("js/content.js");
  assert.ok(!/Don-t|Here-s|What-s/.test(src));
  assert.ok(!/(^|[^~])~(?!~)[a-z]/i.test(src.replace(/~~/g, "")), "single ~ markers");
});

// ---------- Rendering ----------

test("opens on chapter 1 as an overview without checkboxes", () => {
  const dom = boot();
  assert.equal($$(dom, ".chapter-link").length, 11);
  assert.match($(dom, "#ch-title").textContent, /Trailer/);
  assert.equal($$(dom, ".step-input").length, 0);
  assert.equal($$(dom, ".points li").length, 6);
  assert.equal($(dom, "#tracker-pct").textContent, "0%");
  assert.equal($(dom, "#tracker-count").textContent, "0 of 45 steps done");
});

test("strikethrough and bold markup render safely", () => {
  const dom = boot();
  assert.equal($$(dom, ".points s").length, 4, "four struck words in the trailer");
  const dom4 = boot({ hash: "#chapter-4" });
  assert.equal($$(dom4, ".step-text strong")[0].textContent, "Carpet");
  assert.equal($$(dom4, "script").length, 2, "no injected script elements");
});

test("hash routes to the right chapter; bad hash falls back", () => {
  const a = boot({ hash: "#chapter-5" });
  assert.match($(a, "#ch-title").textContent, /product page/i);
  assert.equal($$(a, ".step-input").length, 4);
  assert.equal($$(a, ".sub li").length, 12, "12 product-page elements");
  const b = boot({ hash: "#chapter-99" });
  assert.match($(b, "#ch-title").textContent, /Trailer/);
});

test("chapter 9 shows the bundle fix as a highlighted callout", () => {
  const dom = boot({ hash: "#chapter-9" });
  const fix = $(dom, ".step-fix");
  assert.ok(fix);
  assert.match(fix.textContent, /^Fix:/);
  assert.match(fix.textContent, /specific collection/);
});

// ---------- Progress ----------

test("ticking a step updates counts, rail, tracker and storage", async () => {
  const dom = boot({ hash: "#chapter-2" });
  const boxes = $$(dom, ".step-input");
  assert.equal(boxes.length, 6);
  boxes[0].click();
  boxes[1].click();
  assert.equal($(dom, "#ch-count").textContent, "2 of 6 steps done");
  assert.equal($(dom, "#tracker-count").textContent, "2 of 45 steps done");
  assert.equal($(dom, "#tracker-pct").textContent, "4%");
  assert.equal($(dom, '.chapter-link[data-index="1"] .chapter-count').textContent, "2/6");
  assert.equal($(dom, '[data-block="2"] .lit').style.opacity, String(2 / 6));
  const saved = JSON.parse(dom.window.localStorage.getItem("atlas-guide:v1"));
  assert.deepEqual(Object.keys(saved.done).sort(), ["2:0", "2:1"]);
  boxes[1].click();
  assert.equal($(dom, "#ch-count").textContent, "1 of 6 steps done");
});

test("progress survives a reload", () => {
  const stored = JSON.stringify({ done: { "2:0": true, "2:3": true }, last: 1 });
  const dom = boot({ storage: { "atlas-guide:v1": stored } });
  // no hash: restores the last chapter (index 1 = chapter 2)
  assert.match($(dom, "#ch-title").textContent, /Shopify store starts here/);
  assert.equal($$(dom, ".step-input:checked").length, 2);
  assert.equal($(dom, "#tracker-count").textContent, "2 of 45 steps done");
});

test("corrupt saved data does not break the page", () => {
  const dom = boot({ storage: { "atlas-guide:v1": "{not json" } });
  assert.equal($$(dom, ".chapter-link").length, 11);
  assert.equal($(dom, "#tracker-pct").textContent, "0%");
});

test("mark all done, clear all, and 100% overall", () => {
  const dom = boot({ hash: "#chapter-8" });
  $(dom, "#toggle-all").click();
  assert.equal($$(dom, ".step-input:checked").length, 4);
  assert.equal($(dom, "#toggle-all").textContent, "Clear all steps");
  assert.equal($(dom, '.chapter-link[data-index="7"] .chapter-count').textContent, "Done");
  $(dom, "#toggle-all").click();
  assert.equal($$(dom, ".step-input:checked").length, 0);

  // finish every action chapter
  for (const id of [2, 4, 5, 6, 7, 8, 9, 10]) {
    dom.window.location.hash = "#chapter-" + id;
    dom.window.dispatchEvent(new dom.window.HashChangeEvent("hashchange"));
    $(dom, "#toggle-all").click();
  }
  assert.equal($(dom, "#tracker-pct").textContent, "100%");
  assert.equal($(dom, "#tracker-count").textContent, "45 of 45 steps done");
});

test("reset progress clears everything", () => {
  const stored = JSON.stringify({ done: { "4:0": true, "4:1": true }, last: 3 });
  const dom = boot({ hash: "#chapter-4", storage: { "atlas-guide:v1": stored } });
  assert.equal($$(dom, ".step-input:checked").length, 2);
  $(dom, '[data-global="reset"]').click();
  assert.equal($$(dom, ".step-input:checked").length, 0);
  assert.equal($(dom, "#tracker-pct").textContent, "0%");
  assert.deepEqual(JSON.parse(dom.window.localStorage.getItem("atlas-guide:v1")).done, {});
});

// ---------- Navigation and tools ----------

test("keyboard arrows move between chapters; pager links exist", () => {
  const dom = boot({ hash: "#chapter-3" });
  assert.equal($(dom, ".pager-prev").getAttribute("href"), "#chapter-2");
  assert.equal($(dom, ".pager-next").getAttribute("href"), "#chapter-4");
  dom.window.document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
  assert.equal(dom.window.location.hash, "#chapter-4");
  const first = boot({ hash: "#chapter-1" });
  assert.equal($(first, ".pager-prev"), null, "no previous link on the first chapter");
  const last = boot({ hash: "#chapter-11" });
  assert.equal($(last, ".pager-next"), null, "no next link on the last chapter");
});

test("mobile drawer opens and closes", () => {
  const dom = boot();
  const rail = $(dom, "#rail");
  const btn = $(dom, "#menu-btn");
  btn.click();
  assert.ok(rail.classList.contains("open"));
  assert.equal(btn.getAttribute("aria-expanded"), "true");
  assert.equal($(dom, "#scrim").hidden, false);
  dom.window.document.dispatchEvent(new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.ok(!rail.classList.contains("open"));
  assert.equal(btn.getAttribute("aria-expanded"), "false");
  assert.equal($(dom, "#scrim").hidden, true);
});

test("copy chapter text uses the clipboard", async () => {
  const dom = boot({ hash: "#chapter-9" });
  let copied = "";
  Object.defineProperty(dom.window.navigator, "clipboard", {
    value: { writeText: (t) => { copied = t; return Promise.resolve(); } },
  });
  $(dom, '[data-action="copy"]').click();
  await tick(5);
  assert.match(copied, /^# This one trick doubles your sales instantly/);
  assert.match(copied, /Fix: Select a specific collection/);
  assert.match($(dom, "#toast").textContent, /copied/);
});

test("print view lists every chapter with check state", () => {
  const stored = JSON.stringify({ done: { "2:0": true }, last: 0 });
  const dom = boot({ storage: { "atlas-guide:v1": stored } });
  $(dom, '[data-global="print"]').click();
  assert.ok(dom.window.__printed);
  assert.equal($$(dom, "#print-view h2").length, 11);
  assert.match($(dom, "#print-view").textContent, /\u2611 Open the Shopify landing page/);
  assert.match($(dom, "#print-view").textContent, /\u2610 Choose the Free Trial/);
});

test("html: accessibility basics are present", () => {
  const html = read("index.html");
  assert.match(html, /<html lang="en">/);
  assert.match(html, /name="viewport"/);
  assert.match(html, /class="skip"/);
  const css = read("css/styles.css");
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /:focus-visible/);
});
