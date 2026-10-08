"""
Floating Timer
--------------
- Frameless, always-on-top, dark (black / orange / red).
- Type a start time and press Enter. It runs from there like a clock.
- Positive start counts up:   01:00:00 -> 01:00:01 -> ...
- Negative start goes further negative:  -00:05:00 -> -00:05:01 -> ... -00:06:00
- Hours never wrap at 24 and no AM/PM is ever shown.
- No buttons. Drag anywhere to move. Right-click for "Set new time" / "Quit".

Accepted input:  H:M:S   M:S   S   (optional leading - or +)
Examples:        -0:05:00   1:30:00   90:00   -45   0
"""
import time
import tkinter as tk

BG = "#000000"
ORANGE = "#ff8c00"
RED = "#ff2a2a"
DIM = "#6b3a00"
FONT = ("Consolas", 46, "bold")
SMALL = ("Consolas", 10)


def parse(text):
    """'-0:05:00' -> -300. Raises ValueError on bad input."""
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
    """Magnitude always grows: a negative start keeps getting more negative."""
    direction = -1 if start < 0 else 1
    return start + direction * int(elapsed)


class FloatingTimer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.root = tk.Tk()
        r = self.root
        r.title("Timer")
        r.overrideredirect(True)          # no title bar / close button
        r.attributes("-topmost", True)    # float above other windows
        try:
            r.attributes("-alpha", 0.94)
        except tk.TclError:
            pass
        r.configure(bg=BG, highlightthickness=2, highlightbackground=ORANGE)
        r.geometry("360x120+120+120")

        self.label = tk.Label(r, text="", font=FONT, bg=BG, fg=ORANGE)
        self.hint = tk.Label(r, text="", font=SMALL, bg=BG, fg=DIM)
        self.entry = tk.Entry(
            r, font=("Consolas", 30, "bold"), justify="center", bg=BG, fg=ORANGE,
            insertbackground=ORANGE, relief="flat", highlightthickness=1,
            highlightbackground=DIM, highlightcolor=ORANGE, width=10,
        )
        self.entry.bind("<Return>", self.start)

        self.menu = tk.Menu(r, tearoff=0, bg=BG, fg=ORANGE,
                            activebackground=ORANGE, activeforeground=BG)
        self.menu.add_command(label="Set new time", command=self.ask)
        self.menu.add_separator()
        self.menu.add_command(label="Quit", command=r.destroy)

        for w in (r, self.label, self.hint):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)
            w.bind("<Button-2>", self._popup)
            w.bind("<Button-3>", self._popup)

        self.start_value = 0
        self.t0 = 0.0
        self.running = False
        self._job = None
        self.ask()

    # ---- dragging / menu
    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _popup(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    # ---- modes
    def ask(self):
        self.running = False
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        self.label.pack_forget()
        self.hint.config(text="e.g. -0:05:00 or 1:30:00  ·  Enter")
        self.entry.delete(0, "end")
        self.entry.config(highlightbackground=DIM)
        self.hint.pack(side="bottom", pady=(0, 8))
        self.entry.pack(expand=True)
        self.root.update_idletasks()
        self.root.focus_force()
        self.entry.focus_set()

    def start(self, _=None):
        try:
            self.start_value = parse(self.entry.get())
        except ValueError:
            self.entry.config(highlightbackground=RED)
            self.entry.delete(0, "end")
            return
        self.entry.pack_forget()
        self.hint.pack_forget()
        self.label.pack(expand=True)
        self.t0 = self.clock()
        self.running = True
        self.tick()

    def tick(self):
        if not self.running:
            return
        if self._job:
            self.root.after_cancel(self._job)
        value = value_at(self.start_value, self.clock() - self.t0)
        self.label.config(text=fmt(value), fg=RED if value < 0 else ORANGE)
        self._job = self.root.after(100, self.tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FloatingTimer().run()
