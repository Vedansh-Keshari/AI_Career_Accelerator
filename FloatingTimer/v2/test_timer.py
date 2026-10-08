import time
import tkinter as tk
import unittest

import floating_timer as ft


class Logic(unittest.TestCase):
    def test_parse(self):
        cases = {"-0:05:00": -300, "1:30:00": 5400, "90:00": 5400, "-45": -45,
                 "0": 0, "+2:00": 120, " 00:00:10 ": 10, "100:00:00": 360000, "1": 1}
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
        self.assertNotIn("M", ft.fmt(43200))

    def test_always_decreasing_from_one(self):
        s = ft.parse("1")
        out = [ft.fmt(ft.value_at(s, t)) for t in (0, 0.9, 1, 2, 3)]
        self.assertEqual(out, ["00:00:01", "00:00:01", "00:00:00", "-00:00:01", "-00:00:02"])

    def test_negative_start_keeps_going_down(self):
        s = ft.parse("-3")
        out = [ft.fmt(ft.value_at(s, t)) for t in (0, 1, 2, 3)]
        self.assertEqual(out, ["-00:00:03", "-00:00:04", "-00:00:05", "-00:00:06"])
        self.assertEqual(ft.fmt(ft.value_at(ft.parse("-5:00"), 60)), "-00:06:00")

    def test_positive_counts_down_through_zero(self):
        s = ft.parse("1:00:00")
        self.assertEqual(ft.fmt(ft.value_at(s, 1)), "00:59:59")
        self.assertEqual(ft.fmt(ft.value_at(s, 3600)), "00:00:00")
        self.assertEqual(ft.fmt(ft.value_at(s, 3601)), "-00:00:01")

    def test_zero_start_goes_negative(self):
        self.assertEqual(ft.fmt(ft.value_at(0, 5)), "-00:00:05")


class GUI(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.app = ft.FloatingTimer(clock=lambda: self.now[0])
        self.root = self.app.root
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def text(self):
        return self.app.c.itemcget(self.app.time_txt, "text")

    def color(self):
        return self.app.c.itemcget(self.app.time_txt, "fill")

    def enter(self, t):
        self.app.entry.delete(0, "end")
        self.app.entry.insert(0, t)
        self.app.entry.event_generate("<Return>")
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

    def test_window_flags(self):
        self.assertTrue(self.root.overrideredirect())
        self.assertTrue(self.root.attributes("-topmost"))

    def test_starts_in_setup(self):
        self.assertEqual(self.app.mode, "setup")
        self.assertEqual(self.app.c.itemcget(self.app.entry_win, "state"), "normal")

    def test_one_second_goes_zero_then_negative(self):
        self.enter("1")
        self.assertEqual(self.text(), "00:00:01")
        self.advance(1);  self.assertEqual(self.text(), "00:00:00")
        self.advance(1);  self.assertEqual(self.text(), "-00:00:01")
        self.assertEqual(self.color(), ft.RED)
        self.advance(1);  self.assertEqual(self.text(), "-00:00:02")

    def test_negative_start(self):
        self.enter("-3")
        self.assertEqual(self.text(), "-00:00:03")
        self.advance(1);  self.assertEqual(self.text(), "-00:00:04")
        self.advance(1);  self.assertEqual(self.text(), "-00:00:05")
        self.advance(60); self.assertEqual(self.text(), "-00:01:05")

    def test_positive_is_orange_negative_is_red(self):
        self.enter("0:05")
        self.assertEqual(self.color(), ft.ORANGE)
        self.advance(6)
        self.assertEqual(self.color(), ft.RED)

    def test_pause_play(self):
        self.enter("1:00")
        self.advance(10)
        self.assertEqual(self.text(), "00:00:50")
        self.click("play")                      # pause
        self.assertEqual(self.app.mode, "paused")
        self.advance(100)
        self.assertEqual(self.text(), "00:00:50")   # frozen
        self.click("play")                      # resume
        self.assertEqual(self.app.mode, "running")
        self.advance(5)
        self.assertEqual(self.text(), "00:00:45")

    def test_stop_resets_and_waits(self):
        self.enter("1:00")
        self.advance(20)
        self.click("stop")
        self.assertEqual(self.app.mode, "stopped")
        self.assertEqual(self.text(), "00:01:00")
        self.advance(30)
        self.assertEqual(self.text(), "00:01:00")    # not running
        self.click("play")                          # play from the start again
        self.advance(4)
        self.assertEqual(self.text(), "00:00:56")

    def test_restart(self):
        self.enter("0:30")
        self.advance(12)
        self.click("restart")
        self.assertEqual(self.app.mode, "running")
        self.assertEqual(self.text(), "00:00:30")
        self.advance(2)
        self.assertEqual(self.text(), "00:00:28")

    def test_restart_from_paused_and_overtime(self):
        self.enter("0:05")
        self.advance(9)
        self.click("play")                          # pause in overtime
        self.assertEqual(self.text(), "-00:00:04")
        self.click("restart")
        self.assertEqual(self.text(), "00:00:05")
        self.assertEqual(self.color(), ft.ORANGE)

    def test_set_button_and_cancel(self):
        self.enter("1:00")
        self.advance(10)
        self.click("set")
        self.assertEqual(self.app.mode, "setup")
        self.advance(50)                            # timer held while editing
        self.app.entry.event_generate("<Escape>")
        self.root.update()
        self.assertEqual(self.app.mode, "paused")
        self.assertEqual(self.text(), "00:00:50")

    def test_set_new_time(self):
        self.enter("1:00")
        self.click("set")
        self.enter("-10")
        self.assertEqual(self.app.mode, "running")
        self.assertEqual(self.text(), "-00:00:10")
        self.advance(1)
        self.assertEqual(self.text(), "-00:00:11")

    def test_invalid_input(self):
        self.enter("nope")
        self.assertEqual(self.app.mode, "setup")
        self.assertEqual(str(self.app.entry.cget("highlightbackground")), ft.RED)

    def test_keyboard_shortcuts(self):
        self.enter("1:00")
        self.root.update()
        for key, mode in [("space", "paused"), ("space", "running"),
                          ("s", "stopped"), ("r", "running")]:
            self.root.event_generate("<Key>", keysym=key)
            self.root.update()
            self.assertEqual(self.app.mode, mode, key)

    def test_typing_in_entry_does_not_trigger_shortcuts(self):
        self.app.entry.focus_set()
        self.app.entry.event_generate("<Key>", keysym="r")
        self.app.entry.event_generate("<Key>", keysym="space")
        self.root.update()
        self.assertEqual(self.app.mode, "setup")

    def test_play_icon_switches(self):
        self.enter("1:00")
        self.root.update()
        self.assertEqual(self.app._play_state, "pause")
        self.click("play")
        self.assertEqual(self.app._play_state, "play")

    def test_real_clock(self):
        app2 = ft.FloatingTimer()
        app2.entry.insert(0, "-0:05")
        app2.confirm()
        end = time.time() + 2.3
        while time.time() < end:
            app2.root.update(); time.sleep(0.05)
        self.assertEqual(app2.c.itemcget(app2.time_txt, "text"), "-00:00:07")
        app2.root.destroy()



class Fit(unittest.TestCase):
    def test_long_times_fit_window(self):
        import tkinter.font as tkfont
        app = ft.FloatingTimer(clock=lambda: 0.0)
        app.entry.insert(0, "-100:00:00"); app.confirm(); app.root.update()
        x1, y1, x2, y2 = app.c.bbox(app.time_txt)
        self.assertLessEqual(x2 - x1, ft.W - 20)
        self.assertGreaterEqual(x1, 0)
        app.root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
