"""Colours, global CSS and small HTML building blocks (all user text is escaped)."""
from __future__ import annotations

import html

import streamlit as st

STATE_STYLE = {
    "not_started": ("#9CA3AF", "Not started"),
    "waiting": ("#F59E0B", "Waiting on you"),
    "preview": ("#EC4899", "Preview (demo data)"),
    "done": ("#10B981", "Complete"),
}

CSS = """
<style>
[data-testid="stAppViewContainer"]{background:linear-gradient(135deg,#FFF4E6 0%,#FDF2F8 36%,#EEF2FF 70%,#E0F7F4 100%);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stSidebar"]>div:first-child{background:linear-gradient(185deg,#1E1B4B 0%,#4C1D95 52%,#9D174D 100%);}
[data-testid="stSidebar"] *{color:#F5F3FF !important;}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:.28rem .5rem;border-radius:10px;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(255,255,255,.14);}
.block-container{padding-top:1.4rem;max-width:1250px;}
.hero{border-radius:22px;padding:1.5rem 1.8rem;color:#fff;margin-bottom:1.1rem;box-shadow:0 12px 28px rgba(76,29,149,.25);}
.hero h1{margin:0;font-size:2rem;color:#fff;}
.hero p{margin:.35rem 0 0;color:#FDF2F8;font-size:1.02rem;}
.card{background:#fff;border-radius:16px;padding:.9rem 1.1rem;box-shadow:0 6px 18px rgba(76,29,149,.10);border-left:6px solid var(--c,#7C3AED);margin-bottom:.7rem;}
.card h4{margin:0 0 .2rem;font-size:1rem;color:#1F1B3A;}
.card small{color:#6B7280;}
.kpi{border-radius:16px;padding:.9rem 1rem;color:#fff;text-align:center;box-shadow:0 8px 18px rgba(0,0,0,.12);}
.kpi b{display:block;font-size:1.7rem;}
.kpi span{font-size:.8rem;opacity:.92;}
.chip{display:inline-block;padding:.15rem .6rem;border-radius:999px;color:#fff;font-size:.78rem;font-weight:600;margin-right:.3rem;}
.cal{width:100%;border-collapse:separate;border-spacing:6px;}
.cal th{background:#4C1D95;color:#fff;border-radius:10px;padding:.4rem;font-size:.85rem;}
.cal td{border-radius:10px;padding:.45rem;font-size:.78rem;vertical-align:top;color:#1F1B3A;min-width:105px;}
div.stButton>button,div[data-testid="stFormSubmitButton"] button,div[data-testid="stDownloadButton"] button{
  border-radius:12px;border:0;background:linear-gradient(90deg,#7C3AED,#EC4899);color:#fff;font-weight:600;}
div.stButton>button:hover,div[data-testid="stDownloadButton"] button:hover{filter:brightness(1.08);color:#fff;}
div.stButton>button p,div[data-testid="stDownloadButton"] button p,div[data-testid="stFormSubmitButton"] button p{color:#fff;}
.stTabs [data-baseweb="tab-list"]{gap:.3rem;}
.stTabs [data-baseweb="tab"]{background:rgba(255,255,255,.65);border-radius:10px 10px 0 0;padding:.4rem .9rem;}
.stTabs [aria-selected="true"]{background:#fff;border-bottom:3px solid #EC4899;}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text) -> str:
    return html.escape(str(text))


def hero(title: str, subtitle: str, c1: str = "#4F46E5", c2: str = "#EC4899", emoji: str = "") -> None:
    st.markdown(f'<div class="hero" style="background:linear-gradient(120deg,{c1},{c2})"><h1>{esc(emoji)} {esc(title)}</h1>'
                f'<p>{esc(subtitle)}</p></div>', unsafe_allow_html=True)


def card(title: str, body: str, color: str = "#7C3AED", small: str = "") -> None:
    st.markdown(f'<div class="card" style="--c:{color}"><h4>{esc(title)}</h4>{esc(body)}'
                f'{"<br><small>" + esc(small) + "</small>" if small else ""}</div>', unsafe_allow_html=True)


def kpi(label: str, value, color: str) -> str:
    return f'<div class="kpi" style="background:linear-gradient(135deg,{color},{color}CC)"><b>{esc(value)}</b><span>{esc(label)}</span></div>'


def kpi_row(items: list[tuple]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, color) in zip(cols, items):
        col.markdown(kpi(label, value, color), unsafe_allow_html=True)


def chip(text: str, color: str) -> str:
    return f'<span class="chip" style="background:{color}">{esc(text)}</span>'
