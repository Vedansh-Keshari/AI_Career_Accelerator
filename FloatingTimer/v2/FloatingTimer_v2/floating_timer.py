"""
Floating Timer  (v2)
--------------------
A small always-on-top desktop timer in black / orange / red.

* Type a start time, press Enter -> it starts.
* It ALWAYS counts down:   00:00:03 -> 00:00:02 -> 00:00:01 -> 00:00:00 -> -00:00:01 ...
  A negative start keeps going more negative:  -00:03:00 -> -00:03:01 -> -00:04:00
* No AM/PM, no time of day, hours never wrap at 24.
* Buttons:  Play/Pause  -  Stop  -  Restart  -  Set
* Keys:     Space = play/pause   S = stop   R = restart   E = set time
* Drag anywhere (not on a button) to move it.  Right-click for the menu / Quit.

Time formats:  H:M:S   M:S   S   (optional leading - or +)
Examples:      5:00   1:30:00   90:00   -45   0
"""
import math
import time
import tkinter as tk
import tkinter.font as tkfont

BG = "#000000"
ORANGE = "#ff8c00"
RED = "#ff2a2a"
RED_DK = "#7a1212"
DIM = "#8a4b00"
TRACK = "#241200"
BTN = "#1a1a1a"
FONT = "Consolas"

W, H = 400, 215


# ---------------------------------------------------------------- time logic
def parse(text):
    """'-0:05:00' -> -300.  Raises ValueError on bad input."""
    s = text.strip()
    neg = s.startswith("-")
    s = s.lstrip("+-").strip()
    parts = s.split(":")
    if not 1 <= len(parts) <= 3 or not all(p.strip().isdigit() for p in parts):
        raise ValueError("bad time")
    total = 0
    for p in parts:
        total = total * 60 + int(p)
    return -total if neg else total


def fmt(value):
    """300 -> '00:05:00', -300 -> '-00:05:00'. Hours may exceed 24."""
    sign = "-" if value < 0 else ""
    a = abs(value)
    h, rem = divmod(a, 3600)
    m, s = divmod(rem, 60)
    return f"{sign}{h:02d}:{m:02d}:{s:02d}"


def value_at(start, elapsed):
    """Always goes DOWN: 1 -> 0 -> -1 -> -2 ... and -3 -> -4 -> -5 ..."""
    return start - int(elapsed)


def round_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


# ----------------------------------------------------------------------- app
class FloatingTimer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.mode = "stopped"        # setup | stopped | running | paused
        self.prev_mode = None
        self.has_start = False
        self.start_value = 0
        self.elapsed_before = 0.0
        self.t_resume = 0.0
        self._job = None
        self._fit_cache = {}
        self._hover = None
        self._play_state = None
        self.commands = {}
        self.centers = {}

        self.root = r = tk.Tk()
        r.title("Floating Timer")
        r.overrideredirect(True)          # no title bar -> nothing to close by accident
        r.attributes("-topmost", True)    # floats above other windows
        try:
            r.attributes("-alpha", 0.95)
        except tk.TclError:
            pass
        r.configure(bg=BG, highlightthickness=2, highlightbackground=ORANGE)
        r.geometry(f"{W + 4}x{H + 4}+120+120")

        self.c = c = tk.Canvas(r, width=W, height=H, bg=BG, highlightthickness=0)
        c.pack()

        # status row
        self.dot = c.create_oval(18, 20, 28, 30, fill=ORANGE, outline="")
        self.status = c.create_text(36, 25, anchor="w", text="", fill=ORANGE,
                                    font=(FONT, 11, "bold"))
        self.start_lbl = c.create_text(W - 18, 25, anchor="e", text="", fill=DIM,
                                       font=(FONT, 10))
        # big time
        self.time_txt = c.create_text(W // 2, 84, text="00:00:00", fill=ORANGE,
                                      font=(FONT, 56, "bold"))
        # progress bar
        self.bar_x1, self.bar_x2, self.bar_y = 30, W - 30, 132
        self.track = round_rect(c, self.bar_x1, self.bar_y, self.bar_x2, self.bar_y + 8, 4,
                                fill=TRACK, outline="")
        self.bar = c.create_rectangle(self.bar_x1, self.bar_y, self.bar_x1,
                                      self.bar_y + 8, fill=ORANGE, outline="")
        # input (setup mode)
        self.entry = tk.Entry(
            r, font=(FONT, 30, "bold"), justify="center", bg=BG, fg=ORANGE,
            insertbackground=ORANGE, relief="flat", highlightthickness=1,
            highlightbackground=DIM, highlightcolor=ORANGE, width=9)
        self.entry_win = c.create_window(W // 2, 80, window=self.entry, state="hidden")
        self.hint = c.create_text(W // 2, 124, text="e.g. 5:00    1:30:00    -45    Enter = start",
                                  fill=DIM, font=(FONT, 10), state="hidden")
        self.entry.bind("<Return>", lambda e: self.confirm())
        self.entry.bind("<Escape>", lambda e: self.cancel())

        # buttons
        bw, bh, gap = 70, 36, 12
        x0 = (W - (4 * bw + 3 * gap)) // 2 + bw // 2
        y = 174
        specs = [("play", self.toggle), ("stop", self.stop),
                 ("restart", self.restart), ("set", self.edit)]
        for i, (name, cmd) in enumerate(specs):
            self._add_button(name, x0 + i * (bw + gap), y, bw, bh, cmd)

        # menu + bindings
        self.menu = tk.Menu(r, tearoff=0, bg=BG, fg=ORANGE,
                            activebackground=ORANGE, activeforeground=BG)
        self.menu.add_command(label="Set new time", command=self.edit)
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=r.destroy)
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        c.bind("<Button-2>", self._popup)
        c.bind("<Button-3>", self._popup)
        r.bind("<Key>", self._key)

        self.edit()                      # first thing: ask for the time
        self.tick()

    # ------------------------------------------------------------ buttons
    def _add_button(self, name, cx, cy, w, h, command):
        c = self.c
        self.commands[name] = command
        self.centers[name] = (cx, cy)
        tags = ("btn", f"btn_{name}")
        round_rect(c, cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2, 10,
                   fill=BTN, outline=DIM, tags=tags + (f"{name}_bg",))
        self._draw_icon(name)
        c.tag_bind(f"btn_{name}", "<Enter>", lambda e, n=name: self._set_hover(n))
        c.tag_bind(f"btn_{name}", "<Leave>", lambda e, n=name: self._set_hover(None))
        c.tag_bind(f"btn_{name}", "<ButtonRelease-1>", lambda e, n=name: self._invoke(n))

    def _invoke(self, name):
        self.commands[name]()
        self.refresh()

    def _icon_color(self, name):
        if self._hover == name:
            return BG
        return RED if name == "stop" else ORANGE

    def _draw_icon(self, name, kind=None):
        c = self.c
        cx, cy = self.centers[name]
        col = self._icon_color(name)
        tags = ("btn", f"btn_{name}", f"{name}_icon")
        kind = kind or name
        if kind == "play":
            c.create_polygon(cx - 6, cy - 9, cx - 6, cy + 9, cx + 9, cy,
                             fill=col, outline="", tags=tags)
        elif kind == "pause":
            c.create_rectangle(cx - 8, cy - 9, cx - 3, cy + 9, fill=col, outline="", tags=tags)
            c.create_rectangle(cx + 3, cy - 9, cx + 8, cy + 9, fill=col, outline="", tags=tags)
        elif kind == "stop":
            c.create_rectangle(cx - 8, cy - 8, cx + 8, cy + 8, fill=col, outline="", tags=tags)
        elif kind == "restart":
            c.create_arc(cx - 9, cy - 9, cx + 9, cy + 9, start=60, extent=290,
                         style="arc", width=3, outline=col, tags=tags)
            c.create_polygon(cx + 9, cy - 6, cx + 3, cy + 2, cx + 15, cy + 2,
                             fill=col, outline="", tags=tags)
        elif kind == "set":
            c.create_text(cx, cy, text="SET", fill=col, font=(FONT, 12, "bold"), tags=tags)

    def _recolor(self, name):
        col = self._icon_color(name)
        for item in self.c.find_withtag(f"{name}_icon"):
            if self.c.type(item) == "arc":
                self.c.itemconfig(item, outline=col)
            else:
                self.c.itemconfig(item, fill=col)

    def _set_hover(self, name):
        old, self._hover = self._hover, name
        for n in (old, name):
            if n:
                hot = self._hover == n
                fill = (RED if n == "stop" else ORANGE) if hot else BTN
                self.c.itemconfig(f"{n}_bg", fill=fill)
                self._recolor(n)

    # ----------------------------------------------------- drag / menu / keys
    def _press(self, e):
        self.root.focus_force()
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag(self, e):
        if "btn" in self.c.gettags("current"):
            return
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _popup(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def _key(self, e):
        if self.mode == "setup":
            return
        k = e.keysym.lower()
        if k == "space":
            self.toggle()
        elif k == "s":
            self.stop()
        elif k == "r":
            self.restart()
        elif k == "e":
            self.edit()
        self.refresh()

    # ------------------------------------------------------------ timer state
    def elapsed(self):
        extra = self.clock() - self.t_resume if self.mode == "running" else 0.0
        return self.elapsed_before + extra

    def value(self):
        return value_at(self.start_value, self.elapsed())

    def _resume(self):
        self.t_resume = self.clock()
        self.mode = "running"

    def pause(self):
        if self.mode == "running":
            self.elapsed_before = self.elapsed()
            self.mode = "paused"

    def toggle(self):
        if self.mode == "running":
            self.pause()
        elif self.mode == "paused":
            self._resume()
        elif self.mode == "stopped":
            self.elapsed_before = 0.0
            self._resume()

    def stop(self):
        if self.mode == "setup":
            return
        self.elapsed_before = 0.0
        self.mode = "stopped"

    def restart(self):
        if self.mode == "setup":
            return
        self.elapsed_before = 0.0
        self._resume()

    def edit(self):
        if self.mode == "setup":
            return
        if self.mode == "running":
            self.pause()
        self.prev_mode = self.mode if self.has_start else None
        self.mode = "setup"
        self.entry.delete(0, "end")
        self.entry.config(highlightbackground=DIM)
        self.c.itemconfig(self.entry_win, state="normal")
        self.c.itemconfig(self.hint, state="normal")
        self.c.itemconfig(self.time_txt, state="hidden")
        self.c.itemconfig(self.bar, state="hidden")
        self.c.itemconfig(self.track, state="hidden")
        self.root.update_idletasks()
        self.root.focus_force()
        self.entry.focus_set()

    def _leave_setup(self):
        self.c.itemconfig(self.entry_win, state="hidden")
        self.c.itemconfig(self.hint, state="hidden")
        self.c.itemconfig(self.time_txt, state="normal")
        self.c.itemconfig(self.bar, state="normal")
        self.c.itemconfig(self.track, state="normal")
        self.root.focus_set()

    def confirm(self):
        try:
            self.start_value = parse(self.entry.get())
        except ValueError:
            self.entry.config(highlightbackground=RED)
            self.entry.delete(0, "end")
            return
        self.has_start = True
        self.elapsed_before = 0.0
        self._leave_setup()
        self._resume()
        self.refresh()

    def cancel(self):
        if self.mode != "setup" or not self.has_start:
            return
        self._leave_setup()
        self.mode = self.prev_mode or "stopped"
        self.refresh()

    # ----------------------------------------------------------------- drawing
    def _fit(self, text):
        """Biggest font size (<=56) that keeps `text` inside the window."""
        n = len(text)
        if n not in self._fit_cache:
            size = 56
            while size > 20:
                f = tkfont.Font(family=FONT, size=size, weight="bold")
                if f.measure("0" * n) <= W - 36:
                    break
                size -= 2
            self._fit_cache[n] = size
        return self._fit_cache[n]

    def tick(self):
        if self._job:
            self.root.after_cancel(self._job)
        self.refresh()
        self._job = self.root.after(100, self.tick)

    def refresh(self):
        c = self.c
        v = self.value() if self.has_start else 0
        running = self.mode == "running"
        over = v < 0

        # status
        if self.mode == "setup":
            text, col = "SET TIME", ORANGE
        elif self.mode == "running":
            text, col = ("OVERTIME", RED) if over else ("RUNNING", ORANGE)
        elif self.mode == "paused":
            text, col = "PAUSED", DIM
        else:
            text, col = "STOPPED", DIM
        pulse = running and int(self.elapsed()) % 2 == 1
        c.itemconfig(self.status, text=text, fill=col)
        c.itemconfig(self.dot, fill=(RED_DK if (pulse and over) else col) if running else col)
        c.itemconfig(self.start_lbl,
                     text=f"START {fmt(self.start_value)}" if self.has_start else "")

        # big time
        if self.mode != "setup":
            tcol = RED if over else ORANGE
            if self.mode in ("paused", "stopped"):
                tcol = RED if over else ORANGE
            label = fmt(v)
            c.itemconfig(self.time_txt, text=label, fill=tcol,
                         font=(FONT, self._fit(label), "bold"))

            # progress bar
            span = self.bar_x2 - self.bar_x1
            if v > 0 and self.start_value > 0:
                w, bcol = span * min(1.0, v / self.start_value), ORANGE
            elif v < 0:
                w, bcol = span, (RED_DK if pulse else RED)
            else:
                w, bcol = 0, ORANGE
            c.coords(self.bar, self.bar_x1, self.bar_y, self.bar_x1 + w, self.bar_y + 8)
            c.itemconfig(self.bar, fill=bcol)

        # play/pause icon follows state
        want = "pause" if running else "play"
        if want != self._play_state:
            self.c.delete("play_icon")
            self._draw_icon("play", want)
            self._play_state = want

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FloatingTimer().run()
