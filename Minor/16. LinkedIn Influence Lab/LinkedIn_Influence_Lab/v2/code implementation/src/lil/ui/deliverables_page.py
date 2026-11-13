import pandas as pd
import streamlit as st

from .. import backup, exports, folder_map, paths, persona_content, pipeline, theme
from ..compat import WIDE
from . import common

LABELS = {"capstone": ("00 Capstone report", "#4F46E5"), "calendar": ("01 Content calendar", "#BE185D"), "drafts": ("02 Post drafts", "#C2410C"),
          "dashboard": ("03 Engagement dashboard", "#047857"), "audit": ("04 Branding audit report", "#6D28D9"),
          "review": ("05 Performance review report", "#0369A1"), "taplio": ("06 Taplio queue", "#B45309")}
SKIP_TREE = {".venv", "__pycache__", ".pytest_cache", ".git", "node_modules"}


def _tree(root, prefix="", depth=0, maxdepth=3):
    out = []
    for p in sorted((p for p in root.iterdir() if p.name not in SKIP_TREE and not p.name.startswith(".")), key=lambda x: (x.is_file(), x.name)):
        out.append(f"{prefix}{p.name}{'/' if p.is_dir() else ''}")
        if p.is_dir() and depth < maxdepth:
            out += _tree(p, prefix + "    ", depth + 1, maxdepth)
    return out


def _folder_map():
    """Admin-only. Non-admins see the toggle but cannot open it, and no content is rendered for them."""
    if common.is_admin():
        with st.expander("🗺️ Folder map (what lives where)"):
            for name, purpose in folder_map.FOLDER_PURPOSE.items():
                st.markdown(f"`{name}` — {purpose}")
            st.code("\n".join(_tree(paths.app_root())), language=None)
    else:
        st.toggle("🗺️ Folder map (what lives where)", value=False, disabled=True, key="fm_locked_toggle", help="Only an administrator can open this.")
        theme.locked("Folder map is restricted", "Only an administrator can open it. Sign in under 🔐 Admin access in the sidebar.")


def _explain():
    with st.expander("ℹ️ How backups, snapshots and restores work (and what is used to store them)", expanded=False):
        st.markdown("""
**No database is used.** Everything is stored as ordinary files in the active workspace, so you can open, copy and archive them with any tool.

| What | Stored as | Where |
|---|---|---|
| Your inputs (profile) | JSON | `data/inputs/profile.json` |
| API keys and plugin switches | JSON (never backed up or exported) | `data/inputs/plugins.json` |
| Phase working data (ideas, drafts, calendar, engagement) | JSON and CSV | `phases/<phase folder>/` |
| Path-specific hub data (leads, opportunities, peer log, series) | CSV and JSON | `data/hub/` |
| Phase status | JSON | `data/state/status.json` |
| Client files | DOCX, XLSX, CSV, ICS | `deliverables/<set>/` |
| Backups | ZIP + `MANIFEST.json` with a SHA-256 checksum per file | `backups/` |

**Phase backup** (created every time a phase runs): that phase's working files plus your profile. The previous Phase 2 drafts are also saved as a `before_rerun` backup before they are replaced. The newest 12 per phase are kept.

**Full snapshot** (created at the end of the automated pipeline, on demand, and before every restore): phases, deliverables, hub data, the status ledger and your profile. It never contains API keys, the admin passcode or other backups. Snapshots are never deleted automatically.

**How a restore works**
1. The backup is verified: every file is re-read and its SHA-256 is compared with the manifest. A damaged backup is refused.
2. A safety snapshot of the current state is taken (`before_restore`), so a restore can itself be undone.
3. The folders the backup covers are cleared (one phase folder for a phase backup; phases, deliverables, hub data and status for a snapshot) so the result matches the backup exactly.
4. The files are extracted. Only allowed paths are written; anything else in the zip is ignored.

Backups are per workspace: the sample workspace and your own workspace never share backups. To move work to another computer, download a backup here and import it there.
""")


def render():
    profile = common.get_profile()
    theme.hero("Deliverables & Backups", "Everything the client receives, one folder per set, with a backup behind every phase.", "#6D28D9", "#B45309", "📦")
    c1, c2 = st.columns(2)
    if c1.button("🛠️ Build / rebuild all deliverables", **WIDE):
        common.need_profile(profile)
        with st.spinner("Building every file..."):
            made = pipeline.build_deliverables(profile)
        st.success(f"Built: {', '.join(made)}")
    counts = exports.counts()
    total = sum(counts.values())
    if total:
        c2.download_button(f"⬇ Download ALL files from all sets ({total} files, ZIP)", exports.zip_all(), file_name="LinkedIn_Influence_Lab_all_deliverables.zip",
                           mime="application/zip", key="dl_all_sets", **WIDE)
    else:
        c2.caption("No deliverables built yet. Press the button on the left (or run the pipeline).")
    star = set(persona_content.PRIMARY_DELIVERABLES[profile["persona"]])
    for key, (label, color) in LABELS.items():
        files = exports.set_files(key)
        folder = paths.deliverable_dir(key)
        with st.expander(f"{'⭐ ' if key in star else ''}{label}  ·  {len(files)} file(s)"):
            theme.card(label, f"deliverables/{folder.name}/", color, "Highlighted for your path." if key in star else "")
            if not files:
                st.caption("Nothing here yet. Run the pipeline or build deliverables.")
                continue
            st.download_button(f"⬇ Download all files in this set ({len(files)}, ZIP)", exports.zip_set(key), file_name=f"{folder.name}.zip",
                               mime="application/zip", key=f"dl_set_{key}")
            for f in files:
                if f.suffix != ".png":
                    common.download(f, key=f"d_{key}_{f.name}")

    st.subheader("🗄️ Backups and snapshots")
    _explain()
    items = backup.list_backups()
    b1, b2 = st.columns(2)
    if b1.button("Create a full snapshot now"):
        st.success(f"Saved {backup.backup_snapshot().name}")
        st.rerun()
    up = b2.file_uploader("Import a backup made elsewhere (.zip)", type="zip", key="bk_up")
    if up is not None and st.button("Import this backup"):
        try:
            st.success(f"Imported as {backup.import_backup(up.getvalue(), up.name)}. Select it below to restore.")
        except ValueError as exc:
            st.error(str(exc))
    if not items:
        common.empty_state("No backups yet", ["They appear after the first phase run or when you create a snapshot."])
    else:
        st.dataframe(pd.DataFrame(items).rename(columns={"file": "File", "type": "Type", "scope": "Covers", "tag": "Tag", "files": "Files", "kb": "KB", "created": "Created"}),
                     hide_index=True, **WIDE)
        pick = st.selectbox("Select a backup", [i["file"] for i in items])
        info = backup.describe(pick)
        st.markdown(f"**{info['type'].title()}** · created {info['created']} · {info['count']} files · workspace: {info.get('workspace', '?')}")
        st.dataframe(pd.DataFrame([{"Group": k, "Files": v} for k, v in info["groups"].items()]), hide_index=True, **WIDE)
        v1, v2, v3 = st.columns(3)
        if v1.button("Verify integrity (SHA-256)"):
            ok, problems = backup.verify(pick)
            st.success("All files match their checksums.") if ok else st.error("Problems: " + "; ".join(problems[:5]))
        v2.download_button("⬇ Download this backup", (paths.backups_dir() / pick).read_bytes(), file_name=pick, mime="application/zip", key=f"dl_bk_{pick}")
        sure = st.checkbox("Yes, restore it. The current state is saved as a before_restore snapshot first.", key="bk_sure")
        if v3.button("Restore selected backup", disabled=not sure):
            try:
                res = backup.restore(pick)
                common.clear_widget_state()
                st.success(f"Restored {len(res['restored'])} files ({res['replaced']} replaced). Safety copy: {res['safety_backup']}.")
            except (ValueError, FileNotFoundError) as exc:
                st.error(str(exc))
    _folder_map()
