"""Template-based starter content and prompt refinements.

This is NOT an AI model. It builds an editable starter outline from the prompt and the
options (so a blank page is never the starting point) and applies simple tweaks such as
"brighter", "bigger text" or "different colour". Everything it makes is meant to be edited.
"""
from __future__ import annotations

import json
import re

from . import options as O
from .models import blank_project, clean_project, now
from .paths import DATA_DIR
from .render import pick_icon

SMALL = {"a", "an", "the", "of", "and", "or", "to", "for", "in", "on", "at", "with", "your", "vs"}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def smart_title(text: str) -> str:
    words = text.strip().split()
    out = []
    for i, w in enumerate(words):
        out.append(w if (i and w.lower() in SMALL) else w[:1].upper() + w[1:])
    return " ".join(out)


def topic_from(prompt: str) -> str:
    prompt = (prompt or "").strip()
    if not prompt:
        return "Your topic"
    m = re.search(r"topic is\s+(?:the\s+)?(.+?)(?:,|\.|;|$)", prompt, re.I)
    if not m:
        m = re.search(r"\b(?:about|on)\s+(?:the\s+)?(.+?)(?:,|\.|;|$)", prompt, re.I)
    topic = m.group(1) if m else " ".join(prompt.split()[:6])
    topic = re.sub(r"\s+", " ", topic).strip(" .,")
    return smart_title(topic) if topic else "Your topic"


def _count_in(prompt: str, default: int) -> int:
    m = re.search(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s+(?:benefits|reasons|tips|ways|points|ideas|things|steps)", prompt, re.I)
    if not m:
        return default
    raw = m.group(1).lower()
    return max(1, min(10, int(raw) if raw.isdigit() else NUMBER_WORDS[raw]))


# ---------------------------------------------------------------- presentations
TITLE_BODY = {
    "Casual": "A quick, friendly look",
    "Professional": "An overview for decision-makers",
    "Educational": "A short lesson to learn from",
}


def _pool(T: str, t: str):
    return [
        ("What is {t}?", "- Explain {t} in one clear sentence\n- Say where it comes from\n- Say who it is for"),
        ("Top 3 things to know about {t}", "- Your first key point\n- Your second key point\n- Your third key point"),
        ("Why it matters", "Finish this sentence: {t} matters because…"),
        ("How to get started", "- Pick one small first step\n- Say what you need\n- Say how long it takes"),
        ("What people get wrong", "- Name a common myth\n- Say what is true instead"),
        ("Where it came from", "- A short origin story\n- One turning point worth remembering"),
        ("Key ideas", "- Idea one\n- Idea two\n- Idea three"),
        ("A real example", "Describe one real story that shows {t} in action."),
        ("Challenges to expect", "- The hardest part\n- How to get past it"),
        ("Tips that help", "- A tip you wish you knew sooner\n- A shortcut worth sharing"),
        ("Tools and resources", "- A tool to try\n- A place to learn more"),
        ("Step by step", "- Step one\n- Step two\n- Step three"),
        ("Questions people ask", "- A question you often hear\n- Your short answer"),
        ("Results to expect", "- What changes in a week\n- What changes in a month"),
        ("Key takeaways", "- The one thing to remember\n- The one thing to do next"),
    ]


def generate_presentation(prompt: str, options: dict) -> tuple[str, list[dict]]:
    topic = topic_from(prompt)
    t = topic.lower()
    lo, hi = O.LENGTHS.get(options.get("length", ""), (6, 8))
    n = max(3, (lo + hi + 1) // 2 if hi - lo > 2 else hi)
    title_body = TITLE_BODY.get(options.get("audience", "Casual"), "")
    slides = [{"title": topic, "body": title_body, "layout": "title", "image": ""}]
    pool = _pool(topic, t)
    middle = max(1, n - 2)
    for head, body in pool[:middle]:
        slides.append({"title": head.format(T=topic, t=t), "body": body.format(T=topic, t=t), "layout": "auto", "image": ""})
    slides.append({"title": "Call to action", "body": "Say what you want people to do next.", "layout": "cta", "image": ""})
    return topic, slides


# ---------------------------------------------------------------- documents
def skeleton(doc_type: str, T: str, t: str, prompt: str) -> list[dict]:
    S = lambda h, b: {"heading": h, "body": b}  # noqa: E731
    if doc_type == "Blog post":
        n = _count_in(prompt, 3)
        secs = [S("Introduction", f"Open with a short hook about {t}. Say what readers will get from this post.")]
        secs += [S(f"Reason {i}", "Explain this point in two or three sentences. Add an example or a number.") for i in range(1, n + 1)]
        secs += [S("Key takeaways", "- The first thing to remember\n- The second thing to remember\n- One action to take today"),
                 S("Conclusion", f"Close with one clear next step for anyone interested in {t}.")]
        return secs
    table = {
        "Pitch": [S("The problem", "Who has it and why it hurts."), S("The idea", f"What {t} does about it."), S("Why now", "What changed that makes this the right time."), S("Proof", "One number, quote or result."), S("The ask", "What you need and what happens next.")],
        "Summary": [S("Overview", f"One paragraph on {t}."), S("Key points", "- Point one\n- Point two\n- Point three"), S("Next steps", "- Who does what, and by when")],
        "Caption": [S("", f"{T} - say it in one line.")],
        "Tweet": [S("", f"{T}: one clear thought, short enough to read in a breath.")],
        "Social post": [S("", f"{T}\n\nShare one useful idea, then ask your audience a question.")],
        "Outline": [S("I. Opening", "- Hook\n- Purpose"), S("II. Main points", "- Point one\n- Point two\n- Point three"), S("III. Closing", "- Summary\n- Call to action")],
        "Email": [S("", "Hi [name],\n\nOpening line that says why you are writing.\n\nThe main thing you need them to know or do.\n\nThanks,\n[your name]")],
        "Description": [S("What it is", f"Describe {t} in two sentences."), S("Key features", "- Feature one\n- Feature two\n- Feature three"), S("Who it is for", "Name the person who benefits most.")],
        "Letter": [S("", "Dear [name],\n\nOpening paragraph: why you are writing.\n\nMiddle paragraph: the details.\n\nClosing paragraph: what happens next.\n\nSincerely,\n[your name]")],
        "Article": [S("Lede", f"The most interesting fact about {t}, in two sentences."), S("Background", "What readers need to know first."), S("What matters most", "- Point one\n- Point two\n- Point three"), S("What comes next", "Where this goes from here.")],
        "Itinerary": [S("Day 1", "- Morning: \n- Afternoon: \n- Evening: "), S("Day 2", "- Morning: \n- Afternoon: \n- Evening: "), S("Day 3", "- Morning: \n- Afternoon: \n- Evening: ")],
        "Strategy": [S("Goal", "One sentence on what success looks like."), S("Audience", "Who this is for."), S("Approach", "- Move one\n- Move two\n- Move three"), S("Timeline", "- Week 1\n- Week 4\n- Week 12"), S("How we will measure it", "- Metric one\n- Metric two")],
        "Story": [S("Beginning", "Introduce who and where."), S("Middle", "Something goes wrong or changes."), S("End", "How it resolves and what changed.")],
        "Script": [S("Scene 1", "NARRATOR: Open with the line that sets the scene."), S("Scene 2", "NARRATOR: The main message.\nPERSON: A reaction or question."), S("Scene 3", "NARRATOR: Closing line and call to action.")],
    }
    return table.get(doc_type, table["Summary"])


def generate_document(prompt: str, doc_type: str, options: dict) -> tuple[str, list[dict]]:
    topic = topic_from(prompt)
    return topic, skeleton(doc_type, topic, topic.lower(), prompt)


# ---------------------------------------------------------------- logos
BRAND_STOP = {"that", "which", "who", "where", "for", "selling", "sells", "sell", "in", "on", "with", "and", "is", "are",
              "offering", "offers", "making", "makes", "from", "to", "at", "of", "serving", "serves"}


def _brand_from(prompt: str) -> str:
    m = re.search(r"(?:called|named|name is|brand is)\s+[\"“'‘]([^\"”'’]{1,40})[\"”'’]", prompt, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:called|named|name is|brand is)\s+(.+)", prompt, re.I)
    if not m:
        return ""
    words = []
    for tok in m.group(1).replace(",", " ,").split():
        bare = tok.strip(".,;:!?")
        if tok.startswith(",") or bare.lower() in BRAND_STOP and bare != "&":
            break
        words.append(bare)
        if len(words) >= 4 or tok.endswith((".", ";", "!")):
            break
    return " ".join(w for w in words if w).strip()


def generate_logo(prompt: str) -> dict:
    brand = _brand_from(prompt)
    return {"brand": brand or "Your Brand", "tagline": "", "description": prompt.strip(), "icon": "auto", "variant": 0}


# ---------------------------------------------------------------- refine
TITLE_PATTERNS = ["{T}, Made Simple", "The Little Guide to {T}", "{T}: Start Here", "Why {T} Deserves Your Attention"]


def refine(project: dict, text: str) -> tuple[dict, list[str]]:
    """Apply simple tweaks described in plain words. Returns (project, what changed)."""
    project = clean_project(project)
    text = (text or "").strip()
    low = text.lower()
    changes: list[str] = []
    opts, tune = project["options"], project["tune"]

    for c in O.COLORS:
        if re.search(rf"\b{c.lower()}\b", low) and re.search(r"colou?r|palette|make it|switch|use|go|theme", low):
            if opts["color"] != c:
                opts["color"] = c
                changes.append(f"Colour set to {c}")
            break
    else:
        if re.search(r"(different|new|another|change|fresh).{0,20}(colou?r|palette)", low):
            i = (O.COLORS.index(opts["color"]) + 3) % len(O.COLORS)
            opts["color"] = O.COLORS[i]
            changes.append(f"Switched palette to {O.COLORS[i]}")
    if re.search(r"\b(bright|brighter|bolder|vibrant|vivid|saturat\w*|colou?rful|pop)\b", low):
        if tune["boldness"] < 3:
            tune["boldness"] += 1
            changes.append("Made the colours brighter and bolder")
    if re.search(r"readable|larger|bigger|font size|too small|empty|fill up|fill the", low):
        tune["text_scale"] = round(min(1.6, tune["text_scale"] + 0.15), 2)
        changes.append("Increased text size")
    if re.search(r"smaller text|too big|less crowded|less text", low):
        tune["text_scale"] = round(max(0.7, tune["text_scale"] - 0.15), 2)
        changes.append("Reduced text size")
    for s in O.STYLES:
        if re.search(rf"(?:make it|switch to|use|go|try|more)\s+(?:a\s+)?(?:more\s+)?{s.lower()}\b(?!er)", low) or re.search(rf"\b{s.lower()}\s+(?:style|look|vibe|feel|design)", low):
            if opts["style"] != s:
                opts["style"] = s
                changes.append(f"Style set to {s}")
            break
    if re.search(r"title|headline", low) and re.search(r"interest|different|better|catchy|generic|new|punchy", low):
        topic = topic_from(project["prompt"]) if project["prompt"] else project["title"]
        pat = TITLE_PATTERNS[len(project["history"]) % len(TITLE_PATTERNS)]
        new_title = pat.format(T=topic)
        project["title"] = new_title
        if project["type"] == "presentation" and project["slides"]:
            project["slides"][0]["title"] = new_title
        if project["type"] == "logo":
            pass
        changes.append(f"New title: {new_title}")
    if re.search(r"photo|picture|image", low):
        changes.append("Photos can't be generated here - add your own with Add image on a slide")
    if not changes:
        changes.append("No matching tweak. Try: brighter, bolder, bigger text, a different colour, make it elegant, a catchier title.")
    else:
        project["history"].append({"prompt": text, "changes": changes, "at": now()})
    project["updated"] = now()
    return clean_project(project), changes


# ---------------------------------------------------------------- examples
def load_examples() -> list[dict]:
    path = DATA_DIR / "test_data.json"
    return json.loads(path.read_text(encoding="utf-8"))["examples"]


def project_from_example(example_id: str) -> dict:
    for ex in load_examples():
        if ex["id"] == example_id:
            project = blank_project(ex["project"]["type"], ex["project"].get("title", ex["name"]))
            data = ex["project"]
            merged = {**project, **{k: v for k, v in data.items() if k not in ("id",)}}
            merged["id"] = project["id"]
            merged["prompt"] = ex.get("prompt", "")
            merged["options"] = {**project["options"], **data.get("options", {})}
            merged["tune"] = {**project["tune"], **data.get("tune", {})}
            return clean_project(merged)
    raise KeyError(example_id)


def build_project(ptype: str, prompt: str, options: dict, doc_type: str = "Blog post", title: str = "") -> dict:
    """Create a project from the user's own idea."""
    project = blank_project(ptype, title or "Untitled")
    project["prompt"] = prompt
    project["options"].update({k: v for k, v in options.items() if k in project["options"]})
    if ptype == "presentation":
        topic, slides = generate_presentation(prompt, project["options"])
        project["title"] = title or topic
        project["slides"] = slides
        if title:
            slides[0]["title"] = title
    elif ptype == "document":
        topic, sections = generate_document(prompt, doc_type, project["options"])
        project["title"] = title or topic
        project["doc"] = {"doc_type": doc_type, "sections": sections}
    else:
        logo = generate_logo(prompt)
        if title:
            logo["brand"] = title
        project["logo"] = logo
        project["title"] = logo["brand"]
    return clean_project(project)
