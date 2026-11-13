import streamlit as st

from ..compat import WIDE

from .. import backup, folder_map, paths, pipeline, theme
from . import common

LABELS = {"capstone": ("00 Capstone report", "#4F46E5"), "calendar": ("01 Content calendar", "#EC4899"), "drafts": ("02 Post drafts", "#F97316"),
          "dashboard": ("03 Engagement dashboard", "#10B981"), "audit": ("04 Branding audit report", "#7C3AED"),
          "review": ("05 Performance review report", "#0EA5E9"), "taplio": ("06 Taplio queue", "#F59E0B")}


def _tree(root, prefix="", depth=0, maxdepth=3):
    out = []
    items = sorted(p for p in root.iterdir() if not p.name.startswith((".", "__")))
    for p in items:
        out.append(f"{prefix}{p.name}{'/' if p.is_dir() else ''}")
        if p.is_dir() and depth < maxdepth:
            out += _tree(p, prefix + "    ", depth + 1, maxdepth)
    return out


def render():
    profile = common.get_profile()
    theme.hero("Deliverables & Backups", "Everything the client receives, one folder per set, with a backup behind every phase.", "#7C3AED", "#F59E0B", "📦")
    c1, c2 = st.columns(2)
    demo = c1.checkbox("Use demo data for the dashboard/report if I have no real data", False)
    if c2.button("🛠️ Build / rebuild all deliverables", **WIDE):
        common.need_profile(profile)
        with st.spinner("Building every file..."):
            made = pipeline.build_deliverables(profile, demo=demo)
        st.success(f"Built: {', '.join(made)}")
    for key, (label, color) in LABELS.items():
        folder = paths.deliverable_dir(key)
        files = sorted(f for f in folder.rglob("*") if f.is_file() and f.suffix != ".png")
        with st.expander(f"{label}  ·  {len(files)} file(s)"):
            theme.card(label, f"deliverables/{folder.name}/", color)
            if not files:
                st.caption("Nothing here yet. Run the pipeline or build deliverables.")
            for f in files:
                common.download(f, key=f"d_{key}_{f.name}")
    st.subheader("🗄️ Backups")
    items = backup.list_backups()
    b1, b2 = st.columns(2)
    if b1.button("Create a full snapshot now"):
        st.success(f"Saved {backup.backup_snapshot().name}")
        st.rerun()
    if items:
        st.dataframe(items, **WIDE, hide_index=True)
        pick = st.selectbox("Restore a phase backup", [i["file"] for i in items if not i["file"].startswith("FULL")] or ["(none)"])
        sure = st.checkbox("Yes, overwrite the current phase files with this backup (the current state is backed up first)")
        if st.button("Restore selected backup", disabled=not sure or pick == "(none)"):
            n = backup.restore(pick)
            st.success(f"Restored {len(n)} files from {pick}.")
    else:
        st.info("No backups yet. They appear after the first phase run.")
    with st.expander("🗺️ Folder map (what lives where)"):
        for name, purpose in folder_map.FOLDER_PURPOSE.items():
            st.markdown(f"`{name}` — {purpose}")
        st.code("\n".join(_tree(paths.home())), language=None)
