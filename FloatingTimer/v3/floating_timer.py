"""
Floating Timer  (v3)
--------------------
A small always-on-top desktop timer in black / orange / red.

* Set the start time by SCROLLING (mouse wheel over hours / minutes / seconds),
  or click the small values above/below a column. Shift+wheel = steps of 10.
  The +/- sign switches between a positive and a negative start.
  The "60h" chip fills in 60:00:00 in one click.
* Press play (or Enter) to start. It ALWAYS counts down:
      00:00:03 -> 00:00:02 -> 00:00:01 -> 00:00:00 -> -00:00:01 ...
  A negative start keeps going more negative:  -00:03:00 -> -00:03:01 ...
* +60h  adds 60 hours to the running time, any time, without a reset.
  (Stop / Restart / Set go back to the time you originally set.)
* No AM/PM, no time of day, hours never wrap at 24.
* Buttons: Play/Pause - Stop - Restart - Set - +60h
* Keys while running: Space = play/pause, S = stop, R = restart, E = set, A = +60h
* Keys while setting: Up/Down = change, Left/Right = pick column, - = sign,
                      Enter = start, Esc = cancel
* Drag anywhere (not on a button) to move it.  Right-click for the menu / Quit.
"""
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
ADD_SECONDS = 60 * 3600          # what the +60h button adds
MAX_HOURS = 999
TIME_Y = 84                      # vertical centre of the time / picker row


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
    COLS_X = (112, 198, 280)       # hours / minutes / seconds columns
    SIGN_X = 38

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.mode = "stopped"        # setup | stopped | running | paused
        self.prev_mode = None
        self.has_start = False
        self.base_start = 0          # the time the user set
        self.extra = 0               # seconds added with +60h
        self.elapsed_before = 0.0
        self.t_resume = 0.0
        self.fields = [0, 0, 0]      # picker: hours, minutes, seconds
        self.neg = False
        self.sel = 0
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
        self.time_txt = c.create_text(W // 2, TIME_Y, text="00:00:00", fill=ORANGE,
                                      font=(FONT, 56, "bold"))
        # progress bar
        self.bar_x1, self.bar_x2, self.bar_y = 30, W - 30, 132
        self.track = round_rect(c, self.bar_x1, self.bar_y, self.bar_x2, self.bar_y + 8, 4,
                                fill=TRACK, outline="")
        self.bar = c.create_rectangle(self.bar_x1, self.bar_y, self.bar_x1,
                                      self.bar_y + 8, fill=ORANGE, outline="")

        # ---- scroll picker (setup mode)
        ui = ("setup_ui",)
        self.sign_txt = c.create_text(self.SIGN_X, TIME_Y, text="+", fill=ORANGE,
                                      font=(FONT, 30, "bold"), tags=("btn", "sign") + ui)
        c.tag_bind("sign", "<ButtonRelease-1>", lambda e: self.flip_sign())
        self.cur, self.up, self.down, self.under = [], [], [], []
        for i, cx in enumerate(self.COLS_X):
            tags = ("btn", "wheel", f"wheel{i}") + ui
            c.create_rectangle(cx - 40, 38, cx + 40, 132, fill=BG, outline="", tags=tags)
            self.up.append(c.create_text(cx, 50, text="", fill=DIM, font=(FONT, 14), tags=tags))
            self.cur.append(c.create_text(cx, TIME_Y, text="00", fill=ORANGE,
                                          font=(FONT, 30, "bold"), tags=tags))
            self.down.append(c.create_text(cx, 118, text="", fill=DIM, font=(FONT, 14), tags=tags))
            self.under.append(c.create_line(cx - 30, 104, cx + 30, 104, fill=TRACK,
                                            width=3, tags=ui))
            c.tag_bind(f"wheel{i}", "<ButtonRelease-1>", lambda e, i=i: self._wheel_click(i, e))
        for x in ((self.COLS_X[0] + self.COLS_X[1]) // 2, (self.COLS_X[1] + self.COLS_X[2]) // 2):
            c.create_text(x, TIME_Y - 2, text=":", fill=DIM, font=(FONT, 26, "bold"), tags=ui)
        self.hint = c.create_text(W // 2, 140, fill=DIM, font=(FONT, 9), tags=ui,
                                  text="scroll to set  -  Shift = x10  -  Enter = start")

        # buttons
        bw, bh, gap = 62, 36, 9
        x0 = (W - (5 * bw + 4 * gap)) // 2 + bw // 2
        y = 176
        specs = [("play", self.toggle), ("stop", self.stop), ("restart", self.restart),
                 ("set", self.edit), ("add60", self.add60)]
        for i, (name, cmd) in enumerate(specs):
            self._add_button(name, x0 + i * (bw + gap), y, bw, bh, cmd)
        self._add_button("p60", W - 44, TIME_Y, 54, 30, self.preset60, extra_tags=ui)

        # menu + bindings
        self.menu = tk.Menu(r, tearoff=0, bg=BG, fg=ORANGE,
                            activebackground=ORANGE, activeforeground=BG)
        self.menu.add_command(label="Set new time", command=self.edit)
        self.menu.add_command(label="Add 60 hours", command=self.add60)
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=r.destroy)
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        c.bind("<Button-2>", self._popup)
        c.bind("<Button-3>", self._popup)
        r.bind("<Key>", self._key)
        r.bind("<MouseWheel>", self._wheel)      # Windows / macOS
        r.bind("<Button-4>", self._wheel)        # Linux
        r.bind("<Button-5>", self._wheel)

        self.edit()                      # first thing: ask for the time
        self.tick()

    # -------------------------------------------------------------- properties
    @property
    def start_value(self):
        return self.base_start + self.extra

    # ------------------------------------------------------------ buttons
    def _add_button(self, name, cx, cy, w, h, command, extra_tags=()):
        c = self.c
        self.commands[name] = command
        self.centers[name] = (cx, cy)
        self._xtags = tuple(extra_tags)
        tags = ("btn", f"btn_{name}") + self._xtags
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
        xt = ("setup_ui",) if name == "p60" else ()
        tags = ("btn", f"btn_{name}", f"{name}_icon") + xt
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
        else:
            label = {"set": "SET", "add60": "+60h", "p60": "60h"}[kind]
            size = 11 if kind != "set" else 12
            c.create_text(cx, cy, text=label, fill=col, font=(FONT, size, "bold"), tags=tags)

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
        k = e.keysym.lower()
        shift = bool(e.state & 0x1)
        if self.mode == "setup":
            if k == "up":
                self.bump(self.sel, 10 if shift else 1)
            elif k == "down":
                self.bump(self.sel, -10 if shift else -1)
            elif k == "left":
                self.sel = max(0, self.sel - 1)
            elif k == "right":
                self.sel = min(2, self.sel + 1)
            elif k in ("minus", "kp_subtract", "plus", "kp_add"):
                self.flip_sign()
            elif k in ("return", "kp_enter"):
                self.confirm()
            elif k == "escape":
                self.cancel()
        else:
            if k == "space":
                self.toggle()
            elif k == "s":
                self.stop()
            elif k == "r":
                self.restart()
            elif k == "e":
                self.edit()
            elif k == "a":
                self.add60()
        self.refresh()

    # ------------------------------------------------------------ picker
    def _load_fields(self, seconds):
        self.neg = seconds < 0
        a = abs(seconds)
        h, rem = divmod(a, 3600)
        m, s = divmod(rem, 60)
        self.fields = [min(h, MAX_HOURS), m, s]
        self.sel = 0

    def _fields_seconds(self):
        h, m, s = self.fields
        total = h * 3600 + m * 60 + s
        return -total if self.neg else total

    def bump(self, i, delta):
        if i == 0:
            self.fields[0] = max(0, min(MAX_HOURS, self.fields[0] + delta))
        else:
            self.fields[i] = (self.fields[i] + delta) % 60
        self.sel = i

    def flip_sign(self):
        if self.mode == "setup":
            self.neg = not self.neg
            self.refresh()

    def preset60(self):
        if self.mode == "setup":
            self.fields = [60, 0, 0]
            self.neg = False
            self.sel = 0

    def _wheel(self, e):
        if self.mode != "setup":
            return
        up = getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0
        step = 10 if (e.state & 0x1) else 1
        x = e.x_root - self.c.winfo_rootx()
        i = min(range(3), key=lambda k: abs(self.COLS_X[k] - x))
        self.bump(i, step if up else -step)
        self.refresh()

    def _wheel_click(self, i, e):
        if self.mode != "setup":
            return
        if e.y < TIME_Y - 20:
            self.bump(i, 1)
        elif e.y > TIME_Y + 20:
            self.bump(i, -1)
        else:
            self.sel = i
        self.refresh()

    def _draw_setup(self):
        c = self.c
        c.itemconfig(self.sign_txt, text="-" if self.neg else "+", fill=RED if self.neg else ORANGE)
        for i in range(3):
            v = self.fields[i]
            width = 3 if i == 0 else 2
            c.itemconfig(self.cur[i], text=f"{v:0{width}d}", fill=RED if self.neg else ORANGE)
            if i == 0:
                up = f"{v + 1:03d}" if v < MAX_HOURS else ""
                dn = f"{v - 1:03d}" if v > 0 else ""
            else:
                up, dn = f"{(v + 1) % 60:02d}", f"{(v - 1) % 60:02d}"
            c.itemconfig(self.up[i], text=up)
            c.itemconfig(self.down[i], text=dn)
            c.itemconfig(self.under[i], fill=(RED if self.neg else ORANGE) if i == self.sel else TRACK)

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
        if self.mode == "setup":
            self.confirm()                      # the play button starts the timer
        elif self.mode == "running":
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
        self.extra = 0
        self.mode = "stopped"

    def restart(self):
        if self.mode == "setup":
            return
        self.elapsed_before = 0.0
        self.extra = 0
        self._resume()

    def add60(self):
        """+60h onto the current running time - no reset, no restart."""
        if self.mode == "setup" or not self.has_start:
            return
        self.extra += ADD_SECONDS

    def edit(self):
        if self.mode == "setup":
            return
        if self.mode == "running":
            self.pause()
        self.prev_mode = self.mode if self.has_start else None
        self.mode = "setup"
        self._load_fields(self.base_start if self.has_start else 0)
        c = self.c
        c.itemconfig("setup_ui", state="normal")
        for item in (self.time_txt, self.bar, self.track):
            c.itemconfig(item, state="hidden")
        self.root.update_idletasks()
        self.root.focus_force()

    def _leave_setup(self):
        c = self.c
        c.itemconfig("setup_ui", state="hidden")
        for item in (self.time_txt, self.bar, self.track):
            c.itemconfig(item, state="normal")
        self.root.focus_set()

    def confirm(self):
        if self.mode != "setup":
            return
        self.base_start = self._fields_seconds()
        self.extra = 0
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
        if self.has_start and self.mode != "setup":
            lbl = f"START {fmt(self.base_start)}"
            if self.extra:
                lbl += f"  +{self.extra // 3600}h"
            c.itemconfig(self.start_lbl, text=lbl)
        else:
            c.itemconfig(self.start_lbl, text="")

        if self.mode == "setup":
            self._draw_setup()
        else:
            label = fmt(v)
            c.itemconfig(self.time_txt, text=label, fill=RED if over else ORANGE,
                         font=(FONT, self._fit(label), "bold"))
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
