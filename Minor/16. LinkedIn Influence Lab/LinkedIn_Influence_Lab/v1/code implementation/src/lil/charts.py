"""Matplotlib charts and the workflow diagram (saved as PNG for the reports and docs)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from .knowledge import FORMATS, PILLARS  # noqa: E402

BG = "#FFF9F5"


def _save(fig, path):
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def weekly(m: dict, path) -> None:
    w = m["weekly"]
    fig, ax = plt.subplots(figsize=(7, 3.4), facecolor=BG)
    ax.set_facecolor(BG)
    ax.bar(w["week"], w["impressions"], color="#C4B5FD", label="Impressions", width=.6)
    ax.set_ylabel("Impressions")
    ax2 = ax.twinx()
    ax2.plot(w["week"], w["rate"], color="#EC4899", marker="o", lw=2.5, label="Engagement rate %")
    ax2.set_ylabel("Engagement rate %")
    ax.set_xlabel("Week")
    ax.set_title("Weekly reach and engagement", color="#4C1D95", fontweight="bold")
    ax.set_xticks(list(w["week"]))
    for s in ("top",):
        ax.spines[s].set_visible(False); ax2.spines[s].set_visible(False)
    _save(fig, path)


def bars(df, col: str, labels: dict, colors: dict, title: str, path) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.2), facecolor=BG)
    ax.set_facecolor(BG)
    names = [labels[k]["label"] for k in df[col]]
    ax.barh(names[::-1], df["rate"][::-1], color=[colors[k]["color"] for k in df[col]][::-1])
    ax.set_xlabel("Engagement rate %")
    ax.set_title(title, color="#4C1D95", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, path)


def pillar_chart(m, path):
    bars(m["by_pillar"], "pillar", PILLARS, PILLARS, "Engagement by content pillar", path)


def format_chart(m, path):
    bars(m["by_format"], "format", FORMATS, FORMATS, "Engagement by format", path)


def workflow_diagram(path) -> None:
    """Inputs -> ChatGPT/AI -> Taplio -> LinkedIn -> Analytics -> back to Inputs."""
    steps = [("1  Inputs", "you: profile, goals,\nstories, metrics", "#7C3AED"),
             ("2  ChatGPT / AI", "ideas, drafts,\nrewrites (A, B, C)", "#F97316"),
             ("3  Taplio", "calendar, queue,\nscheduling", "#EC4899"),
             ("4  LinkedIn", "posts go live,\nyou engage", "#0EA5E9"),
             ("5  Analytics", "impressions, likes,\ncomments, shares", "#10B981")]
    fig, ax = plt.subplots(figsize=(11, 4.0), facecolor=BG)
    ax.set_xlim(0, 11); ax.set_ylim(-0.5, 3.6); ax.axis("off")
    for i, (t, sub, col) in enumerate(steps):
        x = 0.25 + i * 2.15
        ax.add_patch(FancyBboxPatch((x, 1.5), 1.8, 1.25, boxstyle="round,pad=0.04,rounding_size=0.15", fc=col, ec="none"))
        ax.text(x + .9, 2.4, t, ha="center", va="center", color="white", fontsize=11, fontweight="bold")
        ax.text(x + .9, 1.9, sub, ha="center", va="center", color="white", fontsize=8)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch((x + 1.84, 2.1), (x + 2.14, 2.1), arrowstyle="-|>", mutation_scale=16, color="#4C1D95", lw=2))
    ax.add_patch(FancyArrowPatch((9.9, 1.45), (1.15, 1.45), connectionstyle="arc3,rad=-0.28", arrowstyle="-|>",
                                 mutation_scale=18, color="#DB2777", lw=2.2))
    ax.text(5.5, -0.2, "Feedback loop: insights refine pillars, hooks and posting times in the next cycle",
            ha="center", color="#9D174D", fontsize=10, fontweight="bold")
    _save(fig, path)
