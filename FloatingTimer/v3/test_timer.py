import time
import unittest

import floating_timer as ft


class Logic(unittest.TestCase):
    def test_parse(self):
        cases = {"-0:05:00": -300, "1:30:00": 5400, "90:00": 5400, "-45": -45,
                 "0": 0, "+2:00": 120, "100:00:00": 360000, "1": 1}
        for text, want in cases.items():
            self.assertEqual(ft.parse(text), want, text)

    def test_parse_bad(self):
        for bad in ["", "abc", "1:2:3:4", "1::2", "-", "1.5", "12:xx"]:
            with self.assertRaises(ValueError, msg=bad):
                ft.parse(bad)

    def test_fmt(self):
        self.assertEqual(ft.fmt(0), "00:00:00")
        self.assertEqual(ft.fmt(-1), "-00:00:01")
        self.assertEqual(ft.fmt(-360), "-00:06:00")
        self.assertEqual(ft.fmt(90061), "25:01:01")
        self.assertEqual(ft.fmt(60 * 3600), "60:00:00")
        self.assertNotIn("M", ft.fmt(43200))

    def test_always_decreasing(self):
        s = ft.parse("1")
        self.assertEqual([ft.fmt(ft.value_at(s, t)) for t in (0, 0.9, 1, 2, 3)],
                         ["00:00:01", "00:00:01", "00:00:00", "-00:00:01", "-00:00:02"])
        s = ft.parse("-3")
        self.assertEqual([ft.fmt(ft.value_at(s, t)) for t in (0, 1, 2, 3)],
                         ["-00:00:03", "-00:00:04", "-00:00:05", "-00:00:06"])


class GUI(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.app = ft.FloatingTimer(clock=lambda: self.now[0])
        self.root = self.app.root
        self.root.update()

    def tearDown(self):
        if self.app._job:
            self.root.after_cancel(self.app._job)
        self.root.destroy()

    # helpers
    def text(self):
        return self.app.c.itemcget(self.app.time_txt, "text")

    def color(self):
        return self.app.c.itemcget(self.app.time_txt, "fill")

    def start_label(self):
        return self.app.c.itemcget(self.app.start_lbl, "text")

    def enter(self, t):
        """Put a time into the picker and start (like scrolling + pressing play)."""
        if self.app.mode != "setup":
            self.app.edit()
        self.app._load_fields(ft.parse(t))
        self.app.confirm()
        self.root.update()

    def advance(self, s):
        self.now[0] += s
        self.app.refresh()
        self.root.update()

    def click(self, name):
        cx, cy = self.app.centers[name]
        self.app.c.event_generate("<Motion>", x=cx, y=cy)
        self.app.c.event_generate("<ButtonPress-1>", x=cx, y=cy)
        self.app.c.event_generate("<ButtonRelease-1>", x=cx, y=cy)
        self.root.update()

    def scroll(self, col, up=True, shift=False):
        x = self.app.COLS_X[col]
        kw = dict(x=x, y=ft.TIME_Y, state=1 if shift else 0)
        self.app.c.event_generate("<Motion>", x=x, y=ft.TIME_Y)
        self.app.c.event_generate("<Button-4>" if up else "<Button-5>", **kw)
        self.root.update()

    def click_wheel(self, col, dy):
        x = self.app.COLS_X[col]
        y = ft.TIME_Y + dy
        self.app.c.event_generate("<Motion>", x=x, y=y)
        self.app.c.event_generate("<ButtonPress-1>", x=x, y=y)
        self.app.c.event_generate("<ButtonRelease-1>", x=x, y=y)
        self.root.update()

    def key(self, k, state=0):
        self.root.event_generate("<Key>", keysym=k, state=state)
        self.root.update()

    # window basics
    def test_window_flags(self):
        self.assertTrue(self.root.overrideredirect())
        self.assertTrue(self.root.attributes("-topmost"))

    def test_no_typing_entry(self):
        import tkinter as tk
        def walk(w):
            yield w
            for ch in w.winfo_children():
                yield from walk(ch)
        self.assertFalse([w for w in walk(self.root) if isinstance(w, (tk.Entry, tk.Spinbox))])

    def test_starts_in_setup_with_picker_visible(self):
        self.assertEqual(self.app.mode, "setup")
        self.assertEqual(self.app.c.itemcget(self.app.cur[0], "state"), "normal")
        self.assertEqual(self.app.c.itemcget(self.app.time_txt, "state"), "hidden")

    # picker
    def test_wheel_scroll_each_column(self):
        for _ in range(3):
            self.scroll(0)
        self.assertEqual(self.app.fields, [3, 0, 0])
        for _ in range(5):
            self.scroll(1)
        self.assertEqual(self.app.fields, [3, 5, 0])
        self.scroll(2, up=False)
        self.assertEqual(self.app.fields, [3, 5, 59])        # seconds wrap
        self.scroll(0, up=False); self.scroll(0, up=False); self.scroll(0, up=False)
        self.scroll(0, up=False)
        self.assertEqual(self.app.fields[0], 0)               # hours stop at 0

    def test_shift_wheel_steps_by_ten(self):
        self.scroll(0, shift=True)
        self.scroll(0, shift=True)
        self.assertEqual(self.app.fields[0], 20)

    def test_click_small_values_above_and_below(self):
        self.click_wheel(1, -34)       # value above = +1
        self.click_wheel(1, -34)
        self.assertEqual(self.app.fields[1], 2)
        self.click_wheel(1, +34)       # value below = -1
        self.assertEqual(self.app.fields[1], 1)

    def test_sign_toggle_makes_negative_start(self):
        self.scroll(1); self.scroll(1); self.scroll(1)        # 3 minutes
        cx = self.app.SIGN_X
        for ev in ("<Motion>", "<ButtonPress-1>", "<ButtonRelease-1>"):
            self.app.c.event_generate(ev, x=cx, y=ft.TIME_Y)
        self.root.update()
        self.assertTrue(self.app.neg)
        self.click("play")
        self.assertEqual(self.text(), "-00:03:00")
        self.assertEqual(self.color(), ft.RED)
        self.advance(60)
        self.assertEqual(self.text(), "-00:04:00")

    def test_60h_chip_and_play_starts(self):
        self.click("p60")
        self.assertEqual(self.app.fields, [60, 0, 0])
        self.click("play")                                    # play = start
        self.assertEqual(self.app.mode, "running")
        self.assertEqual(self.text(), "60:00:00")
        self.advance(1)
        self.assertEqual(self.text(), "59:59:59")

    def test_picker_keyboard(self):
        self.key("Up"); self.key("Up")
        self.assertEqual(self.app.fields[0], 2)
        self.key("Right"); self.key("Up", state=1)
        self.assertEqual(self.app.fields[1], 10)
        self.key("Down", state=1)
        self.assertEqual(self.app.fields[1], 0)
        self.key("minus")
        self.assertTrue(self.app.neg)
        self.key("Return")
        self.assertEqual(self.app.mode, "running")
        self.assertEqual(self.text(), "-02:00:00")

    def test_escape_cancels_only_when_a_time_exists(self):
        self.key("Escape")
        self.assertEqual(self.app.mode, "setup")              # nothing to go back to
        self.enter("1:00")
        self.click("set")
        self.key("Escape")
        self.assertEqual(self.app.mode, "paused")

    def test_set_prefills_current_start(self):
        self.enter("-1:30:00")
        self.click("set")
        self.assertEqual(self.app.fields, [1, 30, 0])
        self.assertTrue(self.app.neg)

    # counting
    def test_one_second_goes_zero_then_negative(self):
        self.enter("1")
        self.assertEqual(self.text(), "00:00:01")
        self.advance(1);  self.assertEqual(self.text(), "00:00:00")
        self.advance(1);  self.assertEqual(self.text(), "-00:00:01")
        self.assertEqual(self.color(), ft.RED)

    def test_negative_start_keeps_going_down(self):
        self.enter("-3")
        self.advance(1);  self.assertEqual(self.text(), "-00:00:04")
        self.advance(60); self.assertEqual(self.text(), "-00:01:04")

    # buttons
    def test_pause_play_stop_restart(self):
        self.enter("1:00")
        self.advance(10)
        self.assertEqual(self.text(), "00:00:50")
        self.click("play")
        self.assertEqual(self.app.mode, "paused")
        self.advance(100)
        self.assertEqual(self.text(), "00:00:50")
        self.click("play")
        self.advance(5)
        self.assertEqual(self.text(), "00:00:45")
        self.click("stop")
        self.assertEqual(self.text(), "00:01:00")
        self.advance(30)
        self.assertEqual(self.text(), "00:01:00")
        self.click("play")
        self.advance(4)
        self.assertEqual(self.text(), "00:00:56")
        self.click("restart")
        self.assertEqual(self.text(), "00:01:00")
        self.assertEqual(self.app.mode, "running")

    # +60h
    def test_add60_while_running_adds_sixty_hours_no_reset(self):
        self.enter("1:00:00")
        self.advance(2 * 3600)
        self.assertEqual(self.text(), "-01:00:00")
        self.click("add60")
        self.assertEqual(self.text(), "59:00:00")
        self.assertEqual(self.color(), ft.ORANGE)
        self.assertEqual(self.app.mode, "running")            # still running, not reset
        self.advance(3600)
        self.assertEqual(self.text(), "58:00:00")

    def test_add60_stacks(self):
        self.enter("0:10:00")
        self.advance(60)
        for _ in range(3):
            self.click("add60")
        self.assertEqual(self.text(), "180:09:00")
        self.assertIn("+180h", self.start_label())
        self.advance(60)
        self.assertEqual(self.text(), "180:08:00")

    def test_add60_works_when_paused(self):
        self.enter("1:00")
        self.advance(30)
        self.click("play")
        self.click("add60")
        self.assertEqual(self.app.mode, "paused")
        self.assertEqual(self.text(), "60:00:30")

    def test_add60_with_keyboard_and_menu_command(self):
        self.enter("0:05")
        self.key("a")
        self.assertEqual(self.text(), "60:00:05")
        self.app.menu.invoke(1)
        self.app.refresh()
        self.assertEqual(self.text(), "120:00:05")

    def test_stop_and_restart_drop_the_added_hours(self):
        self.enter("1:00")
        self.click("add60")
        self.assertEqual(self.text(), "60:01:00")
        self.click("stop")
        self.assertEqual(self.text(), "00:01:00")
        self.assertNotIn("+", self.start_label())
        self.click("play"); self.click("add60"); self.click("restart")
        self.assertEqual(self.text(), "00:01:00")

    def test_add60_ignored_while_setting_time(self):
        self.enter("1:00")
        self.click("set")
        self.click("add60")
        self.assertEqual(self.app.extra, 0)

    def test_set_keeps_nothing_old(self):
        self.enter("1:00")
        self.click("add60")
        self.click("set")
        self.enter("0:30")
        self.assertEqual(self.text(), "00:00:30")

    def test_play_icon_switches(self):
        self.enter("1:00")
        self.assertEqual(self.app._play_state, "pause")
        self.click("play")
        self.assertEqual(self.app._play_state, "play")

    def test_long_times_fit_window(self):
        self.enter("-100:00:00")
        x1, y1, x2, y2 = self.app.c.bbox(self.app.time_txt)
        self.assertLessEqual(x2 - x1, ft.W - 20)
        self.click("add60")
        self.click("add60"); self.click("add60")
        x1, y1, x2, y2 = self.app.c.bbox(self.app.time_txt)
        self.assertLessEqual(x2 - x1, ft.W - 20)
        self.assertGreaterEqual(x1, 0)

    def test_real_clock(self):
        app2 = ft.FloatingTimer()
        app2._load_fields(-5)
        app2.confirm()
        end = time.time() + 2.3
        while time.time() < end:
            app2.root.update(); time.sleep(0.05)
        self.assertEqual(app2.c.itemcget(app2.time_txt, "text"), "-00:00:07")
        app2.root.after_cancel(app2._job)
        app2.root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
