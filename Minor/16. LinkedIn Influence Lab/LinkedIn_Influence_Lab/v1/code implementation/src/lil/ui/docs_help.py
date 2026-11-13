import pandas as pd
import streamlit as st

from ..compat import WIDE

from .. import paths, theme
from ..trace import TRACE
from . import common


def render():
    theme.hero("Docs & Help", "Beginner guide, requirements, architecture, FAQ, and where each of the 24 brief sections lives.", "#0EA5E9", "#7C3AED", "📚")
    home = paths.home()
    docs = [home / "HOW_TO_RUN.txt", home / "README.md"] + sorted((home / "docs").glob("*.md")) + sorted((home / "templates").glob("*.md"))
    docs = [d for d in docs if d.exists()]
    t1, t2 = st.tabs(["📖 Documents", "🧩 24-part traceability"])
    with t1:
        if not docs:
            st.info("No documents found in this workspace.")
            st.stop()
        pick = st.selectbox("Open a document", docs, format_func=lambda p: str(p.relative_to(home)))
        text = pick.read_text(encoding="utf-8")
        (st.markdown(text) if pick.suffix == ".md" else st.code(text, language=None))
        common.download(pick, key=f"doc_{pick.name}")
    with t2:
        rows = [{"Part": n, "Section": name, "How it is covered": how, "Where": ", ".join(files),
                 "Files present": all((home / f).exists() for f in files)} for n, name, how, files in TRACE]
        st.dataframe(pd.DataFrame(rows), **WIDE, hide_index=True)
