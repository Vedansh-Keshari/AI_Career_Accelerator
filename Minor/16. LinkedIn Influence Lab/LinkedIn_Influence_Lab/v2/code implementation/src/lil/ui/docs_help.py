import pandas as pd
import streamlit as st

from .. import paths, theme
from ..compat import WIDE
from ..trace import TRACE
from . import common

RESTRICTED = {"03_PROJECT_STRUCTURE_GUIDE.md"}  # same content as the Folder map: admin only


def render():
    theme.hero("Docs & Help", "Beginner guide, requirements, architecture, FAQ, and where each of the 24 brief sections lives.", "#0369A1", "#6D28D9", "📚")
    root = paths.app_root()
    docs = [root / "HOW_TO_RUN.txt", root / "README.md"] + sorted((root / "docs").glob("*.md")) + sorted((root / "templates").glob("*.md"))
    docs = [d for d in docs if d.exists() and (common.is_admin() or d.name not in RESTRICTED)]
    t1, t2 = st.tabs(["📖 Documents", "🧩 24-part traceability"])
    with t1:
        if not docs:
            st.info("No documents found in this installation.")
            st.stop()
        pick = st.selectbox("Open a document", docs, format_func=lambda p: str(p.relative_to(root)))
        text = pick.read_text(encoding="utf-8")
        (st.markdown(text) if pick.suffix == ".md" else st.code(text, language=None))
        common.download(pick, key=f"doc_{pick.name}")
        if not common.is_admin():
            theme.locked("Project structure guide", "Restricted to administrators, like the Folder map.")
    with t2:
        rows = [{"Part": n, "Section": name, "How it is covered": how, "Where": ", ".join(files),
                 "Files present": all((root / f).exists() for f in files)} for n, name, how, files in TRACE]
        st.dataframe(pd.DataFrame(rows), hide_index=True, **WIDE)
