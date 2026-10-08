import unittest, tkinter as tk
import floating_timer as ft


class Logic(unittest.TestCase):
    def test_parse(self):
        cases = {"-0:05:00": -300, "1:30:00": 5400, "90:00": 5400, "-45": -45,
                 "0": 0, "+2:00": 120, " 00:00:10 ": 10, "100:00:00": 360000}
        for text, want in cases.items():
            self.assertEqual(ft.parse(text), want, text)

    def test_parse_bad(self):
        for bad in ["", "abc", "1:2:3:4", "1::2", "-", "1.5", "12:xx"]:
            with self.assertRaises(ValueError, msg=bad):
                ft.parse(bad)

    def test_fmt(self):
        self.assertEqual(ft.fmt(0), "00:00:00")
        self.assertEqual(ft.fmt(-300), "-00:05:00")
        self.assertEqual(ft.fmt(-360), "-00:06:00")
        self.assertEqual(ft.fmt(90061), "25:01:01")          # no 24h wrap
        self.assertNotIn("M", ft.fmt(43200))                 # no AM/PM

    def test_negative_keeps_growing(self):
        s = ft.parse("-5:00")
        self.assertEqual(ft.fmt(ft.value_at(s, 0)), "-00:05:00")
        self.assertEqual(ft.fmt(ft.value_at(s, 0.9)), "-00:05:00")
        self.assertEqual(ft.fmt(ft.value_at(s, 1)), "-00:05:01")
        self.assertEqual(ft.fmt(ft.value_at(s, 60)), "-00:06:00")   # the bug fix
        self.assertEqual(ft.fmt(ft.value_at(s, 3600)), "-01:05:00")

    def test_positive_counts_up(self):
        s = ft.parse("1:00:00")
        self.assertEqual(ft.fmt(ft.value_at(s, 61)), "01:01:01")
        self.assertEqual(ft.fmt(ft.value_at(ft.parse("23:59:59"), 1)), "24:00:00")

    def test_zero_start_counts_up(self):
        self.assertEqual(ft.fmt(ft.value_at(0, 5)), "00:00:05")


class GUI(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.app = ft.FloatingTimer(clock=lambda: self.now[0])
        self.root = self.app.root
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def enter(self, text):
        self.app.entry.delete(0, "end")
        self.app.entry.insert(0, text)
        self.app.entry.event_generate("<Return>")
        self.root.update()

    def advance(self, secs):
        self.now[0] += secs
        self.app.tick()
        self.root.update()

    def test_window_is_frameless_topmost(self):
        self.assertTrue(self.root.overrideredirect())
        self.assertTrue(self.root.attributes("-topmost"))

    def test_no_buttons(self):
        def walk(w):
            yield w
            for c in w.winfo_children():
                yield from walk(c)
        self.assertFalse([w for w in walk(self.root) if isinstance(w, tk.Button)])

    def test_negative_flow_and_colors(self):
        self.enter("-5:00")
        self.assertEqual(self.app.label.cget("text"), "-00:05:00")
        self.assertEqual(self.app.label.cget("fg"), ft.RED)
        self.advance(60)
        self.assertEqual(self.app.label.cget("text"), "-00:06:00")
        self.assertEqual(self.app.label.cget("fg"), ft.RED)

    def test_positive_flow_and_colors(self):
        self.enter("1:00:00")
        self.advance(3661)
        self.assertEqual(self.app.label.cget("text"), "02:01:01")
        self.assertEqual(self.app.label.cget("fg"), ft.ORANGE)

    def test_invalid_input_stays_on_entry(self):
        self.enter("nope")
        self.assertFalse(self.app.running)
        self.assertEqual(self.app.entry.get(), "")
        self.assertEqual(str(self.app.entry.cget("highlightbackground")), ft.RED)

    def test_reset_via_menu_action(self):
        self.enter("-1:00")
        self.assertTrue(self.app.running)
        self.app.ask()
        self.assertFalse(self.app.running)
        self.enter("0:10")
        self.advance(5)
        self.assertEqual(self.app.label.cget("text"), "00:00:15")

    def test_real_clock_ticks(self):
        import time
        app2 = ft.FloatingTimer()
        app2.entry.insert(0, "-0:05:00")
        app2.start()
        t_end = time.time() + 2.3
        while time.time() < t_end:
            app2.root.update(); time.sleep(0.05)
        self.assertEqual(app2.label.cget("text"), "-00:05:02")
        app2.root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
