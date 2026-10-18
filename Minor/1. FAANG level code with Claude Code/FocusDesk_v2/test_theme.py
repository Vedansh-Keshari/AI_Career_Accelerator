import theme


def test_esc_neutralises_html_and_dollars():
    out = theme.esc('<script>alert("x")</script> & $5 $10')
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert "&amp;" in out and "$" not in out and "&#36;5" in out


def test_task_card_escapes_title_and_shows_chips():
    task = {"title": "<b>bold</b> $9", "priority": "High", "due": "2026-10-20",
            "done": False, "completed": None}
    html = theme.task_card(task, overdue=False)
    assert "<b>bold</b>" not in html and "&lt;b&gt;bold&lt;/b&gt;" in html
    assert "fd-task high open" in html and "due 2026-10-20" in html and "overdue" not in html
    assert "overdue" in theme.task_card(task, overdue=True)


def test_done_task_card():
    task = {"title": "x", "priority": "Low", "due": None, "done": True, "completed": "2026-10-17"}
    html = theme.task_card(task)
    assert "fd-task low done" in html and "done 2026-10-17" in html


def test_metric_card_and_banner():
    card = theme.metric_card("Open tasks", 8, theme.CARD_BLUE, "📝")
    assert "Open tasks" in card and ">8<" in card and theme.BLUE in card
    assert "<img" not in theme.banner("<img>", "sub") and "FocusDesk" in theme.banner("FocusDesk", "s")


def test_priority_bar_percentages():
    assert "width:100%" in theme.priority_bar("High", 4, 4, "#fff")
    assert "width:50%" in theme.priority_bar("Low", 2, 4, "#fff")
    assert "width:0%" in theme.priority_bar("Low", 0, 0, "#fff")


def test_every_priority_has_a_colour_style():
    import logic
    assert set(theme.PRIORITY_STYLE) == set(logic.PRIORITIES)


def test_user_chip_escapes_email():
    assert "&lt;" in theme.user_chip("a<b>@x.com") and "<b>" not in theme.user_chip("a<b>@x.com")
