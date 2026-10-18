"""Colours and small HTML helpers for FocusDesk's look and feel.

Everything user-typed is escaped before it is placed in HTML.
"""
from __future__ import annotations

import html

PURPLE, PINK, ORANGE = "#6C5CE7", "#E84393", "#FF9F43"
BLUE, TEAL, GREEN, RED, AMBER = "#0984E3", "#00B8A9", "#2E9E5B", "#E53935", "#F5A623"

# Gradients for the four headline cards
CARD_BLUE = (BLUE, PURPLE)
CARD_RED = (RED, PINK)
CARD_GREEN = (GREEN, TEAL)
CARD_ORANGE = ("#F57C00", ORANGE)
CARD_PURPLE = (PURPLE, PINK)
CARD_TEAL = (TEAL, BLUE)

PRIORITY_STYLE = {  # (background, text, bar colour, icon)
    "High": ("#FFE3E3", "#C62828", RED, "🔴"),
    "Medium": ("#FFF0D1", "#9A5B00", AMBER, "🟠"),
    "Low": ("#DFF5E7", "#17703A", GREEN, "🟢"),
}


def esc(text) -> str:
    """HTML-escape text and neutralise '$' so Markdown never treats it as maths."""
    return html.escape(str(text), quote=True).replace("$", "&#36;")


CSS = """
<style>
.stApp { background: linear-gradient(180deg, #F3EFFF 0%, #FFFFFF 38%, #FFF7FB 100%); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #E9E3FF 0%, #FFE6F1 100%); }
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    border-radius: 10px; font-weight: 600;
}
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { font-weight: 600; border-radius: 10px 10px 0 0; padding: 8px 16px; }
.fd-banner {
    background: linear-gradient(120deg, #6C5CE7 0%, #E84393 58%, #FF9F43 100%);
    color: #fff; padding: 22px 28px; border-radius: 18px; margin-bottom: 18px;
    box-shadow: 0 6px 18px rgba(108, 92, 231, .30);
}
.fd-banner-title { font-size: 2rem; font-weight: 800; line-height: 1.15; }
.fd-banner-sub { font-size: 1rem; opacity: .92; margin-top: 4px; }
.fd-card {
    color: #fff; border-radius: 16px; padding: 14px 18px; margin-bottom: 10px;
    box-shadow: 0 4px 12px rgba(31, 27, 58, .18);
}
.fd-card-label { font-size: .85rem; font-weight: 600; opacity: .95; }
.fd-card-value { font-size: 2rem; font-weight: 800; line-height: 1.2; }
.fd-chip {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: .78rem; font-weight: 700; margin-right: 6px; white-space: nowrap;
}
.fd-task {
    background: #fff; border-left: 6px solid #6C5CE7; border-radius: 12px;
    padding: 9px 14px; box-shadow: 0 2px 8px rgba(31, 27, 58, .08);
}
.fd-task.high { border-left-color: #E53935; }
.fd-task.medium { border-left-color: #F5A623; }
.fd-task.low { border-left-color: #2E9E5B; }
.fd-task.done { opacity: .62; }
.fd-task-title { font-weight: 700; color: #1F1B3A; margin-bottom: 4px; }
.fd-task.done .fd-task-title { text-decoration: line-through; }
.fd-note { color: #5B5780; font-size: .9rem; margin-left: 2px; }
.fd-user {
    background: #fff; border-radius: 12px; padding: 10px 12px; margin-bottom: 8px;
    border: 2px solid #6C5CE7; color: #1F1B3A; font-size: .85rem; word-break: break-all;
}
.fd-bar-row { display: flex; align-items: center; gap: 10px; margin: 8px 0; }
.fd-bar-label { width: 90px; font-weight: 700; color: #1F1B3A; }
.fd-bar-track { flex: 1; background: #ECE8FA; border-radius: 999px; height: 16px; overflow: hidden; }
.fd-bar-fill { height: 100%; border-radius: 999px; }
.fd-bar-num { width: 28px; text-align: right; font-weight: 800; color: #1F1B3A; }
</style>
"""


def banner(title: str, subtitle: str) -> str:
    return (f'<div class="fd-banner"><div class="fd-banner-title">{esc(title)}</div>'
            f'<div class="fd-banner-sub">{esc(subtitle)}</div></div>')


def metric_card(label: str, value, gradient: tuple[str, str], icon: str = "") -> str:
    a, b = gradient
    return (f'<div class="fd-card" style="background:linear-gradient(135deg,{a},{b})">'
            f'<div class="fd-card-label">{esc(icon)} {esc(label)}</div>'
            f'<div class="fd-card-value">{esc(value)}</div></div>')


def chip(text: str, bg: str, fg: str) -> str:
    return f'<span class="fd-chip" style="background:{bg};color:{fg}">{esc(text)}</span>'


def priority_chip(priority: str) -> str:
    bg, fg, _, icon = PRIORITY_STYLE[priority]
    return chip(f"{icon} {priority}", bg, fg)


def task_card(task: dict, overdue: bool = False) -> str:
    chips = priority_chip(task["priority"])
    if task["due"]:
        if overdue:
            chips += chip(f"⚠️ overdue · {task['due']}", "#FFD9D9", "#B71C1C")
        else:
            chips += chip(f"📅 due {task['due']}", "#DCEBFF", "#0B4F9C")
    if task["done"] and task.get("completed"):
        chips += chip(f"✔ done {task['completed']}", "#D6F5EA", "#0B6B4F")
    state = "done" if task["done"] else "open"
    return (f'<div class="fd-task {task["priority"].lower()} {state}">'
            f'<div class="fd-task-title">{esc(task["title"])}</div><div>{chips}</div></div>')


def session_card(session: dict, minutes_text: str) -> str:
    detail = session["task_title"] or "General focus"
    note = f' <span class="fd-note">— {esc(session["note"])}</span>' if session["note"] else ""
    return (f'<div class="fd-task low"><div>'
            f'{chip("📅 " + session["date"], "#DCEBFF", "#0B4F9C")}'
            f'{chip("⏱ " + minutes_text, "#EDE7FF", "#4B3BB5")}'
            f'<strong>{esc(detail)}</strong>{note}</div></div>')


def user_chip(email: str) -> str:
    return f'<div class="fd-user">👤 Signed in as<br><strong>{esc(email)}</strong></div>'


def priority_bar(label: str, value: int, maximum: int, color: str) -> str:
    pct = 0 if maximum <= 0 else round(100 * value / maximum)
    return (f'<div class="fd-bar-row"><div class="fd-bar-label">{esc(label)}</div>'
            f'<div class="fd-bar-track"><div class="fd-bar-fill" style="width:{pct}%;background:{color}"></div></div>'
            f'<div class="fd-bar-num">{value}</div></div>')
