"""Canvas Studio - desktop app (tkinter). Run:  python app.py"""
from __future__ import annotations

import io
import os
import queue
import sys
import threading
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _find_shared(start: Path) -> Path:
    """Locate the shared folder: $CANVA_SHARED, ./shared, ../shared or ../../shared."""
    candidates = [Path(os.environ["CANVA_SHARED"])] if os.environ.get("CANVA_SHARED") else []
    candidates += [start / "shared", start.parent / "shared", start.parent.parent / "shared"]
    for c in candidates:
        if (c / "studio" / "__init__.py").exists():
            return c.resolve()
    raise SystemExit(
        "Could not find the 'shared' folder.\n"
        "Unzip the desktop app next to the shared folder (canva-clone/shared and canva-clone/desktop), "
        "or set CANVA_SHARED to its path."
    )


sys.path.insert(0, str(_find_shared(HERE)))

import tkinter as tk  # noqa: E402
from tkinter import filedialog, messagebox, ttk  # noqa: E402

from PIL import Image, ImageTk  # noqa: E402

from studio import generator as G  # noqa: E402
from studio import models as M  # noqa: E402
from studio import options as O  # noqa: E402
from studio import render as R  # noqa: E402
from studio.canva_client import CanvaClient, CanvaError, NotSignedIn, make_pkce, push_project, wait_for_callback  # noqa: E402
from studio.mock_canva import ensure_demo_server  # noqa: E402
from studio.paths import load_config  # noqa: E402

BAR, BENCH, PANEL, INK, MUTED, ACCENT, SOFT, LINE = "#151a2a", "#e6e9f1", "#ffffff", "#1a2133", "#566074", "#3250f2", "#e4e9ff", "#d5dae6"
FONT = ("Segoe UI", 10)
KIND = {"presentation": "Presentation", "document": "Document", "logo": "Logo"}


class ScrollFrame(tk.Frame):
    """A vertically scrolling container; put widgets in .inner"""

    def __init__(self, parent, bg=PANEL):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=bg)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        for w in (self.canvas, self.inner):
            w.bind("<Enter>", self._on, add="+")
            w.bind("<Leave>", self._off, add="+")

    def _on(self, _):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))

    def _off(self, _):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(ev)

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120) * 2 or (-2 if e.delta > 0 else 2), "units")


class App:
    def __init__(self, root: tk.Tk, config: dict | None = None, home: Path | None = None, client: CanvaClient | None = None):
        self.root = root
        self.cfg = config or load_config("desktop")
        self.store = M.Store(home) if home else M.Store()
        self.client = client or CanvaClient(self.cfg, home=home)
        self.p: dict | None = None
        self.page = 0
        self.count = 1
        self.tab = "content"
        self.canva = {"signed_in": False, "name": ""}
        self.save_job = None
        self.preview_job = None
        self.tk_main = None
        self.tk_thumbs: list = []
        self.work: "queue.Queue" = queue.Queue()
        self.busy = False
        self.cancel_signin: threading.Event | None = None
        self.last_open_url = ""
        self.recent: list | dict | None = None
        self.newwin: tk.Toplevel | None = None
        self._build_ui()
        self.root.after(100, self._pump)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_list()
        self.bg(self._load_status, self._status_loaded)

    # ------------------------------------------------------------------ plumbing
    def bg(self, fn, done):
        """Run fn in a thread; call done(result, error) on the UI thread."""
        def target():
            try:
                self.work.put((done, fn(), None))
            except Exception as exc:  # noqa: BLE001
                self.work.put((done, None, exc))
        threading.Thread(target=target, daemon=True).start()

    def _pump(self):
        try:
            while True:
                done, result, error = self.work.get_nowait()
                done(result, error)
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def say(self, text: str, bad: bool = False, link: str = ""):
        self.status.configure(text=text, fg="#ff9d90" if bad else "#ffffff")
        self.last_open_url = link
        if link:
            self.open_btn.pack(side="right", padx=8, pady=4)
        else:
            self.open_btn.pack_forget()
        self.root.after(9000, lambda: self.status.cget("text") == text and self.status.configure(text=""))

    # ------------------------------------------------------------------ UI skeleton
    def _build_ui(self):
        r = self.root
        r.title("Canvas Studio")
        r.geometry("1360x860")
        r.minsize(1060, 660)
        r.configure(bg=BENCH)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL, padding=4)
        style.configure("TFrame", background=PANEL)

        bar = tk.Frame(r, bg=BAR)
        bar.pack(fill="x")
        tk.Label(bar, text="Canvas Studio", bg=BAR, fg="#fff", font=("Segoe UI", 13, "bold")).pack(side="left", padx=14, pady=10)
        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(bar, textvariable=self.title_var, bg="#1d2338", fg="#fff", insertbackground="#fff", relief="flat",
                                    font=("Segoe UI", 12), width=36, state="disabled", disabledbackground=BAR)
        self.title_entry.pack(side="left", padx=10, ipady=4)
        self.title_var.trace_add("write", lambda *a: self._title_changed())
        self.push_btn = tk.Button(bar, text="Sign in to push", command=self.on_push, bg=ACCENT, fg="#fff", relief="flat",
                                  font=("Segoe UI", 10, "bold"), padx=14, pady=5, state="disabled", activebackground="#2640d0", activeforeground="#fff")
        self.push_btn.pack(side="right", padx=14)
        self.chip = tk.Button(bar, text="", command=lambda: self.set_tab("canva"), bg="#1d2338", fg="#dfe5ff", relief="flat",
                              font=("Segoe UI", 9), padx=10, pady=4, activebackground="#2a3150", activeforeground="#fff")
        self.chip.pack(side="right", padx=4)
        self.dl_btn = tk.Menubutton(bar, text="Download", bg=BAR, fg="#fff", relief="solid", bd=1, font=("Segoe UI", 10), padx=10, pady=4,
                                    activebackground="#2a3150", activeforeground="#fff")
        self.dl_menu = tk.Menu(self.dl_btn, tearoff=0)
        self.dl_btn.configure(menu=self.dl_menu)
        self.dl_btn.pack(side="right", padx=8)

        self.banner = tk.Label(r, text="", bg="#fff1c4", fg=INK, font=("Segoe UI", 9), anchor="w", padx=14, pady=4)
        if self.cfg["demo"]:
            self.banner.configure(text="Demo mode: sign-in and pushes go to a local stand-in for Canva, not canva.com. Add your Canva keys to connect your real account (Canva tab).")
            self.banner.pack(fill="x")

        sb = tk.Frame(r, bg=BAR)
        sb.pack(side="bottom", fill="x")
        self.status = tk.Label(sb, text="", bg=BAR, fg="#fff", font=("Segoe UI", 10), anchor="w", padx=14, pady=6)
        self.status.pack(side="left", fill="x", expand=True)
        self.open_btn = tk.Button(sb, text="Open in Canva", command=lambda: self.last_open_url and webbrowser.open(self.last_open_url),
                                  bg=ACCENT, fg="#fff", relief="flat", padx=10)

        body = tk.Frame(r, bg=BENCH)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        rail = tk.Frame(body, bg=PANEL, width=270, highlightbackground=LINE, highlightthickness=1)
        rail.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        rail.grid_propagate(False)
        tk.Button(rail, text="New project", command=self.open_new, bg=INK, fg="#fff", relief="flat", font=("Segoe UI", 10, "bold"), pady=6).pack(fill="x", padx=12, pady=12)
        self.plist = tk.Listbox(rail, activestyle="none", relief="flat", highlightthickness=0, font=("Segoe UI", 10), selectbackground=SOFT,
                                selectforeground=INK, bg=PANEL, fg=INK, exportselection=False)
        self.plist.pack(fill="both", expand=True, padx=8)
        self.plist.bind("<<ListboxSelect>>", self._list_pick)
        tk.Button(rail, text="Delete project", command=self.delete_current, bg=PANEL, fg="#b42318", relief="flat").pack(fill="x", padx=12, pady=10)

        stage = tk.Frame(body, bg=BENCH)
        stage.grid(row=0, column=1, sticky="nsew")
        stage.rowconfigure(0, weight=1)
        stage.columnconfigure(0, weight=1)
        self.view = tk.Canvas(stage, bg=BENCH, highlightthickness=0)
        self.view.grid(row=0, column=0, sticky="nsew")
        self.view.bind("<Configure>", lambda e: self.schedule_preview())
        self.strip_holder = tk.Frame(stage, bg=BENCH, height=128)
        self.strip_holder.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.strip_holder.grid_propagate(False)
        self.strip_canvas = tk.Canvas(self.strip_holder, bg=BENCH, highlightthickness=0, height=116)
        xs = ttk.Scrollbar(self.strip_holder, orient="horizontal", command=self.strip_canvas.xview)
        self.strip_canvas.configure(xscrollcommand=xs.set)
        self.strip_canvas.pack(fill="x")
        xs.pack(fill="x")
        self.strip = tk.Frame(self.strip_canvas, bg=BENCH)
        self.strip_canvas.create_window((0, 0), window=self.strip, anchor="nw")
        self.strip.bind("<Configure>", lambda e: self.strip_canvas.configure(scrollregion=self.strip_canvas.bbox("all")))

        insp = tk.Frame(body, bg=PANEL, width=390, highlightbackground=LINE, highlightthickness=1)
        insp.grid(row=0, column=2, sticky="ns", padx=(12, 0))
        insp.grid_propagate(False)
        tabs = tk.Frame(insp, bg=PANEL)
        tabs.pack(fill="x")
        self.tab_btns = {}
        for key, label in (("content", "Content"), ("look", "Look"), ("refine", "Refine"), ("canva", "Canva")):
            b = tk.Button(tabs, text=label, command=lambda k=key: self.set_tab(k), relief="flat", bg=PANEL, fg=MUTED, font=("Segoe UI", 10, "bold"), pady=8, bd=0)
            b.pack(side="left", expand=True, fill="x")
            self.tab_btns[key] = b
        self.panel_holder = tk.Frame(insp, bg=PANEL)
        self.panel_holder.pack(fill="both", expand=True)
        self.panel: ScrollFrame | None = None
        self.draw_empty()
        self.build_panel()
        self.refresh_top()

    # ------------------------------------------------------------------ top bar and list
    def _title_changed(self):
        if self.p is None or getattr(self, "_setting_title", False):
            return
        self.p["title"] = self.title_var.get()
        self.refresh_list(keep=True)
        self.schedule_save()

    def refresh_top(self):
        has = self.p is not None
        self.title_entry.configure(state="normal" if has else "disabled")
        self._setting_title = True
        self.title_var.set(self.p["title"] if has else "")
        self._setting_title = False
        label = "Demo Canva" if self.cfg["demo"] else "Canva"
        if self.canva["signed_in"]:
            self.chip.configure(text=f"●  {label}: {self.canva['name'] or 'signed in'}", fg="#12d6a8")
            self.push_btn.configure(text="Push to Canva")
        else:
            self.chip.configure(text=f"●  {label}: sign in", fg="#f0b429")
            self.push_btn.configure(text="Sign in to push")
        self.push_btn.configure(state="normal" if has and not self.busy else "disabled")
        self.dl_menu.delete(0, "end")
        if has and self.p["type"] == "logo":
            self.dl_menu.add_command(label="Save logo as PNG...", command=self.save_png_single)
        elif has:
            self.dl_menu.add_command(label="Save all pages as PDF...", command=self.save_pdf)
            self.dl_menu.add_command(label="Save pages as PNG images...", command=self.save_pngs)
        else:
            self.dl_menu.add_command(label="Open a project first", state="disabled")

    def refresh_list(self, keep: bool = False):
        self.rows = self.store.list()
        self.plist.delete(0, "end")
        for i, row in enumerate(self.rows):
            self.plist.insert("end", f"{row['title'] or 'Untitled'}  ({KIND.get(row['type'], '')}){' ✓' if row['pushed'] else ''}")
            if self.p and row["id"] == self.p["id"]:
                self.plist.selection_set(i)

    def _list_pick(self, _):
        sel = self.plist.curselection()
        if sel and self.p is None or (sel and self.rows[sel[0]]["id"] != self.p["id"]):
            self.open_project(self.rows[sel[0]]["id"])

    # ------------------------------------------------------------------ projects
    def open_project(self, pid: str):
        self.flush_save()
        self.p = self.store.get(pid)
        self.page = 0
        self.recent = None
        self.tab = "content"
        self.refresh_list()
        self.refresh_top()
        self.build_panel()
        self.refresh_preview()

    def flush_save(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
            self.save_job = None
        if self.p:
            self.p = self.store.save(self.p)

    def schedule_save(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(500, self._do_save)

    def _do_save(self):
        self.save_job = None
        if self.p:
            self.p = self.store.save(self.p)
            self.refresh_list(keep=True)
            self.schedule_preview(0)

    def delete_current(self):
        if not self.p:
            return
        if not messagebox.askyesno("Delete project", f"Delete \"{self.p['title']}\"? This cannot be undone."):
            return
        self.store.delete(self.p["id"])
        self.p = None
        self.refresh_list()
        rows = self.rows
        if rows:
            self.open_project(rows[0]["id"])
        else:
            self.refresh_top()
            self.build_panel()
            self.draw_empty()
            self.rebuild_strip()

    def on_close(self):
        self.flush_save()
        self.root.destroy()

    # ------------------------------------------------------------------ preview
    def draw_empty(self):
        self.view.delete("all")
        w, h = self.view.winfo_width() or 600, self.view.winfo_height() or 400
        self.view.create_text(w / 2, h / 2 - 10, text="Start something", font=("Segoe UI", 20, "bold"), fill=INK)
        self.view.create_text(w / 2, h / 2 + 24, text="Click New project to open an example from the notes or describe your own idea.", font=("Segoe UI", 10), fill=MUTED)

    def schedule_preview(self, delay: int = 120):
        if self.preview_job:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(delay, self.refresh_preview)

    def _base_size(self):
        p = self.p
        if p["type"] == "presentation":
            return O.FORMATS[p["options"]["format"]]
        if p["type"] == "logo":
            return R.LOGO_SIZE
        return R.POST_SIZE if p["doc"]["doc_type"] in O.SHORT_DOC_TYPES else R.DOC_SIZE

    def refresh_preview(self):
        self.preview_job = None
        if not self.p:
            self.draw_empty()
            return
        p = self.p
        if p["type"] == "presentation":
            self.count = max(1, len(p["slides"]))
        elif p["type"] == "logo":
            self.count = len(O.LOGO_VARIANTS)
        else:
            self.count = len(R.render_pages(p, 0.1))
        self.page = max(0, min(self.page, self.count - 1))
        aw, ah = max(200, self.view.winfo_width() - 40), max(150, self.view.winfo_height() - 40)
        bw, bh = self._base_size()
        scale = max(0.1, min(aw / bw, ah / bh, 1.0))
        if p["type"] == "logo":
            img = R.render_logo(p, p["logo"]["variant"], scale)
        elif p["type"] == "presentation":
            img = R.render_slide(p, self.page, size=(int(bw * scale), int(bh * scale)))
        else:
            img = R.render_pages(p, scale)[self.page]
        self.tk_main = ImageTk.PhotoImage(img)
        self.view.delete("all")
        cx, cy = self.view.winfo_width() / 2, self.view.winfo_height() / 2
        self.view.create_rectangle(cx - img.width / 2 + 5, cy - img.height / 2 + 7, cx + img.width / 2 + 5, cy + img.height / 2 + 7, fill="#c9cedc", outline="")
        self.view.create_image(cx, cy, image=self.tk_main)
        self.rebuild_strip()

    def rebuild_strip(self):
        for w in self.strip.winfo_children():
            w.destroy()
        self.tk_thumbs = []
        p = self.p
        if not p:
            return
        if p["type"] == "logo":
            imgs = R.render_logo_variants(p, 0.11)
            labels = O.LOGO_VARIANTS
            current = p["logo"]["variant"]
        else:
            imgs = [R.render_slide(p, i, size=(int(O.FORMATS[p["options"]["format"]][0] * 0.07), int(O.FORMATS[p["options"]["format"]][1] * 0.07)))
                    for i in range(len(p["slides"]))] if p["type"] == "presentation" else R.render_pages(p, 0.075)
            labels = [f"{'Slide' if p['type'] == 'presentation' else 'Page'} {i + 1}" for i in range(len(imgs))]
            current = self.page
        for i, im in enumerate(imgs):
            im.thumbnail((150, 78))
            tkimg = ImageTk.PhotoImage(im)
            self.tk_thumbs.append(tkimg)
            b = tk.Button(self.strip, image=tkimg, text=labels[i], compound="top", command=lambda i=i: self.pick_page(i), font=("Segoe UI", 8),
                          bg=PANEL, relief="solid", bd=3 if i == current else 1, highlightbackground=ACCENT if i == current else LINE,
                          fg=INK if i == current else MUTED, activebackground=SOFT)
            b.configure(highlightthickness=0)
            if i == current:
                b.configure(bd=3, bg=SOFT)
            b.pack(side="left", padx=4, pady=2)

    def pick_page(self, i: int):
        if not self.p:
            return
        if self.p["type"] == "logo":
            self.p["logo"]["variant"] = i
            self.schedule_save()
        else:
            self.page = i
        self.refresh_preview()
        if self.tab == "content" and self.p["type"] == "presentation":
            self.build_panel()

    # ------------------------------------------------------------------ inspector
    def set_tab(self, key: str):
        self.tab = key
        self.build_panel()

    def build_panel(self):
        for k, b in self.tab_btns.items():
            b.configure(fg=INK if k == self.tab else MUTED, bg=SOFT if k == self.tab else PANEL)
        if self.panel:
            self.panel.destroy()
        self.panel = ScrollFrame(self.panel_holder)
        self.panel.pack(fill="both", expand=True, padx=12, pady=10)
        f = self.panel.inner
        if not self.p:
            tk.Label(f, text="Create or open a project to start editing.", bg=PANEL, fg=MUTED, wraplength=330, justify="left").pack(anchor="w")
            return
        {"content": self.tab_content, "look": self.tab_look, "refine": self.tab_refine, "canva": self.tab_canva}[self.tab](f)

    # small widget helpers -------------------------------------------------
    def h(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=INK, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 4))

    def hint(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED, wraplength=340, justify="left", font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 8))

    def entry(self, parent, label, get, setter, maxlen=0):
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        var = tk.StringVar(value=get())
        e = tk.Entry(parent, textvariable=var, relief="solid", bd=1, font=FONT, highlightthickness=0)
        e.pack(fill="x", pady=(2, 8), ipady=4)

        def on_change(*_):
            v = var.get()
            setter(v[:maxlen] if maxlen else v)
            self.schedule_save()
        var.trace_add("write", on_change)
        return e

    def text(self, parent, label, get, setter, height=5):
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        t = tk.Text(parent, height=height, wrap="word", relief="solid", bd=1, font=FONT, undo=True, highlightthickness=0)
        t.insert("1.0", get())
        t.edit_modified(False)
        t.pack(fill="x", pady=(2, 8))

        def on_modified(_):
            # fires for typing, pasting, undo and menu edits alike
            if t.edit_modified():
                t.edit_modified(False)
                setter(t.get("1.0", "end-1c"))
                self.schedule_save()
        t.bind("<<Modified>>", on_modified)
        return t

    def combo(self, parent, label, values, get, setter, rebuild=False, display=None):
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        names = [display.get(v, v) for v in values] if display else list(values)
        cb = ttk.Combobox(parent, values=names, state="readonly", font=FONT)
        cur = get()
        cb.set(display.get(cur, cur) if display else cur)
        cb.pack(fill="x", pady=(2, 8))

        def on_pick(_):
            idx = names.index(cb.get())
            setter(values[idx])
            self.schedule_save()
            if rebuild:
                self.build_panel()
        cb.bind("<<ComboboxSelected>>", on_pick)
        return cb

    def button(self, parent, text, cmd, accent=False, danger=False, state="normal"):
        b = tk.Button(parent, text=text, command=cmd, relief="flat", font=("Segoe UI", 9, "bold" if accent else "normal"), padx=10, pady=4, state=state,
                      bg=ACCENT if accent else SOFT, fg="#fff" if accent else ("#b42318" if danger else INK), activebackground="#2640d0" if accent else "#d3dbff")
        return b

    def btn_row(self, parent, specs):
        r = tk.Frame(parent, bg=PANEL)
        r.pack(fill="x", pady=4)
        for spec in specs:
            text, cmd, kw = (spec + ({},))[:3] if len(spec) == 2 else spec
            self.button(r, text, cmd, **kw).pack(side="left", padx=(0, 6), pady=2)
        return r

    # ---- content tab
    def tab_content(self, f):
        p = self.p
        if p["type"] == "presentation":
            if not p["slides"]:
                self.hint(f, "This deck has no slides.")
                self.btn_row(f, [("Add a slide", self.add_slide)])
                return
            i = self.page = min(self.page, len(p["slides"]) - 1)
            s = p["slides"][i]
            self.h(f, f"Slide {i + 1} of {len(p['slides'])}")
            self.entry(f, "Title", lambda: s["title"], lambda v: s.__setitem__("title", v))
            self.text(f, "Text (start a line with - for a bullet)", lambda: s["body"], lambda v: s.__setitem__("body", v), 6)
            lay = {"auto": "Automatic", "title": "Title", "bullets": "Bullet list", "statement": "Big statement", "cta": "Call to action"}
            self.combo(f, "Layout", list(lay), lambda: s["layout"], lambda v: s.__setitem__("layout", v), display=lay)
            specs = [("Replace image" if s["image"] else "Add image", self.pick_image)]
            if s["image"]:
                specs.append(("Remove image", self.remove_image))
            self.btn_row(f, specs)
            self.h(f, "Slides")
            self.btn_row(f, [("Add slide after", self.add_slide), ("Duplicate", self.dup_slide)])
            self.btn_row(f, [("Move earlier", lambda: self.move_slide(-1), {"state": "normal" if i > 0 else "disabled"}),
                             ("Move later", lambda: self.move_slide(1), {"state": "normal" if i < len(p["slides"]) - 1 else "disabled"}),
                             ("Delete", self.del_slide, {"danger": True, "state": "normal" if len(p["slides"]) > 1 else "disabled"})])
        elif p["type"] == "document":
            self.combo(f, "Document type", O.DOC_TYPES, lambda: p["doc"]["doc_type"], lambda v: p["doc"].__setitem__("doc_type", v))
            self.hint(f, "Caption, Tweet and Social post become a square post; everything else is a paged document.")
            for i, sec in enumerate(p["doc"]["sections"]):
                box = tk.Frame(f, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
                box.pack(fill="x", pady=6)
                inner = tk.Frame(box, bg=PANEL)
                inner.pack(fill="x", padx=8, pady=8)
                self.entry(inner, "Heading", lambda sec=sec: sec["heading"], lambda v, sec=sec: sec.__setitem__("heading", v))
                self.text(inner, "Text", lambda sec=sec: sec["body"], lambda v, sec=sec: sec.__setitem__("body", v), 4)
                self.btn_row(inner, [("Up", lambda i=i: self.move_sec(i, -1), {"state": "normal" if i else "disabled"}),
                                     ("Down", lambda i=i: self.move_sec(i, 1), {"state": "normal" if i < len(p["doc"]["sections"]) - 1 else "disabled"}),
                                     ("Delete", lambda i=i: self.del_sec(i), {"danger": True})])
            self.btn_row(f, [("Add section", self.add_sec)])
        else:
            l = p["logo"]
            self.entry(f, "Brand name", lambda: l["brand"], lambda v: l.__setitem__("brand", v), 60)
            self.entry(f, "Tagline", lambda: l["tagline"], lambda v: l.__setitem__("tagline", v), 80)
            self.text(f, "What does the brand do? (picks the icon)", lambda: l["description"], lambda v: l.__setitem__("description", v), 4)
            self.combo(f, "Icon", O.LOGO_ICONS, lambda: l["icon"], lambda v: l.__setitem__("icon", v))
            self.hint(f, "Pick a layout by clicking one of the four options under the preview.")

    # slide / section operations
    def after_structure(self):
        self.schedule_save()
        self.refresh_preview()
        self.build_panel()

    def add_slide(self):
        self.p["slides"].insert(self.page + 1, {"title": "New slide", "body": "- Add a point", "layout": "auto", "image": ""})
        self.page = min(self.page + 1, len(self.p["slides"]) - 1)
        self.after_structure()

    def dup_slide(self):
        self.p["slides"].insert(self.page + 1, dict(self.p["slides"][self.page]))
        self.page += 1
        self.after_structure()

    def move_slide(self, d: int):
        s, j = self.p["slides"], self.page + d
        s[self.page], s[j] = s[j], s[self.page]
        self.page = j
        self.after_structure()

    def del_slide(self):
        del self.p["slides"][self.page]
        self.page = max(0, self.page - 1)
        self.after_structure()

    def add_sec(self):
        self.p["doc"]["sections"].append({"heading": "New section", "body": ""})
        self.after_structure()

    def del_sec(self, i: int):
        del self.p["doc"]["sections"][i]
        self.after_structure()

    def move_sec(self, i: int, d: int):
        a = self.p["doc"]["sections"]
        a[i], a[i + d] = a[i + d], a[i]
        self.after_structure()

    def pick_image(self, path: str | None = None):
        path = path or filedialog.askopenfilename(title="Choose an image", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif")])
        if not path:
            return
        try:
            img = Image.open(path)
            img.load()
            img = img.convert("RGB")
        except Exception:  # noqa: BLE001
            self.say("That file is not a readable image. Use png, jpg, webp or gif.", True)
            return
        img.thumbnail((2400, 2400))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
        self.p["slides"][self.page]["image"] = self.store.save_upload(buf.getvalue(), "jpg")
        self.after_structure()
        self.say("Image added to the slide.")

    def remove_image(self):
        self.p["slides"][self.page]["image"] = ""
        self.after_structure()

    # ---- look tab
    def tab_look(self, f):
        p = self.p
        o = p["options"]
        self.combo(f, "Style", O.STYLES, lambda: o["style"], lambda v: o.__setitem__("style", v))
        tk.Label(f, text="Colour", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        sw = tk.Frame(f, bg=PANEL)
        sw.pack(fill="x", pady=(2, 10))
        for c in O.COLORS:
            on = c == o["color"]
            tk.Button(sw, bg=O.PALETTES[c]["primary"], width=2, height=1, relief="solid" if on else "flat", bd=3 if on else 0,
                      activebackground=O.PALETTES[c]["primary"], command=lambda c=c: self.set_color(c)).pack(side="left", padx=3)
        tk.Label(f, text=f"Selected: {o['color']}", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        if p["type"] == "presentation":
            self.combo(f, "Format", list(O.FORMATS), lambda: o["format"], lambda v: o.__setitem__("format", v))
        names = ["Soft", "Brighter", "Bold", "Vivid"]
        bl = tk.Label(f, text=f"Colour intensity: {names[p['tune']['boldness']]}", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        bl.pack(anchor="w", pady=(8, 0))

        def on_bold(v):
            n = int(round(float(v)))
            p["tune"]["boldness"] = n
            bl.configure(text=f"Colour intensity: {names[n]}")
            self.schedule_save()
        s1 = ttk.Scale(f, from_=0, to=3, value=p["tune"]["boldness"], command=on_bold)
        s1.pack(fill="x", pady=(2, 8))
        tl = tk.Label(f, text=f"Text size: {round(p['tune']['text_scale'] * 100)}%", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        tl.pack(anchor="w")

        def on_text(v):
            val = round(float(v) / 0.05) * 0.05
            p["tune"]["text_scale"] = round(val, 2)
            tl.configure(text=f"Text size: {round(val * 100)}%")
            self.schedule_save()
        ttk.Scale(f, from_=0.7, to=1.6, value=p["tune"]["text_scale"], command=on_text).pack(fill="x", pady=(2, 8))

    def set_color(self, c: str):
        self.p["options"]["color"] = c
        self.schedule_save()
        self.build_panel()

    # ---- refine tab
    def tab_refine(self, f):
        self.hint(f, "Describe a change in plain words, then apply it. Keep refining until it matches your vision.")
        tk.Label(f, text="What should change?", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.refine_box = tk.Text(f, height=3, wrap="word", relief="solid", bd=1, font=FONT, highlightthickness=0)
        self.refine_box.pack(fill="x", pady=(2, 8))
        ideas = ["Make it brighter and bolder", "Bigger text, fill up slides that look too empty", "Use a different colour palette",
                 "Make it elegant", "Come up with a more interesting title", "Make it blue"]
        for t in ideas:
            tk.Button(f, text=t, anchor="w", relief="flat", bg=PANEL, fg=ACCENT, cursor="hand2", font=("Segoe UI", 9),
                      command=lambda t=t: (self.refine_box.delete("1.0", "end"), self.refine_box.insert("1.0", t))).pack(fill="x")
        self.btn_row(f, [("Apply change", self.apply_refine, {"accent": True})])
        self.h(f, "What you've changed")
        if not self.p["history"]:
            self.hint(f, "Nothing yet.")
        for h in reversed(self.p["history"]):
            tk.Label(f, text=f"“{h['prompt']}”", bg=PANEL, fg=MUTED, wraplength=340, justify="left", font=("Segoe UI", 9, "italic")).pack(anchor="w")
            tk.Label(f, text="; ".join(h.get("changes", [])), bg=PANEL, fg=INK, wraplength=340, justify="left").pack(anchor="w", pady=(0, 6))
        self.hint(f, "These tweaks are rule-based (colour, boldness, size, style, title), not an AI model. Add photos with Add image on a slide.")

    def apply_refine(self, text: str | None = None):
        text = text if text is not None else self.refine_box.get("1.0", "end-1c").strip()
        if not text:
            self.say("Describe the change you want first.", True)
            return
        self.flush_save()
        self.p, changes = G.refine(self.p, text)
        self.p = self.store.save(self.p)
        self.say(" - ".join(changes))
        self.refresh_list()
        self.refresh_preview()
        self.build_panel()
        return changes

    # ---- canva tab
    def tab_canva(self, f):
        c, p = self.canva, self.p
        label = "demo Canva" if self.cfg["demo"] else "Canva"
        box = tk.Frame(f, bg=SOFT)
        box.pack(fill="x", pady=(0, 8))
        if c["signed_in"]:
            tk.Label(box, text=f"Signed in to {label}" + (f" as {c['name']}" if c["name"] else ""), bg=SOFT, fg=INK, font=("Segoe UI", 10, "bold"), anchor="w", padx=10, pady=6).pack(fill="x")
            tk.Label(box, text="Pushes create a new design in this account.", bg=SOFT, fg=INK, anchor="w", padx=10).pack(fill="x", pady=(0, 8))
            self.btn_row(f, [("Sign out", self.sign_out)])
        else:
            tk.Label(box, text="Not signed in", bg=SOFT, fg=INK, font=("Segoe UI", 10, "bold"), anchor="w", padx=10, pady=6).pack(fill="x")
            tk.Label(box, text=("Demo mode uses a local stand-in with an email box." if self.cfg["demo"] else
                                "You sign in with your email on Canva's own page in your browser; this app never sees your password."),
                     bg=SOFT, fg=INK, wraplength=330, justify="left", padx=10).pack(fill="x", pady=(0, 8))
            if self.cancel_signin:
                self.btn_row(f, [("Cancel sign-in", self.cancel_sign_in)])
            else:
                self.btn_row(f, [("Sign in" + (" (demo)" if self.cfg["demo"] else " with Canva"), self.sign_in, {"accent": True})])
        self.combo(f, "Planned finishing touch in Canva", O.FEATURES, lambda: p["options"]["feature"], lambda v: p["options"].__setitem__("feature", v))
        self.hint(f, "Animation, audio and video are added inside Canva after you push.")
        self.btn_row(f, [(("Push this project to Canva" if c["signed_in"] else "Sign in to push"), self.on_push, {"accent": True, "state": "disabled" if self.busy else "normal"})])
        self.hint(f, "Logos arrive as an image design." if p["type"] == "logo" else
                  "Decks and documents arrive as a multi-page design built from the pages you see (pages are images, so recreate text in Canva if you need to edit it).")
        self.h(f, "Pushed from this project")
        pushes = p.get("pushes", [])
        if not pushes:
            self.hint(f, "Nothing pushed yet.")
        for x in pushes:
            self.link_row(f, f"{x['title']} - {x['kind']}", x.get("edit_url", ""))
        if c["signed_in"]:
            self.h(f, "Your recent Canva designs")
            if self.recent is None:
                self.hint(f, "Loading...")
                self.bg(lambda: self.client.list_designs(12), self._recent_loaded)
            elif isinstance(self.recent, dict):
                self.hint(f, self.recent["error"])
            elif not self.recent:
                self.hint(f, "No designs found.")
            else:
                for d in self.recent:
                    self.link_row(f, d["title"], d.get("edit_url", ""))
        self.h(f, "Connect your real Canva account")
        self.hint(f, "1. Go to canva.com/developers and create an integration.\n"
                     f"2. Add this redirect URL: {self.cfg['redirect_uri']}\n"
                     "3. Enable scopes: design:meta:read, design:content:read, design:content:write, asset:read, asset:write, profile:read.\n"
                     "4. Copy shared/config.example.json to shared/config.json and paste your client id and secret.\n"
                     "5. Restart the app. The chip at the top will say Canva (not Demo Canva).")

    def link_row(self, f, text, url):
        r = tk.Frame(f, bg=PANEL)
        r.pack(fill="x", pady=2)
        tk.Label(r, text=text, bg=PANEL, fg=INK, anchor="w", wraplength=250, justify="left").pack(side="left", fill="x", expand=True)
        if url:
            tk.Button(r, text="Open", relief="flat", bg=PANEL, fg=ACCENT, cursor="hand2", command=lambda: webbrowser.open(url)).pack(side="right")

    def _recent_loaded(self, result, error):
        self.recent = result if not error else {"error": str(error)}
        if self.tab == "canva" and self.p:
            self.build_panel()

    # ------------------------------------------------------------------ Canva actions
    def _load_status(self):
        if not self.client.is_signed_in():
            return {"signed_in": False, "name": ""}
        try:
            return {"signed_in": True, "name": self.client.profile().get("display_name", "")}
        except NotSignedIn:
            return {"signed_in": False, "name": ""}
        except CanvaError:
            return {"signed_in": True, "name": ""}

    def _status_loaded(self, result, error):
        if result:
            self.canva = result
        self.refresh_top()
        rows = self.store.list()
        if self.p is None:
            last = rows[0]["id"] if rows else None
            if last:
                self.open_project(last)
            else:
                self.open_new()
        elif self.tab == "canva":
            self.build_panel()

    def sign_in(self):
        if self.cancel_signin:
            return
        self.flush_save()
        verifier, challenge = make_pkce()
        import secrets
        state = secrets.token_urlsafe(24)
        url = self.client.authorize_url(state, challenge)
        self.cancel_signin = threading.Event()
        cancel = self.cancel_signin
        self.say("Your browser opened Canva's sign-in page. Finish there, then come back.")
        self.build_panel() if self.tab == "canva" else None

        def job():
            webbrowser.open(url)
            code = wait_for_callback(self.cfg["redirect_uri"], state, cancel=cancel)
            self.client.exchange_code(code, verifier)
            try:
                name = self.client.profile().get("display_name", "")
            except CanvaError:
                name = ""
            return {"signed_in": True, "name": name}

        def done(result, error):
            self.cancel_signin = None
            if error:
                self.say(str(error), True)
            else:
                self.canva = result
                self.recent = None
                self.say("Signed in to Canva. You can push now.")
            self.refresh_top()
            if self.tab == "canva" and self.p:
                self.build_panel()
        self.bg(job, done)

    def cancel_sign_in(self):
        if self.cancel_signin:
            self.cancel_signin.set()

    def sign_out(self):
        self.client.sign_out()
        self.canva = {"signed_in": False, "name": ""}
        self.recent = None
        self.refresh_top()
        self.build_panel()
        self.say("Signed out of Canva.")

    def on_push(self):
        if not self.p or self.busy:
            return
        if not self.canva["signed_in"]:
            self.set_tab("canva")
            self.sign_in()
            return
        self.flush_save()
        project = dict(self.p)
        self.busy = True
        self.say("Pushing to Canva...")
        self.refresh_top()

        def done(result, error):
            self.busy = False
            if error:
                if isinstance(error, NotSignedIn):
                    self.canva = {"signed_in": False, "name": ""}
                self.say(str(error) + (" Use Sign in to continue." if isinstance(error, NotSignedIn) else ""), True)
            else:
                self.p["pushes"] = ([result] + self.p["pushes"])[:10]
                self.p = self.store.save(self.p)
                self.recent = None
                self.say(f"Pushed \"{result['title']}\" as a {result['kind']}.", link=result.get("edit_url", ""))
                self.refresh_list()
            self.refresh_top()
            if self.tab == "canva":
                self.build_panel()
        self.bg(lambda: push_project(self.client, project), done)

    # ------------------------------------------------------------------ downloads
    def save_pdf(self, path: str | None = None):
        path = path or filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=M.slug(self.p["title"]) + ".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            Path(path).write_bytes(R.pages_to_pdf(R.render_pages(self.p, 1.0)))
            self.say(f"Saved {path}")
        except (ValueError, OSError) as exc:
            self.say(str(exc), True)

    def save_pngs(self, folder: str | None = None):
        folder = folder or filedialog.askdirectory(title="Choose a folder for the PNG images")
        if not folder:
            return
        imgs = R.render_pages(self.p, 1.0)
        for i, im in enumerate(imgs, 1):
            im.save(Path(folder) / f"{M.slug(self.p['title'])}-{i:02d}.png")
        self.say(f"Saved {len(imgs)} images to {folder}")

    def save_png_single(self, path: str | None = None):
        path = path or filedialog.asksaveasfilename(defaultextension=".png", initialfile=M.slug(self.p["title"]) + ".png", filetypes=[("PNG", "*.png")])
        if path:
            R.render_pages(self.p, 1.0)[0].save(path)
            self.say(f"Saved {path}")

    # ------------------------------------------------------------------ new project window
    def open_new(self):
        if self.newwin and self.newwin.winfo_exists():
            self.newwin.lift()
            return
        w = self.newwin = tk.Toplevel(self.root)
        w.title("New project")
        w.geometry("760x640")
        w.configure(bg=PANEL)
        w.transient(self.root)
        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        ex = ScrollFrame(nb)
        nb.add(ex, text="From the notes")
        tk.Label(ex.inner, text="Each one comes from a scenario in the notes. Open one, then change anything.", bg=PANEL, fg=MUTED, wraplength=640, justify="left").pack(anchor="w", pady=8, padx=8)
        for e in G.load_examples():
            card = tk.Button(ex.inner, text=f"{e['name']}   ({KIND[e['kind']]})\n{e['description']}", anchor="w", justify="left", wraplength=620, relief="solid", bd=1,
                             bg=PANEL, activebackground=SOFT, padx=12, pady=10, font=FONT, command=lambda eid=e["id"]: self.start_example(eid))
            card.pack(fill="x", padx=8, pady=5)
        idea = ScrollFrame(nb)
        nb.add(idea, text="From my idea")
        self._build_idea_form(idea.inner)

    def _build_idea_form(self, f):
        self.new_type = tk.StringVar(value="presentation")
        tk.Label(f, text="What are you making?", bg=PANEL, fg=MUTED).pack(anchor="w", padx=8, pady=(8, 2))
        tr = tk.Frame(f, bg=PANEL)
        tr.pack(anchor="w", padx=8)
        for key in O.PROJECT_TYPES:
            tk.Radiobutton(tr, text=KIND[key], variable=self.new_type, value=key, bg=PANEL, command=lambda: None).pack(side="left", padx=(0, 12))
        tk.Label(f, text="Describe your idea (for a logo, say 'called Name' to set the name)", bg=PANEL, fg=MUTED).pack(anchor="w", padx=8, pady=(10, 2))
        self.n_prompt = tk.Text(f, height=4, wrap="word", relief="solid", bd=1, font=FONT, highlightthickness=0)
        self.n_prompt.pack(fill="x", padx=8)
        tk.Label(f, text="Title or brand name (optional)", bg=PANEL, fg=MUTED).pack(anchor="w", padx=8, pady=(10, 2))
        self.n_title = tk.Entry(f, relief="solid", bd=1, font=FONT)
        self.n_title.pack(fill="x", padx=8, ipady=4)
        self.n_vars = {}
        grid = tk.Frame(f, bg=PANEL)
        grid.pack(fill="x", padx=8, pady=10)
        fields = [("style", "Style", O.STYLES, "Modern"), ("color", "Colour", O.COLORS, "Blue"), ("length", "Length (presentations)", list(O.LENGTHS), "Balanced (5 to 15 pages)"),
                  ("format", "Format (presentations)", list(O.FORMATS), "Presentation (16:9)"), ("audience", "Audience", O.AUDIENCES, "Casual"),
                  ("theme", "Theme", O.THEMES, "Productivity"), ("doc_type", "Document type (documents)", O.DOC_TYPES, "Blog post")]
        for i, (key, label, values, default) in enumerate(fields):
            cell = tk.Frame(grid, bg=PANEL)
            cell.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)
            grid.columnconfigure(i % 2, weight=1)
            tk.Label(cell, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
            cb = ttk.Combobox(cell, values=values, state="readonly")
            cb.set(default)
            cb.pack(fill="x")
            self.n_vars[key] = cb
        tk.Label(f, text="This builds an editable starter from your words using templates (it is not an AI). Replace everything with your own text.",
                 bg=PANEL, fg=MUTED, wraplength=640, justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=8)
        tk.Button(f, text="Create project", command=self.create_idea, bg=ACCENT, fg="#fff", relief="flat", padx=14, pady=6, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=12)

    def start_example(self, example_id: str):
        project = self.store.save(G.project_from_example(example_id))
        self._created(project)

    def create_idea(self, values: dict | None = None):
        if values is None:
            values = {"type": self.new_type.get(), "prompt": self.n_prompt.get("1.0", "end-1c").strip(), "title": self.n_title.get().strip(),
                      **{k: v.get() for k, v in self.n_vars.items()}}
        if not values["prompt"]:
            self.say("Describe your idea first - even one sentence works.", True)
            if self.newwin and self.newwin.winfo_exists():
                messagebox.showinfo("Describe your idea", "Describe your idea first - even one sentence works.", parent=self.newwin)
            return
        opts = {k: values[k] for k in ("style", "color", "length", "format", "audience", "theme") if k in values}
        project = G.build_project(values["type"], values["prompt"][:2000], opts, doc_type=values.get("doc_type", "Blog post"), title=values.get("title", "")[:120])
        self._created(self.store.save(project))

    def _created(self, project: dict):
        if self.newwin and self.newwin.winfo_exists():
            self.newwin.destroy()
        self.open_project(project["id"])


def enable_hidpi():
    try:  # Windows: crisp text on high-DPI screens
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def main():
    cfg = load_config("desktop")
    if cfg["demo"]:
        ensure_demo_server()
    enable_hidpi()
    root = tk.Tk()
    App(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()
