"""Matplotlib charts and diagrams saved as PNG for the reports and the app.
Same hues as the app, in deeper shades and a cleaner, flatter style."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Wedge  # noqa: E402

from .knowledge import FORMATS, PILLARS  # noqa: E402

INK, MUTED, LINE, PAPER = "#1F2A44", "#64708A", "#D9DCE6", "#FFFFFF"
# deeper shades of the app colours
VIOLET, ORANGE, PINK, SKY, EMERALD, INDIGO = "#6D28D9", "#EA580C", "#BE185D", "#0369A1", "#047857", "#312E81"
DEEP = {"career_insights": VIOLET, "thought_leadership": ORANGE, "personal_journey": PINK,
        "industry_trends": SKY, "actionable_tips": EMERALD}
DEEP_FMT = {"text": "#4F46E5", "micro_story": PINK, "poll": "#B45309", "carousel": "#0F766E"}

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": LINE, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlecolor": INK,
                     "axes.titlelocation": "left", "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER})


def _save(fig, path):
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


def _clean(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#EEF0F6", lw=1)
    ax.set_axisbelow(True)


# ----------------------------------------------------------------- data charts ----------
def weekly(m: dict, path) -> None:
    w = m["weekly"]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    _clean(ax)
    bars = ax.bar(w["week"], w["impressions"], color="#C7BDF0", width=.58, label="Impressions")
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{int(b.get_height()):,}", ha="center", va="bottom", fontsize=7.5, color=MUTED)
    ax.set_ylabel("Impressions")
    ax.set_xlabel("Week")
    ax.set_xticks(list(w["week"]))
    ax.set_title("Weekly reach and engagement rate")
    ax2 = ax.twinx()
    ax2.plot(w["week"], w["rate"], color=PINK, marker="o", ms=5, lw=2.2, label="Engagement rate %")
    ax2.set_ylabel("Engagement rate %")
    ax2.spines[["top"]].set_visible(False)
    ax2.set_ylim(0, max(1, float(w["rate"].max()) * 1.35))
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=8)
    _save(fig, path)


def bars(df, col: str, labels: dict, colors: dict, title: str, path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#EEF0F6", lw=1); ax.set_axisbelow(True)
    names = [labels[k]["label"] for k in df[col]][::-1]
    vals = list(df["rate"])[::-1]
    cols = [colors[k] for k in df[col]][::-1]
    ax.barh(names, vals, color=cols, height=.58)
    for i, v in enumerate(vals):
        ax.text(v, i, f" {v:.1f}%", va="center", fontsize=8, color=INK)
    ax.set_xlabel("Engagement rate %")
    ax.set_xlim(0, max(vals) * 1.2 if vals else 1)
    ax.set_title(title)
    _save(fig, path)


def pillar_chart(m, path):
    bars(m["by_pillar"], "pillar", PILLARS, DEEP, "Engagement rate by content pillar", path)


def format_chart(m, path):
    bars(m["by_format"], "format", FORMATS, DEEP_FMT, "Engagement rate by format", path)


def mix_donut(weights: dict, path, title: str = "Pillar mix") -> None:
    keys = list(weights)
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    ax.pie([weights[k] for k in keys], colors=[DEEP[k] for k in keys], startangle=90, counterclock=False,
           wedgeprops={"width": .38, "edgecolor": "white", "linewidth": 2})
    ax.set_title(title)
    ax.legend([f"{PILLARS[k]['label']} {round(weights[k] * 100)}%" for k in keys], loc="center left", bbox_to_anchor=(1, .5), frameon=False, fontsize=8)
    _save(fig, path)


# ----------------------------------------------------------------- diagrams --------------
def _shadow_card(ax, x, y, w, h, color, radius=.14):
    ax.add_patch(FancyBboxPatch((x + .05, y - .06), w, h, boxstyle=f"round,pad=0.02,rounding_size={radius}", fc="#000000", ec="none", alpha=.10))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={radius}", fc=PAPER, ec=LINE, lw=1))
    ax.add_patch(FancyBboxPatch((x, y + h - .52), w, .52, boxstyle=f"round,pad=0.02,rounding_size={radius}", fc=color, ec="none"))
    ax.add_patch(plt.Rectangle((x, y + h - .52), w, .26, fc=color, ec="none"))


def _pill(ax, cx, cy, text, filled, color, width=1.3):
    ax.add_patch(FancyBboxPatch((cx - width / 2, cy - .13), width, .26, boxstyle="round,pad=0,rounding_size=.13",
                                fc=color if filled else PAPER, ec=color, lw=1.2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=7, color=PAPER if filled else color, fontweight="bold")


def workflow_diagram(path) -> None:
    """Inputs -> ChatGPT / AI -> Taplio -> LinkedIn -> Analytics -> back to Inputs."""
    steps = [("Inputs", "Profile, goals, stories,\nIDs and plugins", VIOLET, False, "You"),
             ("ChatGPT / AI", "Ideas, drafts, rewrites\n(Templates A, B, C)", ORANGE, True, "Automated"),
             ("Taplio", "Calendar, queue and\nscheduling", PINK, False, "You + app"),
             ("LinkedIn", "Posts go live;\nyou reply to comments", SKY, False, "You"),
             ("Analytics", "Impressions, likes,\ncomments, shares", EMERALD, True, "Automated")]
    fig, ax = plt.subplots(figsize=(12, 4.9))
    ax.set_xlim(0, 12); ax.set_ylim(-0.2, 4.7); ax.axis("off")
    w, h, gap, x0 = 1.88, 2.3, .5, .3
    labels = ["profile.json", "drafts + queue", "scheduled posts", "post metrics"]
    for i, (title, sub, col, auto, tag) in enumerate(steps):
        x = x0 + i * (w + gap)
        _shadow_card(ax, x, 1.55, w, h, col)
        ax.add_patch(Circle((x + .3, 1.55 + h - .26), .17, fc=PAPER, ec="none"))
        ax.text(x + .3, 1.55 + h - .26, str(i + 1), ha="center", va="center", fontsize=9, fontweight="bold", color=col)
        ax.text(x + .58, 1.55 + h - .26, title, ha="left", va="center", fontsize=9.6, fontweight="bold", color=PAPER)
        ax.text(x + w / 2, 1.55 + h - 1.2, sub, ha="center", va="center", fontsize=8.3, color=INK, linespacing=1.5)
        _pill(ax, x + w / 2, 1.55 + .28, tag, auto, col, 1.15)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x + w + .03, 1.55 + h / 2 + .1), (x + w + gap - .03, 1.55 + h / 2 + .1), arrowstyle="-|>", mutation_scale=14, color=INK, lw=1.6))
            ax.text(x + w + gap / 2, 1.55 + h / 2 + .38, labels[i], ha="center", fontsize=6.3, color=MUTED, rotation=0)
    xs, xe = x0 + 4 * (w + gap) + w / 2, x0 + w / 2
    ax.add_patch(FancyArrowPatch((xs, 1.5), (xe, 1.5), connectionstyle="arc3,rad=-0.16", arrowstyle="-|>", mutation_scale=16, color=PINK, lw=1.8, ls=(0, (5, 3))))
    ax.text(6.0, .42, "Feedback loop: insights refine pillars, hooks and posting times for the next cycle", ha="center", fontsize=9, color=PINK, fontweight="bold")
    _pill(ax, 3.9, -.08, "Automated by the app", True, INDIGO, 1.9)
    _pill(ax, 6.1, -.08, "Your action", False, INDIGO, 1.5)
    ax.text(8.2, -.08, "Nothing is published without your review.", fontsize=7.5, color=MUTED, va="center")
    _save(fig, path)


def dependency_diagram(path) -> None:
    """How the five phases connect: what each hands to the next, and which links are hard requirements."""
    from .paths import PHASES
    col = {1: VIOLET, 2: ORANGE, 3: PINK, 4: SKY, 5: EMERALD}
    prod = {1: "audit.json\npillars.json", 2: "slots.json\ndrafts.json", 3: "calendar.json\nTaplio queue", 4: "engagement.csv\npath KPIs", 5: "metrics + insights\nrefined mix"}
    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.set_xlim(0, 12); ax.set_ylim(-0.3, 4.6); ax.axis("off")
    w, h, gap, x0 = 1.82, 2.0, .6, .3
    for i, p in enumerate(PHASES):
        x = x0 + i * (w + gap)
        _shadow_card(ax, x, 1.7, w, h, col[p["n"]])
        ax.text(x + .16, 1.7 + h - .26, f"Phase {p['n']}", fontsize=9.6, fontweight="bold", color=PAPER, va="center")
        ax.text(x + w - .12, 1.7 + h - .26, p["week"], fontsize=6.8, color="#F3F0FF", va="center", ha="right")
        ax.text(x + w / 2, 1.7 + h - .95, p["title"].replace(": ", ":\n").replace(" & ", " &\n"), ha="center", va="center", fontsize=8.4, color=INK, fontweight="bold", linespacing=1.35)
        ax.text(x + w / 2, 1.7 + .32, prod[p["n"]], ha="center", va="center", fontsize=6.8, color=MUTED, family="monospace", linespacing=1.4)
        if i < len(PHASES) - 1:
            soft = i == 0
            ax.add_patch(FancyArrowPatch((x + w + .04, 2.7), (x + w + gap - .04, 2.7), arrowstyle="-|>", mutation_scale=14,
                                         color=MUTED if soft else INK, lw=1.6, ls=(0, (4, 3)) if soft else "-"))
    xs, xe = x0 + 4 * (w + gap) + w / 2, x0 + 1 * (w + gap) + w / 2
    ax.add_patch(FancyArrowPatch((xs, 1.62), (xe, 1.62), connectionstyle="arc3,rad=-0.2", arrowstyle="-|>", mutation_scale=15, color=PINK, lw=1.7, ls=(0, (5, 3))))
    ax.text(7.0, .5, "Next cycle: apply the refined pillar mix and return to Phase 2", ha="center", fontsize=8.6, color=PINK, fontweight="bold")
    ax.plot([.6, 1.1], [-.1, -.1], color=INK, lw=1.6); ax.text(1.2, -.1, "hard dependency: the next phase cannot run without it", fontsize=7.5, color=MUTED, va="center")
    ax.plot([6.3, 6.8], [-.1, -.1], color=MUTED, lw=1.6, ls=(0, (4, 3))); ax.text(6.9, -.1, "soft dependency: uses the same inputs, results guide your work", fontsize=7.5, color=MUTED, va="center")
    _save(fig, path)


def architecture_diagram(path) -> None:
    layers = [("Pages (Streamlit)", "app.py  ·  ui/  ·  one page per file, path-specific hubs", VIOLET),
              ("Orchestration", "pipeline.py  ·  backup.py  ·  samples.py  ·  exports.py", ORANGE),
              ("Engines", "audit  ideation  drafting  quality  planner  analytics  hubs  personas", PINK),
              ("Plugins", "AI engines  ·  export targets  ·  analytics importers (drop-in files)", SKY),
              ("Foundation", "paths  store  settings  auth  guidance  knowledge  context", EMERALD),
              ("Storage (no database)", "JSON + CSV working files  ·  XLSX / DOCX deliverables  ·  ZIP backups with SHA-256 manifest", INDIGO)]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 4.6); ax.axis("off")
    for i, (t, d, c) in enumerate(layers):
        y = 4.6 - (i + 1) * .74
        ax.add_patch(FancyBboxPatch((.15, y + .04), 9.7, .62, boxstyle="round,pad=0.01,rounding_size=.1", fc=c, ec="none"))
        ax.text(.4, y + .35, t, color=PAPER, fontsize=10, fontweight="bold", va="center")
        ax.text(3.15, y + .35, d, color="#F4F1FF", fontsize=8.6, va="center")
    _save(fig, path)


def cover_banner(path, width: float = 7.4, height: float = 2.1) -> None:
    """Gradient band with a restrained geometric pattern for report covers."""
    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_xlim(0, width); ax.set_ylim(0, height)
    g = np.linspace(0, 1, 512)[None, :]
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("b", [INDIGO, VIOLET, "#9D2A8B", PINK])
    ax.imshow(g, extent=[0, width, 0, height], aspect="auto", cmap=cmap, zorder=0)
    for cx, cy, r, a in [(6.4, 1.6, 1.25, .10), (6.9, .4, .9, .12), (5.2, 2.0, .55, .08), (7.3, 1.9, .35, .14)]:
        ax.add_patch(Circle((cx, cy), r, fc="white", ec="none", alpha=a))
    for k in range(7):
        ax.plot([4.4 + k * .28, 5.5 + k * .28], [0, height], color="white", alpha=.07, lw=2)
    ax.add_patch(plt.Rectangle((0, 0), width, .07, fc=ORANGE, ec="none"))
    fig.savefig(path, dpi=200, facecolor=INDIGO)
    plt.close(fig)
